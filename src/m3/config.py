import os
from dataclasses import dataclass
from pathlib import Path

import click
from dotenv import load_dotenv

from m3.types import CliOpts

CONFIG_DIR = Path.home() / ".config" / "m3"
CONFIG_ENV = CONFIG_DIR / ".env"
RATE_STATE_FILE = Path("rate_state.json")
RATE_LOCK_FILE = Path("rate_state.json.lock")

DEFAULT_RATE_LIMIT = 180
MAX_RATE_LIMIT = 200


@dataclass
class Config:
    host: str
    port: int
    apikey: str
    http_root: str
    username: str | None
    password: str | None
    rate_limit: int
    cf_authorization: str | None
    mylar_session: str | None
    verbosity: int = 0
    dry_run: bool = False
    debug_log: str | None = None

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}{self.http_root}"

    @property
    def api_url(self) -> str:
        return f"{self.base_url}/api"


def load_config(opts: CliOpts | None = None) -> Config:
    load_dotenv()
    if CONFIG_ENV.exists():
        load_dotenv(CONFIG_ENV, override=False)

    o = opts or {}

    resolved_host = o.get("host") or os.getenv("MYLAR_HOST", "localhost") or "localhost"
    resolved_port = o.get("port") or int(os.getenv("MYLAR_PORT", "8090"))
    resolved_apikey = o.get("apikey") or os.getenv("MYLAR_APIKEY", "")
    resolved_username = os.getenv("MYLAR_USERNAME") or None
    resolved_password = os.getenv("MYLAR_PASSWORD") or None
    resolved_http_root = o.get("http_root") or os.getenv("MYLAR_HTTP_ROOT", "") or ""
    resolved_rate = o.get("rate") or int(os.getenv("MYLAR_RATE_LIMIT", str(DEFAULT_RATE_LIMIT)))
    cf_authorization = os.getenv("CF_AUTHORIZATION") or None
    mylar_session = os.getenv("MYLAR_SESSION") or None
    verbosity = int(o.get("verbosity") or 0)
    dry_run = bool(o.get("dry_run") or False)
    debug_log = o.get("debug_log")

    if verbosity >= 3 and not debug_log:
        debug_log = "m3_debug.log"

    # In dry-run mode, we use a much higher rate limit (1 call per second)
    if dry_run:
        resolved_rate = 3600

    if not resolved_apikey and not dry_run:
        raise click.UsageError(
            "Mylar API key not configured. Set MYLAR_APIKEY in .env or pass --apikey."
        )

    return Config(
        host=resolved_host,
        port=resolved_port,
        apikey=resolved_apikey,
        http_root=resolved_http_root,
        username=resolved_username,
        password=resolved_password,
        rate_limit=min(int(resolved_rate), 3600 if dry_run else MAX_RATE_LIMIT),
        cf_authorization=cf_authorization,
        mylar_session=mylar_session,
        verbosity=verbosity,
        dry_run=dry_run,
        debug_log=debug_log,
    )


def get_config(ctx: click.Context) -> Config:
    opts: CliOpts = ctx.obj.get("opts", {})
    return load_config(opts)
