# Savol matni ixtiyoriy — draft savol qo'shib keyin to'ldirish uchun

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0016_category_parent'),
    ]

    operations = [
        migrations.AlterField(
            model_name='question',
            name='question_text',
            field=models.TextField(
                blank=True,
                help_text="Bo'sh qoldirsangiz — savol keyinroq to'ldiriladi (draft).",
                verbose_name='Savol matni',
            ),
        ),
    ]
