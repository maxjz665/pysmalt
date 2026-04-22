"""
Команда для запуска экспериментов по определению авторства из консоли.

Примеры использования:
    python manage.py run_authorship --list_id=1 --method=profile --metric=cosine
    python manage.py run_authorship --list_id=1 --method=ml --classifier=svm
    python manage.py run_authorship --list_id=1 --method=both
    python manage.py run_authorship --list_id=1 --extract_only
"""
import logging

from django.core.management.base import BaseCommand

from text_app.models.tbl_textlist import TblTextListDescription, TblTextListItems

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Запуск экспериментов по определению авторства текста'

    def add_arguments(self, parser):
        parser.add_argument('--list_id', type=int, required=True,
                            help='ID списка текстов')
        parser.add_argument('--method', type=str, default='both',
                            choices=['profile', 'ml', 'both'],
                            help='Метод атрибуции')
        parser.add_argument('--metric', type=str, default='cosine',
                            choices=['cosine', 'manhattan', 'kl'],
                            help='Метрика для профильного метода')
        parser.add_argument('--classifier', type=str, default='svm',
                            choices=['svm', 'rf'],
                            help='Классификатор для ML-метода')
        parser.add_argument('--extract_only', action='store_true',
                            help='Только извлечь признаки, не запускать эксперимент')

    def handle(self, *args, **options):
        list_id = options['list_id']

        try:
            text_list = TblTextListDescription.objects.get(id=list_id)
        except TblTextListDescription.DoesNotExist:
            self.stderr.write(f"Список текстов с ID={list_id} не найден")
            return

        self.stdout.write(f"Список: {text_list.name}")

        # Шаг 1: извлечение признаков
        self.stdout.write("Извлечение синтаксических признаков...")
        from research.authorship.utils.features import extract_and_save_features

        items = TblTextListItems.objects.filter(
            list=text_list
        ).select_related('text', 'text__author')

        processed = 0
        errors = 0
        for item in items:
            try:
                sf = extract_and_save_features(item.text)
                processed += 1
                author_name = item.text.author.name if item.text.author else "???"
                self.stdout.write(
                    f"  [{processed}] {item.text.title[:50]} "
                    f"(автор: {author_name}, "
                    f"ср.длина={sf.avg_sentence_length:.1f}, "
                    f"глубина={sf.avg_tree_depth:.1f})"
                )
            except Exception as e:
                errors += 1
                self.stderr.write(f"  Ошибка для текста {item.text.id}: {e}")

        self.stdout.write(self.style.SUCCESS(
            f"Извлечено признаков: {processed}, ошибок: {errors}"
        ))

        if options['extract_only']:
            return

        # Шаг 2: эксперименты
        method = options['method']

        if method in ('profile', 'both'):
            self.stdout.write("\n--- Профильный метод (Ежов) ---")
            from research.authorship.utils.profile_method import run_experiment as run_profile
            exp = run_profile(
                text_list=text_list,
                metric=options['metric'],
            )
            self.stdout.write(self.style.SUCCESS(
                f"Accuracy: {exp.accuracy:.4f}, "
                f"Precision: {exp.precision:.4f}, "
                f"Recall: {exp.recall:.4f}, "
                f"F1: {exp.f1_score:.4f}"
            ))
            if exp.detailed_results:
                for aid, data in exp.detailed_results.items():
                    if isinstance(data, dict) and 'name' in data:
                        self.stdout.write(
                            f"  {data['name']}: {data.get('correct',0)}/{data.get('total',0)}"
                        )

        if method in ('ml', 'both'):
            self.stdout.write("\n--- ML-метод (Севрюков) ---")
            from research.authorship.utils.ml_method import run_experiment as run_ml
            exp = run_ml(
                text_list=text_list,
                classifier_type=options['classifier'],
            )
            self.stdout.write(self.style.SUCCESS(
                f"Accuracy: {exp.accuracy:.4f}, "
                f"Precision: {exp.precision:.4f}, "
                f"Recall: {exp.recall:.4f}, "
                f"F1: {exp.f1_score:.4f}"
            ))

            # Feature importance для RF
            if options['classifier'] == 'rf' and exp.detailed_results:
                fi = exp.detailed_results.get('feature_importance', [])
                if fi:
                    self.stdout.write("\nТоп-10 важных признаков:")
                    for item in fi[:10]:
                        self.stdout.write(f"  {item['name']}: {item['importance']:.4f}")

        self.stdout.write(self.style.SUCCESS("\nГотово."))
