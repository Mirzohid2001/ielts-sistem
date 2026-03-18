"""
IELTS Center — Django admin (modullarga bo'lingan).

Test turlari: Reading, Listening, Writing.
Savol turlari: barcha Question.QUESTION_TYPES — logika o'zgartirilmagan.
"""
from .forms import QuestionAdminForm, QuestionResource, TestResource, question_type_rules_json

# Side-effect: @admin.register
from . import category_admins  # noqa: F401
from . import test_admins  # noqa: F401
from . import user_admins  # noqa: F401
from . import site_custom  # noqa: F401 — index override

__all__ = [
    'QuestionAdminForm',
    'QuestionResource',
    'TestResource',
    'question_type_rules_json',
]
