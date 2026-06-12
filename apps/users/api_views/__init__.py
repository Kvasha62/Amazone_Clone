# ────────────────────────────────────────────────────────────────────────
# apps/users/api_views/__init__.py — реэкспорт view-классов.
# 📖 https://docs.python.org/3/tutorial/modules.html#importing-from-a-package
# ────────────────────────────────────────────────────────────────────────

from apps.users.api_views.auth_views import RegisterView, ChangePasswordView
from apps.users.api_views.user_views import MeView
from apps.users.api_views.address_views import (
    AddressListView,
    AddressDetailView,
    AddressDefaultView,
)

__all__ = [
    'RegisterView',
    'ChangePasswordView',
    'MeView',
    'AddressListView',
    'AddressDetailView',
    'AddressDefaultView',
]
