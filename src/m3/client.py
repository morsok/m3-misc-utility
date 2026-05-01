import json
import re
from datetime import datetime
from typing import Any, cast
from urllib.parse import urlencode

import click
from requests import HTTPError, Response, Session

from m3.config import Config
from m3.types import ComicIndex, ComicResponse, HistoryEntry, UpcomingIssue

_CF_HOST_RE = re.compile(r"cloudflareaccess\.com", re.IGNORECASE)
_BODY_PREVIEW_LEN = 2000


class MylarAuthError(click.ClickException):
    pass


class MylarAPIError(click.ClickException):
    pass


def _masked_url(base: str, params: dict[str, Any]) -> str:
    safe = {k: ("****" if k == "apikey" else v) for k, v in params.items()}
    return f"{base}?{urlencode(safe)}"


class MylarClient:
    def __init__(self, config: Config) -> None:
        self._config = config
        self._v = config.verbosity
        self._session = Session()
        if config.cf_authorization:
            self._session.cookies.set("CF_Authorization", config.cf_authorization)
        if config.mylar_session:
            self._session.cookies.set("session", config.mylar_session)

        # Truncate debug log on initialization
        if self._config.debug_log:
            with open(self._config.debug_log, "w") as f:
                f.write(f"--- m3 session started at {datetime.now().isoformat()} ---\n")

    def _debug_log(self, msg: str) -> None:
        if self._config.debug_log:
            with open(self._config.debug_log, "a") as f:
                ts = datetime.now().isoformat()
                f.write(f"[{ts}] {msg}\n")

    def _vprint(self, msg: str, min_level: int = 1) -> None:
        self._debug_log(msg)
        # Level 3 (vvv) means "Quiet terminal, verbose file"
        # So we set display_level to 0 if v >= 3
        display_level = 0 if self._v >= 3 else self._v
        if display_level >= min_level:
            from m3.utils.display import console

            console.print(f"[dim]{msg}[/dim]")

    def _log_response(self, response: Response, display_url: str) -> None:
        size = len(response.content)
        # Summary (level 1)
        self._vprint(f"  → {response.status_code} {response.reason} ({size} bytes)  {display_url}")

        # Details (level 2) - only to file if -vvv
        if self._v >= 2:
            headers = json.dumps(dict(response.headers), indent=2)
            self._debug_log(f"Headers: {headers}")
            for k, v in response.headers.items():
                self._vprint(f"    {k}: {v}", min_level=2)

            body = response.text[:_BODY_PREVIEW_LEN]
            suffix = "…" if len(response.text) > _BODY_PREVIEW_LEN else ""
            self._debug_log(f"Body: {response.text}")
            self._vprint(f"    Body: {body}{suffix}", min_level=2)

    def _check_auth(self, response: Response) -> None:
        # Check for Cloudflare Access
        if response.status_code in (401, 403) and (
            "cf-mitigated" in response.headers or _CF_HOST_RE.search(response.url)
        ):
            raise MylarAuthError("Cloudflare auth required — run `m3 cf-login` to authenticate.")
        
        for r in response.history:
            if _CF_HOST_RE.search(r.headers.get("Location", "")):
                raise MylarAuthError(
                    "Cloudflare auth required — run `m3 cf-login` to authenticate."
                )

        # Check for Mylar Login page (indicated by 'login' in URL or specific body text)
        is_login_url = "/auth/login" in response.url or "/login" in response.url
        has_login_form = "current_username" in response.text and "current_password" in response.text
        
        if is_login_url or (response.status_code == 200 and has_login_form):
            self._vprint("Mylar login page detected. Attempting auto-login...")
            if self._login():
                self._vprint("Auto-login successful.")
            else:
                raise MylarAuthError(
                    "Mylar authentication required. Please set MYLAR_USERNAME and MYLAR_PASSWORD "
                    "in .env or run `m3 mylar-login`."
                )

    def _login(self) -> bool:
        username = self._config.username
        password = self._config.password
        
        if not username or not password:
            self._vprint("No credentials found for auto-login.")
            return False

        login_url = f"{self._config.base_url}/auth/login"
        self._vprint(f"POST {login_url} (username={username})")
        
        try:
            # Hit the login page first to establish a session
            self._session.get(login_url, timeout=10)
            
            # Post credentials with Mylar-specific field names
            # Mylar's login form uses current_username and current_password
            data = {"current_username": username, "current_password": password}
            headers = {"Referer": login_url}
            response = self._session.post(login_url, data=data, headers=headers, timeout=10, allow_redirects=True)
            
            if response.status_code == 200 and "/auth/login" not in response.url:
                # Login successful, update session cookie in config if possible (memory only here)
                cookie = self._session.cookies.get("session")
                if cookie:
                    self._vprint(f"Login successful. Session cookie: {cookie[:8]}...")
                    return True
            
            self._vprint(f"Login failed: status={response.status_code} url={response.url}")
            if response.status_code != 200:
                self._debug_log(f"Login Failure Body: {response.text}")
            return False
        except Exception as exc:
            self._vprint(f"Login error: {exc}")
            return False

    def _get(self, cmd: str, **params: Any) -> Any:  # noqa: ANN401
        if self._config.dry_run and cmd == "refreshComic":
            self._vprint(f"DRY RUN: Faking refreshComic with {params}")
            return {"success": True}

        query: dict[str, Any] = {"apikey": self._config.apikey, "cmd": cmd, **params}
        display_url = _masked_url(self._config.api_url, query)
        self._vprint(f"GET {display_url}")

        response = self._session.get(self._config.api_url, params=query, timeout=30, allow_redirects=True)
        self._check_auth(response)
        self._log_response(response, display_url)

        try:
            response.raise_for_status()
        except HTTPError as exc:
            raise MylarAPIError(f"HTTP {response.status_code} from {display_url}") from exc

        try:
            data: Any = response.json()
        except json.JSONDecodeError as exc:
            body = response.text[:500] if response.text else "(empty)"
            raise MylarAPIError(
                f"cmd={cmd} returned non-JSON (HTTP {response.status_code}). "
                f"Body: {body!r}  —  check host/port/http-root and that the API key is correct."
            ) from exc

        if isinstance(data, dict) and data.get("success") is False:
            raise MylarAPIError(f"Mylar API error for cmd={cmd}: {data}")
        return data

    def get_upcoming(self) -> list[UpcomingIssue]:
        result: Any = self._get("getUpcoming")
        if isinstance(result, dict):
            return cast(list[UpcomingIssue], result.get("data", []))
        return cast(list[UpcomingIssue], result if isinstance(result, list) else [])

    def get_index(self) -> list[ComicIndex]:
        result: Any = self._get("getIndex")
        if isinstance(result, dict):
            return cast(list[ComicIndex], result.get("data", []))
        return cast(list[ComicIndex], result if isinstance(result, list) else [])

    def get_comic(self, comic_id: str) -> ComicResponse:
        return cast(ComicResponse, self._get("getComic", id=comic_id))

    def get_history(self) -> list[HistoryEntry]:
        result: Any = self._get("getHistory")
        if isinstance(result, dict):
            return cast(list[HistoryEntry], result.get("data", []))
        return cast(list[HistoryEntry], result if isinstance(result, list) else [])

    def refresh_comic(self, comic_id: str, name: str | None = None) -> bool:
        display = f"'{name}' ({comic_id})" if name else comic_id
        result: Any = self._get("refreshComic", id=comic_id)
        if isinstance(result, str):
            ok = result.strip().upper() == "OK"
        else:
            ok = isinstance(result, dict) and bool(result.get("success", False))

        if self._config.dry_run:
            self._vprint(f"DRY RUN: Faked refresh for {display}")
        return ok

    def add_comic(self, comic_id: str, name: str | None = None) -> bool:
        display = f"'{name}' ({comic_id})" if name else comic_id
        # Mylar's addComic command
        result: Any = self._get("addComic", id=comic_id)
        if isinstance(result, str):
            ok = result.strip().upper() == "OK"
        else:
            ok = isinstance(result, dict) and bool(result.get("success", False))

        if self._config.dry_run:
            self._vprint(f"DRY RUN: Faked addComic for {display}")
        return ok

    def metatag_issue(self, issue_id: str, name: str | None = None) -> bool:
        display = f"'{name}' ({issue_id})" if name else issue_id
        if self._config.dry_run:
            self._vprint(f"DRY RUN: Faked metatag for {display}")
            return True

        url = f"{self._config.base_url}/manual_metatag"
        params = {"issueid": issue_id}
        self._vprint(f"GET {url}?issueid={issue_id} ({display})")
        
        response = self._session.get(url, params=params, timeout=30, allow_redirects=True)
        try:
            self._check_auth(response)
        except MylarAuthError:
            # If we just logged in, retry once
            self._vprint("Retrying metatag after auto-login...")
            response = self._session.get(url, params=params, timeout=30, allow_redirects=True)
            self._check_auth(response)

        self._log_response(response, f"{url}?issueid={issue_id}")
        return response.status_code == 200
