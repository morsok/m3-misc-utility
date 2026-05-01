import click

from m3.commands.cf_login import cf_login
from m3.commands.mylar_login import mylar_login
from m3.commands.refresh_2099 import refresh_2099
from m3.commands.refresh_this_week_unknown import refresh_this_week_unknown
from m3.commands.retag import retag
from m3.commands.weekly import weekly
from m3.types import CliOpts


@click.group()
@click.option("--host", envvar="MYLAR_HOST", default=None, help="Mylar3 host.")
@click.option("--port", envvar="MYLAR_PORT", default=None, type=int, help="Mylar3 port.")
@click.option("--apikey", envvar="MYLAR_APIKEY", default=None, help="Mylar3 API key.")
@click.option(
    "--http-root",
    "http_root",
    envvar="MYLAR_HTTP_ROOT",
    default=None,
    help="Mylar3 HTTP root prefix.",
)
@click.option(
    "--rate",
    envvar="MYLAR_RATE_LIMIT",
    default=None,
    type=int,
    help="Max ComicVine calls/hour (max 200).",
)
@click.option(
    "-v",
    "--verbose",
    "verbosity",
    count=True,
    help="Verbose output. -v: summary, -vv: headers/body, -vvv: log all to m3_debug.log.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Dry run mode. Fakes API responses and ignores real rate limits.",
)
@click.pass_context
def main(
    ctx: click.Context,
    host: str | None,
    port: int | None,
    apikey: str | None,
    http_root: str | None,
    rate: int | None,
    verbosity: int,
    dry_run: bool,
) -> None:
    """m3 — Mylar3 maintenance CLI."""
    ctx.ensure_object(dict)
    opts: CliOpts = {
        "host": host,
        "port": port,
        "apikey": apikey,
        "http_root": http_root,
        "rate": rate,
        "verbosity": verbosity,
        "dry_run": dry_run,
        "debug_log": None,
    }
    ctx.obj["opts"] = opts


main.add_command(cf_login)
main.add_command(mylar_login)

main.add_command(refresh_this_week_unknown)
main.add_command(refresh_this_week_unknown, name="ru")

main.add_command(refresh_2099)
main.add_command(refresh_2099, name="r9")

main.add_command(weekly)
main.add_command(weekly, name="w")

main.add_command(retag)
