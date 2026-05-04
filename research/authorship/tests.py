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

