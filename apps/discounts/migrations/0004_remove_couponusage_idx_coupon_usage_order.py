# ARCH-002: отдельный индекс idx_coupon_usage_order избыточен —
# обратный поиск по order обслуживает неявный индекс ограничения
# UNIQUE(order) (uq_coupon_usage_order, миграция 0003).

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("discounts", "0003_remove_couponusage_uq_coupon_usage_coupon_order_and_more"),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name="couponusage",
            name="idx_coupon_usage_order",
        ),
    ]
