from datetime import UTC, datetime, timedelta

import click

from m3.client import MylarClient
from m3.config import RATE_LOCK_FILE, RATE_STATE_FILE, get_config
from m3.types import HistoryEntry
from m3.utils.display import (
    console,
    format_eta,
    make_progress,
    print_info,
    print_table,
    status_spinner,
)
from m3.utils.rate_limiter import RateLimiter

_DATE_FORMATS = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d")


def _parse_date(date_str: str) -> datetime | None:
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(date_str, fmt).replace(tzinfo=UTC)
        except ValueError:
            continue
    return None


def _filter_history(history: list[HistoryEntry], days: int) -> list[HistoryEntry]:
    cutoff = datetime.now(UTC) - timedelta(days=days)
    # Deduplicate by IssueID, keeping the most recent entry
    deduped: dict[str, HistoryEntry] = {}

    for entry in history:
        issue_id = entry.get("IssueID")
        if not issue_id:
            continue

        date_str = entry.get("DateAdded", "") or ""
        dt = _parse_date(date_str)
        if dt and dt >= cutoff:
            existing = deduped.get(issue_id)
            if not existing:
                deduped[issue_id] = entry
            else:
                existing_dt = _parse_date(existing.get("DateAdded", "") or "")
                if existing_dt and dt > existing_dt:
                    deduped[issue_id] = entry

    # Return sorted by DateAdded descending (newest first)
    results = list(deduped.values())
    results.sort(key=lambda x: x.get("DateAdded", "") or "", reverse=True)
    return results


@click.command("retag")
@click.option("--days", "days", type=int, default=None, help="Number of days to look back.")
@click.option("--week", "days", flag_value=7, help="Retag issues from the last 7 days.")
@click.option("--month", "days", flag_value=30, help="Retag issues from the last 30 days.")
@click.pass_context
def retag(ctx: click.Context, days: int | None) -> None:
    """Re-tag issues downloaded within a recent time window."""
    n_days = days if days is not None else 7
    cfg = get_config(ctx)
    client = MylarClient(cfg)
    limiter = RateLimiter(cfg.rate_limit, RATE_STATE_FILE, RATE_LOCK_FILE)

    with status_spinner("Fetching download history…"):
        history = client.get_history()
    candidates = _filter_history(history, n_days)

    if not candidates:
        print_info(f"No issues found downloaded in the last {n_days} day(s).")
        return

    used, remaining = limiter.status()
    eta = format_eta(len(candidates), cfg.rate_limit)
    print_info(
        f"{len(candidates)} issues to retag — "
        f"{used} calls used in last hour, {remaining} remaining — "
        f"estimated time: {eta}"
    )

    rows: list[list[str]] = []
    with make_progress() as progress:
        task = progress.add_task("Retagging issues…", total=len(candidates))
        for entry in candidates:
            issue_id: str = entry.get("IssueID") or ""
            series: str = entry.get("ComicName") or ""
            issue_num: str = entry.get("Issue_Number") or ""
            name = f"{series} #{issue_num}" if series and issue_num else (entry.get("Title") or issue_id)

            progress.update(task, description=f"Retagging {name}…")
            limiter.acquire(console, progress=progress)
            ok = client.metatag_issue(issue_id, name=name)
            rows.append(
                [
                    name,
                    entry.get("DateAdded") or "",
                    "[green]OK[/green]" if ok else "[red]FAILED[/red]",
                ]
            )
            progress.advance(task)
        progress.update(task, description="Retagging issues…")

    print_table(
        f"Retagged Issues (last {n_days} days)",
        ["Title", "Downloaded", "Status"],
        rows,
    )
