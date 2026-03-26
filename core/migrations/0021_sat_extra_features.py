from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0020_satresource'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='SATResourceProgress',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('watch_percentage', models.IntegerField(default=0, verbose_name='Foiz (0-100)')),
                ('watched', models.BooleanField(default=False, verbose_name='Yakunlangan')),
                ('last_accessed_at', models.DateTimeField(auto_now=True, verbose_name='Oxirgi kirish')),
                ('completed_at', models.DateTimeField(blank=True, null=True, verbose_name='Yakunlangan vaqt')),
                ('resource', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='progress', to='core.satresource', verbose_name='Resurs')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sat_progress', to=settings.AUTH_USER_MODEL, verbose_name='Foydalanuvchi')),
            ],
            options={
                'verbose_name': 'SAT Progress',
                'verbose_name_plural': 'SAT Progresslar',
                'unique_together': {('user', 'resource')},
            },
        ),
        migrations.CreateModel(
            name='SATResourceNote',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('note_text', models.TextField(verbose_name='Eslatma matni')),
                ('timestamp', models.IntegerField(default=0, verbose_name='Vaqt (soniya)')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Yaratilgan vaqt')),
                ('resource', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notes', to='core.satresource', verbose_name='Resurs')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sat_notes', to=settings.AUTH_USER_MODEL, verbose_name='Foydalanuvchi')),
            ],
            options={
                'verbose_name': 'SAT Eslatma',
                'verbose_name_plural': 'SAT Eslatmalar',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='SATResourceBookmark',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('timestamp', models.IntegerField(default=0, verbose_name='Vaqt (soniya)')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Yaratilgan vaqt')),
                ('resource', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='bookmarks', to='core.satresource', verbose_name='Resurs')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sat_bookmarks', to=settings.AUTH_USER_MODEL, verbose_name='Foydalanuvchi')),
            ],
            options={
                'verbose_name': 'SAT Bookmark',
                'verbose_name_plural': 'SAT Bookmarklar',
                'unique_together': {('user', 'resource')},
            },
        ),
        migrations.AddIndex(
            model_name='satresourceprogress',
            index=models.Index(fields=['user', 'resource'], name='core_satreso_user_id_2f4f3a_idx'),
        ),
        migrations.AddIndex(
            model_name='satresourceprogress',
            index=models.Index(fields=['user', 'watched'], name='core_satreso_user_id_b4922b_idx'),
        ),
        migrations.AddIndex(
            model_name='satresourcenote',
            index=models.Index(fields=['user', 'resource'], name='core_satreso_user_id_6f8a63_idx'),
        ),
        migrations.AddIndex(
            model_name='satresourcebookmark',
            index=models.Index(fields=['user', 'resource'], name='core_satreso_user_id_644620_idx'),
        ),
    ]

