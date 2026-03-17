"""
Единая точка входа CLI.

Примеры:
    python main.py ingest  data/my_doc.pdf
    python main.py seed-tbox
    python main.py seed-tbox --force --show
"""

import sys
import asyncio
import logging
from pathlib import Path

import typer
from rich.console import Console

# Корень проекта в sys.path (на случай запуска из другой директории)
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
        ...,
        help="Путь к PDF-файлу",
        exists=True,
        readable=True,
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
        console.print("[dim]Сборка зависимостей и загрузка моделей...[/dim]")
        use_case = await container.get(IngestDocumentUseCase)
        doc_id = await use_case.execute(file_path)
        console.print(f"[bold green]✔ Успех![/bold green] doc_id: [cyan]{doc_id}[/cyan]")
    except Exception as e:
        console.print(f"[bold red]✖ Ошибка:[/bold red] {e}")
        logging.getLogger(__name__).exception("Детали:")
    finally:
        await container.close()


# ======================== SEED T-BOX ========================

@app.command("seed-tbox")
def seed_tbox_cmd(
    force: bool = typer.Option(
        False, "--force", "-f",
        help="Перезаписать описания существующих CORE-классов",
    ),
    show: bool = typer.Option(
        False, "--show", "-s",
        help="Показать T-Box после сидирования",
    ),
):
    """Инициализация базовой онтологии (T-Box) в Neo4j"""
    console.print("[bold cyan]📚 Инициализация T-Box...[/bold cyan]")
    asyncio.run(_run_seed(force, show))


async def _run_seed(force: bool, show: bool):
    from src.di.container import setup_di
    from src.application.use_cases.seed_tbox import SeedTboxUseCase
    from src.domain.interfaces.repositories.graph_repository import IGraphRepository

    container = setup_di()
    try:
        use_case = await container.get(SeedTboxUseCase)
        count = await use_case.execute(force=force)

        if count > 0:
            console.print(f"[bold green]✔ Добавлено/обновлено: {count} классов[/bold green]")
        else:
            console.print("[yellow]Все базовые классы уже существуют[/yellow]")

        if show:
            repo = await container.get(IGraphRepository)
            classes = await repo.get_tbox_classes()
            console.print(f"\n[bold cyan]T-Box ({len(classes)} классов):[/bold cyan]")
            for cls in sorted(classes, key=lambda c: (c.status.value, c.name)):
                icon = "🟢" if cls.status.value == "core" else "🟡"
                desc = f" — {cls.description}" if cls.description else ""
                console.print(f"  {icon} {cls.name}{desc}  [{cls.status.value}]")
    finally:
        await container.close()


# ==============================================================

if __name__ == "__main__":
    app()