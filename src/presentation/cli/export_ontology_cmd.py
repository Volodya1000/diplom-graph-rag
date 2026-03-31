"""CLI: Экспорт T-Box в Turtle (OWL) для Protégé."""
import asyncio
from pathlib import Path
import typer
from rich.console import Console

console = Console()

def register(): ...

from src.presentation.cli.app import app  # noqa: E402

@app.command("export-ontology")
def export_ontology_cmd(
    output: Path = typer.Option(
        "data/ontology/gr_a3_ontology.ttl",
        "--output", "-o",
        help="Путь к файлу .ttl",
        dir_okay=False,
        writable=True,
    ),
    force: bool = typer.Option(
        False, "--force", "-f",
        help="Перезаписать существующий файл",
    ),
):
    """Выгрузка актуальной онтологии (T-Box) в Turtle-OWL формат."""
    console.print("[bold cyan]📤 Экспорт онтологии в Turtle (OWL)...[/bold cyan]")
    asyncio.run(_run(output, force))


async def _run(output_path: Path, force: bool):
    if output_path.exists() and not force:
        console.print(f"[yellow]⚠ Файл уже существует: {output_path}[/yellow]")
        console.print("   Используйте --force для перезаписи.")
        return

    from src.di.container import setup_di
    from src.application.use_cases.export_ontology import ExportOntologyUseCase

    container = setup_di()
    try:
        use_case = await container.get(ExportOntologyUseCase)
        saved_path = await use_case.execute(output_path)
        console.print("[bold green]✅ Онтология успешно выгружена:[/bold green]")
        console.print(f"   [cyan]{saved_path}[/cyan]")
        console.print("\n[dim]Открывайте файл в Protégé → File → Open[/dim]")
    except Exception as e:
        console.print(f"[bold red]✖ Ошибка: {e}[/bold red]")
    finally:
        await container.close()