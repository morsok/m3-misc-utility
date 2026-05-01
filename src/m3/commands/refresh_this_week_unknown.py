import click

from m3.client import MylarAPIError, MylarClient
from m3.config import RATE_LOCK_FILE, RATE_STATE_FILE, get_config
from m3.types import IssueDetail, UpcomingIssue
from m3.utils.display import (
    console,
    format_eta,
    make_progress,
    print_info,
    print_table,
    status_spinner,
)
from m3.utils.rate_limiter import RateLimiter

# Mylar3 uses YYYY-MM-DD; "0000-00-00" means unknown. Legacy "00-00-0000" kept as fallback.
_UNKNOWN: set[str] = {"0000-00-00", "00-00-0000", "", "0", "None", "none"}


def _is_unknown(date: str | None) -> bool:
    return not date or date.strip() in _UNKNOWN


def _any_date_unknown(issue: UpcomingIssue) -> bool:
    issue_date = issue.get("IssueDate")
    store_date = issue.get("StoreDate")
    return _is_unknown(issue_date) or _is_unknown(store_date)


def _get_detailed_issue(client: MylarClient, comic_id: str, issue_num: str) -> IssueDetail | None:
    """Fetch full comic details and find the specific issue to get accurate dates."""
    try:
        resp = client.get_comic(comic_id)
        data = resp.get("data", {})
        # Search in issues and annuals
        issues = data.get("issues", []) + data.get("annuals", [])
        for issue in issues:
            if issue.get("number") == issue_num:
                return issue
    except MylarAPIError:
        pass
    return None


@click.command("refresh-this-week-unknown")
@click.pass_context
def refresh_this_week_unknown(ctx: click.Context) -> None:
    """Refresh series for this week's issues where at least one date is unknown (0000-00-00)."""
    cfg = get_config(ctx)
    client = MylarClient(cfg)
    limiter = RateLimiter(cfg.rate_limit, RATE_STATE_FILE, RATE_LOCK_FILE)

    with status_spinner("Fetching this week's upcoming issues…"):
        upcoming = client.get_upcoming()

    filtered: list[UpcomingIssue] = []
    with make_progress() as progress:
        task = progress.add_task("Verifying issue dates…", total=len(upcoming))
        for issue in upcoming:
            name = issue.get("ComicName") or issue["ComicID"]
            progress.update(task, description=f"Verifying {name}…")

            # Always fetch full details to get accurate releaseDate, issueDate, and Status
            detailed = _get_detailed_issue(client, issue["ComicID"], issue.get("IssueNumber", ""))
            if detailed:
                # API uses releaseDate for store and issueDate for cover
                if rd := detailed.get("releaseDate"):
                    issue["StoreDate"] = str(rd)
                if idt := detailed.get("issueDate"):
                    issue["IssueDate"] = str(idt)
                # Merge status from detailed view (uses lowercase 'status')
                if st := detailed.get("status"):
                    issue["Status"] = str(st)

            if _any_date_unknown(issue):
                filtered.append(issue)
            progress.advance(task)
        progress.update(task, description="Verifying issue dates…")

    seen: set[str] = set()
    series: list[UpcomingIssue] = []
    for issue in filtered:
        if issue["ComicID"] not in seen:
            seen.add(issue["ComicID"])
            series.append(issue)

    if not series:
        print_info("No series found with any dates unknown for this week.")
        return

    used, remaining = limiter.status()
    eta = format_eta(len(series), cfg.rate_limit)
    print_info(
        f"{len(series)} series to refresh — "
        f"{used} calls used in last hour, {remaining} remaining — "
        f"estimated time: {eta}"
    )

    rows: list[list[str]] = []
    with make_progress() as progress:
        task = progress.add_task("Refreshing series…", total=len(series))
        for issue in series:
            name = issue.get("ComicName") or issue["ComicID"]
            progress.update(task, description=f"Refreshing {name}…")
            limiter.acquire(console, progress=progress)
            try:
                # WORKAROUND: add_comic on existing series is more stable than refresh_comic (prevents 500 errors)
                ok = client.add_comic(issue["ComicID"], name=name)
                status = "[green]OK[/green]" if ok else "[red]FAILED[/red]"
            except MylarAPIError as exc:
                status = f"[red]ERROR: {exc.format_message()}[/red]"
            rows.append(
                [
                    name,
                    issue.get("IssueNumber") or "?",
                    issue.get("StoreDate") or "0000-00-00",
                    issue.get("IssueDate") or "0000-00-00",
                    status,
                ]
            )
            progress.advance(task)
        progress.update(task, description="Refreshing series…")

    print_table(
        "Refreshed Series",
        ["Series", "Issue #", "Store Date", "Cover Date", "Status"],
        rows,
    )
