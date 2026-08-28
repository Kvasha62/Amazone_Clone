from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('discounts', '0001_initial'),
        ('orders', '0002_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='CouponUsage',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID',
                    ),
                ),
                (
                    'created_at',
                    models.DateTimeField(
                        auto_now_add=True,
                        db_index=True,
                        verbose_name='Создано',
                    ),
                ),
                (
                    'updated_at',
                    models.DateTimeField(
                        auto_now=True,
                        verbose_name='Обновлено',
                    ),
                ),
                (
                    'coupon',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name='usages',
                        to='discounts.coupon',
                    ),
                ),
                (
                    'order',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name='coupon_usages',
                        to='orders.order',
                    ),
                ),
                (
                    'user',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name='coupon_usages',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                'verbose_name': 'Использование купона',
                'verbose_name_plural': 'Использования купонов',
                'constraints': [
                    models.UniqueConstraint(
                        fields=('coupon', 'order'),
                        name='uq_coupon_usage_coupon_order',
                    ),
                ],
                'indexes': [
                    models.Index(
                        fields=('coupon', 'user'),
                        name='idx_coupon_usage_coupon_user',
                    ),
                    models.Index(
                        fields=('order',),
                        name='idx_coupon_usage_order',
                    ),
                ],
            },
        ),
    ]
