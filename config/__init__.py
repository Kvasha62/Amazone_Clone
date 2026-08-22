# ────────────────────────────────────────────────────────────────────────
# config/__init__.py — загрузка Celery при старте Django.
#
# При импорте config.settings Django автоматически выполнит
# this_celery_app = celery.app, что регистрирует все @shared_task.
# ────────────────────────────────────────────────────────────────────────

# Это гарантирует, что Celery-приложение всегда загружено
# когда Django-проект импортируется (worker, beat, shell и т.д.)
from .celery import app as celery_app

__all__ = ('celery_app',)
