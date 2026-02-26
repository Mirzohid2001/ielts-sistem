# Har bir savol turi uchun default shart yozish

from django.db import migrations


DEFAULT_RULES = [
    ('mcq', 'Multiple Choice (A/B/C/D)', 'Variant A, B, C, D to\'ldiring. To\'g\'ri javob maydonida a, b, c yoki d kiriting.'),
    ('true_false', 'True / False', 'A = True, B = False. To\'g\'ri javob: a yoki b.'),
    ('true_false_not_given', 'True / False / Not Given (Reading)', 'A = True, B = False, C = Not Given. To\'g\'ri javob: a, b yoki c.'),
    ('yes_no_not_given', 'Yes / No / Not Given', 'A = Yes, B = No, C = Not Given. To\'g\'ri javob: a, b yoki c.'),
    ('fill_blank', "Bo'sh joyni to'ldirish", 'Savol matnida [1], [2], [3] yozing. «To\'g\'ri javoblar» da vergul bilan: javob1,javob2,javob3.'),
    ('summary_completion', 'Summary Completion (Reading)', 'Matnda [1], [2], [3]… To\'g\'ri javoblar: vergul bilan. Instruction: ONE WORD ONLY yoki ONE WORD AND/OR A NUMBER.'),
    ('notes_completion', 'Notes Completion (Listening)', 'Matnda [1], [2], [3]. To\'g\'ri javoblar vergul bilan. Instruction: ONE WORD ONLY yoki ONE WORD AND/OR A NUMBER.'),
    ('sentence_completion', 'Sentence Completion', 'Savol matnida [1], [2]. To\'g\'ri javoblar vergul bilan.'),
    ('table_completion', 'Table Completion', 'Matnda [1], [2]. To\'g\'ri javoblar vergul bilan.'),
    ('short_answer', "Qisqa javob", 'To\'g\'ri javob(lar) — bitta yoki vergul bilan bir nechta.'),
    ('essay', 'Essay (Writing Task)', 'Savol matnida to\'liq task va diagram/grafik tavsifini yozing. Ball va tushuntirish ixtiyoriy.'),
    ('matching_headings', 'Matching Headings', 'Matching itemlar: har satr 1|Paragraph A. Matching variantlar: A|Heading text. To\'g\'ri javob: 1:A (har satr).'),
    ('matching_sentences', 'Matching Sentence Endings', 'Items va variantlar har satrda raqam|matn yoki harf|matn. To\'g\'ri javob: 1:A formatida.'),
    ('matching_features', 'Matching Features', 'Itemlar va variantlar. To\'g\'ri javob: 1:A (har satr).'),
    ('matching_info', 'Matching Information (paragraflarga)', 'Itemlar va paragraflar. To\'g\'ri javob: 1:A formatida.'),
    ('classification', 'Classification (A/B/C ga)', 'Itemlar va toifalar. To\'g\'ri javob: 1:A (har satr).'),
    ('list_selection', 'List Selection', 'List options: har satr A|Matn. List to\'g\'ri javob: A,C (vergul bilan).'),
]


def populate(apps, schema_editor):
    QuestionTypeRule = apps.get_model('core', 'QuestionTypeRule')
    for order, (qtype, name_uz, shart_text) in enumerate(DEFAULT_RULES, start=1):
        QuestionTypeRule.objects.get_or_create(
            question_type=qtype,
            defaults={'name_uz': name_uz, 'shart_text': shart_text, 'order': order}
        )


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0009_questiontyperule'),
    ]

    operations = [
        migrations.RunPython(populate, noop),
    ]
