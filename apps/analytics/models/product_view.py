# ────────────────────────────────────────────────────────────────────────
# apps/analytics/models/product_view.py — просмотр товара.
#
# БИЗНЕС-ТРЕБОВАНИЯ:
#   • Запись каждого просмотра товара (страница товара открыта)
#   • Дедупликация: один просмотр на сессию/пользователя в час
#   • Источник трафика (organic, search, social, referral, direct)
#   • User-Agent для аналитики устройств
#   • Обновление denormalized Product.views_count
#
# АРХИТЕКТУРНЫЕ РЕШЕНИЯ:
#   • session_key — для анонимных пользователей (cookie-based)
#   • user — nullable (анонимы тоже просматривают)
#   • Нет FK к Order — аналитика просмотров независима от заказов
#
# ПОЧЕМУ ОТДЕЛЬНАЯ ТАБЛИЦА, А НЕ ТОЛЬКО views_count:
#   views_count — денормализованный счётчик (быстрый SELECT).
#   ProductView — журнал просмотров (для аналитики по времени,
#   источникам, устройствам). Можно агрегировать: «сколько просмотров
#   за неделю», «сколько из поиска» и т.д.
#
# 📖 https://docs.djangoproject.com/en/stable/ref/models/fields/
#
# ЧТО БУДЕТ, ЕСЛИ УДАЛИТЬ ФАЙЛ:
#   • Невозможно отслеживать просмотры товаров
#   • Конверсия (просмотры → заказы) не считается
# ────────────────────────────────────────────────────────────────────────

from django.conf import settings
from django.db import models

from apps.core.models.base_model import BaseModel
from apps.analytics.constants import (
    MAX_SESSION_KEY_LENGTH,
    MAX_USER_AGENT_LENGTH,
    SOURCE_CHOICES,
    SOURCE_DIRECT,
)
from apps.analytics.managers.product_view_manager import ProductViewManager


class ProductView(BaseModel):
    """
    Просмотр товара пользователем или гостем.

    Каждая запись = один просмотр страницы товара.
    Дедупликация в ProductViewService.record_view():
      один пользователь/сессия → один просмотр в час.

    СВЯЗИ:
      • Product (FK) — просмотренный товар
      • User (FK, nullable) — кто просмотрел (null = гость)
    """

    objects = ProductViewManager()

    # ── Товар ──
    product = models.ForeignKey(
        'catalog.Product',
        on_delete=models.CASCADE,
        related_name='views',
        verbose_name='Товар',
    )

    # ── Пользователь (nullable для анонимов) ──
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='product_views',
        verbose_name='Пользователь',
    )

    # ── Ключ сессии (для анонимов) ──
    # Django session framework хранит session_key в cookie.
    # Для авторизованных — тоже сохраняем (доп. аналитика).
    session_key = models.CharField(
        verbose_name='Ключ сессии',
        max_length=MAX_SESSION_KEY_LENGTH,
        blank=True,
        default='',
        db_index=True,
    )

    # ── Источник трафика ──
    source = models.CharField(
        verbose_name='Источник',
        max_length=20,
        choices=SOURCE_CHOICES,
        default=SOURCE_DIRECT,
        db_index=True,
    )

    # ── IP-адрес ──
    # Для геоаналитики (город, страна) и защиты от накруток.
    # null = IP не определён (прокси, тесты).
    ip_address = models.GenericIPAddressField(
        verbose_name='IP-адрес',
        null=True,
        blank=True,
    )

    # ── User-Agent ──
    # Для определения устройства (mobile/desktop) и браузера.
    user_agent = models.CharField(
        verbose_name='User-Agent',
        max_length=MAX_USER_AGENT_LENGTH,
        blank=True,
        default='',
    )

    class Meta:
        verbose_name = 'Просмотр товара'
        verbose_name_plural = 'Просмотры товаров'
        ordering = ('-created_at',)
        indexes = [
            # Составной индекс (product, created_at) — для запросов:
            #   «просмотры товара X за последний месяц»
            models.Index(
                fields=['product', 'created_at'],
                name='prodview_prod_created_idx',
            ),
            # Индекс по (source, created_at) — для отчётов по источникам:
            #   «сколько просмотров из поиска за неделю»
            models.Index(
                fields=['source', 'created_at'],
                name='prodview_src_created_idx',
            ),
            # Индекс по session_key + product — для дедупликации
            models.Index(
                fields=['session_key', 'product'],
                name='prodview_sess_prod_idx',
            ),
        ]

    def __str__(self):
        viewer = f'user#{self.user_id}' if self.user_id else f'session={self.session_key[:8]}'
        return f'View(product={self.product_id}, {viewer})'
