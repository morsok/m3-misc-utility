# m3

CLI utilities for [Mylar3](https://github.com/mylar3/mylar3) comic management. Automates common maintenance tasks — refreshing series with placeholder dates, re-tagging recently downloaded issues — while respecting ComicVine's API rate limits across sessions.

## Prerequisites

- Python 3.14+
- [uv](https://docs.astral.sh/uv/) (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- A running Mylar3 instance with the API key enabled (**Settings → Web Interface → Enable API**)

## Installation

```bash
git clone <repo>
cd m3-misc-utility

# Run without installing (development)
uv run m3 --help

# Install globally as `m3`
uv tool install .
```

## Configuration

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

| Variable | Default | Description |
| --- | --- | --- |
| `MYLAR_HOST` | `localhost` | Mylar3 hostname or IP |
| `MYLAR_PORT` | `8090` | Mylar3 port |
| `MYLAR_APIKEY` | *(required)* | API key from Mylar3 settings |
| `MYLAR_HTTP_ROOT` | *(empty)* | URL prefix, e.g. `/mylar` |
| `MYLAR_RATE_LIMIT` | `180` | Max ComicVine calls/hour (hard cap: 200) |
| `CF_AUTHORIZATION` | *(empty)* | Cloudflare Access cookie (see below) |

All variables can also be passed as CLI flags: `--host`, `--port`, `--apikey`, `--http-root`, `--rate`.

### Global Options

| Flag | Description |
| --- | --- |
| `--dry-run` | **Safe testing mode.** Performs real API fetches but fakes all modification requests (`refreshComic`, `metatag`). Overrides rate limit to 3600/hr. |
| `-v`, `--verbose` | **Verbose output.** Use `-v` for request/response summaries, `-vv` to also show full headers and bodies. |

## Cloudflare Access

If your Mylar3 instance is behind Cloudflare Access, run the login helper first:

```bash
m3 cf-login
```

This opens your browser to the Mylar URL, prompts you to paste the `CF_Authorization` cookie after logging in, and saves it to `~/.config/m3/.env`. The cookie typically expires in 24h–7 days — re-run when you see auth errors.

To find the cookie: DevTools → Application tab → Cookies → select your Mylar host → copy `CF_Authorization`.

## Commands

### `m3 weekly` (alias: `w`)

Combined weekly pipeline: refreshes series with unknown dates, then retags those issues.

```sh
m3 weekly
m3 w          # alias
```

Fetches this week's upcoming releases, filters to series where **at least one** of the store date or cover date is unknown (`0000-00-00`), refreshes those series, then retags their issues — all in one rate-limited pipeline.

---

### `m3 refresh-this-week-unknown` (alias: `ru`)

Refresh series for this week's issues where at least one date is unknown.

```sh
m3 refresh-this-week-unknown
m3 ru         # alias
```

---

### `m3 refresh-2099` (alias: `r9`)

Refresh series where the year is set to 2099 (Mylar's placeholder for uncertain dates).

```sh
m3 refresh-2099
m3 r9         # alias
m3 r9 --deep  # inspect individual issue dates instead of the series year field
```

---

### `m3 retag`

Re-tag issues downloaded within a recent time window.

```sh
m3 retag --week          # last 7 days (default)
m3 retag --month         # last 30 days
m3 retag --days 14       # custom number of days
```

Uses the `/manual_metatag` internal web route (same as clicking the Metatag button in the Mylar3 UI).

---

### `m3 cf-login`

Authenticate with Cloudflare Access and save the session cookie.

```sh
m3 cf-login
m3 cf-login --host mylar.example.com --port 443
```

---

## Rate Limiting

ComicVine enforces a hard limit of **200 API calls per hour**. Every `refreshComic` and re-tag operation triggers at least one ComicVine call inside Mylar3.

`m3` enforces a default cap of **180 calls/hour** (20-call safety buffer) with a minimum interval between consecutive calls. State is persisted to `rate_state.json` in the current directory so the limit is respected even when chaining commands:

```bash
m3 ru && m3 r9   # combined quota tracked across both runs
```

When the limit is reached, the CLI waits and shows a countdown before continuing.

Override the rate: `m3 --rate 100 retag --month` or `MYLAR_RATE_LIMIT=100` in `.env`.

## Contributing

```bash
uv sync                    # install all deps including dev tools
uv run ruff check .        # lint
uv run ruff format .       # format
uv run pyright             # type check
uv run m3 --help           # smoke test
```
