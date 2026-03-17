"""Сборка Typer-приложения и регистрация всех команд."""

import logging
from src.utils.logging import setup_logging

setup_logging(level=logging.INFO, disable_verbose=True)

import typer  # noqa: E402

app = typer.Typer(
    name="graphrag",
    help="GraphRAG Pipeline — индексация и вопрос-ответ по графу знаний",
    add_completion=False,
)

# Регистрация команд (импорт с side-effect)
from src.presentation.cli.ingest_cmd import register     # noqa: E402,F401
from src.presentation.cli.seed_tbox_cmd import register   # noqa: E402,F401
from src.presentation.cli.doc_info_cmd import register    # noqa: E402,F401
from src.presentation.cli.ask_cmd import register         # noqa: E402,F401

# Все register() вызываются при импорте (см. ниже)