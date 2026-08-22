# ────────────────────────────────────────────────────────────────────────
# apps/users/models/__init__.py — реэкспорт моделей пользователей.
#
# Единая точка импорта:
#   from apps.users.models import User, UserProfile, Address
#
# 📖 https://docs.djangoproject.com/en/stable/topics/db/models/#organizing-models-in-a-package
# ────────────────────────────────────────────────────────────────────────

from apps.users.models.user import User
from apps.users.models.user_profile import UserProfile
from apps.users.models.address import Address

__all__ = ['User', 'UserProfile', 'Address']
