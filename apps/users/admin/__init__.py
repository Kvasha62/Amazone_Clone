# ────────────────────────────────────────────────────────────────────────
# apps/users/admin/__init__.py — реэкспорт admin-классов.
# При импорте срабатывает @admin.register — побочный эффект.
# 📖 https://docs.djangoproject.com/en/stable/ref/contrib/admin/
# ────────────────────────────────────────────────────────────────────────

from apps.users.admin.user_admin import UserAdmin
from apps.users.admin.address_admin import AddressAdmin

__all__ = ['UserAdmin', 'AddressAdmin']
