# ────────────────────────────────────────────────────────────────────────
# apps/users/signals.py — сигнал создания профиля.
#
# post_save на User → автоматически создаёт UserProfile.
# Это стандартный паттерн Django для OneToOne-профилей.
#
# 📖 https://docs.djangoproject.com/en/stable/topics/signals/
# 📖 https://docs.djangoproject.com/en/stable/ref/signals/#post-save
# ────────────────────────────────────────────────────────────────────────

import logging

from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.users.models import UserProfile

logger = logging.getLogger(__name__)
User = get_user_model()


# @receiver(post_save, sender=User) — регистрирует обработчик.
# post_save — сигнал, посылаемый ПОСЛЕ каждого User.save().
# created=True — только при создании (INSERT), не при обновлении (UPDATE).
# 📖 https://docs.djangoproject.com/en/stable/ref/signals/#post-save
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Создаёт пустой UserProfile при создании нового User.

    get_or_create вместо create:
      Если профиль уже существует (например, создан вручную в сервисе)
      → get_or_create не упадёт с IntegrityError.
      create → IntegrityError при дубликате OneToOne.

    📖 https://docs.djangoproject.com/en/stable/topics/auth/customizing/#extending-the-existing-user-model
    """
    if created:
        UserProfile.objects.get_or_create(user=instance)
        logger.debug(
            'user_profile_created',
            extra={'user_id': instance.pk},
        )
