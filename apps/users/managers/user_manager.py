# ────────────────────────────────────────────────────────────────────────
# apps/users/managers/user_manager.py — менеджер модели User.
#
# Наследует BaseUserManager (Django) — сохраняет:
#   • create_user(username, email, password) — хэширует пароль
#   • create_superuser(username, email, password) — + is_staff, is_superuser
#   • normalize_email() — приводит домен к lowercase
#
# from_queryset(UserQuerySet) — добавляет методы QuerySet:
#   User.objects.with_profile(), .active(), .by_email(), .full()
#
# 📖 https://docs.djangoproject.com/en/stable/topics/auth/customizing/#writing-a-manager-for-the-custom-user-model
# 📖 https://docs.djangoproject.com/en/stable/topics/db/managers/#from-queryset
# ────────────────────────────────────────────────────────────────────────

# BaseUserManager — стандартный Django менеджер с create_user / create_superuser.
# 📖 https://docs.djangoproject.com/en/stable/topics/auth/customizing/#django.contrib.auth.models.BaseUserManager
from django.contrib.auth.models import UserManager as BaseUserManager

# UserQuerySet — методы цепочки (with_profile, active, by_email, ...).
from apps.users.querysets.user_queryset import UserQuerySet


# BaseUserManager.from_queryset(UserQuerySet) — динамика:
#   Создаёт новый класс, содержащий и методы BaseUserManager,
#   и методы UserQuerySet (как прокси через get_queryset()).
# 📖 https://docs.djangoproject.com/en/stable/topics/db/managers/#django.db.models.Manager.from_queryset
class UserManager(BaseUserManager.from_queryset(UserQuerySet)):
    """
    Менеджер пользователя.

    Наследует стандартный UserManager (create_user, create_superuser)
    и добавляет QuerySet-методы (with_profile, active, full, ...).
    """
    pass
