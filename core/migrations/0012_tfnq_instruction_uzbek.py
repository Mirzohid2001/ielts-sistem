# True/False/Not Given va Yes/No/Not Given ko'rsatmasini o'zbekchaga (TRUE/FALSE/NOT GIVEN inglizcha qoladi)

from django.db import migrations


TRUE_FALSE_NOT_GIVEN_UZ = """Quyidagi gap matndagi ma'lumotga to'g'ri keladimi?
Javob varag'ingizdagi qatorlarda yozing
TRUE agar gap matndagi ma'lumotga to'g'ri kelsa
FALSE agar gap matndagi ma'lumotga zid bo'lsa
NOT GIVEN agar bunda haqida ma'lumot bo'lmasa"""

YES_NO_NOT_GIVEN_UZ = """Quyidagi gap muallifning fikriga to'g'ri keladimi?
Javob varag'ingizdagi qatorlarda yozing
YES agar gap muallifning fikriga to'g'ri kelsa
NO agar gap muallifning fikriga zid bo'lsa
NOT GIVEN agar muallifning bu haqda nima deb o'ylashi aytib bo'lmasa"""


def update_to_uzbek(apps, schema_editor):
    QuestionTypeRule = apps.get_model('core', 'QuestionTypeRule')
    QuestionTypeRule.objects.filter(question_type='true_false_not_given').update(
        shart_text=TRUE_FALSE_NOT_GIVEN_UZ
    )
    QuestionTypeRule.objects.filter(question_type='yes_no_not_given').update(
        shart_text=YES_NO_NOT_GIVEN_UZ
    )


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0011_update_tfnq_instruction_text'),
    ]

    operations = [
        migrations.RunPython(update_to_uzbek, noop),
    ]
