import click

from m3.client import MylarAPIError, MylarClient
from m3.config import RATE_LOCK_FILE, RATE_STATE_FILE, get_config
from m3.types import ComicIndex
from m3.utils.display import (
    console,
    format_eta,
    make_progress,
    print_info,
    print_table,
    status_spinner,
)
from m3.utils.rate_limiter import RateLimiter


def _is_2099(comic: ComicIndex) -> bool:
    year = str(comic.get("year") or "")
    return year.strip() == "2099"


@click.command("refresh-2099")
@click.option(
    "--use-refresh",
    is_flag=True,
    help="Use refreshComic instead of addComic (legacy behavior, may cause 500 errors).",
)
@click.pass_context
def refresh_2099(ctx: click.Context, use_refresh: bool) -> None:
    """Refresh series where the year is set to 2099 (Mylar's placeholder for unknown dates)."""
    cfg = get_config(ctx)
    client = MylarClient(cfg)
    limiter = RateLimiter(cfg.rate_limit, RATE_STATE_FILE, RATE_LOCK_FILE)

    with status_spinner("Fetching series index…"):
        index = client.get_index()

    matching = [c for c in index if _is_2099(c)]

    if not matching:
        print_info("No series found with year 2099.")
        return

    used, remaining = limiter.status()
    eta = format_eta(len(matching), cfg.rate_limit)
    
    # Use addComic workaround by default to prevent Mylar 500 errors
    print_info(
        f"{len(matching)} series to refresh — "
        f"{used} calls used in last hour, {remaining} remaining — "
        f"estimated time: {eta}"
    )

    rows: list[list[str]] = []
    with make_progress() as progress:
        task = progress.add_task("Refreshing 2099 series…", total=len(matching))
        for comic in matching:
            name = comic.get("name") or comic["id"]
            progress.update(task, description=f"Refreshing {name}…")
            limiter.acquire(console, progress=progress)
            try:
                # WORKAROUND: addComic is more stable than refreshComic in some Mylar installs
                if use_refresh:
                    ok = client.refresh_comic(comic["id"], name=name)
                else:
                    ok = client.add_comic(comic["id"], name=name)
                status = "[green]OK[/green]" if ok else "[red]FAILED[/red]"
            except MylarAPIError as exc:
                status = f"[red]ERROR: {exc.format_message()}[/red]"
            year = str(comic.get("year") or "2099")
            rows.append([name, year, status])
            progress.advance(task)
        progress.update(task, description="Refreshing 2099 series…")

    print_table("Refreshed 2099 Series", ["Series", "Year", "Status"], rows)
