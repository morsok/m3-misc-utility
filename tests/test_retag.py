from datetime import UTC, datetime, timedelta

from m3.commands.retag import _filter_history
from m3.types import HistoryEntry


def test_filter_history_deduplication() -> None:
    # Setup history with duplicate IssueIDs

    now = datetime.now(UTC)
    date_now = now.strftime("%Y-%m-%d %H:%M:%S")
    date_old = (now - timedelta(minutes=10)).strftime("%Y-%m-%d %H:%M:%S")
    
    history: list[HistoryEntry] = [
        {
            "IssueID": "123",
            "ComicName": "Test Comic",
            "Issue_Number": "1",
            "DateAdded": date_now,
            "Status": "Downloaded"
        },
        {
            "IssueID": "123",
            "ComicName": "Test Comic",
            "Issue_Number": "1",
            "DateAdded": date_old,
            "Status": "Downloaded"
        },
        {
            "IssueID": "456",
            "ComicName": "Another Comic",
            "Issue_Number": "2",
            "DateAdded": date_now,
            "Status": "Downloaded"
        }
    ]
    
    results = _filter_history(history, days=1)
    
    # Should have 2 unique issues
    assert len(results) == 2
    
    # Check that we kept the newest one for ID 123
    issue_123 = next(r for r in results if r.get("IssueID") == "123")
    assert issue_123.get("DateAdded") == date_now
    
    # Check overall sorting (newest first)
    assert results[0].get("DateAdded") == date_now
    assert results[1].get("DateAdded") == date_now
