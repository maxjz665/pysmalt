"""
Контроллеры модуля определения авторства текста.
"""
import json
import logging

from django.contrib import messages
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST

from research.authorship.models import (
    TblSyntacticFeature, TblAuthorProfile,
    TblAttributionExperiment, TblAttributionResult
)
from text_app.models.tbl_text import TblText
from text_app.models.tbl_textlist import TblTextListDescription, TblTextListItems

logger = logging.getLogger(__name__)


def authorship_home(request: HttpRequest) -> HttpResponse:
    """Главная страница модуля определения авторства."""
    text_lists = TblTextListDescription.get_items(
        user=request.user, exclude_deleted=True
    ).order_by("name")

    attribution_candidates = None
    input_text = ""
    selected_list_id = None

    if request.method == "POST":
        action = request.POST.get("action", "")
        selected_list_id = int(request.POST.get("text_list", 0) or 0)
        try:
            if not selected_list_id:
                raise ValueError("Выберите список текстов.")
            text_list = TblTextListDescription.get_item(request.user, selected_list_id)

            if action == "run_profile":
                from research.authorship.utils.profile_method import run_experiment
                experiment = run_experiment(
                    text_list=text_list,
                    metric="manhattan",
                    owner=request.user if request.user.is_authenticated else None,
                )
                if experiment.build_status != "completed":
                    raise ValueError(experiment.build_status)
                return redirect('authorship/experiment_detail', experiment_id=experiment.id)

            if action == "run_ml":
                from research.authorship.utils.ml_method import run_experiment
                experiment = run_experiment(
                    text_list=text_list,
                    classifier_type="svm",
                    owner=request.user if request.user.is_authenticated else None,
                )
                if experiment.build_status != "completed":
                    raise ValueError(experiment.build_status)
                return redirect('authorship/experiment_detail', experiment_id=experiment.id)

            if action == "attribute":
                input_text = request.POST.get("input_text", "").strip()
                if not input_text:
                    raise ValueError("Введите текст для атрибуции.")
                from research.authorship.utils.profile_method import attribute_text
                attribution_candidates = attribute_text(
                    raw_text=input_text,
                    text_list=text_list,
                    metric="manhattan",
                )
            else:
                raise ValueError("Неизвестное действие.")
        except Exception as exc:
            logger.exception("Authorship home action failed")
            messages.error(request, str(exc))

    experiments = TblAttributionExperiment.objects.all().order_by('-created_at')[:20]
    list_rows = []
    for text_list in text_lists:
        item_qs = TblTextListItems.objects.filter(list=text_list)
        text_ids = item_qs.values_list("text_id", flat=True)
        list_rows.append({
            "object": text_list,
            "texts_count": item_qs.count(),
            "authors_count": TblText.objects.filter(
                id__in=text_ids,
                author__isnull=False,
            ).values("author_id").distinct().count(),
            "features_count": TblSyntacticFeature.objects.filter(
                text_id__in=text_ids,
                vector_size=193,
            ).count(),
        })

    # Статистика
    total_features = TblSyntacticFeature.objects.count()
    total_profiles = TblAuthorProfile.objects.count()
    total_experiments = TblAttributionExperiment.objects.count()

    return render(request, "authorship/home.html", {
        "text_lists": text_lists,
        "list_rows": list_rows,
        "experiments": experiments,
        "attribution_candidates": attribution_candidates,
        "input_text": input_text,
        "selected_list_id": selected_list_id,
        "stats": {
            "features": total_features,
            "profiles": total_profiles,
            "experiments": total_experiments,
        },
    })


# ────────────────────────────────────────────────────────────
#  Извлечение признаков
# ────────────────────────────────────────────────────────────

def extract_features_view(request: HttpRequest) -> HttpResponse:
    """Извлечение синтаксических признаков для текстов из списка."""
    text_lists = TblTextListDescription.get_items(
        user=request.user, exclude_deleted=True
    ).order_by("name")

    if request.method == "GET":
        return render(request, "authorship/extract_features.html", {
            "text_lists": text_lists,
        })

    # POST: запускаем извлечение
    list_id = int(request.POST.get("text_list", 0))
    if not list_id:
        messages.error(request, "Выберите список текстов")
        return render(request, "authorship/extract_features.html", {
            "text_lists": text_lists,
        })

    text_list = TblTextListDescription.get_item(request.user, list_id)
    items = TblTextListItems.objects.filter(list=text_list).select_related('text')

    from research.authorship.utils.features import extract_and_save_features
    results = []
    errors = []

    for item in items:
        try:
            sf = extract_and_save_features(item.text)
            results.append({
                'text_id': item.text.id,
                'title': item.text.title,
                'sentences': sf.avg_sentence_length,
                'depth': sf.avg_tree_depth,
            })
        except Exception as e:
            errors.append(f"Текст {item.text.id}: {str(e)}")
            logger.exception(f"Ошибка извлечения признаков для текста {item.text.id}")

    return render(request, "authorship/extract_features_result.html", {
        "results": results,
        "errors": errors,
        "text_list": text_list,
    })


# ────────────────────────────────────────────────────────────
#  Просмотр признаков текста
# ────────────────────────────────────────────────────────────

def text_features_view(request: HttpRequest, text_id: int) -> HttpResponse:
    """Просмотр синтаксических признаков конкретного текста."""
    text_obj = get_object_or_404(TblText, id=text_id)

    try:
        sf = TblSyntacticFeature.objects.get(text=text_obj)
    except TblSyntacticFeature.DoesNotExist:
        sf = None

    return render(request, "authorship/text_features.html", {
        "text": text_obj,
        "features": sf,
    })


# ────────────────────────────────────────────────────────────
#  Эксперименты
# ────────────────────────────────────────────────────────────

def run_experiment_view(request: HttpRequest) -> HttpResponse:
    """Запуск эксперимента по определению авторства."""
    text_lists = TblTextListDescription.get_items(
        user=request.user, exclude_deleted=True
    ).order_by("name")

    if request.method == "GET":
        return render(request, "authorship/run_experiment.html", {
            "text_lists": text_lists,
        })

    # POST: создаём queued-эксперимент и немедленно возвращаем redirect
    list_id = int(request.POST.get("text_list", 0))
    method = request.POST.get("method", "profile")
    metric = request.POST.get("metric", "manhattan")
    classifier_type = request.POST.get("classifier_type", "svm")
    experiment_name = request.POST.get("name", "")

    if not list_id:
        messages.error(request, "Выберите список текстов")
        return render(request, "authorship/run_experiment.html", {
            "text_lists": text_lists,
        })

    if method not in ('profile', 'ml'):
        messages.error(request, f"Неизвестный метод: {method}")
        return render(request, "authorship/run_experiment.html", {
            "text_lists": text_lists,
        })

    try:
        text_list = TblTextListDescription.get_item(request.user, list_id)
        auto_name = (
            f"Profile ({metric}) - {text_list.name}"
            if method == 'profile'
            else f"ML SVC - {text_list.name}"
        )
        params = {
            "metric": metric,
            "cv": "leave-one-out",
        } if method == 'profile' else {
            "pipeline": "StandardScaler -> SelectKBest(f_classif) -> SVC",
            "outer_cv": "leave-one-out",
            "classifier_type": classifier_type,
        }
        experiment = TblAttributionExperiment.objects.create(
            name=experiment_name or auto_name,
            method=method,
            metric=metric if method == 'profile' else "f1_macro",
            text_list=text_list,
            owner=request.user if request.user.is_authenticated else None,
            params=params,
            build_status='queued',
        )
    except Exception as e:
        logger.exception("Ошибка при создании эксперимента")
        messages.error(request, f"Ошибка: {str(e)}")
        return render(request, "authorship/run_experiment.html", {
            "text_lists": text_lists,
        })

    messages.info(request, "Эксперимент поставлен в очередь. Запустите run_authorship_worker.")
    return redirect('authorship/experiment_detail', experiment_id=experiment.id)


def experiment_detail_view(request: HttpRequest, experiment_id: int) -> HttpResponse:
    """Просмотр результатов эксперимента."""
    experiment = get_object_or_404(TblAttributionExperiment, id=experiment_id)
    results = TblAttributionResult.objects.filter(
        experiment=experiment
    ).select_related('text', 'true_author', 'predicted_author').order_by('text__title')
    is_active = experiment.build_status in ('queued', 'running')

    return render(request, "authorship/experiment_detail.html", {
        "experiment": experiment,
        "results": results,
        "is_active": is_active,
    })


def experiment_list_view(request: HttpRequest) -> HttpResponse:
    """Список всех экспериментов."""
    experiments = TblAttributionExperiment.objects.all().order_by('-created_at')
    return render(request, "authorship/experiment_list.html", {
        "experiments": experiments,
    })


# ────────────────────────────────────────────────────────────
#  Атрибуция нового текста
# ────────────────────────────────────────────────────────────

def attribute_text_view(request: HttpRequest) -> HttpResponse:
    """Определение авторства нового текста."""
    text_lists = TblTextListDescription.get_items(
        user=request.user, exclude_deleted=True
    ).order_by("name")

    experiments = TblAttributionExperiment.objects.filter(
        build_status='completed'
    ).order_by('-created_at')

    if request.method == "GET":
        return render(request, "authorship/attribute_text.html", {
            "text_lists": text_lists,
            "experiments": experiments,
        })

    # POST: атрибуция
    input_text = request.POST.get("input_text", "").strip()
    method = request.POST.get("method", "profile")

    if not input_text:
        messages.error(request, "Введите текст для анализа")
        return render(request, "authorship/attribute_text.html", {
            "text_lists": text_lists,
            "experiments": experiments,
        })

    try:
        if method == 'profile':
            list_id = int(request.POST.get("text_list", 0))
            metric = request.POST.get("metric", "manhattan")
            text_list = TblTextListDescription.get_item(request.user, list_id)

            from research.authorship.utils.profile_method import attribute_text
            candidates = attribute_text(input_text, text_list, metric=metric)

            return render(request, "authorship/attribution_result.html", {
                "method": "profile",
                "metric": metric,
                "candidates": candidates,
                "input_text": input_text[:500],
            })

        elif method == 'ml':
            experiment_id = int(request.POST.get("experiment_id", 0))
            experiment = TblAttributionExperiment.objects.get(id=experiment_id)

            from research.authorship.utils.ml_method import attribute_text
            candidates = attribute_text(input_text, experiment)

            return render(request, "authorship/attribution_result.html", {
                "method": "ml",
                "experiment": experiment,
                "candidates": candidates,
                "input_text": input_text[:500],
            })

    except Exception as e:
        logger.exception("Ошибка при атрибуции")
        messages.error(request, f"Ошибка: {str(e)}")
        return render(request, "authorship/attribute_text.html", {
            "text_lists": text_lists,
            "experiments": experiments,
        })


# ────────────────────────────────────────────────────────────
#  Демо-страница
# ────────────────────────────────────────────────────────────

def demo_view(request: HttpRequest) -> HttpResponse:
    """Презентационная страница с итогами экспериментов."""
    CORPORA = [
        {
            'label':       'Baseline 5×8',
            'list_id':     3,
            'n_authors':   5,
            'n_texts':     40,
            'description': 'Даль, Достоевский Ф.М., Мещерский В.П., Пуцыкович В.Ф., Страхов Н.Н.',
            'is_best':     False,
        },
        {
            'label':       '5×7',
            'list_id':     4,
            'n_authors':   5,
            'n_texts':     35,
            'description': 'Достоевский Ф.М., Мещерский В.П., Страхов Н.Н., Достоевский М.М., Григорьев А.А.',
            'is_best':     False,
        },
        {
            'label':       '7×6',
            'list_id':     5,
            'n_authors':   7,
            'n_texts':     42,
            'description': 'Достоевский Ф.М., Мещерский В.П., Страхов Н.Н., Достоевский М.М., '
                           'Григорьев А.А., Победоносцев К.П., Пуцыкович В.Ф.',
            'is_best':     True,
        },
    ]

    for corpus in CORPORA:
        profile_exp = TblAttributionExperiment.objects.filter(
            text_list_id=corpus['list_id'],
            method='profile',
            build_status='completed',
        ).order_by('-f1_score').first()

        ml_exp = TblAttributionExperiment.objects.filter(
            text_list_id=corpus['list_id'],
            method='ml',
            build_status='completed',
        ).order_by('-f1_score').first()

        corpus['profile_f1']     = round(profile_exp.f1_score * 100, 1) if profile_exp else None
        corpus['profile_acc']    = round(profile_exp.accuracy  * 100, 1) if profile_exp else None
        corpus['ml_f1']          = round(ml_exp.f1_score * 100, 1)      if ml_exp     else None
        corpus['ml_acc']         = round(ml_exp.accuracy  * 100, 1)     if ml_exp     else None
        corpus['profile_exp_id'] = profile_exp.id if profile_exp else None
        corpus['ml_exp_id']      = ml_exp.id      if ml_exp      else None

    best = next(c for c in CORPORA if c['is_best'])
    best['texts_per_author'] = best['n_texts'] // best['n_authors']
    best['authors_list'] = [a.strip() for a in best['description'].split(',')]

    return render(request, 'authorship/demo.html', {
        'corpora': CORPORA,
        'best': best,
    })


# ────────────────────────────────────────────────────────────
#  Сравнение методов
# ────────────────────────────────────────────────────────────

def compare_methods_view(request: HttpRequest) -> HttpResponse:
    """Сравнение результатов двух методов."""
    experiments = TblAttributionExperiment.objects.filter(
        build_status='completed'
    ).order_by('-created_at')

    if request.method == "GET":
        return render(request, "authorship/compare_methods.html", {
            "experiments": experiments,
        })

    exp1_id = int(request.POST.get("experiment_1", 0))
    exp2_id = int(request.POST.get("experiment_2", 0))

    exp1 = get_object_or_404(TblAttributionExperiment, id=exp1_id)
    exp2 = get_object_or_404(TblAttributionExperiment, id=exp2_id)

    results1 = {r.text_id: r for r in TblAttributionResult.objects.filter(experiment=exp1)}
    results2 = {r.text_id: r for r in TblAttributionResult.objects.filter(experiment=exp2)}

    # Сравнение по общим текстам
    common_ids = set(results1.keys()) & set(results2.keys())
    comparison = []
    for text_id in common_ids:
        r1 = results1[text_id]
        r2 = results2[text_id]
        comparison.append({
            'text': r1.text,
            'true_author': r1.true_author,
            'pred_1': r1.predicted_author,
            'correct_1': r1.is_correct,
            'pred_2': r2.predicted_author,
            'correct_2': r2.is_correct,
            'both_correct': r1.is_correct and r2.is_correct,
        })

    both_correct = sum(1 for c in comparison if c['both_correct'])
    only_1 = sum(1 for c in comparison if c['correct_1'] and not c['correct_2'])
    only_2 = sum(1 for c in comparison if c['correct_2'] and not c['correct_1'])
    neither = sum(1 for c in comparison if not c['correct_1'] and not c['correct_2'])

    return render(request, "authorship/compare_result.html", {
        "exp1": exp1,
        "exp2": exp2,
        "comparison": comparison,
        "summary": {
            "total": len(comparison),
            "both_correct": both_correct,
            "only_1": only_1,
            "only_2": only_2,
            "neither": neither,
        },
    })


# ────────────────────────────────────────────────────────────
#  Атрибуция фрагментов текста
# ────────────────────────────────────────────────────────────

def fragment_attribution_view(request: HttpRequest) -> HttpResponse:
    """Разбивает текст на фрагменты и атрибутирует каждый по профильному методу."""
    text_lists = TblTextListDescription.get_items(
        user=request.user, exclude_deleted=True
    ).order_by("name")

    defaults = {
        "mode": "word_window",
        "window_words": 300,
        "step_words": 150,
        "min_words_warn": 150,
        "metric": "manhattan",
    }

    if request.method == "GET":
        return render(request, "authorship/fragment_attribution_form.html", {
            "text_lists": text_lists,
            **defaults,
        })

    # POST
    list_id = int(request.POST.get("text_list", 0) or 0)
    raw_text = request.POST.get("raw_text", "").strip()
    mode = request.POST.get("mode", "word_window")
    metric = request.POST.get("metric", "manhattan")
    try:
        window_words = max(1, int(request.POST.get("window_words", 300)))
        step_words = max(1, int(request.POST.get("step_words", 150)))
        min_words_warn = max(1, int(request.POST.get("min_words_warn", 150)))
    except (ValueError, TypeError):
        window_words, step_words, min_words_warn = 300, 150, 150

    form_ctx = {
        "text_lists": text_lists,
        "mode": mode,
        "window_words": window_words,
        "step_words": step_words,
        "min_words_warn": min_words_warn,
        "metric": metric,
        "selected_list_id": list_id,
        "raw_text": raw_text,
    }

    if not list_id:
        messages.error(request, "Выберите список текстов.")
        return render(request, "authorship/fragment_attribution_form.html", form_ctx)

    if not raw_text:
        messages.error(request, "Введите текст для анализа.")
        return render(request, "authorship/fragment_attribution_form.html", form_ctx)

    try:
        text_list = TblTextListDescription.get_item(request.user, list_id)
        from research.authorship.utils.fragment_attribution import attribute_fragments
        fragments = attribute_fragments(
            raw_text=raw_text,
            text_list=text_list,
            mode=mode,
            window_words=window_words,
            step_words=step_words,
            min_words_warn=min_words_warn,
            metric=metric,
        )
    except Exception as exc:
        logger.exception("Fragment attribution failed")
        messages.error(request, f"Ошибка: {exc}")
        return render(request, "authorship/fragment_attribution_form.html", form_ctx)

    has_unreliable = any(not f["reliable"] for f in fragments)

    return render(request, "authorship/fragment_attribution_results.html", {
        "text_list": text_list,
        "fragments": fragments,
        "mode": mode,
        "window_words": window_words,
        "step_words": step_words,
        "min_words_warn": min_words_warn,
        "metric": metric,
        "raw_text_preview": raw_text[:200],
        "has_unreliable": has_unreliable,
    })
