# ────────────────────────────────────────────────────────────────────────
# apps/notifications/constants.py
# ────────────────────────────────────────────────────────────────────────

# Типы уведомлений
NOTIF_ORDER_CREATED = 'order_created'
NOTIF_ORDER_CONFIRMED = 'order_confirmed'
NOTIF_ORDER_SHIPPED = 'order_shipped'
NOTIF_ORDER_DELIVERED = 'order_delivered'
NOTIF_ORDER_CANCELLED = 'order_cancelled'
NOTIF_PAYMENT_SUCCESS = 'payment_success'
NOTIF_PAYMENT_FAILED = 'payment_failed'
NOTIF_SHIPMENT_IN_TRANSIT = 'shipment_in_transit'
NOTIF_SHIPMENT_DELIVERED = 'shipment_delivered'
NOTIF_REVIEW_REPLY = 'review_reply'
NOTIF_PROMO = 'promo'
NOTIF_SYSTEM = 'system'

NOTIFICATION_TYPE_CHOICES = (
    (NOTIF_ORDER_CREATED, 'Заказ создан'),
    (NOTIF_ORDER_CONFIRMED, 'Заказ подтверждён'),
    (NOTIF_ORDER_SHIPPED, 'Заказ отправлен'),
    (NOTIF_ORDER_DELIVERED, 'Заказ доставлен'),
    (NOTIF_ORDER_CANCELLED, 'Заказ отменён'),
    (NOTIF_PAYMENT_SUCCESS, 'Оплата прошла'),
    (NOTIF_PAYMENT_FAILED, 'Ошибка оплаты'),
    (NOTIF_SHIPMENT_IN_TRANSIT, 'Посылка в пути'),
    (NOTIF_SHIPMENT_DELIVERED, 'Посылка доставлена'),
    (NOTIF_REVIEW_REPLY, 'Ответ на отзыв'),
    (NOTIF_PROMO, 'Промо-уведомление'),
    (NOTIF_SYSTEM, 'Системное'),
)

# Каналы доставки
CHANNEL_IN_APP = 'in_app'
CHANNEL_EMAIL = 'email'
CHANNEL_PUSH = 'push'

CHANNEL_CHOICES = (
    (CHANNEL_IN_APP, 'В приложении'),
    (CHANNEL_EMAIL, 'Email'),
    (CHANNEL_PUSH, 'Push'),
)

# Статусы отправки
STATUS_PENDING = 'pending'
STATUS_SENT = 'sent'
STATUS_FAILED = 'failed'
STATUS_READ = 'read'

STATUS_CHOICES = (
    (STATUS_PENDING, 'Ожидает'),
    (STATUS_SENT, 'Отправлено'),
    (STATUS_FAILED, 'Ошибка'),
    (STATUS_READ, 'Прочитано'),
)

# Максимальная длина заголовка / тела
MAX_TITLE_LENGTH = 255
MAX_BODY_LENGTH = 2000
