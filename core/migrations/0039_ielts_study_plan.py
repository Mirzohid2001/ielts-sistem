import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0038_practicelabrecord'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='IELTSStudyPlan',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('revision', models.PositiveBigIntegerField(default=1, verbose_name='Versiya')),
                ('document', models.JSONField(blank=True, default=dict, verbose_name='Reja hujjati')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Yaratilgan')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Yangilangan')),
                ('user', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='ielts_study_plan',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='Foydalanuvchi',
                )),
            ],
            options={
                'verbose_name': 'IELTS study plan',
                'verbose_name_plural': 'IELTS study plans',
            },
        ),
        migrations.AddIndex(
            model_name='ieltsstudyplan',
            index=models.Index(fields=['user', 'revision'], name='core_ieltss_user_id_9ad5d8_idx'),
        ),
    ]
