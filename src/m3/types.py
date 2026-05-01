from typing import NotRequired, TypedDict


class UpcomingIssue(TypedDict):
    # Confirmed field names from live getUpcoming response
    ComicID: str
    IssueID: NotRequired[str | None]  # can be null when issue not yet in DB
    ComicName: NotRequired[str]
    DisplayComicName: NotRequired[str]
    IssueNumber: NotRequired[str]  # actual field name (not IssueNum)
    # Date is YYYY-MM-DD; "0000-00-00" means unknown
    IssueDate: NotRequired[str]
    # StoreDate is not present in getUpcoming — only IssueDate
    StoreDate: NotRequired[str]
    Status: NotRequired[str]


class ComicIndex(TypedDict):
    # getIndex uses lowercase "id" and "name" (ComicVine-sourced field names)
    id: str
    name: NotRequired[str]
    year: NotRequired[str | int]
    status: NotRequired[str]
    publisher: NotRequired[str]
    publishYear: NotRequired[str]
    latestIssue: NotRequired[str]
    totalIssues: NotRequired[int]
    detailsURL: NotRequired[str]
    imageURL: NotRequired[str]
    alternateSearch: NotRequired[str | None]


class IssueDetail(TypedDict):
    IssueID: str
    ComicID: NotRequired[str]
    Issue_Number: NotRequired[str]
    IssueNum: NotRequired[str]
    IssueDate: NotRequired[str]
    StoreDate: NotRequired[str]
    ReleaseDate: NotRequired[str]
    ComicName: NotRequired[str]
    Status: NotRequired[str]


class ComicDetail(TypedDict):
    ComicID: str
    ComicName: NotRequired[str]
    ComicYear: NotRequired[str | int]
    LatestDate: NotRequired[str]
    Status: NotRequired[str]


class ComicResponse(TypedDict):
    comic: ComicDetail
    issues: list[IssueDetail]
    annuals: NotRequired[list[IssueDetail]]


class HistoryEntry(TypedDict):
    IssueID: NotRequired[str | None]
    ComicID: NotRequired[str]
    ComicName: NotRequired[str]
    Issue_Number: NotRequired[str]
    Title: NotRequired[str]
    DateAdded: NotRequired[str]
    Status: NotRequired[str]
    NZBName: NotRequired[str]
    FolderName: NotRequired[str]


class RateState(TypedDict):
    calls: list[str]


class CliOpts(TypedDict, total=False):
    host: str | None
    port: int | None
    apikey: str | None
    http_root: str | None
    rate: int | None
    verbosity: int
    dry_run: bool
    debug_log: str | None
