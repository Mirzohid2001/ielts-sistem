# MCQ uchun admin shart matnini yangilash (A–H va ro'yxat)

from django.db import migrations


NEW_MCQ_SHART = (
    "A–D dan tashqari variantlar kerak bo‘lsa E, F, G, H maydonlarini to‘ldiring (testda a–h harflari bilan chiqadi). "
    "9 tadan ortiq yoki maxsus tartib uchun «MCQ variantlar (ro'yxat)» da har satr: harf|matn. "
    "To‘g‘ri javob: tanlangan harflardan biri (masalan d yoki g)."
)


def update_rule(apps, schema_editor):
    QuestionTypeRule = apps.get_model('core', 'QuestionTypeRule')
    QuestionTypeRule.objects.filter(question_type='mcq').update(shart_text=NEW_MCQ_SHART)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0018_tfng_ynng_instruction_english'),
    ]

    operations = [
        migrations.RunPython(update_rule, noop),
    ]
