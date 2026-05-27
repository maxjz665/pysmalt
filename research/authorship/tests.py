from io import StringIO

from django.core.management import call_command
from django.test import Client, TestCase

from research.authorship.models import TblAttributionResult, TblSyntacticFeature
from research.authorship.utils.demo_data import SMOKE_LIST_NAME, load_smoke_corpus
from research.authorship.utils.features import VECTOR_SIZE, extract_and_vectorize
from research.authorship.utils.profile_method import run_experiment
from text_app.models.tbl_author import TblAuthor
from text_app.models.tbl_text import TblText
from text_app.models.tbl_textlist import TblTextListDescription, TblTextListItems


class AuthorshipPipelineTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        load_smoke_corpus(extract_features=True)
        cls.text_list = TblTextListDescription.objects.get(name=SMOKE_LIST_NAME)

    def test_feature_vector_size_is_193(self):
        _features, vector = extract_and_vectorize(
            "Это короткий проверочный текст. Он разбирается Natasha и дает полный вектор."
        )
        self.assertEqual(len(vector), VECTOR_SIZE)
        self.assertEqual(VECTOR_SIZE, 193)

    def test_load_authorship_demo_command_is_idempotent(self):
        before = {
            "authors": TblAuthor.objects.count(),
            "texts": TblText.objects.filter(idkey__startswith="authorship-smoke").count(),
            "items": TblTextListItems.objects.filter(list=self.text_list).count(),
            "features": TblSyntacticFeature.objects.count(),
        }
        call_command("load_authorship_demo", stdout=StringIO())
        after = {
            "authors": TblAuthor.objects.count(),
            "texts": TblText.objects.filter(idkey__startswith="authorship-smoke").count(),
            "items": TblTextListItems.objects.filter(list=self.text_list).count(),
            "features": TblSyntacticFeature.objects.count(),
        }
        self.assertEqual(before, after)

    def test_profile_method_on_smoke_demo(self):
        experiment = run_experiment(self.text_list, metric="manhattan", extract_features=False)
        self.assertEqual(experiment.build_status, "completed")
        self.assertEqual(experiment.metrics["n_texts"], 12)
        self.assertEqual(experiment.metrics["n_authors"], 3)
        self.assertEqual(TblAttributionResult.objects.filter(experiment=experiment).count(), 12)

    def test_authorship_home_returns_200(self):
        response = Client().get("/research/authorship/")
        self.assertEqual(response.status_code, 200)

    # ── Stage G: Fragment attribution ────────────────────────

    def test_attribute_fragments_returns_fragments(self):
        """attribute_fragments returns at least one fragment with required keys."""
        from research.authorship.utils.fragment_attribution import attribute_fragments
        text = " ".join(["слово"] * 200)
        results = attribute_fragments(
            text,
            self.text_list,
            mode="word_window",
            window_words=200,
            step_words=100,
            min_words_warn=150,
        )
        self.assertGreater(len(results), 0)
        self.assertIn("predicted_author", results[0])
        self.assertIn("reliable", results[0])
        self.assertIn("scores", results[0])

    def test_attribute_fragments_short_text_unreliable(self):
        """A text shorter than min_words_warn produces reliable=False with a warning."""
        from research.authorship.utils.fragment_attribution import attribute_fragments
        short = " ".join(["слово"] * 50)
        results = attribute_fragments(
            short,
            self.text_list,
            mode="word_window",
            window_words=200,
            min_words_warn=150,
        )
        self.assertEqual(len(results), 1)
        self.assertFalse(results[0]["reliable"])
        self.assertNotEqual(results[0]["warning"], "")

    def test_fragment_attribution_get_returns_200(self):
        """GET /research/authorship/attribute/fragments/ returns HTTP 200."""
        response = Client().get("/research/authorship/attribute/fragments/")
        self.assertEqual(response.status_code, 200)

    def test_fragment_attribution_post_smoke(self):
        """POST with smoke corpus list returns HTTP 200 and contains fragment results."""
        c = Client()
        text = " ".join(["Достоевский писал о человеке и судьбе"] * 30)
        response = c.post(
            "/research/authorship/attribute/fragments/",
            {
                "text_list": self.text_list.id,
                "raw_text": text,
                "mode": "word_window",
                "window_words": "100",
                "step_words": "50",
                "min_words_warn": "50",
                "metric": "manhattan",
            },
        )
        self.assertEqual(response.status_code, 200)
        # Confirm the results template was rendered (not the form)
        self.assertContains(response, "Результаты атрибуции фрагментов")

    # ── Stage G: optimisation & robustness ───────────────────

    def test_attribute_fragments_includes_trailing_unreliable(self):
        """Trailing partial window is included and marked reliable=False."""
        from research.authorship.utils.fragment_attribution import attribute_fragments
        # 340 words, window=200, step=100, min_words_warn=100.
        # Loop produces: [0:200]=200w, [100:300]=200w, [200:340]=140w, [300:340]=40w
        # The 40-word last fragment (40 < 100) must be unreliable.
        text = " ".join(["слово"] * 340)
        results = attribute_fragments(
            text,
            self.text_list,
            mode="word_window",
            window_words=200,
            step_words=100,
            min_words_warn=100,
        )
        self.assertGreater(len(results), 0)
        last = results[-1]
        self.assertFalse(last["reliable"])
        self.assertNotEqual(last["warning"], "")
        self.assertLess(last["word_count"], 100)

    def test_attribute_fragments_max_fragments_raises(self):
        """Exceeding max_fragments raises ValueError with a descriptive message."""
        from research.authorship.utils.fragment_attribution import attribute_fragments
        # 200 words, window=50, step=10 → 20 windows; max_fragments=5 → should raise
        text = " ".join(["слово"] * 200)
        with self.assertRaises(ValueError) as ctx:
            attribute_fragments(
                text,
                self.text_list,
                mode="word_window",
                window_words=50,
                step_words=10,
                min_words_warn=50,
                max_fragments=5,
            )
        self.assertIn("Слишком много фрагментов", str(ctx.exception))

