from django.db import models
from django.core.exceptions import ValidationError

from treebeard.mp_tree import MP_Node

from apps.catalog.services.slug_service import generate_unique_slug
from apps.core.models import BaseModel


# ==========================================================
# КАТЕГОРИИ
# ==========================================================

class Category(MP_Node, BaseModel):
    """
    Иерархическая модель категорий на django-treebeard (Materialized Path).

    Служебные поля от MP_Node (создаются автоматически миграцией):
        path      — внутренний путь в дереве (НЕ URL, формат вида '00010002')
        depth     — глубина (1 = корень)
        numchild  — количество прямых детей

    Иерархия управляется ТОЛЬКО методами treebeard:
        Category.add_root(name=...)
        node.add_child(name=...)
        node.move(target, pos='last-child')

    Обычный Category.objects.create(...) использовать НЕЛЬЗЯ —
    treebeard не будет знать, куда вставить узел в дереве.
    """

    # ----------------------------------------------------------
    # Основные поля
    # ----------------------------------------------------------

    name = models.CharField(
        'Название',
        max_length=200,
        db_index=True,
    )

    slug = models.SlugField(
        'Слаг',
        unique=True,
        blank=True,
        null=True,
        db_index=True,
    )

    is_active = models.BooleanField(
        'Активна',
        default=True,
        db_index=True,
    )

    meta_title = models.CharField(
        'SEO title',
        max_length=255,
        blank=True,
    )

    meta_description = models.TextField(
        'SEO description',
        blank=True,
    )

    # ----------------------------------------------------------
    # Денормализованные поля для скорости
    # ----------------------------------------------------------

    # URL-путь из slug'ов: 'electronics/phones/smartphones'.
    # Системное поле path от MP_Node имеет другой формат, поэтому храним отдельно.
    url_path = models.CharField(
        'URL-путь',
        max_length=1000,
        editable=False,
        db_index=True,
        blank=True,
    )

    # Кэш полного имени: 'Электроника → Телефоны → Смартфоны'.
    # Позволяет выводить full_name без единого SQL-запроса.
    full_name_cached = models.CharField(
        'Полное название',
        max_length=2000,
        editable=False,
        blank=True,
    )

    # ----------------------------------------------------------
    # Конфигурация treebeard
    # ----------------------------------------------------------

    # Автосортировка новых узлов по name внутри одного уровня.
    # Пока задано node_order_by — нельзя руками менять позицию через move(pos='left/right'),
    # treebeard сам ставит узел в нужное место.
    node_order_by = ['name']

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'
        # ordering НЕ задаём: treebeard сортирует по своему системному path,
        # иначе ломаются обходы дерева.

    # ----------------------------------------------------------
    # Представление
    # ----------------------------------------------------------

    def __str__(self):
        return self.name

    @property
    def full_name(self):
        """Полное имя из кэша — 0 SQL-запросов."""
        return self.full_name_cached or self.name

    # ----------------------------------------------------------
    # Валидация
    # ----------------------------------------------------------

    def clean(self):
        """
        treebeard сам не даёт создать цикл (move() валидирует),
        но оставляем явную проверку на случай прямых манипуляций.
        """
        super().clean()

        if self.pk and not self.is_root():
            parent = self.get_parent()
            if parent and parent.pk == self.pk:
                raise ValidationError(
                    'Категория не может быть родителем самой себе.'
                )

    # ----------------------------------------------------------
    # Построение денормализованных полей
    # ----------------------------------------------------------

    def _build_url_path(self):
        """Собирает URL-путь из slug родителя + своего slug."""
        if self.is_root():
            return self.slug or ''
        parent = self.get_parent()
        parent_path = parent.url_path if parent else ''
        if parent_path:
            return f'{parent_path}/{self.slug}'
        return self.slug or ''

    def _build_full_name(self):
        """Собирает 'Корень → ... → Я'. Использует кэш родителя, если он есть."""
        if self.is_root():
            return self.name
        parent = self.get_parent()
        if parent and parent.full_name_cached:
            return f'{parent.full_name_cached} → {self.name}'
        # Фолбэк: один запрос на всех предков
        ancestors = list(self.get_ancestors()) + [self]
        return ' → '.join(a.name for a in ancestors)

    def _refresh_descendants(self):
        """
        Пересчитывает url_path и full_name_cached для всех потомков.
        Вызывается после переименования или перемещения узла.

        get_descendants() отдаёт потомков, отсортированных по системному path,
        то есть родитель всегда раньше своих детей — можем строить кэш на лету.
        """
        cache = {self.pk: (self.url_path, self.full_name_cached)}
        updates = []

        for node in self.get_descendants():
            parent = node.get_parent()
            parent_url, parent_full = cache[parent.pk]

            node.url_path = (
                f'{parent_url}/{node.slug}' if parent_url else (node.slug or '')
            )
            node.full_name_cached = f'{parent_full} → {node.name}'

            cache[node.pk] = (node.url_path, node.full_name_cached)
            updates.append(node)

        if updates:
            Category.objects.bulk_update(
                updates,
                fields=['url_path', 'full_name_cached'],
                batch_size=500,
            )

    # ----------------------------------------------------------
    # Сохранение
    # ----------------------------------------------------------

    def save(self, *args, **kwargs):
        # 1. Генерируем slug, если пустой
        if not self.slug:
            self.slug = generate_unique_slug(self, self.name)

        # 2. Запоминаем старые slug/name — чтобы понять, нужно ли пересчитывать потомков
        old_slug = None
        old_name = None
        if self.pk:
            old = (
                Category.objects
                .filter(pk=self.pk)
                .only('slug', 'name')
                .first()
            )
            if old:
                old_slug = old.slug
                old_name = old.name

        # 3. Считаем кэш ДО сохранения — один UPDATE вместо двух.
        #    Возможно только если узел уже в дереве (treebeard уже выставил path).
        if self.pk and getattr(self, 'path', None):
            self.url_path = self._build_url_path()
            self.full_name_cached = self._build_full_name()

        # 4. Валидация
        self.full_clean()

        # 5. Сохраняем сам объект
        super().save(*args, **kwargs)

        # 6. Если slug или name изменились — каскадно обновляем потомков
        if self.pk and (old_slug != self.slug or old_name != self.name):
            self._refresh_descendants()

    # ----------------------------------------------------------
    # Перемещение узла с обновлением кэша поддерева
    # ----------------------------------------------------------

    def move(self, target, pos=None):
        """
        После смены родителя обновляем url_path и full_name_cached
        и у самого узла, и у всех его потомков.
        """
        super().move(target, pos=pos)

        # treebeard поменял системные path/depth — перечитываем из БД.
        refreshed = Category.objects.get(pk=self.pk)
        refreshed.url_path = refreshed._build_url_path()
        refreshed.full_name_cached = refreshed._build_full_name()
        Category.objects.filter(pk=refreshed.pk).update(
            url_path=refreshed.url_path,
            full_name_cached=refreshed.full_name_cached,
        )
        refreshed._refresh_descendants()

