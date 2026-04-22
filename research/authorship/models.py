"""
Модели для модуля определения авторства текста
на основе синтаксического анализа.
"""
import json

from django.db import models
from django.utils import timezone

from text_app.models.tbl_text import TblText
from text_app.models.tbl_word import TblWord
from text_app.models.tbl_author import TblAuthor
from text_app.models.tbl_textlist import TblTextListDescription
from user_app.models import TblUser


class TblSign(models.Model):
    """
    Таблица знаков препинания.
    Хранит знаки препинания отдельно от слов с привязкой к позиции
    в предложении. Позволяет точно восстановить исходный текст.
    """
    class Meta:
        db_table = 'signs'
        db_table_comment = 'Знаки препинания текста'
        indexes = [
            models.Index(fields=['text', 'sentence_index', 'position_index'],
                         name='idx_signs_text_sent_pos'),
        ]

    id = models.AutoField(primary_key=True)
    text = models.ForeignKey(TblText, on_delete=models.CASCADE,
                             db_column='TEXT_ID',
                             help_text='Идентификатор текста')
    word = models.ForeignKey(TblWord, on_delete=models.SET_NULL,
                             null=True, blank=True,
                             db_column='WORD_ID',
                             help_text='Связанное слово (NULL если знак перед первым словом)')
    chapter_index = models.IntegerField(default=0,
                                        help_text='Индекс главы')
    paragraph_index = models.IntegerField(default=0,
                                          help_text='Индекс параграфа')
    sentence_index = models.IntegerField(default=0,
                                         help_text='Индекс предложения')
    position_index = models.IntegerField(default=0,
                                         help_text='Порядковая позиция знака в предложении')
    sign_value = models.CharField(max_length=10,
                                  help_text='Значение знака препинания')
    placement = models.CharField(max_length=10, default='after',
                                 choices=[('before', 'Перед словом'),
                                          ('after', 'После слова')],
                                 help_text='Позиция относительно слова')


class TblSyntacticFeature(models.Model):
    """
    Извлечённые синтаксические признаки текста.
    Хранит вектор признаков в формате JSON для каждого текста.
    """
    class Meta:
        db_table = 'syntactic_features'
        db_table_comment = 'Синтаксические признаки текстов'

    id = models.AutoField(primary_key=True)
    text = models.OneToOneField(TblText, on_delete=models.CASCADE,
                                db_column='TEXT_ID',
                                related_name='syntactic_features')
    # Средние характеристики предложений
    avg_sentence_length = models.FloatField(default=0,
                                            help_text='Средняя длина предложения в словах')
    std_sentence_length = models.FloatField(default=0,
                                            help_text='Стандартное отклонение длины предложений')
    avg_tree_depth = models.FloatField(default=0,
                                       help_text='Средняя глубина дерева зависимостей')
    avg_tree_width = models.FloatField(default=0,
                                       help_text='Средняя ширина дерева зависимостей')

    # Распределения в формате JSON
    pos_unigram_dist = models.JSONField(default=dict,
                                        help_text='Распределение POS-униграмм')
    pos_bigram_dist = models.JSONField(default=dict,
                                       help_text='Распределение POS-биграмм')
    pos_trigram_dist = models.JSONField(default=dict,
                                        help_text='Распределение POS-триграмм')
    dep_type_dist = models.JSONField(default=dict,
                                     help_text='Распределение типов синтаксических связей')
    clause_type_dist = models.JSONField(default=dict,
                                        help_text='Распределение типов предложений')
    punct_pattern_dist = models.JSONField(default=dict,
                                          help_text='Распределение пунктуационных паттернов')
    tree_depth_dist = models.JSONField(default=dict,
                                       help_text='Распределение глубин деревьев')

    # Полный вектор признаков
    feature_vector = models.JSONField(default=list,
                                      help_text='Полный нормализованный вектор признаков')

    extracted_at = models.DateTimeField(auto_now=True)

    def get_feature_vector_np(self):
        """Возвращает вектор признаков как numpy-массив."""
        import numpy as np
        return np.array(self.feature_vector, dtype=float)


class TblAuthorProfile(models.Model):
    """
    Синтаксический профиль автора.
    Агрегированные признаки по всем текстам автора из списка.
    """
    class Meta:
        db_table = 'author_profiles'
        db_table_comment = 'Синтаксические профили авторов'
        unique_together = [['author', 'text_list']]

    id = models.AutoField(primary_key=True)
    author = models.ForeignKey(TblAuthor, on_delete=models.CASCADE,
                               db_column='AUTHOR_ID')
    text_list = models.ForeignKey(TblTextListDescription,
                                  on_delete=models.CASCADE,
                                  db_column='LIST_ID',
                                  help_text='Список текстов, по которому строился профиль')
    texts_count = models.IntegerField(default=0,
                                      help_text='Количество текстов в профиле')
    profile_vector = models.JSONField(default=list,
                                      help_text='Усреднённый вектор признаков')
    profile_data = models.JSONField(default=dict,
                                    help_text='Детализированные данные профиля')
    built_at = models.DateTimeField(auto_now=True)

    def get_profile_vector_np(self):
        import numpy as np
        return np.array(self.profile_vector, dtype=float)


class TblAttributionExperiment(models.Model):
    """
    Результат эксперимента по определению авторства.
    Хранит параметры и метрики эксперимента.
    """
    class Meta:
        db_table = 'attribution_experiments'
        db_table_comment = 'Эксперименты по определению авторства'

    METHOD_CHOICES = [
        ('profile', 'Статистический профильный метод (Ежов)'),
        ('ml', 'Метод машинного обучения (Севрюков)'),
    ]

    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    method = models.CharField(max_length=20, choices=METHOD_CHOICES)
    text_list = models.ForeignKey(TblTextListDescription,
                                  on_delete=models.CASCADE,
                                  db_column='LIST_ID')
    owner = models.ForeignKey(TblUser, on_delete=models.SET_NULL,
                              null=True, blank=True)

    # Параметры эксперимента
    params = models.JSONField(default=dict,
                              help_text='Параметры эксперимента')

    # Результаты
    accuracy = models.FloatField(default=0)
    precision = models.FloatField(default=0)
    recall = models.FloatField(default=0)
    f1_score = models.FloatField(default=0)
    confusion_matrix = models.JSONField(default=list)
    detailed_results = models.JSONField(default=dict,
                                        help_text='Подробные результаты по авторам')
    # Сериализованная модель (для ML-метода)
    trained_model = models.BinaryField(null=True, blank=True,
                                       help_text='Обученная модель (pickle)')

    created_at = models.DateTimeField(auto_now_add=True)
    build_status = models.CharField(max_length=50, default='pending')


class TblAttributionResult(models.Model):
    """
    Результат атрибуции конкретного текста.
    """
    class Meta:
        db_table = 'attribution_results'
        db_table_comment = 'Результаты атрибуции текстов'

    id = models.AutoField(primary_key=True)
    experiment = models.ForeignKey(TblAttributionExperiment,
                                   on_delete=models.CASCADE,
                                   related_name='results')
    text = models.ForeignKey(TblText, on_delete=models.CASCADE)
    true_author = models.ForeignKey(TblAuthor, on_delete=models.SET_NULL,
                                    null=True, related_name='true_results')
    predicted_author = models.ForeignKey(TblAuthor, on_delete=models.SET_NULL,
                                         null=True, related_name='predicted_results')
    confidence = models.FloatField(default=0,
                                   help_text='Уверенность предсказания (0-1)')
    scores = models.JSONField(default=dict,
                              help_text='Оценки по каждому автору-кандидату')
    is_correct = models.BooleanField(default=False)
