# Generated manually

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_add_reading_passages_json'),
    ]

    operations = [
        migrations.CreateModel(
            name='ReadingPassage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('order', models.PositiveIntegerField(default=1, verbose_name='Tartib')),
                ('title', models.CharField(blank=True, max_length=255, verbose_name='Sarlavha (masalan: Passage 1)')),
                ('text', models.TextField(blank=True, verbose_name='Matn')),
                ('test', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reading_passages', to='core.test', verbose_name='Test')),
            ],
            options={
                'verbose_name': "Passage",
                'verbose_name_plural': "Passage'lar",
                'ordering': ['test', 'order'],
            },
        ),
    ]
