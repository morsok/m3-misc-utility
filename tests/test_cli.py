from typing import Any

import requests_mock
from click.testing import CliRunner

from m3.cli import main


def test_weekly_dry_run(get_upcoming_fixture: Any, get_comic_fixture: Any) -> None:  # noqa: ANN401
    runner = CliRunner()

    with requests_mock.Mocker() as m:

        # Mock getUpcoming
        m.get("http://localhost:8090/api?apikey=fake&cmd=getUpcoming", json=get_upcoming_fixture)
        
        # Mock getComic calls
        m.get("http://localhost:8090/api?apikey=fake&cmd=getComic", json=get_comic_fixture)
        
        # Mock addComic (used by weekly for refresh)
        m.get("http://localhost:8090/api?apikey=fake&cmd=addComic", json={"success": True})
        
        # Mock metatag_issue (manual_metatag web route)
        m.get("http://localhost:8090/manual_metatag", text="OK")
        
        # Run weekly command
        result = runner.invoke(main, ["--apikey", "fake", "--dry-run", "weekly"])
        
        if result.exit_code != 0:
            print(result.output)
            if result.exception:
                print(result.exception)
        
        assert result.exit_code == 0
        assert "Verifying issue dates" in result.output
        assert "Weekly Summary" in result.output

def test_refresh_2099_dry_run(get_index_fixture: Any) -> None:  # noqa: ANN401
    runner = CliRunner()
    
    # Modify one entry in the fixture to have year 2099 for the test
    get_index_fixture["data"][0]["year"] = "2099"
    get_index_fixture["data"][0]["name"] = "Test 2099 Series"
    
    with requests_mock.Mocker() as m:
        m.get("http://localhost:8090/api?apikey=fake&cmd=getIndex", json=get_index_fixture)
        m.get("http://localhost:8090/api?apikey=fake&cmd=addComic", json={"success": True})
        
        result = runner.invoke(main, ["--apikey", "fake", "--dry-run", "refresh-2099"])
        
        if result.exit_code != 0:
            print(result.output)
            if result.exception:
                print(result.exception)
            
        assert result.exit_code == 0
        assert "Test 2099 Series" in result.output
