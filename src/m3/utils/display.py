from collections.abc import Generator
from contextlib import contextmanager

from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeRemainingColumn,
)
from rich.table import Table

console = Console()


@contextmanager
def status_spinner(msg: str) -> Generator[None]:
    with console.status(f"[cyan]{msg}[/cyan]"):
        yield


def make_progress() -> Progress:
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TaskProgressColumn(),
        TimeRemainingColumn(),
        console=console,
    )


def print_table(title: str, columns: list[str], rows: list[list[str]]) -> None:
    table = Table(title=title, show_header=True, highlight=True)
    for col in columns:
        table.add_column(col)
    for row in rows:
        table.add_row(*row)
    console.print(table)


def print_error(msg: str) -> None:
    console.print(f"[bold red]Error:[/bold red] {msg}")


def print_success(msg: str) -> None:
    console.print(f"[bold green]✓[/bold green] {msg}")


def print_info(msg: str) -> None:
    console.print(f"[cyan]{msg}[/cyan]")


def format_eta(n_items: int, rate_per_hour: int) -> str:
    if rate_per_hour <= 0 or n_items <= 0:
        return "unknown"
    seconds = (n_items / rate_per_hour) * 3600
    minutes = seconds / 60
    if minutes < 1:
        return f"{seconds:.0f}s"
    if minutes < 60:
        return f"{minutes:.0f}m"
    hours = minutes / 60
    return f"{hours:.1f}h"
