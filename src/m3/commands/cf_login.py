import webbrowser

import click

from m3.config import CONFIG_DIR, CONFIG_ENV


@click.command("cf-login")
@click.option(
    "--host", envvar="MYLAR_HOST", default="localhost", show_default=True, help="Mylar3 host."
)  # noqa: E501
@click.option(
    "--port", envvar="MYLAR_PORT", default=8090, show_default=True, type=int, help="Mylar3 port."
)  # noqa: E501
@click.option("--http-root", envvar="MYLAR_HTTP_ROOT", default="", help="Mylar3 HTTP root prefix.")
def cf_login(host: str, port: int, http_root: str) -> None:
    """Authenticate with Cloudflare Access and save the session cookie."""
    url = f"http://{host}:{port}{http_root}"

    click.echo(f"\nOpening browser to: {url}")
    click.echo(
        "\nSteps:\n"
        "  1. Complete the Cloudflare Access login in your browser\n"
        "  2. Open DevTools → Application → Cookies\n"
        f"  3. Find the cookie named 'CF_Authorization' for {host}\n"
        "  4. Copy its value and paste it below\n"
    )

    webbrowser.open(url)

    cookie_value: str = click.prompt("CF_Authorization cookie value", hide_input=True)

    if not cookie_value.strip():
        click.echo("No value entered — aborting.", err=True)
        raise SystemExit(1)

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    existing = CONFIG_ENV.read_text() if CONFIG_ENV.exists() else ""
    lines = [line for line in existing.splitlines() if not line.startswith("CF_AUTHORIZATION=")]
    lines.append(f"CF_AUTHORIZATION={cookie_value.strip()}")
    CONFIG_ENV.write_text("\n".join(lines) + "\n")

    click.echo(f"\n✓ Saved CF_Authorization to {CONFIG_ENV}")
    click.echo(
        "Note: Cloudflare cookies typically expire in 24h–7 days — "
        "re-run `m3 cf-login` when you see auth errors."
    )
