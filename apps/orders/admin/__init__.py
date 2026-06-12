# ────────────────────────────────────────────────────────────────────────
# apps/orders/admin/__init__.py — регистрация моделей в Django Admin.
#
# Django Admin — встроенный CRUD-интерфейс для управления данными.
# Регистрируем Order и OrderItem с кастомным отображением.
#
# 📖 https://docs.djangoproject.com/en/stable/ref/contrib/admin/
# ────────────────────────────────────────────────────────────────────────

from apps.orders.admin.order_admin import OrderAdmin, OrderItemInline

# Явный импорт для автодискавери admin.autodiscover().
# Django автоматически найдёт этот файл и зарегистрирует модели.
