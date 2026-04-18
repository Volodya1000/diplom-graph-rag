"""
title: GraphRAG Pipeline
author: Volodya
date: 2024-05-20
version: 1.0
license: MIT
description: Knowledge Graph Retrieval Pipeline (FastAPI)
requirements: requests
"""

import os
import requests
from typing import List, Union, Generator, Iterator, Any
from pydantic import BaseModel, Field

from logging import getLogger

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

        # 2. Правильная инициализация Valves.
        # Собираем параметры в словарь с типом dict[str, Any].
        # Это успокоит статический тайп-чекер (ошибка str -> int исчезнет),
        # а Pydantic сам преобразует строки из os.getenv в нужные типы.
        valves_data: dict[str, Any] = {
            k: os.getenv(k, v.default) for k, v in self.Valves.model_fields.items()
        }
        self.valves = self.Valves(**valves_data)

    async def on_startup(self):
        # Эта функция вызывается при старте сервера пайплайнов
        logger.debug(f"on_startup:{self.name}")
        pass

    async def on_shutdown(self):
        # Эта функция вызывается при остановке
        logger.debug(f"on_shutdown:{self.name}")
        pass

    def pipe(
        self, user_message: str, model_id: str, messages: List[dict], body: dict
    ) -> Union[str, Generator, Iterator]:
        """
        Main pipeline function. Отправляет запрос в FastAPI и возвращает ответ.
        """
        logger.debug(f"pipe:{self.name} -> User Message: {user_message}")

        # Защита от автогенерации заголовков чата самим Open WebUI (как в эталоне)
        if ("broad tags categorizing" in user_message.lower()) or (
            "create a concise" in user_message.lower()
        ):
            logger.debug(f"Title Generation (aborted): {user_message}")
            return "GraphRAG Chat"

        try:
            endpoint = f"{self.valves.API_BASE_URL}/chat/completions"

            payload = {
                "model": self.valves.MODEL_NAME,
                "messages": messages,
                "temperature": body.get("temperature", 0.7),
                "top_k": self.valves.TOP_K,
            }

            headers = {"Content-Type": "application/json", "Accept": "application/json"}

            logger.debug(f"Sending request to {endpoint}")
            response = requests.post(endpoint, json=payload, headers=headers)
            response.raise_for_status()

            data = response.json()
            choices = data.get("choices", [])
            if not choices:
                return "Ошибка: Получен пустой ответ от GraphRAG API."

            # Извлекаем текст ответа
            answer = choices[0].get("message", {}).get("content", "")

            # Извлекаем метаданные: источники и статистику
            sources = data.get("sources", [])
            stats = data.get("context_stats", {})

            extra_info = []

            if sources:
                extra_info.append("\n\n---\n**📚 Источники:**")

                from collections import defaultdict

                # Теперь храним список страниц, url и максимальный score
                file_info = defaultdict(
                    lambda: {"pages": set(), "url": "", "score": 0.0}
                )

                for src in sources:
                    filename = src.get("filename") or "Неизвестный файл"
                    url = src.get("download_url") or ""
                    start_page = src.get("start_page", 0)
                    end_page = src.get("end_page", 0)
                    relevance = src.get("relevance", 0.0)

                    if start_page == 0:
                        pages_str = "Стр. неизвестна"
                    elif start_page == end_page:
                        pages_str = f"Стр. {start_page}"
                    else:
                        pages_str = f"Стр. {start_page}-{end_page}"

                    file_info[filename]["pages"].add(pages_str)

                    # Если URL есть, запоминаем его
                    if url:
                        file_info[filename]["url"] = url

                    # Берем максимальный score
                    if relevance > file_info[filename]["score"]:
                        file_info[filename]["score"] = relevance

                for i, (filename, info) in enumerate(file_info.items(), 1):
                    pages = ", ".join(sorted(info["pages"]))
                    score = info["score"]
                    url = info["url"]

                    # Делаем имя файла кликабельным, если есть URL
                    if url:
                        file_link = f"[{filename}]({url})"
                    else:
                        file_link = filename

                    extra_info.append(
                        f"{i}. {file_link} ({pages}) | *Score: {score:.2f}*"
                    )

            if stats:
                extra_info.append(
                    f"\n*📊 Статистика: Чанков: {stats.get('chunks_count', 0)} | "
                    f"Триплетов: {stats.get('triples_count', 0)} | "
                    f"Сообществ: {stats.get('communities_count', 0)}*"
                )

            # Добавляем источники к тексту ответа
            if extra_info:
                answer += "\n\n" + "\n".join(extra_info)

            return answer

        except requests.exceptions.ConnectionError:
            return (
                f"**Ошибка подключения:** Не удалось подключиться к API по адресу `{self.valves.API_BASE_URL}`. "
                "Проверьте, что сервер запущен и доступен по сети."
            )
        except requests.exceptions.HTTPError as e:
            return f"**Ошибка API (HTTP {e.response.status_code}):**\n```json\n{e.response.text}\n```"
        except Exception as e:
            return f"**Внутренняя ошибка пайплайна:** {str(e)}"
