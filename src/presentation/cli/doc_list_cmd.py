"""CLI: список загруженных документов со статистикой."""

import asyncio
import logging

from rich.console import Console
from rich.table import Table

console = Console()


def register(): ...


from src.presentation.cli.app import app


@app.command("doc-list")
def doc_list_cmd():
    """Показать список загруженных документов и их статистику."""
    console.print("[bold cyan]📚 Список загруженных документов[/bold cyan]")
    asyncio.run(_run())


async def _run():
    from src.di.container import setup_di
    from src.domain.interfaces.repositories.document_repository import IDocumentRepository

    container = setup_di()
    try:
        doc_repo = await container.get(IDocumentRepository)
        stats = await doc_repo.get_all_documents_with_stats()

        if not stats:
            console.print("[yellow]Нет загруженных документов.[/yellow]")
            return

        table = Table(show_lines=True)
        table.add_column("Файл", style="cyan")
        table.add_column("Дата загрузки", style="magenta")
        table.add_column("Чанки", justify="right")
        table.add_column("Сущности", justify="right", style="green")
        table.add_column("Связи", justify="right", style="blue")
        table.add_column("Сообщества", justify="right", style="yellow")

        for stat in stats:
            date_str = stat.upload_date.strftime("%Y-%m-%d %H:%M")
            table.add_row(
                stat.filename,
                date_str,
                str(stat.chunks_count),
                str(stat.entities_count),
                str(stat.triples_count),
                str(stat.communities_count),
            )

        console.print(table)
        console.print(f"\n[dim]Всего документов: {len(stats)}[/dim]")
        console.print("[dim]Для просмотра чанков конкретного документа: graphrag doc-info <ID> --show-chunks[/dim]")

    except Exception as e:
        console.print(f"[bold red]✖ {e}[/bold red]")
        logging.getLogger(__name__).exception("Детали:")
    finally:
        await container.close()
