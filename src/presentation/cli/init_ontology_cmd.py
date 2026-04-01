"""CLI: Инициализация пустой базы данных онтологией из TTL-файла."""

import asyncio
from pathlib import Path
import typer
from rich.console import Console

console = Console()


def register():
    """Пустышка для удобного импорта в app.py"""
    pass


from src.presentation.cli.app import app  # noqa: E402


@app.command("init-ontology")
def init_ontology_cmd(
    ttl: Path = typer.Argument(
        ..., help="Путь к файлу онтологии в формате .ttl", exists=True, readable=True
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Продолжить, даже если онтология уже существует (сработает merge)",
    ),
):
    """
    Инициализация T-Box из TTL-файла (вместо Python-классов).
    Рекомендуется выполнять на пустой базе данных.
    """
    console.print(f"[bold cyan]🚀 Инициализация БД из файла:[/bold cyan] {ttl}")
    asyncio.run(_run(ttl, force))


async def _run(ttl_path: Path, force: bool):
    from src.di.container import setup_di
    from src.application.use_cases.update_ontology_use_case import UpdateOntologyUseCase
    from src.domain.interfaces.repositories.schema_repository import ISchemaRepository

    container = setup_di()
    try:
        schema_repo = await container.get(ISchemaRepository)

        # 1. Проверяем, пустая ли база
        current_classes = await schema_repo.get_tbox_classes()
        if current_classes and not force:
            console.print("[yellow]⚠️ База данных уже содержит онтологию.[/yellow]")
            console.print(
                "Для обновления существующей онтологии используйте команду: [bold cyan]import-ontology[/bold cyan]"
            )
            console.print(
                "Или используйте флаг [bold]--force[/bold], чтобы принудительно добавить новые данные."
            )
            return

        # 2. Обязательно создаем графовые/векторные индексы (как в seed-tbox)
        console.print("📐 Создание векторных и текстовых индексов Neo4j...")
        await schema_repo.ensure_indexes()

        # 3. Используем существующий UseCase для парсинга, валидации и сохранения
        use_case = await container.get(UpdateOntologyUseCase)
        result = await use_case.execute(ttl_path)

        console.print(
            f"[bold green]✅ Онтология успешно инициализирована:[/bold green] "
            f"{result['updated_classes']} классов, "
            f"{result['updated_relations']} отношений"
        )

        if result.get("warnings"):
            for w in result["warnings"]:
                console.print(f"[yellow]⚠️ {w}[/yellow]")

    except ValueError as e:
        console.print(f"[bold red]❌ Ошибка валидации TTL файла:[/bold red]\n{str(e)}")
    except Exception as e:
        console.print(f"[bold red]✖ Системная ошибка:[/bold red] {e}")
    finally:
        await container.close()
