# Savol turi bo'yicha shart (har tur uchun bitta)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0008_videolesson_cover_image'),
    ]

    operations = [
        migrations.CreateModel(
            name='QuestionTypeRule',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('question_type', models.CharField(help_text="Question.QUESTION_TYPES dagi qiymat (mcq, true_false, fill_blank, ...)", max_length=30, unique=True, verbose_name='Savol turi')),
                ('name_uz', models.CharField(max_length=200, verbose_name="Nomi (o'zbekcha)")),
                ('shart_text', models.TextField(blank=True, help_text="Bu savol turi uchun talab matni. Admin da savol qo'shishda tanlangan turda shu matn ko'rsatiladi.", verbose_name='Shart (qoida / talab)')),
                ('order', models.IntegerField(default=0, verbose_name='Tartib')),
            ],
            options={
                'verbose_name': 'Savol turi qoidasi',
                'verbose_name_plural': 'Savol turi qoidalari',
                'ordering': ['order', 'question_type'],
            },
        ),
    ]
