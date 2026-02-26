# Generated for video file upload (admin) and optional YouTube URL

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0006_readingpassage'),
    ]

    operations = [
        migrations.AddField(
            model_name='videolesson',
            name='video_file',
            field=models.FileField(
                blank=True,
                help_text="Admin orqali yuklangan video. Bo'lsa, interfeysda shu video ko'rsatiladi.",
                null=True,
                upload_to='videos/%Y/%m/',
                verbose_name='Video fayl',
            ),
        ),
        migrations.AlterField(
            model_name='videolesson',
            name='youtube_url',
            field=models.URLField(blank=True, null=True, verbose_name='YouTube URL (ixtiyoriy)'),
        ),
    ]
