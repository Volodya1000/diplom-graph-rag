#!/usr/bin/env python
"""
Скрипт для очистки базы данных Neo4j.
Удаляет все узлы и связи.
"""

import asyncio
import sys
import logging
from pathlib import Path
from rich.console import Console
from rich.prompt import Confirm

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.utils.logging import setup_logging, get_logger
from src.di.container import setup_di
from src.persistence.neo4j.neo4j_repository import Neo4jRepository
from src.config.base import AppConfig

# Настраиваем логирование
setup_logging(level=logging.INFO, disable_verbose=True)
logger = get_logger(__name__)
console = Console()


async def clear_database():
    """Полная очистка базы данных Neo4j"""

    # Запрашиваем подтверждение
    if not Confirm.ask("[bold red]Вы уверены, что хотите удалить ВСЕ данные из Neo4j?[/bold red]"):
        console.print("[yellow]Операция отменена[/yellow]")
        return

    console.print("[dim]Подключение к Neo4j...[/dim]")

    # Получаем конфигурацию
    config = AppConfig()

    # Создаем прямое подключение к Neo4j (без использования контейнера DI)
    repo = Neo4jRepository(
        config.NEO4J_URI,
        config.NEO4J_USER,
        config.NEO4J_PASSWORD
    )

    try:
        # Запросы для очистки базы данных
        queries = [
            # Удаляем все связи
            "MATCH ()-[r]-() DELETE r",

            # Удаляем все узлы
            "MATCH (n) DELETE n",

            # Удаляем все индексы (опционально)
            # "CALL apoc.schema.assert({}, {})",  # Требует APOC
        ]

        console.print("[yellow]Удаление всех данных...[/yellow]")

        async with repo.driver.session() as session:
            for query in queries:
                await session.run(query)

        # Проверяем, что база пуста
        async with repo.driver.session() as session:
            result = await session.run("MATCH (n) RETURN count(n) as count")
            data = await result.data()
            count = data[0]['count'] if data else 0

            if count == 0:
                console.print("[bold green]✔ База данных успешно очищена![/bold green]")
            else:
                console.print(f"[yellow]В базе осталось {count} узлов[/yellow]")

    except Exception as e:
        console.print(f"[bold red]Ошибка при очистке:[/bold red] {str(e)}")
        logger.exception("Детали ошибки:")
    finally:
        await repo.driver.close()


async def clear_documents_only():
    """Удаляет только документы и чанки, сохраняя схему и экземпляры"""

    if not Confirm.ask("[bold yellow]Удалить только документы и чанки? Схема и экземпляры сохранятся[/bold yellow]"):
        return

    console.print("[dim]Подключение к Neo4j...[/dim]")

    config = AppConfig()
    repo = Neo4jRepository(
        config.NEO4J_URI,
        config.NEO4J_USER,
        config.NEO4J_PASSWORD
    )

    try:
        queries = [
            # Удаляем связи NEXT_CHUNK и PREV_CHUNK
            "MATCH ()-[r:NEXT_CHUNK]-() DELETE r",
            "MATCH ()-[r:PREV_CHUNK]-() DELETE r",

            # Удаляем связи HAS_CHUNK
            "MATCH ()-[r:HAS_CHUNK]-() DELETE r",

            # Удаляем связи MENTIONED_IN
            "MATCH ()-[r:MENTIONED_IN]-() DELETE r",

            # Удаляем чанки
            "MATCH (c:Chunk) DELETE c",

            # Удаляем документы
            "MATCH (d:Document) DELETE d",
        ]

        console.print("[yellow]Удаление документов и чанков...[/yellow]")

        async with repo.driver.session() as session:
            for query in queries:
                await session.run(query)

        console.print("[bold green]✔ Документы и чанки удалены[/bold green]")

    except Exception as e:
        console.print(f"[bold red]Ошибка:[/bold red] {str(e)}")
    finally:
        await repo.driver.close()


async def show_stats():
    """Показывает статистику базы данных"""

    config = AppConfig()
    repo = Neo4jRepository(
        config.NEO4J_URI,
        config.NEO4J_USER,
        config.NEO4J_PASSWORD
    )

    try:
        async with repo.driver.session() as session:
            # Считаем узлы по типам
            result = await session.run("""
                MATCH (n)
                RETURN labels(n) as type, count(n) as count
                ORDER BY count DESC
            """)
            nodes = await result.data()

            console.print("\n[bold cyan]Статистика базы данных:[/bold cyan]")

            if not nodes:
                console.print("[yellow]База данных пуста[/yellow]")
                return

            for node in nodes:
                types = ', '.join(node['type']) if node['type'] else 'No labels'
                console.print(f"  {types}: {node['count']}")

            # Считаем связи
            result = await session.run("""
                MATCH ()-[r]->()
                RETURN type(r) as type, count(r) as count
                ORDER BY count DESC
            """)
            rels = await result.data()

            if rels:
                console.print("\n[bold cyan]Связи:[/bold cyan]")
                for rel in rels:
                    console.print(f"  {rel['type']}: {rel['count']}")

    except Exception as e:
        console.print(f"[bold red]Ошибка:[/bold red] {str(e)}")
    finally:
        await repo.driver.close()


async def main():
    """Главная функция с меню"""

    console.print("[bold cyan]Очистка базы данных Neo4j[/bold cyan]")
    console.print("=" * 50)

    # Показываем текущую статистику
    await show_stats()

    console.print("\n[bold]Выберите действие:[/bold]")
    console.print("  1. [red]Полная очистка базы (удалить ВСЁ)[/red]")
    console.print("  2. [yellow]Удалить только документы и чанки[/yellow]")
    console.print("  3. [green]Показать статистику[/green]")
    console.print("  4. [blue]Выход[/blue]")

    choice = input("\nВаш выбор (1-4): ").strip()

    if choice == "1":
        await clear_database()
    elif choice == "2":
        await clear_documents_only()
    elif choice == "3":
        await show_stats()
    elif choice == "4":
        console.print("[blue]Выход[/blue]")
        return
    else:
        console.print("[red]Неверный выбор[/red]")


if __name__ == "__main__":
    asyncio.run(main())