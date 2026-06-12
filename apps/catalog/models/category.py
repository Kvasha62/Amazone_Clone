# ==============================================================================
# apps/catalog/models/category.py — Иерархическая категория
# ==============================================================================
# Использует django-treebeard MP_Node (Materialized Path).
#
# Что такое Materialized Path:
#   Каждая категория хранит полный путь от корня:
#     Корень «Электроника»       → path='0001', depth=1
#     Ребёнок «Телефоны»         → path='00010001', depth=2
#     Внук «Смартфоны»           → path='000100010001', depth=3
#
#   Это позволяет:
#     - Получить всех предков за 1 запрос: WHERE path LIKE '00010001%'
#     - Получить поддерево за 1 запрос
#     - Перемещать узлы атомарно (UPDATE path)
#
# Альтернативы:
#   Adjacency List (parent_id) — простой, но рекурсивные запросы.
#   Nested Sets (lft/rgt) — быстрые чтения, медленные записи.
#   Materialized Path — баланс обоих миров.
#
# ВАЖНО: создание категорий — ТОЛЬКО через treebeard API:
#   Category.add_root(name='Электроника')
#   parent.add_child(name='Телефоны')
#   Category.objects.create(...) — ЗАПРЕЩЕНО: treebeard не обновит дерево.
#
# Денормализованные кэши:
#   url_path         — 'electronics/phones/smartphones' (из slug'ов)
#   full_name_cached — 'Электроника → Телефоны → Смартфоны'
#   Обновляются автоматически в save() и move().
# ==============================================================================

from django.core.exceptions import ValidationError
from django.db import models

# treebeard MP_Node — абстрактная модель, добавляет поля:
#   path     — varchar, уникальный путь в дереве
#   depth    — int, глубина (1 = корень)
#   numchild — int, количество прямых потомков
from treebeard.mp_tree import MP_Node

from apps.catalog.services.slug_service import generate_unique_slug
from apps.core.models import BaseModel


class Category(MP_Node, BaseModel):
    """
    Иерархическая категория (django-treebeard, Materialized Path).

    Создание / перемещение — ТОЛЬКО через treebeard API:
        Category.add_root(name='Электроника')
        node.add_child(name='Телефоны')
        node.move(target, pos='last-child')

    Category.objects.create(...) — ЗАПРЕЩЕНО: treebeard не обновит дерево.
    """

    # ------------------------------------------------------------------
    # Основные поля
    # ------------------------------------------------------------------

    name = models.CharField(
        'Название',
        max_length=200,
    )

    # slug для URL: /catalog/electronics/phones/
    # unique=True — глобально уникальный (не только внутри родителя)
    # blank=True — заполняется автоматически в save()
    # null=True — для совместимости с treebeard (пока не сохранён)
    slug = models.SlugField(
        'Слаг',
        unique=True,
        blank=True,
        null=True,
    )

    description = models.TextField(
        'Описание',
        blank=True,
    )

    image = models.ImageField(
        'Изображение',
        upload_to='categories/%Y/%m/',
        null=True,
        blank=True,
    )

    is_active = models.BooleanField(
        'Активна',
        default=True,
        db_index=True,
    )

    # ------------------------------------------------------------------
    # SEO-поля
    # ------------------------------------------------------------------

    meta_title = models.CharField(
        'SEO title',
        max_length=255,
        blank=True,
    )

    meta_description = models.TextField(
        'SEO description',
        blank=True,
    )

    # ------------------------------------------------------------------
    # Денормализованные кэши
    # ------------------------------------------------------------------
    # editable=False — нельзя редактировать вручную в admin.
    # Вычисляются автоматически из slug/name предков.
    #
    # Зачем: чтобы показать breadcrumbs «Электроника → Телефоны»
    # без 3 SQL-запросов к предкам — читаем одно поле.
    # ------------------------------------------------------------------

    url_path = models.CharField(
        'URL-путь',
        max_length=1000,
        editable=False,
        db_index=True,    # поиск по URL: WHERE url_path LIKE 'electronics/%'
        blank=True,
    )

    full_name_cached = models.CharField(
        'Полное название',
        max_length=2000,
        editable=False,
        blank=True,
    )

    # ------------------------------------------------------------------
    # treebeard: сортировка потомков одного родителя
    # ------------------------------------------------------------------
    # node_order_by определяет порядок siblings (братьев) в дереве.
    # По имени — логично для каталога (алфавитный порядок).
    # ------------------------------------------------------------------
    node_order_by = ['name']

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'

    # ----------------------------------------------------------
    # Представление
    # ----------------------------------------------------------

    def __str__(self) -> str:
        return self.name

    @property
    def full_name(self) -> str:
        """Полное имя из кэша — 0 SQL-запросов."""
        return self.full_name_cached or self.name

    def get_absolute_url(self) -> str:
        """URL категории: /catalog/electronics/phones/."""
        return f'/catalog/{self.url_path}/'

    # ----------------------------------------------------------
    # Валидация
    # ----------------------------------------------------------

    def clean(self):
        # Защита от самоссылки: категория не может быть родителем самой себе.
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
    # Методы ниже строят url_path и full_name_cached
    # из slug'ов и названий предков.
    #
    # Вызываются в save() и move() — автоматически.
    # ----------------------------------------------------------

    def _build_url_path(self) -> str:
        """Склеивает slug'и всех предков через '/'."""
        if self.is_root():
            return self.slug or ''
        parent = self.get_parent()
        parent_path = parent.url_path if parent else ''
        if parent_path:
            return f'{parent_path}/{self.slug}'
        return self.slug or ''

    def _build_full_name(self) -> str:
        """Склеивает названия предков через ' → '."""
        if self.is_root():
            return self.name
        parent = self.get_parent()
        if parent and parent.full_name_cached:
            return f'{parent.full_name_cached} → {self.name}'
        # Fallback: если кэш пуст — перечитываем предков
        ancestors = list(self.get_ancestors()) + [self]
        return ' → '.join(a.name for a in ancestors)

    def _refresh_descendants(self) -> None:
        """
        Пересчитывает url_path / full_name_cached у ВСЕХ потомков.

        Вызывается при изменении slug или name у родителя —
        каскадное обновление дочерних путей.

        Использует bulk_update — один SQL-запрос вместо N.
        batch_size=500 — баланс между памятью и скоростью.
        """
        cache = {self.pk: (self.url_path, self.full_name_cached)}
        updates = []

        for node in self.get_descendants():
            parent = node.get_parent()
            parent_url, parent_full = cache.get(
                parent.pk,
                (parent.url_path, parent.full_name_cached),
            )

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

    def _rebuild_caches(self):
        """Пересчитывает url_path и full_name_cached для этого узла."""
        if self.pk and getattr(self, 'path', None):
            self.url_path = self._build_url_path()
            self.full_name_cached = self._build_full_name()
            Category.objects.filter(pk=self.pk).update(
                url_path=self.url_path,
                full_name_cached=self.full_name_cached,
            )

    # ----------------------------------------------------------
    # Сохранение
    # ----------------------------------------------------------

    def save(self, *args, **kwargs):
        is_new = not self.pk

        # 1. Генерация slug из name
        if not self.slug:
            self.slug = generate_unique_slug(self, self.name)

        # 2. Запоминаем старые slug/name (для каскадного обновления)
        old_slug = None
        old_name = None
        if not is_new:
            old = (
                Category.objects
                .filter(pk=self.pk)
                # .only() — читаем ТОЛЬКО slug и name,
                # а не все поля (оптимизация)
                .only('slug', 'name')
                .first()
            )
            if old:
                old_slug = old.slug
                old_name = old.name

        # 3. Кэш — считаем ДО сохранения (если узел уже в дереве)
        if self.pk and getattr(self, 'path', None):
            self.url_path = self._build_url_path()
            self.full_name_cached = self._build_full_name()

        # super().save() — treebeard обновляет path, depth, numchild
        super().save(*args, **kwargs)

        # 4. После ПЕРВОГО сохранения — treebeard назначил path/pk.
        #    Теперь можно построить кэш (до save() pk был None).
        if is_new and self.pk and getattr(self, 'path', None):
            self.url_path = self._build_url_path()
            self.full_name_cached = self._build_full_name()
            Category.objects.filter(pk=self.pk).update(
                url_path=self.url_path,
                full_name_cached=self.full_name_cached,
            )

        # 5. Каскадное обновление потомков при изменении slug/name.
        #    Если переименовали «Телефоны» → «Мобильные»,
        #    все дети обновят full_name_cached.
        if not is_new and (old_slug != self.slug or old_name != self.name):
            self._refresh_descendants()

    # ----------------------------------------------------------
    # Перемещение узла
    # ----------------------------------------------------------

    def move(self, target, pos=None):
        """
        Перемещает узел в дереве.

        После перемещения пересчитывает кэши
        для себя и всех потомков.
        """
        # super().move() — treebeard обновляет path, depth
        super().move(target, pos=pos)

        # Перечитываем из БД — treebeard изменил path
        refreshed = Category.objects.get(pk=self.pk)
        refreshed.url_path = refreshed._build_url_path()
        refreshed.full_name_cached = refreshed._build_full_name()
        Category.objects.filter(pk=refreshed.pk).update(
            url_path=refreshed.url_path,
            full_name_cached=refreshed.full_name_cached,
        )
        # Каскад на потомков
        refreshed._refresh_descendants()
