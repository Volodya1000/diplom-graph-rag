
# 🧠 Дипломный проект Ontology Graph RAG
Система анализа документо на базе графа знаний (Neo4j) и локальных LLM (Ollama).
Проект позволяет извлекать сущности и связи из PDF-документов, строить граф знаний, находить в нем сообщества  и отвечать на вопросы с точным цитированием источников.

## 🛠 Установка и настройка

Проект использует менеджер пакетов [uv](https://github.com/astral-sh/uv).

### 1. Установка зависимостей
Для создания окружения и установки всех зависимостей (включая dev-инструменты), выполните в корне проекта:
```bash
uv sync
```

---

## 🚀 Основные команды (через `uv run`)

Все команды запускаются из корня проекта. `uv run` автоматически использует виртуальное окружение, созданное в папке `.venv`.

### Инициализация и индексация
1. **Инициализация онтологии (T-Box) из TTL-файла:**
   ```bash
   uv run main.py init-ontology alpha_onotlogy.ttl
   ```

2. **Индексация документа:**
   ```bash
   uv run main.py ingest устав.pdf
   ```

3. **Сборка сообществ графа:**
   ```bash
   uv run main.py build-communities --algo leiden --min-size 3
   ```

### Работа с системой
4. **Задать вопрос (QA):**
   ```bash
   uv run main.py ask "Ваш вопрос?" --mode hybrid
   ```

5. **Информация о документе:**
   ```bash
   uv run main.py doc-info устав.pdf
   ```

6. **Экспорт онтологии:**
   ```bash
   uv run main.py export-ontology -o data/ontology/my_ontology.ttl
   ```
7. **Импорт онтологии:**
   ```bash
   uv run main.py import-ontology alpha_onotlogy.ttl
   ```
8. **Полная очистка neo4j**
```bash
 uv run main.py drop-db
 ```
---

## 🌐 Запуск REST API

Для запуска API-сервера в режиме разработки с доступностью извне:

```bash
uv run fastapi dev src/presentation/api/main.py --host 0.0.0.0 --port 8000
```
либо
```bash
uv run uvicorn src.presentation.api.main:app --reload --host 0.0.0.0 --port 8000
```

* **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
* **Хост**: `0.0.0.0` позволяет принимать запросы не только с `localhost`, но и из локальной сети или Docker-контейнеров.

---

## 🧪 Разработка и тестирование

### Линтеры и форматирование (Ruff)
```bash
# Проверка кода
uv run ruff check .

# Исправление и форматирование
uv run ruff check . --fix
uv run ruff format .
```

### Запуск тестов
Используйте `uv run` для запуска `pytest`.

* **Запуск только быстрых юнит-тестов:**
  ```bash
  uv run pytest -m unit -v
  ```

* **Запуск интеграционных тестов** (требуется установленный Docker):
  ```bash
  uv run pytest -m integration -v
  ```

* **Запуск всех тестов:**
  ```bash
  uv run pytest -v
  ```

---

## 📁 Краткая структура проекта
* `src/domain/` — бизнес-логика и модели.
* `src/application/` — юз-кейсы и пайплайны.
* `src/infrastructure/` — реализация (LLM, Embeddings, Docling, Neo4j репозитории).
* `src/presentation/` — CLI (typer) и API (fastapi).
* `tests/` — unit и integration тесты.

---
**Примечание:** Перед запуском `ingest` или `ask`, убедитесь, что ваш `.env` файл содержит корректные параметры подключения к Neo4j, а Ollama запущена и доступна.
