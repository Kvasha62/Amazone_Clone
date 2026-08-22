"""
Тесты AddressService — бизнес-логика адресов.
"""
from django.test import TestCase
from rest_framework.exceptions import NotFound, ValidationError

from apps.users.models import Address
from apps.users.services.address_service import AddressService
from apps.users.tests.factories import UserTestCase


class CreateAddressTests(UserTestCase):

    def test_create_address(self):
        address = AddressService.create_address(
            self.user,
            recipient_name='Иван Тестов',
            city='Москва',
            street='ул. Пушкина, д. 10',
        )
        self.assertEqual(address.city, 'Москва')
        self.assertEqual(address.user, self.user)
        self.assertFalse(address.is_default)

    def test_create_default_address(self):
        address = AddressService.create_address(
            self.user,
            recipient_name='Иван',
            city='Москва',
            street='ул. 1',
            is_default=True,
        )
        self.assertTrue(address.is_default)

    def test_create_address_max_limit(self):
        from apps.users.constants import MAX_ADDRESSES_PER_USER

        for i in range(MAX_ADDRESSES_PER_USER):
            AddressService.create_address(
                self.user,
                recipient_name=f'Адрес {i}',
                city=f'Город {i}',
                street=f'ул. {i}',
            )

        with self.assertRaises(ValidationError):
            AddressService.create_address(
                self.user,
                recipient_name='Лишний',
                city='Город',
                street='ул.',
            )

    def test_create_address_default_unsets_others(self):
        addr1 = AddressService.create_address(
            self.user,
            recipient_name='Первый',
            city='Москва',
            street='ул. 1',
            is_default=True,
        )
        addr2 = AddressService.create_address(
            self.user,
            recipient_name='Второй',
            city='СПб',
            street='ул. 2',
            is_default=True,
        )
        addr1.refresh_from_db()
        self.assertFalse(addr1.is_default)
        self.assertTrue(addr2.is_default)


class UpdateAddressTests(UserTestCase):

    def setUp(self):
        self.address = self._create_address()

    def test_update_city(self):
        address = AddressService.update_address(
            self.user, self.address.pk, city='Казань',
        )
        self.assertEqual(address.city, 'Казань')

    def test_update_not_owned(self):
        from apps.users.models import User
        other = User.objects.create_user(
            username='other', email='other@example.com', password='pass',
        )
        with self.assertRaises(NotFound):
            AddressService.update_address(other, self.address.pk, city='Казань')

    def test_update_nonexistent(self):
        with self.assertRaises(NotFound):
            AddressService.update_address(self.user, 99999, city='Казань')

    def test_update_set_default(self):
        AddressService.update_address(
            self.user, self.address.pk, is_default=True,
        )
        self.address.refresh_from_db()
        self.assertTrue(self.address.is_default)


class DeleteAddressTests(UserTestCase):

    def setUp(self):
        self.address = self._create_address()

    def test_delete_address(self):
        AddressService.delete_address(self.user, self.address.pk)
        self.assertFalse(Address.objects.filter(pk=self.address.pk).exists())

    def test_delete_not_owned(self):
        from apps.users.models import User
        other = User.objects.create_user(
            username='other2', email='other2@example.com', password='pass',
        )
        with self.assertRaises(NotFound):
            AddressService.delete_address(other, self.address.pk)

    def test_delete_nonexistent(self):
        with self.assertRaises(NotFound):
            AddressService.delete_address(self.user, 99999)


class SetDefaultTests(UserTestCase):

    def test_set_default(self):
        addr1 = self._create_address(is_default=True)
        addr2 = self._create_address(city='СПб')

        result = AddressService.set_default(self.user, addr2.pk)

        addr1.refresh_from_db()
        self.assertFalse(addr1.is_default)
        self.assertTrue(result.is_default)

    def test_set_default_not_owned(self):
        from apps.users.models import User
        other = User.objects.create_user(
            username='other3', email='other3@example.com', password='pass',
        )
        address = self._create_address()
        with self.assertRaises(NotFound):
            AddressService.set_default(other, address.pk)


class ListAddressesTests(UserTestCase):

    def test_list_empty(self):
        addresses = AddressService.list_addresses(self.user)
        self.assertEqual(addresses.count(), 0)

    def test_list_ordering(self):
        self._create_address(city='Б')
        self._create_address(city='А', is_default=True)

        addresses = list(AddressService.list_addresses(self.user))
        # is_default=True — первый
        self.assertEqual(addresses[0].city, 'А')
        self.assertEqual(addresses[1].city, 'Б')
