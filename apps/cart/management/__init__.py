# ────────────────────────────────────────────────────────────────────────
# apps/cart/management/__init__.py
#
# Превращает management/ в Python-пакет.
# Django ищет management/commands/ для обнаружения кастомных команд.
# Без этого файла: python manage.py cleanup_expired_carts → Unknown command
# 📖 https://docs.djangoproject.com/en/stable/howto/custom-management-commands/
# ────────────────────────────────────────────────────────────────────────
