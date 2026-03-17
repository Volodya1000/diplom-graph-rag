"""
Единая точка входа CLI.

    python main.py ingest  data/my_doc.pdf
    python main.py seed-tbox
    python main.py seed-tbox --force --show
    python main.py doc-info my_doc.pdf
"""

import sys
import asyncio
import logging
from pathlib import Path

import typer
from rich.console import Console

root = Path(__file__).resolve().parent
sys.path.insert(0, str(root))

from src.utils.logging import setup_logging

setup_logging(level=logging.INFO, disable_verbose=True)

console = Console()
app = typer.Typer(
    name="graphrag",
    help="GraphRAG Pipeline — индексация документов в граф знаний",
    add_completion=False,
)


# ========================== INGEST ==========================

@app.command("ingest")
def ingest_cmd(
    file: Path = typer.Argument(
        ..., help="Путь к PDF-файлу", exists=True, readable=True,
    ),
):
    """Индексация PDF-документа в графовую БД"""
    console.print(f"[bold yellow]📄 Индексация:[/bold yellow] {file.name}")
    asyncio.run(_run_ingest(file))


async def _run_ingest(file_path: Path):
    from src.di.container import setup_di
    from src.application.use_cases.ingest_document import IngestDocumentUseCase

    container = setup_di()
    try:
        console.print("[dim]Сборка зависимостей и загрузка моделей…[/dim]")
        use_case = await container.get(IngestDocumentUseCase)
        doc_id = await use_case.execute(file_path)
        console.print(
            f"[bold green]✔ Успех![/bold green] "
            f"doc_id: [cyan]{doc_id}[/cyan]"
        )
    except Exception as e:
        console.print(f"[bold red]✖ Ошибка:[/bold red] {e}")
        logging.getLogger(__name__).exception("Детали:")
    finally:
        await container.close()


# ======================== SEED T-BOX ========================

@app.command("seed-tbox")
def seed_tbox_cmd(
    force: bool = typer.Option(False, "--force", "-f"),
    show: bool = typer.Option(False, "--show", "-s"),
):
    """Инициализация базовой онтологии (T-Box) в Neo4j"""
    console.print("[bold cyan]📚 Инициализация T-Box…[/bold cyan]")
    asyncio.run(_run_seed(force, show))


async def _run_seed(force: bool, show: bool):
    from src.di.container import setup_di
    from src.application.use_cases.seed_tbox import SeedTboxUseCase
    from src.domain.interfaces.repositories.schema_repository import (
        ISchemaRepository,
    )

    container = setup_di()
    try:
        use_case = await container.get(SeedTboxUseCase)
        count = await use_case.execute(force=force)

        if count > 0:
            console.print(
                f"[bold green]✔ Добавлено/обновлено: "
                f"{count} элементов[/bold green]"
            )
        else:
            console.print(
                "[yellow]Все базовые элементы уже существуют[/yellow]"
            )

        if show:
            schema_repo = await container.get(ISchemaRepository)

            classes = await schema_repo.get_tbox_classes()
            console.print(
                f"\n[bold cyan]Классы ({len(classes)}):[/bold cyan]"
            )
            for cls in sorted(
                classes, key=lambda c: (c.status.value, c.name),
            ):
                icon = "🟢" if cls.status.value == "core" else "🟡"
                desc = f" — {cls.description}" if cls.description else ""
                parent = f" (↑ {cls.parent})" if cls.parent else ""
                console.print(
                    f"  {icon} {cls.name}{parent}{desc}  "
                    f"[{cls.status.value}]"
                )

            relations = await schema_repo.get_schema_relations()
            console.print(
                f"\n[bold cyan]Отношения ({len(relations)}):[/bold cyan]"
            )
            for rel in sorted(
                relations,
                key=lambda r: (
                    r.status.value, r.source_class, r.relation_name,
                ),
            ):
                icon = "🟢" if rel.status.value == "core" else "🟡"
                desc = f" — {rel.description}" if rel.description else ""
                console.print(
                    f"  {icon} {rel.source_class} → "
                    f"{rel.relation_name} → {rel.target_class}"
                    f"{desc}  [{rel.status.value}]"
                )
    finally:
        await container.close()


# ======================== DOC-INFO ========================

@app.command("doc-info")
def doc_info_cmd(
    filename: str = typer.Argument(..., help="Имя файла документа"),
):
    """Показать информацию о документе: текст чанков, сущности, триплеты"""
    console.print(
        f"[bold cyan]📄 Информация о документе:[/bold cyan] {filename}"
    )
    asyncio.run(_run_doc_info(filename))


async def _run_doc_info(filename: str):
    from src.di.container import setup_di
    from src.domain.interfaces.repositories.document_repository import (
        IDocumentRepository,
    )
    from src.domain.interfaces.repositories.instance_repository import (
        IInstanceRepository,
    )

    container = setup_di()
    try:
        doc_repo = await container.get(IDocumentRepository)
        instance_repo = await container.get(IInstanceRepository)

        docs = await doc_repo.get_document_by_filename(filename)
        if not docs:
            console.print(
                f"[red]❌ Документ '{filename}' не найден[/red]"
            )
            return

        doc = docs[0]
        console.print(f"ID: [cyan]{doc.doc_id}[/cyan]")
        console.print(f"Дата: {doc.upload_date}\n")

        chunks = await doc_repo.get_chunks_by_document(doc.doc_id)
        if not chunks:
            console.print("[yellow]У документа нет чанков[/yellow]")
            return

        for chunk in chunks:
            console.rule(
                f"[bold]Чанк {chunk.chunk_index} "
                f"(стр. {chunk.start_page}-{chunk.end_page})[/bold]"
            )
            console.print("\n[bold]📝 Текст:[/bold]")
            console.print(chunk.text, soft_wrap=True)

            instances = await instance_repo.get_instances_by_chunk(
                chunk.chunk_id,
            )
            if instances:
                console.print("\n[bold]🧩 Сущности:[/bold]")
                for inst in instances:
                    console.print(
                        f"  • [green]{inst.name}[/green] "
                        f"([cyan]{inst.class_name}[/cyan])"
                    )

            triples = await instance_repo.get_triples_by_chunk(
                chunk.chunk_id,
            )
            if triples:
                console.print("\n[bold]🔗 Триплеты:[/bold]")
                for t in triples:
                    console.print(
                        f"  • [green]{t['subject_name']}[/green] "
                        f"([cyan]{t['subject_type']}[/cyan]) "
                        f"—[yellow]{t['predicate']}[/yellow]→ "
                        f"[green]{t['object_name']}[/green] "
                        f"([cyan]{t['object_type']}[/cyan])"
                    )

            console.print()

    except Exception as e:
        console.print(f"[bold red]✖ Ошибка:[/bold red] {e}")
        logging.getLogger(__name__).exception("Детали:")
    finally:
        await container.close()


if __name__ == "__main__":
    app()