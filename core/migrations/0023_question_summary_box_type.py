# Generated manually: summary_box savol turi

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0022_rename_core_catego_parent__5a5c44_idx_core_catego_parent__68b602_idx_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='question',
            name='question_type',
            field=models.CharField(
                choices=[
                    ('mcq', 'Multiple Choice (A/B/C/D)'),
                    ('true_false', 'True / False'),
                    ('true_false_not_given', 'True / False / Not Given (Reading)'),
                    ('yes_no_not_given', 'Yes / No / Not Given'),
                    ('fill_blank', "Bo'sh joyni to'ldirish (bitta so'z)"),
                    ('summary_completion', 'Summary Completion (Reading)'),
                    ('notes_completion', 'Notes Completion (Listening)'),
                    ('sentence_completion', 'Sentence Completion'),
                    ('table_completion', 'Table Completion'),
                    ('short_answer', 'Qisqa javob'),
                    ('essay', 'Essay (Writing Task)'),
                    ('matching_headings', 'Matching Headings (matnga sarlavha)'),
                    ('matching_sentences', 'Matching Sentence Endings'),
                    ('matching_features', 'Matching Features (elementlarni toifalarga)'),
                    ('matching_info', 'Matching Information (paragraflarga)'),
                    ('classification', 'Classification (A/B/C ga tasniflash)'),
                    ('list_selection', "List Selection (ro'yxatdan tanlash)"),
                    ('summary_box', 'Summary + box (inline qavslar, A–H tanlash)'),
                ],
                default='mcq',
                max_length=30,
                verbose_name='Savol turi',
            ),
        ),
    ]
