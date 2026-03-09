# 2 variantli test: Test.variants_to_select, Question.variant, ReadingPassage.variant

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0013_category_show_on_site'),
    ]

    operations = [
        migrations.AddField(
            model_name='test',
            name='variants_to_select',
            field=models.PositiveSmallIntegerField(
                choices=[(1, '1 variant'), (2, '2 variant')],
                default=1,
                help_text="2 qilsangiz — foydalanuvchi ikkala variantni ham bajaradi; har bir savol va passage da «Variant 1» yoki «Variant 2» tanlang.",
                verbose_name='Variantlar soni',
            ),
        ),
        migrations.AddField(
            model_name='question',
            name='variant',
            field=models.PositiveSmallIntegerField(
                blank=True,
                choices=[(1, 'Variant 1'), (2, 'Variant 2')],
                help_text="Faqat test «2 variant» bo'lsa tanlang.",
                null=True,
                verbose_name='Variant (2 variantli testda)',
            ),
        ),
        migrations.AddField(
            model_name='readingpassage',
            name='variant',
            field=models.PositiveSmallIntegerField(
                blank=True,
                choices=[(1, 'Variant 1'), (2, 'Variant 2')],
                help_text="Faqat test «2 variant» bo'lsa to'ldiring.",
                null=True,
                verbose_name='Variant (2 variantli testda)',
            ),
        ),
    ]
