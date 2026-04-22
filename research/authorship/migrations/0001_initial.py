# Generated manually for authorship module

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('text_app', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Таблица знаков препинания
        migrations.CreateModel(
            name='TblSign',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('chapter_index', models.IntegerField(default=0)),
                ('paragraph_index', models.IntegerField(default=0)),
                ('sentence_index', models.IntegerField(default=0)),
                ('position_index', models.IntegerField(default=0)),
                ('sign_value', models.CharField(max_length=10)),
                ('placement', models.CharField(
                    choices=[('before', 'Перед словом'), ('after', 'После слова')],
                    default='after', max_length=10)),
                ('text', models.ForeignKey(
                    db_column='TEXT_ID', on_delete=django.db.models.deletion.CASCADE,
                    to='text_app.tbltext')),
                ('word', models.ForeignKey(
                    blank=True, db_column='WORD_ID', null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    to='text_app.tblword')),
            ],
            options={
                'db_table': 'signs',
                'db_table_comment': 'Знаки препинания текста',
            },
        ),
        migrations.AddIndex(
            model_name='tblsign',
            index=models.Index(
                fields=['text', 'sentence_index', 'position_index'],
                name='idx_signs_text_sent_pos'),
        ),

        # Синтаксические признаки текста
        migrations.CreateModel(
            name='TblSyntacticFeature',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('avg_sentence_length', models.FloatField(default=0)),
                ('std_sentence_length', models.FloatField(default=0)),
                ('avg_tree_depth', models.FloatField(default=0)),
                ('avg_tree_width', models.FloatField(default=0)),
                ('pos_unigram_dist', models.JSONField(default=dict)),
                ('pos_bigram_dist', models.JSONField(default=dict)),
                ('pos_trigram_dist', models.JSONField(default=dict)),
                ('dep_type_dist', models.JSONField(default=dict)),
                ('clause_type_dist', models.JSONField(default=dict)),
                ('punct_pattern_dist', models.JSONField(default=dict)),
                ('tree_depth_dist', models.JSONField(default=dict)),
                ('feature_vector', models.JSONField(default=list)),
                ('extracted_at', models.DateTimeField(auto_now=True)),
                ('text', models.OneToOneField(
                    db_column='TEXT_ID', on_delete=django.db.models.deletion.CASCADE,
                    related_name='syntactic_features', to='text_app.tbltext')),
            ],
            options={
                'db_table': 'syntactic_features',
                'db_table_comment': 'Синтаксические признаки текстов',
            },
        ),

        # Профили авторов
        migrations.CreateModel(
            name='TblAuthorProfile',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('texts_count', models.IntegerField(default=0)),
                ('profile_vector', models.JSONField(default=list)),
                ('profile_data', models.JSONField(default=dict)),
                ('built_at', models.DateTimeField(auto_now=True)),
                ('author', models.ForeignKey(
                    db_column='AUTHOR_ID', on_delete=django.db.models.deletion.CASCADE,
                    to='text_app.tblauthor')),
                ('text_list', models.ForeignKey(
                    db_column='LIST_ID', on_delete=django.db.models.deletion.CASCADE,
                    to='text_app.tbltextlistdescription')),
            ],
            options={
                'db_table': 'author_profiles',
                'db_table_comment': 'Синтаксические профили авторов',
                'unique_together': {('author', 'text_list')},
            },
        ),

        # Эксперименты
        migrations.CreateModel(
            name='TblAttributionExperiment',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255)),
                ('method', models.CharField(
                    choices=[('profile', 'Статистический профильный метод (Ежов)'),
                             ('ml', 'Метод машинного обучения (Севрюков)')],
                    max_length=20)),
                ('params', models.JSONField(default=dict)),
                ('accuracy', models.FloatField(default=0)),
                ('precision', models.FloatField(default=0)),
                ('recall', models.FloatField(default=0)),
                ('f1_score', models.FloatField(default=0)),
                ('confusion_matrix', models.JSONField(default=list)),
                ('detailed_results', models.JSONField(default=dict)),
                ('trained_model', models.BinaryField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('build_status', models.CharField(default='pending', max_length=50)),
                ('text_list', models.ForeignKey(
                    db_column='LIST_ID', on_delete=django.db.models.deletion.CASCADE,
                    to='text_app.tbltextlistdescription')),
                ('owner', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'attribution_experiments',
                'db_table_comment': 'Эксперименты по определению авторства',
            },
        ),

        # Результаты атрибуции
        migrations.CreateModel(
            name='TblAttributionResult',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('confidence', models.FloatField(default=0)),
                ('scores', models.JSONField(default=dict)),
                ('is_correct', models.BooleanField(default=False)),
                ('experiment', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='results',
                    to='authorship.tblattributionexperiment')),
                ('text', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    to='text_app.tbltext')),
                ('true_author', models.ForeignKey(
                    null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name='true_results', to='text_app.tblauthor')),
                ('predicted_author', models.ForeignKey(
                    null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name='predicted_results', to='text_app.tblauthor')),
            ],
            options={
                'db_table': 'attribution_results',
                'db_table_comment': 'Результаты атрибуции текстов',
            },
        ),
    ]
