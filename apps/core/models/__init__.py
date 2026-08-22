# ==============================================================================
# apps/core/models/__init__.py
# ==============================================================================
# Реэкспорт BaseModel из base_model.py.
# Позволяет импортировать: from apps.core.models import BaseModel
# вместо: from apps.core.models.base_model import BaseModel
# ==============================================================================

from apps.core.models.base_model import BaseModel

__all__ = ['BaseModel']
