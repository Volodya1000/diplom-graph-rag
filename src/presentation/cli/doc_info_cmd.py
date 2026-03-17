"""CLI: информация о документе."""

import asyncio
import logging
from rich.console import Console
import typer

console = Console()

def register(): ...

from src.presentation.cli.app import app  # noqa: E402


@app.command("doc-info")
def doc_info_cmd(
    filename: str = typer.Argument(..., help="Имя файла документа"),
):
    """Показать чанки, сущности и триплеты документа"""
    console.print(f"[bold cyan]📄 Документ:[/bold cyan] {filename}")
    asyncio.run(_run(filename))


async def _run(filename: str):
    from src.di.container import setup_di
    from src.domain.interfaces.repositories.document_repository import IDocumentRepository
    from src.domain.interfaces.repositories.instance_repository import IInstanceRepository

    container = setup_di()
    try:
        doc_repo = await container.get(IDocumentRepository)
        inst_repo = await container.get(IInstanceRepository)

        docs = await doc_repo.get_document_by_filename(filename)
        if not docs:
            console.print(f"[red]❌ '{filename}' не найден[/red]")
            return

        doc = docs[0]
        chunks = await doc_repo.get_chunks_by_document(doc.doc_id)
        for chunk in chunks:
            console.rule(f"[bold]Чанк {chunk.chunk_index}[/bold]")
            console.print(chunk.text, soft_wrap=True)

            for inst in await inst_repo.get_instances_by_chunk(chunk.chunk_id):
                console.print(f"  🧩 [green]{inst.name}[/green] [{inst.class_name}]")

            for t in await inst_repo.get_triples_by_chunk(chunk.chunk_id):
                console.print(
                    f"  🔗 {t['subject_name']} —{t['predicate']}→ {t['object_name']}"
                )
    except Exception as e:
        console.print(f"[bold red]✖ {e}[/bold red]")
        logging.getLogger(__name__).exception("Детали:")
    finally:
        await container.close()