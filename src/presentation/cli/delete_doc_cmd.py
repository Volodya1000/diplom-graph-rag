"""CLI: Удаление документа по имени."""

import asyncio
import logging

import typer
from rich.console import Console

from src.presentation.cli.app import app

console = Console()


def register():
    pass


@app.command("delete-doc")
def delete_doc_cmd(
    filename: str = typer.Argument(..., help="Имя файла для удаления"),
):
    """Полностью и безопасно удаляет документ, его чанки, связи и изолированные сущности."""
    console.print(f"[bold red]🗑️ Удаление документа:[/bold red] {filename}")
    asyncio.run(_run(filename))


async def _run(filename: str):
    from src.application.use_cases.delete_document_use_case import DeleteDocumentUseCase
    from src.di.container import setup_di

    container = setup_di()
    try:
        use_case = await container.get(DeleteDocumentUseCase)
        success = await use_case.execute(filename)

        if success:
            console.print(f"[bold green]✅ Документ '{filename}' успешно удален из графа и хранилища.[/bold green]")
        else:
            console.print(f"[bold yellow]⚠️ Документ '{filename}' не найден ни в БД, ни в хранилище.[/bold yellow]")
    except Exception as e:
        console.print(f"[bold red]✖ Ошибка при удалении:[/bold red] {e}")
        logging.getLogger(__name__).exception("Детали:")
    finally:
        await container.close()
