"""CLI: Импорт онтологии из TTL (Protégé → Neo4j)."""
import asyncio
from pathlib import Path
import typer
from rich.console import Console

console = Console()

def register(): ...  # <--- ЭТО НУЖНО ДОБАВИТЬ

from src.presentation.cli.app import app  # noqa: E402


@app.command("import-ontology")
def import_ontology_cmd(
    ttl: Path = typer.Argument(
        ..., help="Путь к .ttl файлу", exists=True, readable=True
    ),
):
    """Импорт онтологии из Protégé (Turtle) с валидацией."""
    console.print(f"[bold cyan]📥 Импорт онтологии из[/bold cyan] {ttl}")
    asyncio.run(_run(ttl))


async def _run(ttl_path: Path):
    from src.di.container import setup_di
    from src.application.use_cases.update_ontology_use_case import UpdateOntologyUseCase

    container = setup_di()
    try:
        use_case = await container.get(UpdateOntologyUseCase)
        result = await use_case.execute(ttl_path)

        console.print(
            f"[bold green]✅ Успешно обновлено:[/bold green] "
            f"{result['updated_classes']} классов, "
            f"{result['updated_relations']} отношений"
        )
        if result["warnings"]:
            for w in result["warnings"]:
                console.print(f"[yellow]⚠️ {w}[/yellow]")
    except ValueError as e:
        console.print(f"[bold red]❌ Ошибка валидации:[/bold red]\n{str(e)}")
    except Exception as e:
        console.print(f"[bold red]✖ {e}[/bold red]")
    finally:
        await container.close()