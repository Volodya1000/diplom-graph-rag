"""
Базовый T-Box — ядро онтологии.

Классы (с иерархией) + допустимые отношения.
"""

from src.domain.ontology.schema import SchemaStatus, SchemaClass, SchemaRelation
# ===================================================================
# КЛАССЫ
# ===================================================================

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
]

# ===================================================================
# ОТНОШЕНИЯ
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
        description="Человек создал продукт / объект",
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
        description="Организация производит продукт",
    ),
    SchemaRelation(
        source_class="Organization",
        relation_name="PART_OF",
        target_class="Organization",
        status=SchemaStatus.CORE,
        description="Организация — часть другой организации",
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
        description="Событие произошло в дату",
    ),
    SchemaRelation(
        source_class="Event",
        relation_name="INVOLVES",
        target_class="Person",
        status=SchemaStatus.CORE,
        description="Событие включает / касается человека",
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
    SchemaRelation(
        source_class="Product",
        relation_name="LOCATED_IN",
        target_class="Location",
        status=SchemaStatus.CORE,
        description="Продукт / объект находится в месте",
    ),
    # --- Concept ---
    SchemaRelation(
        source_class="Concept",
        relation_name="RELATED_TO",
        target_class="Concept",
        status=SchemaStatus.CORE,
        description="Концепция связана с другой концепцией",
    ),
    # --- Animal ---
    SchemaRelation(
        source_class="Animal",
        relation_name="LOCATED_IN",
        target_class="Location",
        status=SchemaStatus.CORE,
        description="Животное находится в месте",
    ),
    SchemaRelation(
        source_class="Animal",
        relation_name="INTERACTS_WITH",
        target_class="Person",
        status=SchemaStatus.CORE,
        description="Животное взаимодействует с человеком",
    ),
    SchemaRelation(
        source_class="Animal",
        relation_name="INTERACTS_WITH",
        target_class="Product",
        status=SchemaStatus.CORE,
        description="Животное взаимодействует с объектом",
    ),
    SchemaRelation(
        source_class="Animal",
        relation_name="INTERACTS_WITH",
        target_class="Animal",
        status=SchemaStatus.CORE,
        description="Животное взаимодействует с другим животным",
    ),
    # --- Универсальные ---
    SchemaRelation(
        source_class="Person",
        relation_name="INTERACTS_WITH",
        target_class="Person",
        status=SchemaStatus.CORE,
        description="Человек взаимодействует с другим человеком",
    ),
    SchemaRelation(
        source_class="Person",
        relation_name="INTERACTS_WITH",
        target_class="Animal",
        status=SchemaStatus.CORE,
        description="Человек взаимодействует с животным",
    ),
    SchemaRelation(
        source_class="Person",
        relation_name="INTERACTS_WITH",
        target_class="Product",
        status=SchemaStatus.CORE,
        description="Человек взаимодействует с объектом",
    ),
]
