from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0039_ielts_study_plan'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='VocabularyLabProgress',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('revision', models.PositiveBigIntegerField(default=1, verbose_name='Versiya')),
                ('document', models.JSONField(blank=True, default=dict, verbose_name='Progress hujjati')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Yaratilgan')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Yangilangan')),
                ('user', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='vocabulary_lab_progress',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='Foydalanuvchi',
                )),
            ],
            options={
                'verbose_name': 'Vocabulary Lab progress',
                'verbose_name_plural': 'Vocabulary Lab progress',
            },
        ),
        migrations.AddIndex(
            model_name='vocabularylabprogress',
            index=models.Index(fields=['user', 'revision'], name='core_vocabu_user_id_635784_idx'),
        ),
    ]
