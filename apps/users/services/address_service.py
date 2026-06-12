# ────────────────────────────────────────────────────────────────────────
# apps/users/services/address_service.py — бизнес-логика адресов доставки.
#
# МЕТОДЫ:
#   create_address() — создание с лимитом MAX_ADDRESSES_PER_USER
#   update_address() — частичное обновление (kwargs)
#   delete_address() — удаление с проверкой ownership
#   set_default()    — установка адреса по умолчанию
#   list_addresses() — список адресов пользователя
#
# БЕЗОПАСНОСТЬ:
#   Все методы принимают user → проверяют что адрес принадлежит пользователю.
#   Другой пользователь не может изменить/удалить чужой адрес (IDOR protection).
#   📖 https://cheatsheetseries.owasp.org/cheatsheets/Insecure_Direct_Object_Reference_Prevention_Cheat_Sheet.html
#
# 📖 https://docs.djangoproject.com/en/stable/topics/db/transactions/
# 📖 https://www.django-rest-framework.org/api-guide/exceptions/
# ────────────────────────────────────────────────────────────────────────

from __future__ import annotations

import logging

from django.db import transaction
from rest_framework.exceptions import NotFound, ValidationError

# MAX_ADDRESSES_PER_USER — лимит адресов (10).
from apps.users.constants import MAX_ADDRESSES_PER_USER

# Address — модель адреса доставки.
from apps.users.models import Address

logger = logging.getLogger(__name__)


class AddressService:
    """Сервис для работы с адресами доставки."""

    @staticmethod
    @transaction.atomic
    def create_address(
        user,
        *,
        recipient_name: str,
        country: str = 'Россия',
        region: str = '',
        city: str,
        street: str,
        postal_code: str = '',
        notes: str = '',
        is_default: bool = False,
    ) -> Address:
        """
        Создаёт новый адрес доставки.

        Проверяет лимит MAX_ADDRESSES_PER_USER (10).
        Если is_default=True → Address.save() снимет default с других.

        *, — заставляет передавать ВСЕ аргументы (кроме user) по имени.
        Без: create_address(user, 'Иван', 'Россия', ...) — что есть что?
        С: create_address(user, recipient_name='Иван', ...) — явно.
        """
        # Проверяем лимит ДО создания — быстро, без JOIN.
        current_count = Address.objects.filter(user=user).count()
        if current_count >= MAX_ADDRESSES_PER_USER:
            raise ValidationError({
                'detail': (
                    f'Максимум адресов — {MAX_ADDRESSES_PER_USER}. '
                    'Удалите ненужный адрес перед добавлением нового.'
                ),
            })

        address = Address(
            user=user,
            recipient_name=recipient_name,
            country=country,
            region=region,
            city=city,
            street=street,
            postal_code=postal_code,
            notes=notes,
            is_default=is_default,
        )
        # full_clean() — вызывает validators + clean() (CheckConstraint на Python).
        # 📖 https://docs.djangoproject.com/en/stable/ref/models/instances/#django.db.models.Model.full_clean
        address.full_clean()
        # save() — снимает is_default с других адресов (переопределённый save).
        address.save()

        logger.info(
            'address_created',
            extra={'user_id': user.pk, 'address_id': address.pk},
        )
        return address

    @staticmethod
    @transaction.atomic
    def update_address(
        user,
        address_id: int,
        **kwargs,
    ) -> Address:
        """
        Обновляет адрес доставки.
        Передавать только те поля, которые нужно изменить.

        **kwargs — произвольные именованные аргументы:
          update_address(user, 5, city='Казань', street='ул. Новая')
        """
        # Проверяем ownership: get(pk=address_id, user=user)
        # Если адрес чужой → DoesNotExist → NotFound.
        try:
            address = Address.objects.get(pk=address_id, user=user)
        except Address.DoesNotExist:
            raise NotFound('Адрес не найден.')

        # Whitelist полей — защита от передачи служебных полей.
        # Без whitelist: kwargs={'user': other_user} → сменит владельца!
        updatable_fields = {
            'recipient_name', 'country', 'region', 'city',
            'street', 'postal_code', 'notes', 'is_default',
        }

        # Собираем изменённые поля для update_fields.
        update_fields = []
        for field, value in kwargs.items():
            if field in updatable_fields:
                setattr(address, field, value)
                update_fields.append(field)

        if update_fields:
            address.full_clean()
            # save() — снимает is_default с других если is_default=True.
            address.save()

        logger.info(
            'address_updated',
            extra={'user_id': user.pk, 'address_id': address_id},
        )
        return address

    @staticmethod
    @transaction.atomic
    def delete_address(user, address_id: int) -> None:
        """
        Удаляет адрес доставки.

        filter(pk=address_id, user=user) — IDOR protection:
          нельзя удалить чужой адрес.
        .delete() — возвращает (count, details).
        """
        deleted, _ = Address.objects.filter(pk=address_id, user=user).delete()
        if not deleted:
            raise NotFound('Адрес не найден.')

        logger.info(
            'address_deleted',
            extra={'user_id': user.pk, 'address_id': address_id},
        )

    @staticmethod
    @transaction.atomic
    def set_default(user, address_id: int) -> Address:
        """
        Устанавливает адрес как адрес по умолчанию.

        address.is_default = True → address.save()
        → save() снимает is_default с других адресов.
        """
        try:
            address = Address.objects.get(pk=address_id, user=user)
        except Address.DoesNotExist:
            raise NotFound('Адрес не найден.')

        address.is_default = True
        # update_fields=['is_default'] — но save() также снимет default
        # с других адресов через переопределённый метод save().
        address.save(update_fields=['is_default'])

        logger.info(
            'address_set_default',
            extra={'user_id': user.pk, 'address_id': address_id},
        )
        return address

    @staticmethod
    def list_addresses(user):
        """
        Возвращает все адреса пользователя.
        Сортировка: сначала default, потом по дате создания.
        """
        return Address.objects.filter(user=user).order_by(
            '-is_default', '-created_at',
        )
