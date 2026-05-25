from django.core.management.base import BaseCommand, CommandError

from research.authorship.models import TblAttributionExperiment
from research.authorship.utils.demo_data import get_default_authorship_list
from research.authorship.utils.features import FeatureExtractionError, extract_and_save_features
from text_app.models.tbl_textlist import TblTextListDescription, TblTextListItems


class Command(BaseCommand):
    help = "Run authorship attribution experiments on a text list."

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group()
        group.add_argument("--list_id", "--list-id", dest="list_id", type=int, default=None,
                           help="Text list id.")
        group.add_argument("--list-name", "--list_name", dest="list_name", default=None,
                           help="Text list name or substring (resolved via text_lists.resolve_text_list).")
        parser.add_argument(
            "--method",
            default="both",
            choices=["profile", "ml", "both"],
            help="Experiment method.",
        )
        parser.add_argument(
            "--metric",
            default="manhattan",
            choices=["manhattan", "cosine"],
            help="Profile metric. The report pipeline uses Manhattan.",
        )
        parser.add_argument(
            "--classifier",
            default="svm",
            choices=["svm", "rf"],
            help="ML classifier family. The report pipeline uses svm.",
        )
        parser.add_argument(
            "--extract-features",
            action="store_true",
            help="Extract/re-extract real Natasha 193-dimensional features before experiments.",
        )
        parser.add_argument(
            "--extract-only",
            "--extract_only",
            dest="extract_only",
            action="store_true",
            help="Only extract real Natasha features and stop.",
        )
        parser.add_argument(
            "--queue",
            action="store_true",
            help="Create a queued experiment instead of running synchronously. Requires run_authorship_worker.",
        )

    def handle(self, *args, **options):
        text_list = self._resolve_text_list(options["list_id"], options.get("list_name"))
        self.stdout.write(f"Text list: id={text_list.id} name='{text_list.name}'")

        if options["extract_features"] or options["extract_only"]:
            self._extract_features(text_list)
            if options["extract_only"]:
                return

        if options.get("queue"):
            self._create_queued(text_list, options)
            return

        if options["method"] in ("profile", "both"):
            from research.authorship.utils.profile_method import run_experiment as run_profile

            exp = run_profile(
                text_list=text_list,
                metric=options["metric"],
                extract_features=options["extract_features"],
            )
            self._print_experiment(exp)

        if options["method"] in ("ml", "both"):
            from research.authorship.utils.ml_method import run_experiment as run_ml

            exp = run_ml(
                text_list=text_list,
                classifier_type=options["classifier"],
            )
            self._print_experiment(exp)

    def _create_queued(self, text_list, options):
        methods = ["profile", "ml"] if options["method"] == "both" else [options["method"]]
        for method in methods:
            if method == 'profile':
                params = {
                    "metric": options["metric"],
                    "cv": "leave-one-out",
                    "extract_features": options["extract_features"],
                }
                name = f"Profile ({options['metric']}) - {text_list.name}"
                metric = options["metric"]
            else:
                params = {
                    "pipeline": "StandardScaler -> SelectKBest(f_classif) -> SVC",
                    "outer_cv": "leave-one-out",
                    "classifier_type": options["classifier"],
                }
                name = f"ML SVC - {text_list.name}"
                metric = "f1_macro"
            exp = TblAttributionExperiment.objects.create(
                name=name,
                method=method,
                metric=metric,
                text_list=text_list,
                params=params,
                build_status='queued',
            )
            self.stdout.write(self.style.SUCCESS(
                f"Queued experiment_id={exp.id} method={method} list='{text_list.name}'"
            ))
        self.stdout.write("Run 'manage.py run_authorship_worker' to process.")

    def _resolve_text_list(self, list_id, list_name):
        if list_name is not None:
            from research.authorship.utils.text_lists import resolve_text_list
            return resolve_text_list(user=None, name_or_id=list_name)

        if list_id is not None:
            try:
                return TblTextListDescription.objects.get(id=list_id)
            except TblTextListDescription.DoesNotExist as exc:
                raise CommandError(f"Text list id={list_id} was not found.") from exc

        text_list = get_default_authorship_list()
        if not text_list:
            raise CommandError(
                "No text list was found. Run load_authorship_demo first or pass --list_id / --list-name."
            )
        return text_list

    def _extract_features(self, text_list):
        items = (
            TblTextListItems.objects
            .filter(list=text_list)
            .select_related("text", "text__author")
            .order_by("text_id")
        )
        processed = 0
        errors = []
        self.stdout.write("Extracting real Natasha authorship features...")
        for item in items:
            try:
                sf = extract_and_save_features(item.text)
                processed += 1
                author_name = item.text.author.name if item.text.author else "unknown"
                self.stdout.write(
                    f"  [{processed}] text_id={item.text_id} author='{author_name}' "
                    f"vector_size={sf.vector_size}"
                )
            except FeatureExtractionError as exc:
                errors.append(f"text_id={item.text_id}: {exc}")

        if errors:
            for error in errors:
                self.stderr.write(error)
            raise CommandError(
                f"Feature extraction failed for {len(errors)} text(s); "
                "the command did not use a synthetic fallback."
            )

        self.stdout.write(self.style.SUCCESS(f"Features extracted: {processed}"))

    def _print_experiment(self, exp):
        metrics = exp.metrics or {
            "accuracy": exp.accuracy,
            "macro_f1": exp.f1_score,
            "n_texts": exp.results.count(),
            "n_authors": len(exp.detailed_results.get("by_author", {}))
            if isinstance(exp.detailed_results, dict) else 0,
        }
        self.stdout.write(self.style.SUCCESS(
            f"experiment_id={exp.id} method={exp.method} status={exp.build_status} "
            f"accuracy={metrics.get('accuracy', exp.accuracy):.4f} "
            f"macro_f1={metrics.get('macro_f1', exp.f1_score):.4f} "
            f"texts={metrics.get('n_texts', exp.results.count())} "
            f"authors={metrics.get('n_authors', 0)}"
        ))
        if exp.build_status != "completed":
            raise CommandError(f"{exp.method} experiment did not complete: {exp.build_status}")
