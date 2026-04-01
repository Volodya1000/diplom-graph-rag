"""
Базовый T-Box — ядро онтологии.

"""

from src.domain.ontology.schema import SchemaStatus, SchemaClass

BASE_TBOX_CLASSES: list[SchemaClass] = [
    # ---- Верхний уровень ----
    SchemaClass(
        name="Person",
        status=SchemaStatus.CORE,
        description="Люди: персоналии, должностные лица, авторы, персонажи",
    ),
    SchemaClass(
        name="Organization",
        status=SchemaStatus.CORE,
        description="Организации: компании, учреждения, ведомства",
    ),
    SchemaClass(
        name="Location",
        status=SchemaStatus.CORE,
        description="Места: города, страны, здания, географические объекты",
    ),
    SchemaClass(
        name="Date",
        status=SchemaStatus.CORE,
        description="Даты: конкретные даты, периоды, сроки",
    ),
    SchemaClass(
        name="Event",
        status=SchemaStatus.CORE,
        description="События: мероприятия, инциденты, встречи, действия",
    ),
    SchemaClass(
        name="Product",
        status=SchemaStatus.CORE,
        description="Продукты: изделия, объекты, еда, предметы, документы",
    ),
    SchemaClass(
        name="Concept",
        status=SchemaStatus.CORE,
        description="Понятия: термины, методы, технологии, абстракции",
    ),
    SchemaClass(
        name="Animal",
        status=SchemaStatus.CORE,
        description="Животные: реальные или персонажи-животные",
    ),
    # ---- Подклассы ----
    SchemaClass(
        name="GovernmentOrg",
        status=SchemaStatus.CORE,
        description="Государственные организации и ведомства",
        parent="Organization",
    ),
    SchemaClass(
        name="Company",
        status=SchemaStatus.CORE,
        description="Коммерческие компании и предприятия",
        parent="Organization",
    ),
    SchemaClass(
        name="Technology",
        status=SchemaStatus.CORE,
        description="Технологии, фреймворки, языки программирования",
        parent="Concept",
    ),
    SchemaClass(
        name="TimePeriod",
        status=SchemaStatus.CORE,
        parent="Date",
        description="Временные интервалы: периоды, сроки, эпохи, диапазоны дат",
    ),
    SchemaClass(
        name="Address",
        status=SchemaStatus.CORE,
        parent="Location",
        description="Конкретный адрес, координаты, помещение, офис",
    ),
    SchemaClass(
        name="Role",
        status=SchemaStatus.CORE,
        description="Должность, роль, профессия (CEO, разработчик, директор и т.д.)",
    ),
    SchemaClass(
        name="Project",
        status=SchemaStatus.CORE,
        description="Проекты, инициативы, программы, задачи",
    ),
    SchemaClass(
        name="Document",
        status=SchemaStatus.CORE,
        description="Документы, контракты, публикации, отчёты",
    ),
    SchemaClass(
        name="Startup",
        status=SchemaStatus.CORE,
        parent="Company",
        description="Стартапы и молодые компании",
    ),
    SchemaClass(
        name="Subsidiary",
        status=SchemaStatus.CORE,
        parent="Company",
        description="Дочерние компании и филиалы",
    ),
]
