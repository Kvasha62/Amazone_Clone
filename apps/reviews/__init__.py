# ────────────────────────────────────────────────────────────────────────
# apps/reviews/__init__.py — модуль отзывов и рейтингов.
#
# Отвечает за:
#   • Отзывы пользователей на товары (текст + рейтинг 1-5)
#   • Проверку «купил ли пользователь товар» (verified_purchase)
#   • Лайки/дизлайки отзывов
#   • Пересчёт denormalized rating/reviews_count на Product через
#     catalog-owned контракт CatalogService.set_review_stats()
#     (ARCH-001 C1: reviews считает агрегаты, catalog пишет поля)
# ────────────────────────────────────────────────────────────────────────

default_app_config = 'apps.reviews.apps.ReviewsConfig'
