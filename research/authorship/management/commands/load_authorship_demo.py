from django.core.management.base import BaseCommand, CommandError

from research.authorship.utils.demo_data import CORPUS_SPECS, CorpusLoadError, load_corpus


class Command(BaseCommand):
    help = "Load authorship smoke corpus or report corpora and extract real Natasha features."

    def add_arguments(self, parser):
        parser.add_argument(
            "--corpus",
            default="smoke",
            choices=["smoke", "all", *CORPUS_SPECS.keys()],
            help=(
                "Corpus to load. 'smoke' is a tiny 3x4 launch test; "
                "5x8/5x7/7x6 are report corpora loaded from the real SQL dump."
            ),
        )
        parser.add_argument(
            "--source-sql",
            default=None,
            help="Path to smalt.sql.20220421.112227.gz for full corpora.",
        )
        parser.add_argument(
            "--no-extract",
            action="store_true",
            help="Load texts/lists only. By default real Natasha features are extracted.",
        )
        parser.add_argument(
            "--force-extract",
            action="store_true",
            help="Re-extract features even if a 193-dimensional vector already exists.",
        )

    def handle(self, *args, **options):
        try:
            results = load_corpus(
                corpus=options["corpus"],
                sql_path=options["source_sql"],
                extract_features=not options["no_extract"],
                force_extract=options["force_extract"],
            )
        except CorpusLoadError as exc:
            raise CommandError(str(exc)) from exc

        for result in results:
            self.stdout.write(self.style.SUCCESS(
                f"Loaded corpus={result['corpus']} list_id={result['list_id']} "
                f"list='{result['list_name']}' texts={result['texts']} "
                f"authors={result['authors']} features={result['features_extracted']}"
            ))
            self.stdout.write(f"source: {result['source']}")

