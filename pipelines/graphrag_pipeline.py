"""
title: GraphRAG Pipeline.

author: Volodya
date: 2024-05-20
version: 1.1
license: MIT
description: Knowledge Graph Retrieval Pipeline (FastAPI)
requirements: requests
"""

import os
from collections import defaultdict
from collections.abc import Generator, Iterator
from logging import getLogger
from typing import Any

import requests
from pydantic import BaseModel, Field

logger = getLogger(__name__)
logger.setLevel("DEBUG")


class Pipeline:
    class Valves(BaseModel):
        API_BASE_URL: str = Field(
            default="http://host.docker.internal:8000/v1",
            description="Базовый URL вашего FastAPI",
        )
        MODEL_NAME: str = Field(
            default="graphrag-hybrid",
            description="Имя модели для API (от этого зависит SearchMode)",
        )
        TOP_K: int = Field(default=10, description="Количество возвращаемых чанков")

    def __init__(self):
        self.name = 'Ассистент по базе знаний ЗАО "Альфа-Банк"'
        valves_data: dict[str, Any] = {k: os.getenv(k, v.default) for k, v in self.Valves.model_fields.items()}
        self.valves = self.Valves(**valves_data)

    async def on_startup(self):
        logger.debug(f"on_startup: {self.name}")

    async def on_shutdown(self):
        logger.debug(f"on_shutdown: {self.name}")

    def pipe(
        self,
        user_message: str,
        model_id: str,
        messages: list[dict],
        body: dict,
    ) -> str | Generator | Iterator:
        """Точка входа. Управляет высокоуровневым пайплайном."""
        logger.debug(f"pipe: {self.name} -> User Message: {user_message}")

        if self._is_ui_auto_title_request(user_message):
            return "GraphRAG Chat"

        try:
            response_data = self._fetch_graphrag_response(messages=messages, temperature=body.get("temperature", 0.7))
            return self._build_reply_text(response_data)

        except requests.exceptions.ConnectionError:
            return f"**Ошибка подключения:** API недоступен по адресу `{self.valves.API_BASE_URL}`."
        except requests.exceptions.HTTPError as e:
            return f"**Ошибка API (HTTP {e.response.status_code}):**\n```json\n{e.response.text}\n```"
        except requests.exceptions.Timeout:
            return "**Ошибка:** Превышено время ожидания ответа от API."
        except Exception as e:
            logger.exception("Внутренняя ошибка пайплайна")
            return f"**Внутренняя ошибка пайплайна:** {e!s}"

    # --- Приватные методы (Инкапсуляция и SRP) ---

    def _is_ui_auto_title_request(self, message: str) -> bool:
        """Фильтрует системные запросы Open WebUI на генерацию заголовка."""
        msg = message.lower()
        return "broad tags categorizing" in msg or "create a concise" in msg

    def _fetch_graphrag_response(self, messages: list[dict], temperature: float) -> dict:
        """Отвечает только за HTTP запрос и получение данных."""
        endpoint = f"{self.valves.API_BASE_URL}/chat/completions"
        payload = {
            "model": self.valves.MODEL_NAME,
            "messages": messages,
            "temperature": temperature,
            "top_k": self.valves.TOP_K,
        }

        logger.debug(f"Sending request to {endpoint}")
        # Senior best practice: всегда добавлять timeout для сетевых запросов
        response = requests.post(endpoint, json=payload, timeout=60)
        response.raise_for_status()

        return response.json()

    def _build_reply_text(self, data: dict) -> str:
        """Собирает итоговый текстовый ответ из частей."""
        choices = data.get("choices", [])
        if not choices:
            return "Ошибка: Получен пустой ответ от GraphRAG API."

        # Использование списка для конкатенации строк (эффективнее, чем +=)
        reply_parts = [choices[0].get("message", {}).get("content", "")]

        sources_text = self._format_sources(data.get("sources", []))
        if sources_text:
            reply_parts.append(f"\n\n---\n**📚 Источники:**\n{sources_text}")

        stats_text = self._format_stats(data.get("context_stats", {}))
        if stats_text:
            reply_parts.append(f"\n{stats_text}")

        return "".join(reply_parts)

    def _format_sources(self, sources: list[dict]) -> str:
        """Агрегирует и форматирует список источников."""
        if not sources:
            return ""

        file_info = defaultdict(lambda: {"pages": set(), "url": "", "score": 0.0})

        for src in sources:
            filename = src.get("filename") or "Неизвестный файл"
            url = src.get("download_url") or ""
            start, end = src.get("start_page", 0), src.get("end_page", 0)

            # DRY: лаконичное обновление данных
            if url:
                file_info[filename]["url"] = url

            file_info[filename]["score"] = max(file_info[filename]["score"], src.get("relevance", 0.0))

            # Форматирование страниц
            if start == 0:
                page_str = "Стр. неизвестна"
            elif start == end:
                page_str = f"Стр. {start}"
            else:
                page_str = f"Стр. {start}-{end}"

            file_info[filename]["pages"].add(page_str)

        # Сборка строк источников
        formatted_lines = []
        for i, (filename, info) in enumerate(file_info.items(), 1):
            pages = ", ".join(sorted(info["pages"]))
            score = info["score"]
            url = info["url"]

            file_link = f"[{filename}]({url})" if url else filename
            formatted_lines.append(f"{i}. {file_link} ({pages}) | *Score: {score:.2f}*")

        return "\n".join(formatted_lines)

    def _format_stats(self, stats: dict) -> str:
        """Форматирует статистику."""
        if not stats:
            return ""
        return (
            f"*📊 Статистика: Чанков: {stats.get('chunks_count', 0)} | "
            f"Триплетов: {stats.get('triples_count', 0)} | "
            f"Сообществ: {stats.get('communities_count', 0)}*"
        )
