# Video kartochkalari uchun obloshka (cover) rasm

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0007_videolesson_video_file_and_youtube_optional'),
    ]

    operations = [
        migrations.AddField(
            model_name='videolesson',
            name='cover_image',
            field=models.ImageField(
                blank=True,
                help_text="Video kartochkasida ko'rinadigan rasm. Yuklanmasa, YouTube thumbnail yoki placeholder ishlatiladi.",
                null=True,
                upload_to='video_covers/%Y/%m/',
                verbose_name='Obloshka (cover)',
            ),
        ),
    ]
