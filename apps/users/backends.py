# ────────────────────────────────────────────────────────────────────────
# apps/users/backends.py — кастомный authentication backend.
#
# 🔴 ПРОБЛЕМА: Django по умолчанию authenticate() ищет по username.
# Наш User логинится по email. Нужно чтобы authenticate(username=email)
# искал пользователя по полю email.
#
# КАК РАБОТАЕТ:
#   authenticate(username="ivan@example.com", password="secret")
#     → User.objects.get(email="ivan@example.com")
#     → user.check_password("secret")
#
# 📖 https://docs.djangoproject.com/en/stable/topics/auth/customizing/#writing-an-authentication-backend
# ────────────────────────────────────────────────────────────────────────

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class EmailOrUsernameModelBackend(ModelBackend):
    """
    Authentication backend, позволяющий логин по email ИЛИ username.

    АЛГОРИТМ:
      1. Если username содержит '@' — ищем по email
      2. Иначе — по username
      3. Проверяем пароль

    Это позволяет:
      • React: POST {email, password} → логин по email
      • Django Admin: логин по username (как обычно)
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        UserModel = get_user_model()

        if username is None or password is None:
            return None

        try:
            if '@' in username:
                # Email login
                user = UserModel.objects.get(email__iexact=username)
            else:
                # Username login (Django Admin)
                user = UserModel.objects.get(username=username)
        except UserModel.DoesNotExist:
            # Запускаем хэширование чтобы timing-атака не работала
            UserModel().set_password(password)
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user

        return None
