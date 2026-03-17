"""Сборка Typer-приложения."""

import logging
from src.utils.logging import setup_logging

setup_logging(level=logging.INFO, disable_verbose=True)

import typer  # noqa: E402

app = typer.Typer(
    name="graphrag",
    help="GraphRAG Pipeline — индексация, граф знаний, QA",
    add_completion=False,
)

from src.presentation.cli.ingest_cmd import register            # noqa
from src.presentation.cli.seed_tbox_cmd import register          # noqa
from src.presentation.cli.doc_info_cmd import register           # noqa
from src.presentation.cli.ask_cmd import register                # noqa
from src.presentation.cli.build_communities_cmd import register  # noqa