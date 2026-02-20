# Generated manually for flexible question types

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='question',
            name='question_type',
            field=models.CharField(choices=[('mcq', 'Multiple Choice (A/B/C/D)'), ('true_false', 'True / False'), ('fill_blank', "Bo'sh joyni to'ldirish (bitta so'z)"), ('summary_completion', 'Summary Completion (Reading)'), ('notes_completion', 'Notes Completion (Listening)'), ('short_answer', 'Qisqa javob')], default='mcq', max_length=30, verbose_name='Savol turi'),
        ),
        migrations.AddField(
            model_name='question',
            name='options_json',
            field=models.JSONField(blank=True, default=dict, verbose_name="Qo'shimcha parametrlar (JSON)"),
        ),
        migrations.AddField(
            model_name='question',
            name='correct_answer_json',
            field=models.JSONField(blank=True, default=list, verbose_name="To'g'ri javoblar ro'yxati (JSON)"),
        ),
        migrations.AlterField(
            model_name='question',
            name='option_a',
            field=models.CharField(blank=True, max_length=500, verbose_name='Variant A'),
        ),
        migrations.AlterField(
            model_name='question',
            name='option_b',
            field=models.CharField(blank=True, max_length=500, verbose_name='Variant B'),
        ),
        migrations.AlterField(
            model_name='question',
            name='option_c',
            field=models.CharField(blank=True, max_length=500, verbose_name='Variant C'),
        ),
        migrations.AlterField(
            model_name='question',
            name='option_d',
            field=models.CharField(blank=True, max_length=500, verbose_name='Variant D'),
        ),
        migrations.AlterField(
            model_name='question',
            name='correct_answer',
            field=models.CharField(blank=True, max_length=10, verbose_name="To'g'ri javob (MCQ: a/b/c/d)"),
        ),
        migrations.AlterField(
            model_name='usertestanswer',
            name='user_answer',
            field=models.TextField(blank=True, verbose_name='Foydalanuvchi javobi'),
        ),
    ]
