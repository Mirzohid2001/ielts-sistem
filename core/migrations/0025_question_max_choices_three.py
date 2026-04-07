# MCQ: «Tanlash soni» ga 3 ta javob tanlash

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0024_three_exam_variants'),
    ]

    operations = [
        migrations.AlterField(
            model_name='question',
            name='max_choices',
            field=models.PositiveSmallIntegerField(
                choices=[(1, '1 ta javob'), (2, '2 ta javob'), (3, '3 ta javob')],
                default=1,
                help_text="2 yoki 3 — foydalanuvchi shuncha variantni belgilaydi; «To'g'ri javob» da vergul bilan shuncha harf (masalan a,c,f). 3 ta faqat MCQ uchun.",
                verbose_name='Tanlash soni (MCQ/T-F)',
            ),
        ),
    ]
