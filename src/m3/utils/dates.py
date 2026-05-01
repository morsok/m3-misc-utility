from m3.types import UpcomingIssue

_UNKNOWN: set[str] = {"0000-00-00", "00-00-0000", "", "0", "None", "none"}


def is_unknown(date: str | None) -> bool:
    """Check if a date string represents an unknown date in Mylar."""
    return not date or date.strip() in _UNKNOWN


def any_date_unknown(issue: UpcomingIssue) -> bool:
    """
    Check if an issue has any unknown dates.
    
    If both IssueDate and StoreDate are present in the dictionary, it checks both.
    If only one is present (e.g. getUpcoming API response), it only checks that one.
    Absence of a key in the dictionary is NOT treated as unknown.
    """
    to_check = []
    if "IssueDate" in issue:
        to_check.append(issue.get("IssueDate"))
    if "StoreDate" in issue:
        to_check.append(issue.get("StoreDate"))
    
    if not to_check:
        return False
        
    return any(is_unknown(d) for d in to_check)
