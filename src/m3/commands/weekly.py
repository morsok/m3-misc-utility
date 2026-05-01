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


@click.command("weekly")
@click.pass_context
def weekly(ctx: click.Context) -> None:
    """Refresh this week's unknown-date series, then retag their issues (combined pipeline)."""
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

    # Deduplicated series list for refresh phase
    seen: set[str] = set()
    series_to_refresh: list[UpcomingIssue] = []
    for issue in filtered:
        if issue["ComicID"] not in seen:
            seen.add(issue["ComicID"])
            series_to_refresh.append(issue)

    if not series_to_refresh:
        print_info("No series found with any dates unknown for this week.")
        return

    # Only retag issues that have a valid IssueID and are in 'Downloaded' status
    retag_issues = [i for i in filtered if i.get("IssueID") and i.get("Status") == "Downloaded"]

    n_refresh = len(series_to_refresh)
    n_retag = len(retag_issues)
    used, remaining = limiter.status()
    eta = format_eta(n_refresh + n_retag, cfg.rate_limit)
    print_info(
        f"{n_refresh} series to refresh + {n_retag} issues to retag — "
        f"{used} calls used in last hour, {remaining} remaining — "
        f"estimated time: {eta}"
    )

    # Phase 1: Refresh series
    refresh_status: dict[str, bool] = {}
    with make_progress() as progress:
        task = progress.add_task("Refreshing series…", total=n_refresh)
        for issue in series_to_refresh:
            name = issue.get("ComicName") or issue["ComicID"]
            progress.update(task, description=f"Refreshing {name}…")
            limiter.acquire(console, progress=progress)
            try:
                # WORKAROUND: add_comic on existing series is more stable than refresh_comic (prevents 500 errors)
                ok = client.add_comic(issue["ComicID"], name=name)
            except MylarAPIError:
                ok = False
            refresh_status[issue["ComicID"]] = ok
            progress.advance(task)
        progress.update(task, description="Refreshing series…")

    # Phase 2: Retag issues (same rate-limit window carries over)
    retag_status: dict[str, bool] = {}
    with make_progress() as progress:
        task = progress.add_task("Retagging issues…", total=n_retag)
        for issue in retag_issues:
            issue_id = str(issue.get("IssueID") or "")
            name = f"{issue.get('ComicName')} #{issue.get('IssueNumber')}"
            progress.update(task, description=f"Retagging {name}…")
            limiter.acquire(console, progress=progress)
            try:
                ok = client.metatag_issue(issue_id, name=name)
            except MylarAPIError:
                ok = False
            retag_status[issue_id] = ok
            progress.advance(task)
        progress.update(task, description="Retagging issues…")

    # Combined summary table — one row per issue
    rows: list[list[str]] = []
    for issue in filtered:
        r_ok = refresh_status.get(issue["ComicID"], False)
        issue_id = issue.get("IssueID")
        issue_status = issue.get("Status")

        if not issue_id:
            t_status = "[dim]Not on CV[/dim]"
        elif issue_status != "Downloaded":
            t_status = "[dim]Not Downloaded[/dim]"
        elif retag_status.get(str(issue_id), False):
            t_status = "[green]OK[/green]"
        else:
            t_status = "[red]FAILED[/red]"

        rows.append(
            [
                issue.get("ComicName") or issue["ComicID"],
                issue.get("IssueNumber") or "?",
                "[green]OK[/green]" if r_ok else "[dim]skipped[/dim]",
                t_status,
            ]
        )

    print_table("Weekly Summary", ["Series", "Issue #", "Refreshed", "Retagged"], rows)
