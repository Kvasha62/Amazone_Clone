# ────────────────────────────────────────────────────────────────────────
# apps/users/serializers/__init__.py — реэкспорт сериализаторов.
# 📖 https://docs.python.org/3/tutorial/modules.html#importing-from-a-package
# ────────────────────────────────────────────────────────────────────────

from apps.users.serializers.user_serializers import (
    RegisterInputSerializer,
    ChangePasswordInputSerializer,
    UpdateProfileInputSerializer,
    UserProfileSerializer,
    UserDetailSerializer,
    UserShortSerializer,
)
from apps.users.serializers.address_serializers import (
    AddressInputSerializer,
    AddressOutputSerializer,
)

__all__ = [
    'RegisterInputSerializer',
    'ChangePasswordInputSerializer',
    'UpdateProfileInputSerializer',
    'UserProfileSerializer',
    'UserDetailSerializer',
    'UserShortSerializer',
    'AddressInputSerializer',
    'AddressOutputSerializer',
]
