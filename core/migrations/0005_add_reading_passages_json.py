# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_add_essay_question_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='test',
            name='reading_passages_json',
            field=models.JSONField(blank=True, default=list, verbose_name="Passage'lar (3 ta)"),
        ),
    ]
