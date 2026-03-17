"""CLI: community detection + summary generation."""

import asyncio
import logging

import typer
from rich.console import Console
from rich.table import Table

console = Console()

def register(): ...

from src.presentation.cli.app import app  # noqa: E402


@app.command("build-communities")
def build_communities_cmd(
    algorithm: str = typer.Option(
        "leiden", "--algo", "-a",
        help="Алгоритм: leiden | louvain",
    ),
    min_size: int = typer.Option(
        2, "--min-size",
        help="Мин. размер сообщества для генерации summary",
    ),
    no_summaries: bool = typer.Option(
        False, "--no-summaries",
        help="Пропустить генерацию summaries",
    ),
    force: bool = typer.Option(
        False, "--force", "-f",
        help="Пересоздать проекцию и пересчитать",
    ),
    show: bool = typer.Option(
        False, "--show", "-s",
        help="Показать сообщества после создания",
    ),
):
    """Запуск community detection и генерация summaries"""
    console.print(
        f"[bold cyan]🧩 Community Detection[/bold cyan] "
        f"({algorithm})"
    )
    asyncio.run(_run(algorithm, min_size, no_summaries, force, show))


async def _run(
    algorithm: str,
    min_size: int,
    no_summaries: bool,
    force: bool,
    show: bool,
):
    from src.di.container import setup_di
    from src.application.use_cases.build_communities import (
        BuildCommunitiesUseCase,
    )
    from src.domain.interfaces.services.graph_analytics_service import (
        IGraphAnalyticsService,
    )

    container = setup_di()
    try:
        use_case = await container.get(BuildCommunitiesUseCase)
        result = await use_case.execute(
            algorithm=algorithm,
            min_community_size=min_size,
            generate_summaries=not no_summaries,
            force=force,
        )

        console.print(
            f"[bold green]✔ Сообществ: {result['communities']}, "
            f"summaries: {result['summaries_generated']}[/bold green]"
        )

        if show:
            analytics = await container.get(IGraphAnalyticsService)
            communities = await analytics.get_communities()

            table = Table(
                title=f"Сообщества ({len(communities)})",
                show_lines=True,
            )
            table.add_column("ID", style="cyan", width=6)
            table.add_column("Размер", width=8)
            table.add_column("Ключевые сущности", width=40)
            table.add_column("Summary", width=60)

            for comm in sorted(
                communities,
                key=lambda c: c.entity_count,
                reverse=True,
            ):
                entities = ", ".join(comm.key_entities[:5])
                summary = (
                    (comm.summary[:80] + "…")
                    if comm.summary and len(comm.summary) > 80
                    else (comm.summary or "—")
                )
                table.add_row(
                    str(comm.community_id),
                    str(comm.entity_count),
                    entities,
                    summary,
                )

            console.print(table)

    except Exception as e:
        console.print(f"[bold red]✖ {e}[/bold red]")
        logging.getLogger(__name__).exception("Детали:")
    finally:
        await container.close()