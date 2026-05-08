"""Базовый T-Box — ядро онтологии."""

from src.domain.ontology.schema import SchemaClass, SchemaStatus

BASE_TBOX_CLASSES: list[SchemaClass] = [
    # ---- Верхний уровень ----
    SchemaClass(
        name="Person",
        status=SchemaStatus.CORE,
        description="Люди: персоналии, должностные лица, авторы, персонажи",
    ),
    SchemaClass(
        name="PhysicalPerson",
        status=SchemaStatus.CORE,
        parent="Person",
        description="Физическое лицо",
    ),
    SchemaClass(
        name="LegalEntity",
        status=SchemaStatus.CORE,
        description="Юридическое лицо: организация, компания, ведомство, учреждение",
    ),
    SchemaClass(
        name="Organization",
        status=SchemaStatus.CORE,
        parent="LegalEntity",
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
        name="Process",
        status=SchemaStatus.CORE,
        description="Бизнес-процессы, процедуры, workflow",
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
        name="System",
        status=SchemaStatus.CORE,
        description="Система: организационная, информационная или IT-система",
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
        name="LegalAct",
        status=SchemaStatus.CORE,
        parent="Document",
        description="Нормативно-правовой акт: закон, указ, декрет",
    ),
    SchemaClass(
        name="Regulation",
        status=SchemaStatus.CORE,
        parent="Document",
        description="Локальный нормативный акт, положение, инструкция",
    ),
    SchemaClass(
        name="Technology",
        status=SchemaStatus.CORE,
        parent="Concept",
        description="Технологии, фреймворки, языки программирования",
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
