from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0033_aiwritingfeedback_sentence_corrections'),
    ]

    operations = [
        migrations.AddField(
            model_name='aiwritingfeedback',
            name='writing_errors',
            field=models.JSONField(
                blank=True,
                default=list,
                help_text='[{wrong, correct, type, why}] — essaydagi aniq grammatika/imlo xatolari',
                verbose_name='Aniq xatolar',
            ),
        ),
    ]
