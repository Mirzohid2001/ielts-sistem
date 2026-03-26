from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0019_update_mcq_rule_extra_options'),
    ]

    operations = [
        migrations.CreateModel(
            name='SATResource',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=300, verbose_name='Sarlavha')),
                ('subject', models.CharField(choices=[('math', 'Matematika'), ('english', 'Ingliz tili')], db_index=True, max_length=20, verbose_name="Bo'lim")),
                ('description', models.TextField(blank=True, verbose_name='Tavsif')),
                ('video_file', models.FileField(blank=True, null=True, upload_to='sat/videos/%Y/%m/', verbose_name='Video fayl')),
                ('youtube_url', models.URLField(blank=True, null=True, verbose_name='YouTube URL')),
                ('youtube_id', models.CharField(blank=True, db_index=True, max_length=50, verbose_name='YouTube ID')),
                ('pdf_file', models.FileField(blank=True, null=True, upload_to='sat/pdfs/%Y/%m/', verbose_name='PDF fayl')),
                ('order', models.IntegerField(default=0, verbose_name='Tartib')),
                ('is_active', models.BooleanField(default=True, verbose_name='Faol')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'SAT Resurs',
                'verbose_name_plural': 'SAT Resurslar',
                'ordering': ['subject', 'order', '-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='satresource',
            index=models.Index(fields=['subject', 'is_active'], name='core_satres_subject_0f2ccd_idx'),
        ),
    ]

