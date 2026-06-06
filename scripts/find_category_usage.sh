#!/usr/bin/env bash
#
# Поиск мест в проекте, которые нужно обновить после перехода
# модели Category на django-treebeard (MP_Node).
#
# Запуск из корня проекта:
#   bash scripts/find_category_usage.sh
#
# Скрипт ничего не меняет — только показывает совпадения с указанием
# файла и номера строки. По каждому блоку — комментарий, что делать.

set -u

# Куда смотреть. По умолчанию — текущая директория.
ROOT="${1:-.}"

# Что игнорировать (виртуальные окружения, миграции, кэш и т.п.)
EXCLUDES=(
  --exclude-dir=.venv
  --exclude-dir=venv
  --exclude-dir=env
  --exclude-dir=.git
  --exclude-dir=node_modules
  --exclude-dir=__pycache__
  --exclude-dir=migrations          # миграции трогать не надо
  --exclude-dir=static
  --exclude-dir=media
  --exclude=*.pyc
)

# Цвета для читабельности
if [ -t 1 ]; then
  BOLD="\033[1m"; YELLOW="\033[33m"; CYAN="\033[36m"; RESET="\033[0m"
else
  BOLD=""; YELLOW=""; CYAN=""; RESET=""
fi

section() {
  echo
  echo -e "${BOLD}${CYAN}===========================================================${RESET}"
  echo -e "${BOLD}${CYAN} $1${RESET}"
  echo -e "${BOLD}${CYAN}===========================================================${RESET}"
  echo -e "${YELLOW}$2${RESET}"
  echo
}

run_grep() {
  # -R рекурсивно, -n с номерами строк, -I игнор бинарников,
  # --include=*.py — только Python (шаблоны/JS добавим отдельно при желании)
  grep -RIn --color=always "${EXCLUDES[@]}" --include="*.py" -E "$1" "$ROOT" || echo "  (ничего не найдено — ок)"
}

# -----------------------------------------------------------------
# 1. Обращение к .parent у категории
# -----------------------------------------------------------------
section "1) category.parent  →  category.get_parent()" \
"В treebeard у узла нет атрибута parent.
Используйте get_parent(). Если объект — точно категория, замените все
.parent на .get_parent(). Будьте аккуратны с другими моделями, где
.parent — это валидное поле (фильтруйте вручную по контексту)."
run_grep '\.parent(\b|[^_a-zA-Z0-9])'

# -----------------------------------------------------------------
# 2. Обращение к .children у категории
# -----------------------------------------------------------------
section "2) category.children  →  category.get_children()" \
"related_name='children' у ForeignKey('self') больше не существует.
Замените category.children.all() → category.get_children().
И category.children.filter(...) → category.get_children().filter(...)."
run_grep '\.children(\b|[^_a-zA-Z0-9])'

# -----------------------------------------------------------------
# 3. Создание категорий обычным способом
# -----------------------------------------------------------------
section "3) Category.objects.create(...)  →  add_root / add_child" \
"Создавать узлы дерева через obj.create() НЕЛЬЗЯ — treebeard не узнает,
куда вставить узел. Используйте:
   Category.add_root(name=...)
   parent.add_child(name=...)
Также проверьте Category(...) с последующим .save() — это та же ошибка."
run_grep 'Category\.objects\.create\('
run_grep 'Category\(.*\)\.save\('
run_grep 'Category\s*\(\s*[a-zA-Z_]+\s*=' | grep -v 'class Category'

# -----------------------------------------------------------------
# 4. Старое поле path (URL-путь) — переименовано в url_path
# -----------------------------------------------------------------
section "4) category.path  →  category.url_path" \
"Системное поле path в MP_Node — это внутренний путь treebeard,
а НЕ человеко-читаемый URL. Везде, где раньше использовалось
category.path как URL, замените на category.url_path.
Также проверьте admin (list_display, ordering, readonly_fields)."
run_grep '\bpath\b' | grep -iE '(category|cat)' || true
# отдельно поищем явные обращения вида category.path / cat.path / obj.path в контексте Category
run_grep '(category|cat|obj|self)\.path\b'

# -----------------------------------------------------------------
# 5. full_name — теперь читает кэш, но проверим использование
# -----------------------------------------------------------------
section "5) Использование full_name / full_name_cached" \
"full_name теперь возвращает full_name_cached (0 запросов).
Если где-то писали .full_name в цикле — теперь это безопасно.
Проверьте, не сохраняется ли в БД старая логика через .save()."
run_grep '\.full_name(\b|[^_a-zA-Z0-9])'

# -----------------------------------------------------------------
# 6. ordering = ('path',) и подобные сортировки по path в админке
# -----------------------------------------------------------------
section "6) ordering = ('path',)  →  убрать (TreeAdmin сам сортирует)" \
"В Category.Meta нельзя ставить ordering — это ломает обходы дерева.
В admin тоже не задавайте ordering='path'."
run_grep "ordering\s*=\s*\(?\s*'path'"
run_grep "ordering\s*=\s*\(?\s*'parent'"

# -----------------------------------------------------------------
# 7. Фильтры по родителю в QuerySet
# -----------------------------------------------------------------
section "7) Фильтры parent__... / children__..." \
"Старый ForeignKey parent больше не существует.
Если фильтровали Product.objects.filter(category__parent=...) или
делали .filter(parent__isnull=True) для поиска корней — нужно переписать:
   корни:        Category.get_root_nodes()
   потомки:      node.get_descendants()
   предки:       node.get_ancestors()
   ветка целиком: node.get_tree(parent=node)"
run_grep 'parent__'
run_grep 'children__'
run_grep "parent__isnull"

# -----------------------------------------------------------------
# 8. ForeignKey('self') — если где-то ещё остался дублирующий код
# -----------------------------------------------------------------
section "8) Остатки ForeignKey('self') у Category" \
"После перехода в модели Category не должно остаться ForeignKey('self').
Если найдётся — значит, миграция модели не завершена."
run_grep "ForeignKey\(\s*['\"]self['\"]"

# -----------------------------------------------------------------
# 9. Сериализаторы / формы / шаблоны — обращение к parent_id
# -----------------------------------------------------------------
section "9) parent_id (часто в сериализаторах и формах)" \
"Если где-то писали data['parent_id'] для категории — теперь это поле
не существует. В API создание/перемещение делается отдельным эндпоинтом
через add_root() / move(). Подумайте, как это переделать."
run_grep '\bparent_id\b'

# -----------------------------------------------------------------
# 10. Импорты MPTT/treebeard — на случай, если что-то старое осталось
# -----------------------------------------------------------------
section "10) Контроль: упоминания mptt и treebeard" \
"Проверим, что нет смешения двух библиотек одновременно."
run_grep '\bmptt\b'
run_grep '\btreebeard\b'

# -----------------------------------------------------------------
# 11. Шаблоны (если есть) — бонусом
# -----------------------------------------------------------------
section "11) HTML/Jinja-шаблоны: category.parent, category.children, category.path" \
"Просто чтобы ничего не забыть в template-слое."
grep -RIn --color=always "${EXCLUDES[@]}" --include="*.html" --include="*.jinja" --include="*.j2" \
  -E '(category|cat)\.(parent|children|path)\b' "$ROOT" 2>/dev/null \
  || echo "  (шаблонов с такими обращениями не найдено)"

echo
echo -e "${BOLD}Готово.${RESET} Просмотрите каждую секцию и обновите соответствующие места."
echo "Совет: перед заменами сделайте коммит, чтобы можно было удобно сравнить diff."
