# True/False/Not Given va Yes/No/Not Given — standart IELTS inglizcha ko'rsatma (DB / admin)

from django.db import migrations


TRUE_FALSE_NOT_GIVEN_EN = """Do the following statements agree with the information given in the reading passage?

On your answer sheet, write

TRUE if the statement agrees with the information
FALSE if the statement contradicts the information
NOT GIVEN if there is no information on this"""

YES_NO_NOT_GIVEN_EN = """Do the following statements agree with the views of the writer in the reading passage?

On your answer sheet, write

YES if the statement agrees with the views of the writer
NO if the statement contradicts the views of the writer
NOT GIVEN if it is impossible to say what the writer thinks about this"""


def forwards(apps, schema_editor):
    QuestionTypeRule = apps.get_model('core', 'QuestionTypeRule')
    QuestionTypeRule.objects.filter(question_type='true_false_not_given').update(
        shart_text=TRUE_FALSE_NOT_GIVEN_EN
    )
    QuestionTypeRule.objects.filter(question_type='yes_no_not_given').update(
        shart_text=YES_NO_NOT_GIVEN_EN
    )


def backwards(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0017_question_text_blank'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
