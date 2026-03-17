#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
CLI для очистки Neo4j базы данных

Примеры:
    python clear_db.py                     # интерактивный режим
    python clear_db.py stats               # только статистика
    python clear_db.py full --force        # полная очистка без вопросов
    python clear_db.py docs                # удалить только документы и чанки
"""

import asyncio
import sys
from pathlib import Path

import typer
from rich.console import Console

# Добавляем корень проекта в sys.path
root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(root))

from src.utils.logging import setup_logging
from src.config.base import AppConfig
from src.persistence.neo4j.neo4j_repository import Neo4jRepository
from src.config.neo4j_settings import Neo4jSettings

setup_logging(level="INFO", disable_verbose=True)
console = Console()

app = typer.Typer(
    name="neo4j-clean",
    help="Инструмент для очистки Neo4j",
    add_completion=False,
)


def get_repo() -> Neo4jRepository:
    config = AppConfig()

    # Создаём объект настроек, который ожидает Neo4jRepository
    settings = Neo4jSettings(
        uri=config.NEO4J_URI,
        user=config.NEO4J_USER,
        password_value=config.NEO4J_PASSWORD,  # ← обратите внимание на имя поля
    )

    return Neo4jRepository(settings)


async def clear_all(force: bool = False):
    """Полная очистка базы (узлы + связи)"""
    if not force and not typer.confirm(
            "[bold red]Вы уверены, что хотите удалить ВСЁ из Neo4j?[/bold red]",
            default=False,
    ):
        console.print("[yellow]Отменено[/yellow]")
        return

    repo = get_repo()
    try:
        console.print("[yellow]Очистка базы...[/yellow]")
        async with repo.driver.session() as session:
            await session.run("MATCH ()-[r]-() DELETE r")
            await session.run("MATCH (n) DELETE n")

        # Проверка
        async with repo.driver.session() as session:
            result = await session.run("MATCH (n) RETURN count(n) AS cnt")
            record = await result.single()
            cnt = record["cnt"] if record else 0

        if cnt == 0:
            console.print("[bold green]База успешно очищена ✓[/bold green]")
        else:
            console.print(f"[yellow]Осталось узлов: {cnt}[/yellow]")

    except Exception as e:
        console.print(f"[bold red]Ошибка:[/bold red] {e}")
        raise typer.Exit(1)
    finally:
        await repo.driver.close()


async def clear_documents():
    """Удалить только документы и чанки (с подтверждением)"""
    if not typer.confirm(
            "[bold yellow]Удалить только документы и чанки?[/bold yellow]",
            default=False,
    ):
        return

    repo = get_repo()
    try:
        console.print("[yellow]Удаление документов и чанков...[/yellow]")
        queries = [
            "MATCH ()-[r:NEXT_CHUNK|PREV_CHUNK|HASA_CHUNK|MENTIONED_IN]-() DELETE r",
            "MATCH (c:Chunk) DELETE c",
            "MATCH (d:Document) DELETE d",
        ]
        async with repo.driver.session() as session:
            for q in queries:
                await session.run(q)

        console.print("[bold green]Документы и чанки удалены ✓[/bold green]")

    except Exception as e:
        console.print(f"[bold red]Ошибка:[/bold red] {e}")
        raise typer.Exit(1)
    finally:
        await repo.driver.close()


async def print_stats():
    """Показать статистику по узлам и связям"""
    repo = get_repo()
    try:
        async with repo.driver.session() as s:
            # Узлы
            nodes_result = await s.run("""
                MATCH (n)
                RETURN labels(n) AS lbls, count(n) AS cnt
                ORDER BY cnt DESC
            """)
            rows = await nodes_result.data()

            console.print("\n[bold cyan]Узлы[/bold cyan]")
            if not rows:
                console.print("    (база пуста)")
            else:
                for r in rows:
                    lbl = ", ".join(r["lbls"]) or "<без меток>"
                    console.print(f"    {lbl:<36} {r['cnt']:>6}")

            # Связи
            rels_result = await s.run("""
                MATCH ()-[r]->()
                RETURN type(r) AS typ, count(r) AS cnt
                ORDER BY cnt DESC
            """)
            rows = await rels_result.data()

            if rows:
                console.print("\n[bold cyan]Связи[/bold cyan]")
                for r in rows:
                    console.print(f"    {r['typ']:<24} {r['cnt']:>6}")

    except Exception as e:
        console.print(f"[bold red]Ошибка статистики:[/bold red] {e}")
    finally:
        await repo.driver.close()


@app.command("full")
def full(force: bool = typer.Option(False, "--force", "-f", help="Без подтверждения")):
    """Полная очистка базы без меню"""
    asyncio.run(clear_all(force=force))


@app.command("docs")
def docs():
    """Удалить только документы и чанки"""
    asyncio.run(clear_documents())


@app.command("stats")
def stats():
    """Показать статистику базы"""
    asyncio.run(print_stats())


@app.callback(invoke_without_command=True)
def main(
        ctx: typer.Context,
        stats: bool = typer.Option(False, "--stats", "-s", help="Только показать статистику"),
):
    """
    Без аргументов → интерактивный режим
    """
    if ctx.invoked_subcommand is not None:
        return

    if stats:
        asyncio.run(print_stats())
        raise typer.Exit()

    # Интерактивный режим
    console.print("[bold cyan]Очистка Neo4j[/bold cyan]  (используйте --help для команд)")
    console.print("═" * 45)

    asyncio.run(print_stats())

    console.print("\nЧто сделать?")
    console.print("  [red]f[/red]  —  полная очистка")
    console.print("  [yellow]d[/yellow]  —  только документы/чанки")
    console.print("  [green]s[/green]  —  статистика ещё раз")
    console.print("  [blue]⏎ / q[/blue]  —  выход")

    while True:
        choice = input("\nВыбор (f/d/s/q): ").strip().lower() or "q"
        if choice in ("f", "full", "clear", "delete"):
            asyncio.run(clear_all(force=False))
            break
        elif choice in ("d", "docs", "documents"):
            asyncio.run(clear_documents())
            break
        elif choice in ("s", "stats", "stat"):
            asyncio.run(print_stats())
        elif choice in ("q", "exit", "quit", ""):
            console.print("[blue]Выход[/blue]")
            break
        else:
            console.print("[red]Неверно, попробуйте снова[/red]")


if __name__ == "__main__":
    app()