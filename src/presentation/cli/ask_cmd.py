"""CLI: вопрос-ответ по графу знаний."""

import asyncio
import logging

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


def register(): ...


from src.presentation.cli.app import app  # noqa: E402


@app.command("ask")
def ask_cmd(
    question: str = typer.Argument(..., help="Вопрос"),
    mode: str = typer.Option(
        "hybrid",
        "--mode",
        "-m",
        help="Режим: local | global | local_ppr | hybrid",
    ),
    top_k: int = typer.Option(10, "--top-k", "-k"),
):
    """Задать вопрос по графу знаний"""
    console.print(f"[bold cyan]❓[/bold cyan] {question}")
    asyncio.run(_run(question, mode, top_k))


async def _run(question: str, mode_str: str, top_k: int):
    from src.di.container import setup_di
    from src.application.use_cases.answer_question import AnswerQuestionUseCase
    from src.domain.value_objects.search_context import SearchMode

    try:
        search_mode = SearchMode(mode_str)
    except ValueError:
        console.print(
            f"[red]❌ Неизвестный режим: '{mode_str}'. "
            f"Доступны: local, global, local_ppr, hybrid[/red]"
        )
        return

    container = setup_di()
    try:
        use_case = await container.get(AnswerQuestionUseCase)
        response = await use_case.execute(
            question=question,
            mode=search_mode,
            top_k=top_k,
        )

        console.print(
            Panel(
                response.answer,
                title=f"[bold green]Ответ[/bold green] ({response.search_mode})",
                border_style="green",
            )
        )

        if response.sources:
            table = Table(title="Источники")
            table.add_column("Файл", style="cyan")
            table.add_column("Страницы", style="yellow")
            table.add_column("Чанк")
            table.add_column("Relevance")
            for src in response.sources:
                pages = (
                    f"{src.start_page}-{src.end_page}"
                    if src.start_page != src.end_page
                    else str(src.start_page)
                )
                if src.start_page == 0:
                    pages = "?"
                table.add_row(
                    src.filename or "—",
                    pages,
                    str(src.chunk_index),
                    f"{src.relevance:.3f}",
                )
            console.print(table)

        stats = response.context_stats
        console.print(
            f"\n[dim]📊 chunks={stats.get('chunks_count', 0)} "
            f"triples={stats.get('triples_count', 0)} "
            f"communities={stats.get('communities_count', 0)}[/dim]"
        )

    except Exception as e:
        console.print(f"[bold red]✖ {e}[/bold red]")
        logging.getLogger(__name__).exception("Детали:")
    finally:
        await container.close()
