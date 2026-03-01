# True/False/Not Given va Yes/No/Not Given uchun to'liq IELTS ko'rsatma matni
# (TRUE/FALSE/NOT GIVEN dan keyin gaplar — skrinshotdagi kabi)

from django.db import migrations


TRUE_FALSE_NOT_GIVEN_TEXT = """Do the following statements agree with the information given in Reading Passage?
in boxes on your answer sheet, write
TRUE if the statement agrees with the information
FALSE if the statement contradicts the information
NOT GIVEN if there is no information on this"""

YES_NO_NOT_GIVEN_TEXT = """Do the following statements agree with the views of the writer?
in boxes on your answer sheet, write
YES if the statement agrees with the views of the writer
NO if the statement contradicts the views of the writer
NOT GIVEN if it is impossible to say what the writer thinks about this"""


def update_instructions(apps, schema_editor):
    QuestionTypeRule = apps.get_model('core', 'QuestionTypeRule')
    QuestionTypeRule.objects.filter(question_type='true_false_not_given').update(
        shart_text=TRUE_FALSE_NOT_GIVEN_TEXT
    )
    QuestionTypeRule.objects.filter(question_type='yes_no_not_given').update(
        shart_text=YES_NO_NOT_GIVEN_TEXT
    )


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0010_populate_question_type_rules'),
    ]

    operations = [
        migrations.RunPython(update_instructions, noop),
    ]
