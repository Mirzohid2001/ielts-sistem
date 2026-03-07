# Namuna kategoriyasi va boshqalarni interfeysda yashirish uchun

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0012_tfnq_instruction_uzbek'),
    ]

    operations = [
        migrations.AddField(
            model_name='category',
            name='show_on_site',
            field=models.BooleanField(
                default=True,
                help_text="O'chirilsa — faqat admin panelda ko'rinadi, foydalanuvchi sahifasida emas.",
                verbose_name="Interfeysda ko'rsatish"
            ),
        ),
    ]
