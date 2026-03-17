"""
Базовый T-Box — ядро онтологии.

Эти классы представляют универсальные типы сущностей,
которые подходят для большинства документов.
LLM может добавлять новые типы (со статусом DRAFT),
но базовые (CORE) всегда присутствуют.
"""

from src.domain.models import SchemaClass, SchemaStatus

BASE_TBOX_CLASSES: list[SchemaClass] = [
    SchemaClass(
        name="Person",
        status=SchemaStatus.CORE,
        description="Люди: персоналии, должностные лица, авторы, специалисты",
    ),
    SchemaClass(
        name="Organization",
        status=SchemaStatus.CORE,
        description="Организации: компании, учреждения, ведомства, подразделения",
    ),
    SchemaClass(
        name="Location",
        status=SchemaStatus.CORE,
        description="Места: города, страны, регионы, адреса, географические объекты",
    ),
    SchemaClass(
        name="Date",
        status=SchemaStatus.CORE,
        description="Даты: конкретные даты, временные периоды, сроки, дедлайны",
    ),
    SchemaClass(
        name="Event",
        status=SchemaStatus.CORE,
        description="События: мероприятия, заседания, инциденты, процессы",
    ),
    SchemaClass(
        name="Product",
        status=SchemaStatus.CORE,
        description="Продукты: изделия, системы, ПО, документы, стандарты, нормативные акты",
    ),
    SchemaClass(
        name="Concept",
        status=SchemaStatus.CORE,
        description="Понятия: термины, методы, технологии, абстрактные концепции",
    ),
]