# ────────────────────────────────────────────────────────────────────────
# apps/users/admin/user_admin.py — Django Admin для модели User.
#
# Расширяет стандартный BaseUserAdmin (Django) с:
#   • UserProfileInline — встроенный профиль (StackedInline)
#   • Дополнительные поля (phone)
#   • select_related('profile') для оптимизации
#
# 📖 https://docs.djangoproject.com/en/stable/ref/contrib/auth/#django.contrib.auth.admin.UserAdmin
# 📖 https://docs.djangoproject.com/en/stable/ref/contrib/admin/#inlinemodeladmin-objects
# ────────────────────────────────────────────────────────────────────────

from django.contrib import admin
# BaseUserAdmin — стандартный admin для User с fieldsets, filters, ...
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from apps.users.models import User, UserProfile


# StackedInline — вертикальные блоки (подходит для профиля — мало полей).
# TabularInline — горизонтальная таблица (для many items).
# 📖 https://docs.djangoproject.com/en/stable/ref/contrib/admin/#stackedinline
class UserProfileInline(admin.StackedInline):
    """Inline-редактирование профиля внутри страницы User."""
    model = UserProfile
    fk_name = 'user'            # Явно указываем FK (у модели только один)
    can_delete = False          # Нельзя удалить профиль из admin
    verbose_name = 'Профиль'
    verbose_name_plural = 'Профиль'
    fields = (
        'avatar', 'date_of_birth', 'gender',
        'timezone', 'language', 'email_subscribed',
    )


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Расширенный admin для кастомной модели User.
    Наследует все настройки BaseUserAdmin и добавляет phone + profile inline.
    """

    list_display = (
        'id', 'email', 'username', 'full_name',
        'is_active', 'is_staff', 'date_joined',
    )
    # list_display_links — кликабельные колонки (по умолчанию только первая).
    list_display_links = ('email', 'username')
    list_filter = ('is_active', 'is_staff', 'is_superuser')
    search_fields = ('email', 'username', 'first_name', 'last_name', 'phone')
    ordering = ('-date_joined',)

    # fieldsets — группы полей на странице редактирования.
    # BaseUserAdmin.fieldsets — стандартные секции Django (username, password, permissions).
    # Мы ДОБАВЛЯЕМ свою секцию «Дополнительно» с phone.
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Дополнительно', {
            'fields': ('phone',),
        }),
    )

    # add_fieldsets — поля при СОЗДАНИИ пользователя через admin.
    # Базовый: username + password. Добавляем email + phone.
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Дополнительно', {
            'fields': ('email', 'phone'),
        }),
    )

    inlines = (UserProfileInline,)

    def get_queryset(self, request):
        """select_related('profile') — JOIN без N+1."""
        return super().get_queryset(request).select_related('profile')
