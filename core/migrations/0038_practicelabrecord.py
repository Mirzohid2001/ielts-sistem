from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('core', '0037_ai_feedback_language'),
    ]

    operations = [
        migrations.CreateModel(
            name='PracticeLabRecord',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('skill', models.CharField(max_length=16, verbose_name='Ko‘nikma')),
                ('kind', models.CharField(choices=[('draft', 'Qoralama'), ('done', 'Tugallangan')], max_length=8, verbose_name='Holat')),
                ('level', models.CharField(blank=True, max_length=8, verbose_name='Daraja')),
                ('practice_type', models.CharField(blank=True, max_length=40, verbose_name='Savol turi')),
                ('mode', models.CharField(blank=True, max_length=16, verbose_name='Rejim')),
                ('title', models.CharField(blank=True, max_length=240, verbose_name='Sarlavha')),
                ('label', models.CharField(blank=True, max_length=120, verbose_name='Tur nomi')),
                ('correct', models.PositiveSmallIntegerField(default=0, verbose_name='To‘g‘ri')),
                ('total', models.PositiveSmallIntegerField(default=0, verbose_name='Jami')),
                ('public', models.JSONField(blank=True, default=dict, verbose_name='O‘quvchiga ochiq matn')),
                ('secret', models.JSONField(blank=True, default=dict, verbose_name='Javob kaliti')),
                ('state', models.JSONField(blank=True, default=dict, verbose_name='Javoblar va belgilar')),
                ('result', models.JSONField(blank=True, default=dict, verbose_name='Tekshiruv')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Yaratilgan vaqt')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Yangilangan vaqt')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='practice_lab_records', to=settings.AUTH_USER_MODEL, verbose_name='Foydalanuvchi')),
            ],
            options={
                'verbose_name': 'Mashq yozuvi',
                'verbose_name_plural': 'Mashq yozuvlari',
                'ordering': ['-updated_at'],
            },
        ),
        migrations.AddIndex(
            model_name='practicelabrecord',
            index=models.Index(fields=['user', 'skill', 'kind', '-updated_at'], name='core_plab_user_kind_idx'),
        ),
    ]
