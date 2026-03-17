from langchain_core.prompts import ChatPromptTemplate

def get_entity_extraction_prompt() -> ChatPromptTemplate:
    """
    Промпт для извлечения сущностей.
    """
    system_message = (
        "Ты — анализатор текста. Твоя единственная задача — извлекать сущности.\n"
        "Ты ДОЛЖЕН отвечать строго в формате JSON.\n"
        "Никаких приветствий, никаких размышлений, никаких тегов <think>.\n\n"
        "{format_instructions}"
    )

    human_message = (
        "Онтология (допустимые типы сущностей):\n"
        "{tbox_schema}\n\n"
        "Правила:\n"
        "1. Извлеки все именованные сущности из текста.\n"
        "2. Используй типы из онтологии. Если ничего не подходит, придумай свой тип (на английском).\n"
        "3. Возвращай только валидный JSON объект с ключом 'entities'.\n\n"
        "Текст:\n"
        "{text}"
    )

    return ChatPromptTemplate.from_messages([
        ("system", system_message),
        ("human", human_message),
    ])