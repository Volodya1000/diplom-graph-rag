"""CLI: инициализация T-Box."""

import asyncio
from rich.console import Console
import typer

console = Console()

def register(): ...

from src.presentation.cli.app import app  # noqa: E402


@app.command("seed-tbox")
def seed_tbox_cmd(
    force: bool = typer.Option(False, "--force", "-f"),
    show: bool = typer.Option(False, "--show", "-s"),
):
    """Инициализация базовой онтологии (T-Box) в Neo4j"""
    console.print("[bold cyan]📚 Инициализация T-Box…[/bold cyan]")
    asyncio.run(_run(force, show))


async def _run(force: bool, show: bool):
    from src.di.container import setup_di
    from src.application.use_cases.seed_tbox import SeedTboxUseCase
    from src.domain.interfaces.repositories.schema_repository import ISchemaRepository

    container = setup_di()
    try:
        use_case = await container.get(SeedTboxUseCase)
        count = await use_case.execute(force=force)

        if count > 0:
            console.print(f"[bold green]✔ {count} элементов[/bold green]")
        else:
            console.print("[yellow]Всё уже есть[/yellow]")

        if show:
            repo = await container.get(ISchemaRepository)
            classes = await repo.get_tbox_classes()
            console.print(f"\n[bold cyan]Классы ({len(classes)}):[/bold cyan]")
            for cls in sorted(classes, key=lambda c: (c.status.value, c.name)):
                icon = "🟢" if cls.status.value == "core" else "🟡"
                desc = f" — {cls.description}" if cls.description else ""
                parent = f" (↑ {cls.parent})" if cls.parent else ""
                console.print(f"  {icon} {cls.name}{parent}{desc}  [{cls.status.value}]")

            relations = await repo.get_schema_relations()
            console.print(f"\n[bold cyan]Отношения ({len(relations)}):[/bold cyan]")
            for rel in sorted(relations, key=lambda r: (r.status.value, r.source_class)):
                icon = "🟢" if rel.status.value == "core" else "🟡"
                desc = f" — {rel.description}" if rel.description else ""
                console.print(
                    f"  {icon} {rel.source_class} → {rel.relation_name} → "
                    f"{rel.target_class}{desc}  [{rel.status.value}]"
                )
    finally:
        await container.close()