"""
Базовый T-Box — ядро онтологии.

Классы (с иерархией) + допустимые отношения.
LLM может расширять онтологию (DRAFT), но CORE — всегда присутствуют.
"""

from src.domain.models import SchemaClass, SchemaRelation, SchemaStatus

# ===================================================================
# БАЗОВЫЕ КЛАССЫ (с возможной иерархией)
# ===================================================================

BASE_TBOX_CLASSES: list[SchemaClass] = [
    # ---- Верхний уровень ----
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

    # ---- Примеры подклассов (иерархия) ----
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
]

# ===================================================================
# БАЗОВЫЕ ДОПУСТИМЫЕ ОТНОШЕНИЯ
# ===================================================================

BASE_TBOX_RELATIONS: list[SchemaRelation] = [
    # --- Person ---
    SchemaRelation(
        source_class="Person",
        relation_name="WORKS_AT",
        target_class="Organization",
        status=SchemaStatus.CORE,
        description="Человек работает в организации",
    ),
    SchemaRelation(
        source_class="Person",
        relation_name="LOCATED_IN",
        target_class="Location",
        status=SchemaStatus.CORE,
        description="Человек находится / проживает в месте",
    ),
    SchemaRelation(
        source_class="Person",
        relation_name="PARTICIPATED_IN",
        target_class="Event",
        status=SchemaStatus.CORE,
        description="Человек участвовал в событии",
    ),
    SchemaRelation(
        source_class="Person",
        relation_name="CREATED",
        target_class="Product",
        status=SchemaStatus.CORE,
        description="Человек создал продукт / документ",
    ),
    SchemaRelation(
        source_class="Person",
        relation_name="KNOWS",
        target_class="Person",
        status=SchemaStatus.CORE,
        description="Человек знает другого человека",
    ),

    # --- Organization ---
    SchemaRelation(
        source_class="Organization",
        relation_name="LOCATED_IN",
        target_class="Location",
        status=SchemaStatus.CORE,
        description="Организация расположена в месте",
    ),
    SchemaRelation(
        source_class="Organization",
        relation_name="PRODUCES",
        target_class="Product",
        status=SchemaStatus.CORE,
        description="Организация производит / выпускает продукт",
    ),
    SchemaRelation(
        source_class="Organization",
        relation_name="PART_OF",
        target_class="Organization",
        status=SchemaStatus.CORE,
        description="Организация является частью другой организации",
    ),

    # --- Event ---
    SchemaRelation(
        source_class="Event",
        relation_name="OCCURRED_AT",
        target_class="Location",
        status=SchemaStatus.CORE,
        description="Событие произошло в месте",
    ),
    SchemaRelation(
        source_class="Event",
        relation_name="OCCURRED_ON",
        target_class="Date",
        status=SchemaStatus.CORE,
        description="Событие произошло в определённую дату",
    ),

    # --- Product ---
    SchemaRelation(
        source_class="Product",
        relation_name="USES",
        target_class="Concept",
        status=SchemaStatus.CORE,
        description="Продукт использует концепцию / технологию",
    ),
    SchemaRelation(
        source_class="Product",
        relation_name="PRODUCED_BY",
        target_class="Organization",
        status=SchemaStatus.CORE,
        description="Продукт произведён организацией",
    ),

    # --- Concept ---
    SchemaRelation(
        source_class="Concept",
        relation_name="RELATED_TO",
        target_class="Concept",
        status=SchemaStatus.CORE,
        description="Концепция связана с другой концепцией",
    ),
]