import json
from pathlib import Path
from typing import Any

import pytest

FIXTURE_DIR = Path(__file__).parent / "fixtures"

@pytest.fixture
def get_upcoming_fixture() -> Any:  # noqa: ANN401
    with open(FIXTURE_DIR / "getUpcoming.json") as f:
        return json.load(f)

@pytest.fixture
def get_index_fixture() -> Any:  # noqa: ANN401
    with open(FIXTURE_DIR / "getIndex.json") as f:
        return json.load(f)

@pytest.fixture
def get_comic_fixture() -> Any:  # noqa: ANN401
    with open(FIXTURE_DIR / "getComic_171675.json") as f:
        return json.load(f)

