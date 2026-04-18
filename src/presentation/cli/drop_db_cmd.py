"""CLI: Очистка базы данных."""

import asyncio
import typer
from rich.console import Console
from src.presentation.cli.app import app

console = Console()


def register():
    """Вызывается при импорте — команда уже добавлена декоратором."""


@app.command("drop-db")
def drop_db_cmd(
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        prompt="Вы уверены, что хотите удалить ВСЕ данные из Neo4j?",
    ),
):
    """Полное удаление всех данных из Neo4j"""
    if not force:
        console.print("[yellow]Операция отменена.[/yellow]")
        return

    console.print("[bold red]⚠️ Очистка базы данных...[/bold red]")
    asyncio.run(_run())


async def _run():
    from src.di.container import setup_di
    from src.persistence.neo4j.session_manager import Neo4jSessionManager

    container = setup_di()
    try:
        sm = await container.get(Neo4jSessionManager)
        async with sm.session() as s:
            result = await s.run("MATCH (n) DETACH DELETE n")
            await result.consume()
        console.print("[bold green]✅ База данных успешно очищена.[/bold green]")
    except Exception as e:
        console.print(f"[bold red]✖ Ошибка при удалении:[/bold red] {e}")
    finally:
        await container.close()
