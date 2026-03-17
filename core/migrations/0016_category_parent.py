from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0015_question_max_choices'),
    ]

    operations = [
        migrations.AddField(
            model_name='category',
            name='parent',
            field=models.ForeignKey(
                to='core.category',
                on_delete=models.CASCADE,
                null=True,
                blank=True,
                related_name='children',
                verbose_name='Ota kategoriya',
            ),
        ),
        migrations.AddIndex(
            model_name='category',
            index=models.Index(fields=['parent', 'is_active'], name='core_catego_parent__5a5c44_idx'),
        ),
    ]

