# CLAUDE.md — Development Guide for m3

## Stack

- **Python 3.14+** with full type annotations throughout
- **Click** — CLI framework (`src/m3/cli.py`)
- **Requests** — HTTP client (`src/m3/client.py`)
- **Rich** — terminal output (`src/m3/utils/display.py`)
- **filelock** — cross-process locking for rate state
- **python-dotenv** — `.env` loading
- Packaged with **hatchling** + **uv**

## Code Quality

All code must pass with zero errors before a change is considered done:

```bash
uv run pytest                # run functional tests
uv run ruff check .          # linting
uv run ruff format .         # formatting
uv run pyright               # type checking
uv run m3 --dry-run -vvv weekly # verify with full debug logging
```

**MANDATORY:** Always use `--dry-run` when running commands for verification. 

**AUTHENTICATION:**
- **Cloudflare**: If Mylar is behind Cloudflare Access, run `m3 cf-login` and paste the token.
- **Mylar Session**: The `retag` command uses a web route that requires a Mylar session.
    - **Automatic**: Set `MYLAR_USERNAME` and `MYLAR_PASSWORD` in `.env`. The client will automatically log in via `/auth/login` when needed.
    - **Manual**: Run `m3 mylar-login` to authenticate and save a persistent `session` cookie.

**DEBUGGING:** Use `-vvv` to log all API calls and full response bodies to `m3_debug.log`. 
 This file is truncated at the start of each run. 
**NEVER** attempt to read `m3_debug.log` directly (it is too large for context efficiency). Instead, **ALWAYS** ask the user to provide relevant extracts from the log when investigating issues.

**DOCUMENTATION:** Always check if documentation (like README.md or GEMINI.md) needs to be updated when making functional changes.

## Types


- API response shapes live in `src/m3/types.py` as `TypedDict` classes.
- **Never** use bare `dict[str, Any]` in public interfaces — add a new `TypedDict` if a shape is missing.
- All functions must have complete parameter and return type annotations.
- `cast()` from `typing` is acceptable at API boundaries where we trust the server's shape.

## Rate Limiter

Every call to `client.refresh_comic()`, `client.add_comic()`, or `client.metatag_issue()` must go through `RateLimiter.acquire()` **before** the call. Never hit the Mylar API in a tight loop without it. The limiter persists state to `rate_state.json` (in the current directory) and is shared across sessions.

## Mylar API Workarounds

- **Series Refresh**: Commands (`weekly`, `refresh-this-week-unknown`, `refresh-2099`) use `client.add_comic()` by default instead of `client.refresh_comic()`. Calling `addComic` on a series that already exists in Mylar triggers a metadata refresh and is significantly more stable (prevents 500 Internal Server Errors) in many Mylar installations.
- **Issue Retag**: Only issues with `Status == 'Downloaded'` are targeted for retagging to avoid Mylar errors when no local file exists.

## Config

All config flows through the `Config` dataclass in `config.py`. Call `get_config(ctx)` at the top of each command. **Never** read environment variables directly in command files.

## Adding a Command

1. Create `src/m3/commands/<name>.py` with a `@click.command()` function.
2. Import and register it in `src/m3/cli.py` with `main.add_command(...)`.
3. Use `get_config(ctx)` to obtain the `Config` instance.
4. Use `RateLimiter(cfg.rate_limit, RATE_STATE_FILE, RATE_LOCK_FILE)` for any CV-triggering calls.
5. Use helpers from `src/m3/utils/display.py` (`make_progress`, `print_table`, `print_info`).

## Cloudflare Auth

`MylarClient` automatically adds the `CF_Authorization` cookie from `Config.cf_authorization` to every request. The client raises `MylarAuthError` on CF-redirect detection — callers should let this propagate to the user.

## Project Layout

```shell
src/m3/
├── types.py          ← TypedDicts for API responses + CliOpts
├── config.py         ← Config dataclass, load_config(), get_config()
├── client.py         ← MylarClient (API + metatag web route)
├── cli.py            ← Click group + command registration
├── commands/         ← one file per command
└── utils/
    ├── display.py    ← Rich helpers (console, make_progress, print_table…)
    └── rate_limiter.py ← RateLimiter with persistent sliding-window state
```
