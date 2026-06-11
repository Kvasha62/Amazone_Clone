from django.db import models


class BaseModel(models.Model):
    """
    Абстрактная базовая модель проекта.

    Предоставляет:
      - created_at  — дата создания (автоматически)
      - updated_at  — дата последнего обновления (автоматически)

    Контракт для дочерних моделей:
      - Meta.ordering — ДОЛЖНА быть определена явно в каждой конкретной модели.
        BaseModel намеренно НЕ задаёт ordering по умолчанию, потому что:
          1. Глобальный ordering на крупных таблицах замедляет запросы.
          2. Разным моделям нужен разный порядок.
          3. Отсутствие ordering — немедленный UnorderedObjectListWarning
             в админке (видно на раннем этапе, а не на проде).
      - Meta.verbose_name / verbose_name_plural — рекомендуется задавать
        в каждой модели для читаемости в админке.
    """

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Создано',
        db_index=True,           # индекс для ORDER BY / фильтрации по дате
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Обновлено',
        # db_index не нужен — updated_at редко используется в ORDER BY / WHERE
    )

    class Meta:
        abstract = True
        get_latest_by = ('created_at',)     # позволяет .latest() / .earliest() без аргументов
