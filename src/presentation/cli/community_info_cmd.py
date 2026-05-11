"""CLI: Детальная аналитика по сообществам."""

import asyncio
import logging

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns

console = Console()


def register(): ...


from src.presentation.cli.app import app


@app.command("community-info")
def community_info_cmd(
    community_id: int = typer.Argument(None, help="ID сообщества для детального просмотра"),
    limit_nodes: int = typer.Option(10, "--limit-nodes", "-n", help="Сколько вершин показать"),
    limit_edges: int = typer.Option(10, "--limit-edges", "-e", help="Сколько связей показать"),
):
    """Показывает список сообществ или глубокую аналитику по конкретному сообществу."""
    asyncio.run(_run(community_id, limit_nodes, limit_edges))


async def _run(community_id: int | None, limit_nodes: int, limit_edges: int):
    from src.di.container import setup_di
    from src.domain.interfaces.services.graph_analytics_service import IGraphAnalyticsService

    container = setup_di()
    try:
        analytics = await container.get(IGraphAnalyticsService)

        if community_id is None:
            communities = await analytics.get_communities()
            if not communities:
                console.print("[yellow]Сообщества не найдены. Выполните 'graphrag build-communities'[/yellow]")
                return

            table = Table(title="Обнаруженные сообщества", show_lines=True)
            table.add_column("ID", style="cyan", width=5)
            table.add_column("Название", style="green", width=30)
            table.add_column("Узлов", style="magenta", justify="right")
            table.add_column("Описание", width=60)

            for comm in communities:
                name = comm.name or "Без названия"
                summary = comm.summary or "—"
                table.add_row(str(comm.community_id), name, str(comm.entity_count), summary)

            console.print(table)
            console.print("\n[dim]Для деталей введите: graphrag community-info <ID>[/dim]")

        else:
            details = await analytics.get_community_details(community_id)
            if not details:
                console.print(f"[red]❌ Сообщество #{community_id} не найдено[/red]")
                return

            title_name = details.name or "Без названия"
            console.print(
                Panel(
                    f"[italic]{details.summary}[/italic]",
                    title=f"[bold green]Сообщество #{details.community_id}: {title_name}[/bold green]",
                )
            )

            stats_table = Table(title="📊 Базовая статистика", show_header=False, box=None)
            stats_table.add_row("[bold]Вершин:[/bold]", str(details.node_count))
            stats_table.add_row("[bold]Связей:[/bold]", str(details.edge_count))
            stats_table.add_row("[bold]Плотность:[/bold]", f"{details.density:.3f}")
            stats_table.add_row("[bold]Документов:[/bold]", str(details.document_count))

            # Использование атрибутов (Pydantic), а не ключей словаря
            top_table = Table(title="🧩 Топология", show_header=False, box=None)
            hubs_str = ", ".join([f"{h.name} ({h.degree})" for h in details.hubs]) or "—"
            bound_str = ", ".join([f"{b.name} ({b.degree})" for b in details.boundary_nodes]) or "—"

            top_table.add_row("[bold]Ядра (Hubs):[/bold]", hubs_str)
            top_table.add_row("[bold]Мосты (Boundary):[/bold]", bound_str)

            console.print(Columns([stats_table, top_table], expand=True))

            console.print("\n[bold cyan]🗂 Доминирующие типы сущностей:[/bold cyan]")
            types_str = " | ".join([f"{k}: {v}" for k, v in list(details.dominant_types.items())[:5]])
            console.print(types_str)

            console.print("\n[bold cyan]📄 Источники (Встречается в файлах):[/bold cyan]")
            for d in details.documents:
                console.print(f"  • [yellow]{d}[/yellow]")

            console.print(
                f"\n[bold cyan]📍 Узлы ({min(limit_nodes, details.node_count)} из {details.node_count}):[/bold cyan]"
            )
            for n in details.nodes[:limit_nodes]:
                console.print(f"  - {n.name} [dim]({n.type})[/dim]")
            if details.node_count > limit_nodes:
                console.print(
                    f"  [dim]... и еще {details.node_count - limit_nodes} узлов (используйте --limit-nodes N)[/dim]"
                )

            console.print(
                f"\n[bold cyan]🔗 Связи ({min(limit_edges, details.edge_count)} из {details.edge_count}):[/bold cyan]"
            )
            for e in details.edges[:limit_edges]:
                console.print(f"  - {e.source} —[magenta]{e.type}[/magenta]→ {e.target}")
            if details.edge_count > limit_edges:
                console.print(
                    f"  [dim]... и еще {details.edge_count - limit_edges} связей (используйте --limit-edges N)[/dim]"
                )

    except Exception as e:
        console.print(f"[bold red]✖ {e}[/bold red]")
        logging.getLogger(__name__).exception("Детали:")
    finally:
        await container.close()
