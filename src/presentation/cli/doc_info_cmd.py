"""CLI: информация о документе."""

import asyncio
import logging

import typer
from rich.console import Console

console = Console()


def register(): ...


from src.presentation.cli.app import app


@app.command("doc-info")
def doc_info_cmd(
    filename: str = typer.Argument(..., help="Имя файла документа"),
    show_chunks: bool = typer.Option(False, "--show-chunks", "-c", help="Показать детальное содержимое чанков"),
):
    """Показать информацию о документе, его статистику и граф (по желанию)."""
    console.print(f"[bold cyan]📄 Документ:[/bold cyan] {filename}")
    asyncio.run(_run(filename, show_chunks))


async def _run(filename: str, show_chunks: bool):
    from src.di.container import setup_di
    from src.domain.interfaces.repositories.document_repository import IDocumentRepository
    from src.domain.interfaces.repositories.instance_repository import IInstanceRepository

    container = setup_di()
    try:
        doc_repo = await container.get(IDocumentRepository)
        inst_repo = await container.get(IInstanceRepository)

        # Ищем строго по имени файла
        docs = await doc_repo.get_document_by_filename(filename)
        if not docs:
            console.print(f"[red]❌ '{filename}' не найден[/red]")
            return

        doc = docs[0]

        # Запрашиваем новую статистику
        stat = await doc_repo.get_document_stats(doc.doc_id)

        if stat:
            console.print(f"\n[bold]ID:[/bold] {stat.doc_id}")
            console.print(f"[bold]Загружен:[/bold] {stat.upload_date.strftime('%Y-%m-%d %H:%M:%S')}")
            console.print("[bold]Статистика по документу:[/bold]")
            console.print(f"  - Чанков: {stat.chunks_count}")
            console.print(f"  - Сущностей: {stat.entities_count}")
            console.print(f"  - Триплетов (связей): {stat.triples_count}")
            console.print(f"  - Участие в сообществах: {stat.communities_count}")

        if not show_chunks:
            console.print(
                "\n[dim]Чтобы увидеть содержимое чанков, извлеченные сущности и связи, используйте флаг --show-chunks[/dim]"
            )
            return

        chunks = await doc_repo.get_chunks_by_document(doc.doc_id)
        for chunk in chunks:
            console.rule(f"[bold]Чанк {chunk.chunk_index}[/bold]")
            console.print(chunk.text, soft_wrap=True)

            for inst in await inst_repo.get_instances_by_chunk(chunk.chunk_id):
                console.print(f"  🧩 [green]{inst.name}[/green] [{inst.class_name}]")

            for t in await inst_repo.get_triples_by_chunk(chunk.chunk_id):
                console.print(
                    f"  🔗 {t['subject_name']} —{t['predicate']}→ {t['object_name']}",
                )
    except Exception as e:
        console.print(f"[bold red]✖ {e}[/bold red]")
        logging.getLogger(__name__).exception("Детали:")
    finally:
        await container.close()
