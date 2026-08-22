# 🎓 Как устроен интернет-магазин: учебник для начинающих

**Это документ по проекту Amazone Clone — копии Amazon, которую мы написали на Python.**

Здесь всё объяснено с нуля. Если ты не знаешь ни Python, ни Django — это нормально.
Читай по порядку, выполняй задания. К концу ты поймёшь, как работает настоящий интернет-магазин.

---

# 📚 ЧАСТЬ 1. БАЗОВЫЕ ПОНЯТИЯ

Прежде чем лезть в код, нужно понять 7 вещей. Без них ничего не будет понятно.

---

## Урок 1. Что такое бэкенд и фронтенд

Когда ты открываешь ozon.ru или wildberries.ru, ты видишь красивые кнопки, картинки, анимации.
Это **фронтенд** — то, что работает в твоём браузере.

Но когда ты нажимаешь «Купить», браузер отправляет запрос на другой компьютер — **сервер**.
Сервер — это **бэкенд**. Он:

- Проверяет, есть ли товар на складе
- Списывает деньги
- Сохраняет заказ в базу данных
- Отправляет email с подтверждением

```
┌─────────────┐         ┌─────────────┐         ┌─────────────┐
│  Браузер     │ ──────► │  Сервер      │ ──────► │  База данных │
│  (фронтенд)  │ ◄────── │  (бэкенд)    │ ◄────── │  (PostgreSQL)│
│  React       │  JSON   │  Django      │  SQL    │  Таблицы     │
└─────────────┘         └─────────────┘         └─────────────┘
```

**Аналогия:** Ресторан. Ты (фронтенд) сидишь за столиком и смотришь в меню.
Официант (API) принимает заказ. Кухня (бэкенд) готовит. Склад (база данных) хранит продукты.

📌 **Что запомнить:** Наш проект — это бэкенд. Он НЕ рисует кнопки.
Он только получает запросы и отдаёт данные в формате JSON.

---

## Урок 2. Что такое JSON

JSON — это формат обмена данными. Расшифровывается как JavaScript Object Notation.
Выглядит так:

```json
{
  "name": "iPhone 15",
  "price": 89990,
  "in_stock": true
}
```

Это просто текст с парами «ключ: значение». Фронтенд и бэкенд общаются через JSON.

**Аналогия:** JSON — это язык, на котором фронтенд и бэкенд разговаривают между собой.
Как английский для дипломатов — оба понимают.

📌 **Задание:** Открой http://localhost:8000/api/v1/health/ в браузере.
Ты увидишь JSON-ответ: `{"status": "ok", "version": "1.0.0", "database": "ok"}`

---

## Урок 3. Что такое API

API (Application Programming Interface) — это «меню» бэкенда.
Список всех запросов, которые можно сделать.

Например:

| Что хочешь | Запрос к API | Что вернёт |
|---|---|---|
| Посмотреть товары | `GET /api/v1/catalog/products/` | Список товаров в JSON |
| Добавить в корзину | `POST /api/v1/cart/items/` | Обновлённая корзина |
| Войти в аккаунт | `POST /api/v1/auth/login/` | JWT-токен |

**Аналогия:** API — это меню в ресторане. Ты не идёшь на кухню сам.
Ты выбираешь блюдо из меню, официант приносит его тебе.

Методы запросов:
- **GET** — получить данные (прочитать)
- **POST** — создать новые данные
- **PATCH** — изменить существующие
- **DELETE** — удалить

📌 **Задание:** Открой http://localhost:8000/api/v1/docs/ — это Swagger,
интерактивная документация API. Попробуй выполнить GET-запрос к списку продуктов.

---

## Урок 4. Что такое база данных

База данных (БД) — это место, где хранятся ВСЕ данные магазина.
Пользователи, товары, заказы, корзины — всё в таблицах.

Как Excel, но мощнее:

```
Таблица "users_user":
┌────┬─────────────────────┬───────────┬──────────────┐
│ id │ email               │ username  │ password     │
├────┼─────────────────────┼───────────┼──────────────┤
│  1 │ ivan@example.com    │ ivan      │ $2b$12$xyz…  │
│  2 │ maria@example.com   │ maria     │ $2b$12$abc…  │
└────┴─────────────────────┴───────────┴──────────────┘

Таблица "catalog_product":
┌────┬──────────────┬───────────┬─────────┬────────┐
│ id │ name         │ slug      │ rating  │ min_price │
├────┼──────────────┼───────────┼─────────┼────────┤
│  1 │ iPhone 15    │ iphone-15 │ 4.5     │ 89990  │
│  2 │ MacBook Air  │ macbook   │ 4.8     │ 129990 │
└────┴──────────────┴───────────┴─────────┴────────┘
```

Мы используем **PostgreSQL** — настоящую профессиональную БД.
В тестах — **SQLite** (проще, хранит всё в одном файле).

**Аналогия:** База данных — это склад магазина. Товары на полках, записи в журналах.
Когда кассир пробивает товар — он ищет его на складе по штрих-коду (id).

---

## Урок 5. Что такое Django

**Django** (читается «Джа́нго») — это фреймворк на Python для создания сайтов.

Фреймворк — это «конструктор» для программиста. Вместо того чтобы писать всё с нуля
(обработка запросов, база данных, авторизация), ты берёшь готовые детали и собираешь.

Django предоставляет:
- **ORM** — работа с базой данных через Python (без SQL)
- **Admin** — готовая админка
- **Auth** — регистрация, логин, пароли
- **DRF** (Django REST Framework) — создание API

**Аналогия:** Django — это LEGO-конструктор. Ты не льёшь пластик сам.
Ты берёшь готовые детали и собираешь то, что нужно.

---

## Урок 6. Что такое ORM

ORM (Object-Relational Mapping) — это способ работать с базой данных через Python-объекты,
без написания SQL-запросов.

Вместо:
```sql
SELECT * FROM catalog_product WHERE rating > 4.0;
```

Пишешь:
```python
Product.objects.filter(rating__gt=4.0)
```

ORM сам переводит Python-код в SQL и отправляет в базу.

**Аналогия:** ORM — это переводчик. Ты говоришь по-русски,
ORM переводит на SQL (язык базы данных).

📌 **Задание:** Открой терминал и выполни:
```bash
python manage.py shell
```
Потом:
```python
from apps.catalog.models import Product
Product.objects.count()   # Сколько товаров в базе
```

---

## Урок 7. Что такое JWT-токен

Когда ты логинишься, бэкенд выдаёт тебе **JWT-токен** — длинную строку вроде паспорта.

```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxfQ.abc123...
```

Этот токен фронтенд отправляет с каждым запросом, и бэкенд понимает: «А, это Иван!»

Два токена:
- **Access** — живёт 15 минут (для обычных запросов)
- **Refresh** — живёт 7 дней (чтобы получить новый access без повторного логина)

**Аналогия:** JWT — это браслет в аквапарке. Показал на входе — пустили.
Потерял — иди на кассу (логинься заново). Браслет действует до конца дня (15 мин).

---

# 📚 ЧАСТЬ 2. КАК УСТРОЕН ПРОЕКТ

Теперь разберём структуру нашего проекта.

---

## Урок 8. Папки и модули

Наш проект состоит из **14 модулей** (папок). Каждый модуль — это отдельная «деталь» магазина:

```
apps/
├── core/          🏗️ Фундамент (BaseModel — общий предок всех моделей)
├── users/         👤 Пользователи (регистрация, логин, профиль, адреса)
├── catalog/       📦 Каталог (товары, категории, бренды, теги)
├── pricing/       💰 Цены (цена, скидочная цена, история цен)
├── cart/          🛒 Корзина (добавить, убрать, изменить количество)
├── orders/        📋 Заказы (оформить, отменить, статусы)
├── inventory/     📊 Склад (остатки, резервы, движения)
├── payments/      💳 Оплата (платежи, возвраты, вебхуки)
├── reviews/       ⭐ Отзывы (рейтинг, текст, фото)
├── discounts/     🏷️ Скидки (купоны, кампании, промокоды)
├── shipping/      🚚 Доставка (зоны, методы, отслеживание)
├── wishlist/      ❤️ Избранное (хочу позже)
├── notifications/ 🔔 Уведомления (заказ создан, отправлен и т.д.)
└── analytics/     📈 Аналитика (просмотры, продажи, конверсия)
```

**Аналогия:** Каждый модуль — это отдел в магазине.
Отдел электроники, отдел одежды, касса, склад, бухгалтерия.
Каждый делает свою работу, но все работают вместе.

---

## Урок 9. Анатомия одного модуля

Каждый модуль устроен одинаково. Возьмём для примера корзину (`apps/cart/`):

```
apps/cart/
├── models/           📦 МОДЕЛИ — таблицы в базе данных
│   ├── cart.py           Cart (корзина)
│   └── cart_item.py      CartItem (товар в корзине)
├── services/         🧠 СЕРВИСЫ — бизнес-логика
│   └── cart_service.py   CartService (добавить, убрать, слить)
├── serializers/      🔄 СЕРИАЛИЗАТОРЫ — переводят объекты в JSON
│   └── cart_serializers.py
├── api_views/        🌐 VIEWS — принимают HTTP-запросы
│   └── cart_views.py
├── urls.py           🔗 URL — маршруты (какой URL → какой View)
├── admin.py          👔 ADMIN — настройка админки Django
├── signals.py        📡 СИГНАЛЫ — автодействия при событиях
├── tests/            ✅ ТЕСТЫ — проверяют что всё работает
│   ├── test_models.py
│   ├── test_services.py
│   └── test_api.py
├── constants.py      🔢 КОНСТАНТЫ — числа-лимиты
└── migrations/       📜 МИГРАЦИИ — история изменений базы
```

### Путь запроса

Когда фронтенд отправляет `POST /api/v1/cart/items/ {variant_id: 5, quantity: 2}`:

```
1. URL:    /api/v1/cart/items/ → CartItemView (api_views/)
2. View:   Принимает запрос, вызывает CartItemSerializer
3. Serial: Проверяет данные (variant_id есть? quantity > 0?)
4. View:   Вызывает CartService.add_item()
5. Service: @transaction.atomic + select_for_update
            Проверяет сток, ищет корзину, создаёт CartItem
6. ORM:    INSERT INTO cart_cartitem (...)
7. Service: Возвращает обновлённую корзину
8. View:   Отдаёт JSON-ответ
```

**Аналогия:** Как в ресторане:
1. Официант (URL) принимает заказ
2. Проверяет, всё ли заполнено в бланке (Serializer)
3. Передаёт на кухню (Service)
4. Повар готовит по рецепту (бизнес-логика)
5. Берёт продукты из холодильника (ORM → БД)
6. Отдаёт блюдо через официанта (View → JSON)

📌 **Задание:** Открой `apps/cart/api_views/cart_views.py` и найди метод `post()`
в классе `CartItemView`. Проследи путь: что он вызывает?

---

## Урок 10. Модели — таблицы в базе

Модель — это Python-класс, который становится таблицей в базе данных.

Пример — корзина:

```python
class Cart(BaseModel):                    # Наследуем created_at, updated_at
    user = models.ForeignKey(             # Связь с пользователем
        User,
        on_delete=models.CASCADE,         # Удалён пользователь → удалена корзина
        null=True,                        # Может быть NULL (гостевая корзина)
        blank=True,
    )
    session_key_hash = models.CharField(  # Для гостей (хэш сессии)
        max_length=64,
        null=True,
    )
    is_active = models.BooleanField(      # Активна ли корзина?
        default=True,
    )
```

Django создаёт таблицу:

```
cart_cart:
┌────┬─────────┬───────────────────┬───────────┬────────────┬────────────┐
│ id │ created │ updated           │ user_id   │ session_…  │ is_active  │
├────┼─────────┼───────────────────┼───────────┼────────────┼────────────┤
│  1 │ …       │ …                 │ 1         │ NULL       │ True       │
│  2 │ …       │ …                 │ NULL      │ a3f8b2…   │ True       │
└────┴─────────┴───────────────────┴───────────┴────────────┴────────────┘
```

### BaseModel — общий предок

У нас есть `apps/core/models/base_model.py` — абстрактная модель:

```python
class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)  # Автоматически при создании
    updated_at = models.DateTimeField(auto_now=True)      # Автоматически при изменении

    class Meta:
        abstract = True   # НЕ создаёт свою таблицу!
```

Все модели (кроме User) наследуют BaseModel → получают `created_at` и `updated_at` бесплатно.

**Аналогия:** BaseModel — как заготовка для паспорта.
Все паспорта имеют страницу «Дата выдачи» и «Дата замены».
Не нужно каждый раз рисовать эти страницы — они уже есть в шаблоне.

### ForeignKey — связь между таблицами

```python
CartItem.cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
```

Это значит: каждый CartItem привязан к ОДНОЙ корзине.
А корзина может иметь МНОГО items (через `related_name='items'`).

```
Cart #1 ←── CartItem (iPhone, 2 шт)
         ←── CartItem (MacBook, 1 шт)

Cart #2 ←── CartItem (AirPods, 3 шт)
```

**Аналогия:** ForeignKey — как номер заказа на чеке.
Каждая позиция в чеке знает, к какому заказу она принадлежит.

📌 **Задание:** Открой `apps/catalog/models/product.py` и найди все ForeignKey.
К каким моделям они ведут?

---

## Урок 11. Сервисы — мозг проекта

Сервис — это класс с бизнес-логикой. Вся «умная» работа происходит здесь.

Зачем сервисы отдельным слоем? Представь:

```
❌ БЕЗ сервисов (логика в View):
    View сам проверяет сток, создаёт корзину, считает цену, резервирует товар
    → 200 строк кода в одном методе
    → если нужно «создать заказ из CLI» — дублируем код

✅ С СЕРВИСАМИ:
    View: «CartService, добавь товар» — 3 строки
    Service: проверяет сток, создаёт корзину, считает цену — всё в одном месте
    → и View, и CLI, и management-команда используют один и тот же сервис
```

Пример — добавление в корзину:

```python
class CartService:
    @staticmethod
    @transaction.atomic           # ← Всё или ничего! Если ошибка — откат
    def add_item(cart, variant_id, quantity=1):
        # 1. Проверяем лимит позиций
        if cart.items.count() >= MAX_CART_ITEMS:
            raise ValidationError("Слишком много товаров")

        # 2. Проверяем что товар существует и активен
        variant = ProductVariant.objects.select_for_update().get(
            pk=variant_id, is_active=True
        )

        # 3. Проверяем что на складе есть
        if hasattr(variant, 'stock') and variant.stock.quantity < quantity:
            raise ValidationError("Недостаточно на складе")

        # 4. Добавляем или обновляем
        item, created = CartItem.objects.get_or_create(
            cart=cart, variant=variant,
            defaults={'quantity': quantity}
        )
        if not created:
            item.quantity += quantity
            item.save()

        return cart
```

### @transaction.atomic — «Всё или ничего»

```python
@transaction.atomic
def transfer_money(from_account, to_account, amount):
    from_account.balance -= amount      # Шаг 1
    from_account.save()
    to_account.balance += amount        # Шаг 2
    to_account.save()
    # Если шаг 2 упал — шаг 1 тоже откатывается автоматически!
```

**Аналогия:** transaction.atomic — как эскроу-счёт при покупке квартиры.
Или деньги переведены покупателю, или квартира — продавцу.
Не бывает «деньги списаны, а квартира не передана».

### select_for_update — «Не трогай, я занял!»

```python
stock = Stock.objects.select_for_update().get(variant=variant)
stock.quantity -= 1
stock.save()
```

Пока мы держим `select_for_update()`, другой запрос НЕ может изменить эту строку.
Это защищает от «race condition» — когда два человека одновременно покупают последний товар.

**Аналогия:** select_for_update — как табличка «Занято» на двери переговорки.
Пока ты внутри — никто другой не войдёт.

📌 **Задание:** Открой `apps/orders/services/order_service.py` и найди метод
`create_from_cart`. Сколько проверок он делает перед созданием заказа?

---

## Урок 12. Сериализаторы — переводчики

Сериализатор превращает Python-объект в JSON (и обратно).

```python
class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total_quantity = serializers.IntegerField(read_only=True)
    total = serializers.DecimalField(read_only=True, max_digits=12, decimal_places=2)

    class Meta:
        model = Cart
        fields = ['id', 'items', 'total_quantity', 'total']
```

Результат:
```json
{
    "id": 1,
    "items": [
        {"id": 5, "product_name": "iPhone 15", "quantity": 2, "price": "89990.00"}
    ],
    "total_quantity": 2,
    "total": "179980.00"
}
```

Сериализатор также **валидирует** входящие данные:

```python
class AddItemSerializer(serializers.Serializer):
    variant_id = serializers.IntegerField()       # Обязательное поле
    quantity = serializers.IntegerField(min_value=1, default=1)  # Минимум 1
```

Если отправить `{variant_id: "abc"}` → ошибка: «variant_id должен быть числом».

**Аналогия:** Сериализатор — таможенник. Проверяет багаж (данные) на входе
и упаковывает товар (объект) для отправки на выходе.

---

## Урок 13. Views — приёмная

View — это функция/класс, которая принимает HTTP-запрос и возвращает HTTP-ответ.

```python
class CartItemView(APIView):
    permission_classes = (AllowAny,)  # Любой может добавить в корзину

    def post(self, request):
        # 1. Валидируем входящие данные
        serializer = AddItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # 2. Получаем корзину (создаём если нет)
        cart = CartService.get_or_create_cart(request)

        # 3. Вызываем бизнес-логику
        cart = CartService.add_item(
            cart=cart,
            variant_id=serializer.validated_data['variant_id'],
            quantity=serializer.validated_data.get('quantity', 1),
        )

        # 4. Возвращаем обновлённую корзину
        return Response(CartSerializer(cart).data, status=201)
```

**Правило:** View НЕ содержит бизнес-логику. Только:
1. Принять запрос
2. Валидировать данные (через сериализатор)
3. Вызвать сервис
4. Вернуть ответ

📌 **Задание:** Открой `apps/users/api_views/auth_views.py` и прочти класс `RegisterView`.
Проследи: что делает View, а что — сериализатор?

---

## Урок 14. URL — маршруты

URL-файл связывает адрес (URL) с конкретным View:

```python
# apps/cart/urls.py
urlpatterns = [
    path('', CartView.as_view(), name='cart'),               # GET /api/v1/cart/
    path('items/', CartItemView.as_view(), name='cart-items'),  # POST /api/v1/cart/items/
    path('items/<int:item_id>/', CartItemDetailView.as_view()), # PATCH /api/v1/cart/items/5/
    path('merge/', CartMergeView.as_view(), name='cart-merge'), # POST /api/v1/cart/merge/
]
```

А в `config/urls.py` всё собирается вместе:

```python
path('api/v1/cart/', include('apps.cart.urls'))
```

Итого полный URL: `/api/v1/cart/items/`

**Аналогия:** URL — это таблички на дверях в здании.
«Касса — 1 этаж, комната 3». Табличка не работает, она только показывает дорогу.

---

## Урок 15. Тесты — страховка

Тесты проверяют, что код работает правильно. У нас 898 тестов!

```python
class CartServiceTests(TestCase):
    def test_add_item(self):
        """Добавление товара в корзину."""
        cart = self._create_cart()
        CartService.add_item(cart=cart, variant_id=self.variant.pk, quantity=2)
        self.assertEqual(cart.items.count(), 1)        # 1 позиция
        self.assertEqual(cart.items.first().quantity, 2)  # количество = 2

    def test_add_same_item_increments(self):
        """Повторное добавление увеличивает количество."""
        cart = self._create_cart()
        CartService.add_item(cart=cart, variant_id=self.variant.pk, quantity=1)
        CartService.add_item(cart=cart, variant_id=self.variant.pk, quantity=3)
        self.assertEqual(cart.items.count(), 1)        # всё ещё 1 позиция
        self.assertEqual(cart.items.first().quantity, 4)  # 1 + 3 = 4
```

Запуск:
```bash
python manage.py test          # Все 898 тестов
python manage.py test apps.cart  # Только корзину
```

**Аналогия:** Тесты — как техосмотр автомобиля. Перед выездом на дорогу
проверяем: тормоза работают? фары горят? руль крутится?
Если хоть одна проверка не прошла — на дорогу нельзя.

📌 **Задание:** Запусти `python manage.py test apps.cart` и посмотри результат.
Сколько тестов прошло?

---

## Урок 16. Миграции — эволюция базы

Миграция — это инструкция «как изменить базу данных».

```python
# 0001_initial.py — создаёт таблицу
operations = [
    migrations.CreateModel(
        name='Cart',
        fields=[
            ('id', models.BigAutoField(primary_key=True)),
            ('user', models.ForeignKey(...)),
            ('is_active', models.BooleanField(default=True)),
        ],
    ),
]
```

Миграции можно сравнить с историей коммитов в Git.
Каждая миграция — это шаг, и все шаги применяются по порядку.

```bash
python manage.py makemigrations  # Создать миграцию (из модели → SQL)
python manage.py migrate         # Применить миграцию (выполнить SQL)
```

**Аналогия:** Миграции — как строительные чертежи.
Сначала чертёж «Фундамент» (0001), потом «Стены» (0002), потом «Крыша» (0003).
Нельзя построить крышу без стен!

---

# 📚 ЧАСТЬ 3. КАК МОДУЛИ РАБОТАЮТ ВМЕСТЕ

---

## Урок 17. Путь заказа от начала до конца

Вот что происходит, когда пользователь покупает товар:

```
1. 👤 ПОЛЬЗОВАТЕЛЬ ЗАХОДИТ НА САЙТ
   → users: Регистрация/Логин → JWT-токен

2. 📦 ПРОСМАТРИВАЕТ КАТАЛОГ
   → catalog: Список товаров, категории, бренды
   → analytics: Записываем просмотр (record_view)

3. 🛒 КЛАДЁТ В КОРЗИНУ
   → cart: CartService.add_item()
   → inventory: Проверяем остаток (stock.quantity)

4. 📋 ОФОРМЛЯЕТ ЗАКАЗ
   → orders: OrderService.create_from_cart()
   → cart: Корзина деактивируется
   → inventory: Статус CONFIRMED → резервируем товар (reserve)
   → discounts: Применяем купон если есть
   → shipping: Рассчитываем стоимость доставки
   → notifications: «Ваш заказ создан!»

5. 💳 ОПЛАЧИВАЕТ
   → payments: PaymentService.process()
   → payments: Статус PAID → OrderService.confirm()
   → orders: Статус CONFIRMED → PROCESSING
   → notifications: «Оплата прошла!»

6. 🚚 ОТПРАВЛЯЕТСЯ
   → shipping: Shipment → IN_TRANSIT
   → orders: Статус PROCESSING → SHIPPED
   → notifications: «Заказ отправлен!»

7. 📦 ДОСТАВЛЯЕТСЯ
   → shipping: Shipment → DELIVERED
   → orders: Статус SHIPPED → DELIVERED
   → inventory: Списываем со склада (commit)
   → notifications: «Заказ доставлен!»

8. ⭐ ОСТАВЛЯЕТ ОТЗЫВ
   → reviews: ReviewService.create()
   → catalog: Пересчитываем рейтинг товара
```

📌 **Задание:** Нарисуй эту цепочку на бумаге. Подпиши, какой модуль за что отвечает.

---

## Урок 18. Статусная машина заказа

Заказ проходит через статусы как светофор:

```
    PENDING (ожидает)
       │
       ▼
    CONFIRMED (подтверждён)  ←─── оплата прошла
       │
       ▼
    PROCESSING (в обработке) ←─── начали собирать
       │
       ▼
    SHIPPED (отправлен)      ←─── передали в доставку
       │
       ▼
    DELIVERED (доставлен)    ←─── клиент получил

    На любом этапе → CANCELLED (отменён)
```

Правила переходов зашифрованы в `OrderService`:

```python
ALLOWED_TRANSITIONS = {
    'PENDING':    ['CONFIRMED', 'CANCELLED'],
    'CONFIRMED':  ['PROCESSING', 'CANCELLED'],
    'PROCESSING': ['SHIPPED', 'CANCELLED'],
    'SHIPPED':    ['DELIVERED'],
    'DELIVERED':  [],
    'CANCELLED':  [],  # Из отмены уже никуда
}
```

Нельзя перескочить из PENDING сразу в SHIPPED — сервис не позволит.

**Аналогия:** Статусная машина — как уровня в игре.
Нельзя перейти на уровень 3, не пройдя уровень 2.

---

## Урок 19. Сигналы — автодействия

Сигнал — это автоматическое действие при каком-то событии.

Например: когда создан новый пользователь, автоматически создаём его профиль:

```python
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
```

Или: когда отзыв создан, пересчитываем рейтинг товара:

```python
@receiver(post_save, sender=Review)
def recalculate_product_rating(sender, instance, **kwargs):
    product = instance.product
    # Пересчитываем средний рейтинг
    reviews = Review.objects.filter(product=product, is_approved=True)
    product.rating = reviews.aggregate(avg=Avg('rating'))['avg'] or 0
    product.reviews_count = reviews.count()
    product.save()
```

**Аналогия:** Сигнал — как датчик дыма. Сработал → автоматически вызвал пожарных.
Ты не звонишь сам — система реагирует сама.

📌 **Задание:** Найди все сигналы в проекте:
```bash
grep -r "@receiver" apps/ --include="*.py"
```
Сколько сигналов в проекте?

---

# 📚 ЧАСТЬ 4. ПРАКТИЧЕСКИЕ ЗАДАНИЯ

Теперь попробуй сам!

---

## 🛠️ Задание 1: Создай товар через Django Admin

1. Запусти сервер: `python manage.py runserver`
2. Открой http://localhost:8000/admin/
3. Залогинься (нужен superuser — создай через `python manage.py createsuperuser`)
4. Создай бренд, категорию, товар, вариант товара

📌 **Что ты поймёшь:** Как данные попадают в базу через админку.

---

## 🛠️ Задание 2: Получи данные через API

1. Залогинься через API:
```bash
curl -X POST http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "твой@email.com", "password": "твой_пароль"}'
```
2. Скопируй access-токен из ответа
3. Получи список товаров:
```bash
curl http://localhost:8000/api/v1/catalog/products/ \
  -H "Authorization: Bearer ТОКЕН"
```

📌 **Что ты поймёшь:** Как фронтенд общается с бэкендом.

---

## 🛠️ Задание 3: Добавь товар в корзину через API

```bash
curl -X POST http://localhost:8000/api/v1/cart/items/ \
  -H "Authorization: Bearer ТОКЕН" \
  -H "Content-Type: application/json" \
  -d '{"variant_id": 1, "quantity": 2}'
```

Потом посмотри корзину:
```bash
curl http://localhost:8000/api/v1/cart/ \
  -H "Authorization: Bearer ТОКЕН"
```

📌 **Что ты поймёшь:** Как POST-запросы создают данные.

---

## 🛠️ Задание 4: Напиши свой тест

Открой `apps/cart/tests/test_services.py` и добавь в конец:

```python
def test_add_item_quantity_zero_raises_error(self):
    """Нельзя добавить 0 товаров."""
    cart = self._create_cart()
    with self.assertRaises(ValidationError):
        CartService.add_item(
            cart=cart,
            variant_id=self.variant_a.pk,
            quantity=0,
        )
```

Запусти: `python manage.py test apps.cart`

📌 **Что ты поймёшь:** Как писать тесты и зачем они нужны.

---

## 🛠️ Задание 5: Прочитай код одного модуля полностью

Выбери модуль `apps/wishlist/` (он маленький) и прочти ВСЕ файлы по порядку:

1. `models/wishlist.py` — какие поля у модели?
2. `services/wishlist_service.py` — какие методы у сервиса?
3. `serializers/wishlist_serializers.py` — какие поля отдаются в JSON?
4. `api_views/wishlist_views.py` — какие URL обрабатываются?
5. `urls.py` — какие маршруты?
6. `tests/test_services.py` — какие проверки?

📌 **Что ты поймёшь:** Как весь модуль работает как единое целое.

---

# 📚 ЧАСТЬ 5. СЛОВАРЬ ТЕРМИНОВ

| Термин | Простыми словами |
|--------|-----------------|
| **Бэкенд** | Программа на сервере (не видна пользователю) |
| **Фронтенд** | Программа в браузере (кнопки, картинки) |
| **API** | Меню запросов к бэкенду |
| **JSON** | Формат данных (текст с ключами и значениями) |
| **ORM** | Переводчик Python ↔ SQL |
| **Модель** | Таблица в базе данных |
| **ForeignKey** | Ссылка на другую таблицу |
| **Сериализатор** | Переводчик Python-объект ↔ JSON |
| **View** | Обработчик HTTP-запроса |
| **Сервис** | Бизнес-логика (мозг) |
| **Migration** | Инструкция по изменению базы |
| **Тест** | Автоматическая проверка кода |
| **JWT** | Электронный паспорт пользователя |
| **Transaction** | «Всё или ничего» — группа операций |
| **select_for_update** | «Занято, не трогай!» — блокировка строки |
| **Signal** | Автодействие при событии |
| **Constraint** | Правило в базе (уникальность, проверка) |
| **Index** | Ускорение поиска (как алфавитный указатель) |
| **FSM** | Конечный автомат (статусная машина) |
| **CORS** | Разрешение для фронтенда делать запросы |
| **Throttle** | Ограничение количества запросов |

---

# 📚 ЧАСТЬ 6. ПЛАН ДАЛЬНЕЙШЕГО ИЗУЧЕНИЯ

Если хочешь углубиться — вот порядок:

```
1️⃣ Python основы        → переменные, циклы, функции, классы
2️⃣ Django основы        → модели, views, urls, admin
3️⃣ DRF (Django REST)    → сериализаторы, API views, пагинация
4️⃣ Базы данных          → SQL, индексы, транзакции
5️⃣ Паттерны             → Service Layer, Repository, FSM
6️⃣ React основы         → компоненты, стейт, роутинг
7️⃣ Fullstack            → React + Django вместе
```

Ресурсы:
- 📖 [Django для начинающих](https://djangoforbeginners.com/) (книга)
- 📖 [DRF туториал](https://www.django-rest-framework.org/tutorial/quickstart/)
- 📖 [Python для детей](https://www.amazon.com/Python-Kids-Playful-Introduction-Programming/dp/1593274076) (книга)
- 🎥 [Corey Schafer Django](https://youtube.com/playlist?list=PL-osiE80TeTtoQCKZ03TU5fNfx2UY6U4p) (видео)

---

*Если что-то непонятно — переспрашивай. Лучше спросить 10 раз, чем сделать неправильно 1 раз.* 🚀
