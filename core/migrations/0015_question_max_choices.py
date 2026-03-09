# MCQ/True-False da 1 yoki 2 ta javob tanlash

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0014_test_variants_question_passage_variant'),
    ]

    operations = [
        migrations.AddField(
            model_name='question',
            name='max_choices',
            field=models.PositiveSmallIntegerField(
                choices=[(1, '1 ta javob'), (2, '2 ta javob')],
                default=1,
                help_text="«2 ta javob» qilsangiz — foydalanuvchi ikkita variantni belgilaydi; to'g'ri javobda ikkalasini kiriting (masalan a,c).",
                verbose_name='Tanlash soni (MCQ/T-F)',
            ),
        ),
    ]
