import click
import requests

from m3.config import CONFIG_ENV, get_config
from m3.utils.display import console, print_info


@click.command("mylar-login")
@click.option("--username", prompt=True, help="Mylar3 username.")
@click.option("--password", prompt=True, hide_input=True, help="Mylar3 password.")
@click.pass_context
def mylar_login(ctx: click.Context, username: str, password: str) -> None:
    """Log in to Mylar3 and save the session cookie."""
    cfg = get_config(ctx)
    url = f"{cfg.base_url}/auth/login"
    
    console.print(f"Logging in to {url}...")
    
    # We use a session to catch the cookie
    session = requests.Session()
    
    # Establish session before posting credentials
    try:
        session.get(url, timeout=10)
    except Exception as exc:
        raise click.ClickException(f"Failed to reach Mylar login page: {exc}") from exc

    # Authenticate using Mylar-specific field names
    data = {"current_username": username, "current_password": password}
    try:
        response = session.post(url, data=data, timeout=10, allow_redirects=True)
        response.raise_for_status()
    except Exception as exc:
        raise click.ClickException(f"Login request failed: {exc}") from exc

    if "/auth/login" in response.url.lower() and response.status_code == 200:
        # Remaining on login page indicates failed authentication
        raise click.ClickException("Login failed. Check your username and password.")

    # Persist the session cookie
    mylar_session = session.cookies.get("session")

    if not mylar_session:
        # Some versions might use different cookie names, but 'session' is standard for Flask/Mylar
        raise click.ClickException("Login appeared successful, but no 'session' cookie was returned.")

    # Save to CONFIG_ENV
    if not CONFIG_ENV.parent.exists():
        CONFIG_ENV.parent.mkdir(parents=True)
    
    lines = []
    if CONFIG_ENV.exists():
        with open(CONFIG_ENV) as f:
            lines = f.readlines()
    
    new_lines = []
    found = False
    for line in lines:
        if line.startswith("MYLAR_SESSION="):
            new_lines.append(f"MYLAR_SESSION={mylar_session}\n")
            found = True
        else:
            new_lines.append(line)
    
    if not found:
        new_lines.append(f"MYLAR_SESSION={mylar_session}\n")
        
    with open(CONFIG_ENV, "w") as f:
        f.writelines(new_lines)
        
    print_info(f"Successfully logged in! Session cookie saved to {CONFIG_ENV}")
