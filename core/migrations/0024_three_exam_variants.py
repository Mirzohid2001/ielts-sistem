# 3 ta imtihon qog‘ozi varianti: choices yangilanishi

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0023_question_summary_box_type'),
    ]

    operations = [
        migrations.AlterField(
            model_name='test',
            name='variants_to_select',
            field=models.PositiveSmallIntegerField(
                choices=[(1, '1 variant'), (2, '2 variant'), (3, '3 variant')],
                default=1,
                help_text="2 yoki 3 — foydalanuvchi barcha variantlarni ketma-ket yechadi; har savol va passage uchun Variant 1, 2 yoki 3 tanlang.",
                verbose_name='Variantlar soni',
            ),
        ),
        migrations.AlterField(
            model_name='question',
            name='variant',
            field=models.PositiveSmallIntegerField(
                blank=True,
                choices=[(1, 'Variant 1'), (2, 'Variant 2'), (3, 'Variant 3')],
                help_text="Testda 2 yoki 3 variant bo'lsa — har savol uchun imtihon qog‘ozi variantini tanlang.",
                null=True,
                verbose_name="Variant (ko'p variantli testda)",
            ),
        ),
        migrations.AlterField(
            model_name='readingpassage',
            name='variant',
            field=models.PositiveSmallIntegerField(
                blank=True,
                choices=[(1, 'Variant 1'), (2, 'Variant 2'), (3, 'Variant 3')],
                help_text="Testda 2 yoki 3 variant bo'lsa — har passage uchun Variant 1, 2 yoki 3 tanlang.",
                null=True,
                verbose_name="Variant (ko'p variantli testda)",
            ),
        ),
    ]
