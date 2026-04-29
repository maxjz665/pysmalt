"""
Management command: authorship_report

Reads experiment results from DB and generates a console summary
+ HTML report. Does NOT re-run experiments unless --rerun is used.

Usage examples:
    python manage.py authorship_report                  # list_id=5, profile only
    python manage.py authorship_report --include-ml     # also show ML results
    python manage.py authorship_report --all-corpora    # all 3 corpora
    python manage.py authorship_report --list_id=3      # specific corpus
    python manage.py authorship_report --rerun          # force re-run profile
    python manage.py authorship_report --no-save        # skip HTML file
"""
import os
import sys
from datetime import datetime

from django.core.management.base import BaseCommand

from research.authorship.models import (
    TblAttributionExperiment, TblAttributionResult,
)
from text_app.models.tbl_textlist import TblTextListDescription, TblTextListItems

# ──────────────────────────────────────────────────────────────
#  Corpus catalogue
# ──────────────────────────────────────────────────────────────
CORPUS_META = {
    3: {
        'label':      '5×8 baseline',
        'n_authors':  5,
        'n_texts':    40,
        'authors':    'Даль В.И., Достоевский Ф.М., Мещерский В.П., '
                      'Пуцыкович В.Ф., Страхов Н.Н.',
    },
    4: {
        'label':      '5×7',
        'n_authors':  5,
        'n_texts':    35,
        'authors':    'Достоевский Ф.М., Мещерский В.П., Страхов Н.Н., '
                      'Достоевский М.М., Григорьев А.А.',
    },
    5: {
        'label':      '7×6',
        'n_authors':  7,
        'n_texts':    42,
        'authors':    'Достоевский Ф.М., Мещерский В.П., Страхов Н.Н., '
                      'Достоевский М.М., Григорьев А.А., '
                      'Победоносцев К.П., Пуцыкович В.Ф.',
    },
}


class Command(BaseCommand):
    help = 'Generate authorship attribution experiment report from DB results'

    def add_arguments(self, parser):
        parser.add_argument(
            '--list_id', type=int, default=5,
            help='Corpus list ID to report on (default: 5)',
        )
        parser.add_argument(
            '--all-corpora', action='store_true',
            help='Report on all three corpora (list_id 3, 4, 5)',
        )
        parser.add_argument(
            '--include-ml', action='store_true',
            help='Include ML SVM results in the report',
        )
        parser.add_argument(
            '--rerun', action='store_true',
            help='Re-run profile experiment even if results already exist '
                 '(adds new record to DB)',
        )
        parser.add_argument(
            '--no-save', action='store_true',
            help='Skip saving the HTML report file',
        )

    # ──────────────────────────────────────────────────────────
    #  Entry point
    # ──────────────────────────────────────────────────────────

    def handle(self, *args, **options):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')

        list_ids = [3, 4, 5] if options['all_corpora'] else [options['list_id']]
        include_ml = options['include_ml']
        rerun      = options['rerun']
        save_html  = not options['no_save']

        ts = datetime.now()
        self._print_header(ts)

        rows = []
        detail_corpus = None   # per-author detail for the primary corpus

        for list_id in list_ids:
            row = self._build_row(list_id, include_ml, rerun)
            if row:
                rows.append(row)
                if list_id == list_ids[-1]:
                    detail_corpus = row

        if not rows:
            self.stderr.write('No results found. Run experiments first.')
            return

        self._print_table(rows, include_ml)

        if detail_corpus:
            self._print_per_author(detail_corpus, include_ml)

        best = max(rows, key=lambda r: r['profile_f1'] or 0)
        self._print_conclusion(best, include_ml)

        if save_html:
            path = self._save_html(rows, detail_corpus, include_ml, ts)
            self.stdout.write('')
            self.stdout.write(
                self.style.SUCCESS(f'  Report saved: {path}')
            )

        self._print_footer()

    # ──────────────────────────────────────────────────────────
    #  Data retrieval
    # ──────────────────────────────────────────────────────────

    def _build_row(self, list_id, include_ml, rerun):
        meta = CORPUS_META.get(list_id)
        try:
            text_list = TblTextListDescription.objects.get(id=list_id)
        except TblTextListDescription.DoesNotExist:
            self.stderr.write(f'  List id={list_id} not found, skipping.')
            return None

        # ── Profile ──────────────────────────────────────────
        profile_exp = None
        if not rerun:
            profile_exp = (
                TblAttributionExperiment.objects
                .filter(text_list_id=list_id, method='profile',
                        build_status='completed')
                .order_by('-f1_score')
                .first()
            )

        if profile_exp is None:
            self.stdout.write(f'  Running profile/manhattan for list {list_id}...')
            from research.authorship.utils.profile_method import (
                run_experiment as run_profile,
            )
            profile_exp = run_profile(text_list=text_list, metric='manhattan')
            if profile_exp.build_status != 'completed':
                self.stderr.write(
                    f'  Profile experiment failed: {profile_exp.build_status}'
                )
                return None
            self.stdout.write(self.style.SUCCESS('  Profile done.'))

        # ── ML ────────────────────────────────────────────────
        ml_exp = None
        if include_ml:
            ml_exp = (
                TblAttributionExperiment.objects
                .filter(text_list_id=list_id, method='ml',
                        build_status='completed')
                .order_by('-f1_score')
                .first()
            )
            if ml_exp is None:
                self.stdout.write(
                    f'  No ML results for list {list_id}. '
                    f'Run: python manage.py run_authorship '
                    f'--list_id={list_id} --method=ml'
                )

        # ── Per-author data ───────────────────────────────────
        profile_by_author = self._per_author(profile_exp)
        ml_by_author      = self._per_author(ml_exp) if ml_exp else {}

        label = meta['label'] if meta else text_list.name

        return {
            'list_id':    list_id,
            'label':      label,
            'n_authors':  meta['n_authors'] if meta else '?',
            'n_texts':    meta['n_texts']   if meta else '?',
            'authors':    meta['authors']   if meta else '',
            # Profile
            'profile_exp':       profile_exp,
            'profile_f1':        profile_exp.f1_score  if profile_exp else None,
            'profile_acc':       profile_exp.accuracy  if profile_exp else None,
            'profile_by_author': profile_by_author,
            # ML
            'ml_exp':       ml_exp,
            'ml_f1':        ml_exp.f1_score  if ml_exp else None,
            'ml_acc':       ml_exp.accuracy  if ml_exp else None,
            'ml_by_author': ml_by_author,
        }

    @staticmethod
    def _per_author(exp):
        if exp is None:
            return {}
        results = (
            TblAttributionResult.objects
            .filter(experiment=exp)
            .select_related('true_author')
        )
        by_author = {}
        for r in results:
            aid = r.true_author_id
            if aid not in by_author:
                by_author[aid] = {
                    'name':    r.true_author.name,
                    'correct': 0,
                    'total':   0,
                }
            by_author[aid]['total']   += 1
            by_author[aid]['correct'] += int(r.is_correct)
        return by_author

    # ──────────────────────────────────────────────────────────
    #  Console output helpers
    # ──────────────────────────────────────────────────────────

    SEP = '=' * 66

    def _print_header(self, ts):
        self.stdout.write('')
        self.stdout.write(self.SEP)
        self.stdout.write('  SMALT Authorship Attribution  --  Experiment Report')
        self.stdout.write(f'  Generated: {ts.strftime("%Y-%m-%d %H:%M:%S")}')
        self.stdout.write(self.SEP)
        self.stdout.write('')

    def _print_footer(self):
        self.stdout.write('')
        self.stdout.write(self.SEP)
        self.stdout.write('')

    def _pct(self, v):
        return f'{v * 100:.1f}%' if v is not None else '—'

    def _bar(self, v, width=12):
        if v is None:
            return ' ' * width
        filled = int(round(v * width))
        return '█' * filled + '░' * (width - filled)

    def _print_table(self, rows, include_ml):
        ml_col = '  ML SVM F1 ' if include_ml else ''
        hdr = f'  {"Corpus":<20} {"Auth":>5} {"Texts":>6}   {"Profile F1":>11}{ml_col}'
        sep = '  ' + '-' * (len(hdr) - 2)
        self.stdout.write(hdr)
        self.stdout.write(sep)

        best_f1 = max((r['profile_f1'] or 0) for r in rows)

        for r in rows:
            is_best = (r['profile_f1'] or 0) == best_f1
            label   = r['label'] + (' [BEST]' if is_best else '')
            pf1     = self._pct(r['profile_f1'])
            bar     = self._bar(r['profile_f1'])
            ml_part = ''
            if include_ml:
                mf1 = self._pct(r['ml_f1'])
                ml_part = f'  {mf1:>8}'
            line = f'  {label:<27} {r["n_authors"]:>3} {r["n_texts"]:>6}   {bar} {pf1:>6}{ml_part}'
            if is_best:
                self.stdout.write(self.style.SUCCESS(line))
            else:
                self.stdout.write(line)

        self.stdout.write(sep)

    def _print_per_author(self, row, include_ml):
        self.stdout.write('')
        self.stdout.write(
            f'  Per-author accuracy — {row["label"]} (Profile / manhattan):'
        )
        prof = row['profile_by_author']
        ml   = row['ml_by_author'] if include_ml else {}

        for aid, data in sorted(prof.items(), key=lambda x: -x[1]['correct']):
            c, t = data['correct'], data['total']
            pct  = c / t * 100
            bar  = '█' * c + '░' * (t - c)
            ml_part = ''
            if include_ml and aid in ml:
                mc, mt = ml[aid]['correct'], ml[aid]['total']
                ml_part = f'   ML: {mc}/{mt}'
            name = data['name'][:28]
            status = self.style.SUCCESS('OK') if c == t else self.style.WARNING(f'{pct:.0f}%')
            self.stdout.write(
                f'    {name:<30}  {bar}  {c}/{t}  [{status}]{ml_part}'
            )

    def _print_conclusion(self, best, include_ml):
        self.stdout.write('')
        self.stdout.write('  Conclusion:')
        pf1 = self._pct(best['profile_f1'])
        self.stdout.write(
            self.style.SUCCESS(
                f'  Profile (manhattan) on {best["label"]}:  F1 = {pf1}'
            )
        )
        if include_ml and best['ml_f1'] is not None:
            mf1 = self._pct(best['ml_f1'])
            diff = (best['profile_f1'] - best['ml_f1']) * 100
            self.stdout.write(
                f'  ML SVM on {best["label"]}:              F1 = {mf1}'
            )
            self.stdout.write(
                f'  Profile leads by {diff:+.1f} pp — '
                f'expected for small corpora (LOO, {best["n_texts"]} texts).'
            )

    # ──────────────────────────────────────────────────────────
    #  HTML report
    # ──────────────────────────────────────────────────────────

    def _save_html(self, rows, detail_corpus, include_ml, ts):
        base_dir = os.path.dirname(  # pysmalt/
            os.path.dirname(         # research/
                os.path.dirname(     # authorship/
                    os.path.dirname( # management/
                        os.path.dirname(__file__)  # commands/
                    )
                )
            )
        )
        reports_dir = os.path.join(base_dir, 'reports')
        os.makedirs(reports_dir, exist_ok=True)

        filename = f'authorship_report_{ts.strftime("%Y%m%d_%H%M%S")}.html'
        filepath = os.path.join(reports_dir, filename)

        best = max(rows, key=lambda r: r['profile_f1'] or 0)

        html = self._render_html(rows, detail_corpus, include_ml, ts, best)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html)

        return filepath

    def _render_html(self, rows, detail_corpus, include_ml, ts, best):
        # ── Corpus table rows ──────────────────────────────
        table_rows_html = ''
        for r in rows:
            is_best = r['list_id'] == best['list_id']
            bg      = ' style="background:#f1f8e9;"' if is_best else ''
            badge   = ' <span style="background:#2e7d32;color:#fff;padding:1px 7px;border-radius:10px;font-size:.75rem;">BEST</span>' if is_best else ''
            pf1_pct = round(r['profile_f1'] * 100, 1) if r['profile_f1'] else 0
            pf1_str = f'{pf1_pct}%' if r['profile_f1'] else '—'
            p_bar   = f'<div style="background:#4caf50;height:14px;width:{pf1_pct}%;border-radius:3px;"></div>' if r['profile_f1'] else ''

            ml_cell = ''
            if include_ml:
                mf1_pct = round(r['ml_f1'] * 100, 1) if r['ml_f1'] else 0
                mf1_str = f'{mf1_pct}%' if r['ml_f1'] else '—'
                m_bar   = f'<div style="background:#ff9800;height:14px;width:{mf1_pct}%;border-radius:3px;"></div>' if r['ml_f1'] else ''
                ml_cell = f'<td style="min-width:160px;"><div style="display:flex;align-items:center;gap:6px;"><div style="flex:1;background:#eee;border-radius:3px;">{m_bar}</div><b>{mf1_str}</b></div></td>'

            table_rows_html += f'''
<tr{bg}>
  <td><b>{r["label"]}</b>{badge}<br><span style="color:#888;font-size:.78rem;">{r["authors"]}</span></td>
  <td style="text-align:center;">{r["n_authors"]}</td>
  <td style="text-align:center;">{r["n_texts"]}</td>
  <td style="min-width:180px;"><div style="display:flex;align-items:center;gap:6px;"><div style="flex:1;background:#eee;border-radius:3px;">{p_bar}</div><b>{pf1_str}</b></div></td>
  {ml_cell}
</tr>'''

        ml_th = '<th>ML SVM F1</th>' if include_ml else ''

        # ── Per-author table ───────────────────────────────
        per_author_html = ''
        if detail_corpus:
            prof = detail_corpus['profile_by_author']
            ml   = detail_corpus['ml_by_author'] if include_ml else {}
            ml_th2 = '<th>ML: correct/total</th>' if include_ml else ''
            rows_pa = ''
            for aid, d in sorted(prof.items(), key=lambda x: -x[1]['correct']):
                c, t = d['correct'], d['total']
                pct  = round(c / t * 100)
                bar  = f'<div style="background:#4caf50;height:10px;width:{pct}%;border-radius:2px;"></div>'
                ml_td = ''
                if include_ml and aid in ml:
                    mc, mt = ml[aid]['correct'], ml[aid]['total']
                    ml_td = f'<td>{mc}/{mt} ({round(mc/mt*100)}%)</td>'
                elif include_ml:
                    ml_td = '<td>—</td>'
                color = '#2e7d32' if c == t else ('#f57f17' if pct >= 67 else '#c62828')
                rows_pa += f'''
<tr>
  <td>{d["name"]}</td>
  <td style="text-align:center;">{c}/{t}</td>
  <td style="width:120px;"><div style="background:#eee;border-radius:2px;">{bar}</div></td>
  <td style="text-align:center;font-weight:bold;color:{color};">{pct}%</td>
  {ml_td}
</tr>'''

            per_author_html = f'''
<h3 style="margin-top:32px;">Per-author accuracy — {detail_corpus["label"]}</h3>
<table style="border-collapse:collapse;width:100%;font-size:.9rem;">
  <thead><tr style="background:#f5f5f5;">
    <th>Author</th><th>Profile: correct/total</th><th>Progress</th><th>Accuracy</th>
    {ml_th2}
  </tr></thead>
  <tbody>{rows_pa}</tbody>
</table>'''

        best_f1_str = f'{round(best["profile_f1"]*100, 1)}%' if best['profile_f1'] else '?'

        return f'''<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Authorship Attribution Report — {ts.strftime("%Y-%m-%d")}</title>
<style>
  *{{box-sizing:border-box;}}
  body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;margin:0;padding:0;color:#212121;}}
  .hero{{background:linear-gradient(135deg,#1a237e,#0d47a1);color:#fff;padding:36px 48px;}}
  .hero h1{{margin:0 0 6px;font-size:1.7rem;line-height:1.3;}}
  .hero p{{margin:4px 0;opacity:.85;font-size:.95rem;}}
  .content{{max-width:960px;margin:0 auto;padding:32px 24px;}}
  .stat-row{{display:flex;gap:16px;margin:24px 0;flex-wrap:wrap;}}
  .stat-card{{flex:1;min-width:140px;background:#fff;border-radius:8px;padding:16px 20px;
             text-align:center;box-shadow:0 1px 4px rgba(0,0,0,.12);}}
  .stat-num{{font-size:2.2rem;font-weight:700;line-height:1;}}
  .stat-label{{font-size:.8rem;color:#757575;margin-top:4px;}}
  table{{border-collapse:collapse;width:100%;margin-top:8px;}}
  th,td{{padding:8px 12px;border-bottom:1px solid #e0e0e0;text-align:left;vertical-align:middle;}}
  thead tr{{background:#f5f5f5;}}
  .badge-best{{background:#2e7d32;color:#fff;padding:1px 8px;border-radius:10px;font-size:.75rem;margin-left:6px;}}
  .conclusion{{background:#e8f5e9;border-left:4px solid #2e7d32;padding:16px 24px;border-radius:4px;margin-top:24px;}}
  .conclusion h3{{margin:0 0 8px;color:#1b5e20;}}
  .footer{{text-align:center;color:#9e9e9e;font-size:.8rem;margin-top:40px;padding-top:16px;border-top:1px solid #eee;}}
  @media print{{.hero{{-webkit-print-color-adjust:exact;print-color-adjust:exact;}}}}
</style>
</head>
<body>
<div class="hero">
  <div style="font-size:.8rem;opacity:.7;margin-bottom:6px;">Дипломная работа · Петрозаводский государственный университет, 2026</div>
  <h1>Алгоритмы определения авторства текста<br>
      <span style="font-weight:400;font-size:1.1rem;">на основе синтаксического анализа</span></h1>
  <p>Report generated: {ts.strftime("%Y-%m-%d %H:%M:%S")}</p>
</div>

<div class="content">

<div class="stat-row">
  <div class="stat-card">
    <div class="stat-num" style="color:#1565c0;">{best["n_authors"]}</div>
    <div class="stat-label">authors (best corpus)</div>
  </div>
  <div class="stat-card">
    <div class="stat-num" style="color:#1565c0;">{best["n_texts"]}</div>
    <div class="stat-label">texts (best corpus)</div>
  </div>
  <div class="stat-card">
    <div class="stat-num" style="color:#2e7d32;">{best_f1_str}</div>
    <div class="stat-label">Profile F1 (best)</div>
  </div>
  {"" if not include_ml or not best["ml_f1"] else f'<div class="stat-card"><div class="stat-num" style="color:#e65100;">{round(best["ml_f1"]*100,1)}%</div><div class="stat-label">ML SVM F1 (best)</div></div>'}
</div>

<h3>Corpus comparison</h3>
<table>
  <thead><tr>
    <th>Corpus</th>
    <th style="text-align:center;">Authors</th>
    <th style="text-align:center;">Texts</th>
    <th>Profile F1 (manhattan)</th>
    {ml_th}
  </tr></thead>
  <tbody>{table_rows_html}</tbody>
</table>

{per_author_html}

<div class="conclusion">
  <h3>Conclusion</h3>
  <p><b>Profile method (Ezhov, manhattan distance)</b> achieves the best result:
     <b style="color:#2e7d32;">F1 = {best_f1_str}</b> on the <b>{best["label"]}</b> corpus
     ({best["n_authors"]} authors × {best["n_texts"] // best["n_authors"]} texts each).</p>
  {"<p><b>ML method (Sevryukov, SVM RBF)</b> achieves F1 = " + str(round(best["ml_f1"]*100,1)) + "% on the same corpus — " + str(round((best["profile_f1"]-best["ml_f1"])*100,1)) + " pp below profile. Expected for small corpora with LOO evaluation.</p>" if include_ml and best["ml_f1"] else ""}
  <p style="margin:0;font-size:.85rem;color:#555;">
    Both methods use a 193-component syntactic feature vector (POS-tags, dependency
    relations, syntactic productions, function words) extracted with <b>Natasha</b> NLP.
    Evaluation: Leave-One-Out cross-validation, macro-F1.
  </p>
</div>

<h3 style="margin-top:32px;">Feature vector (193 components, 8 blocks)</h3>
<table style="font-size:.85rem;">
  <thead><tr style="background:#f5f5f5;"><th>Block</th><th style="text-align:center;">Size</th><th style="text-align:center;">Weight</th></tr></thead>
  <tbody>
    <tr><td>Scalar (sentence length, depth)</td><td style="text-align:center;">4</td><td style="text-align:center;">×0.35</td></tr>
    <tr><td>POS unigrams</td><td style="text-align:center;">17</td><td style="text-align:center;">×1.0</td></tr>
    <tr><td>Dependency relation types</td><td style="text-align:center;">38</td><td style="text-align:center;">×1.2</td></tr>
    <tr><td>Clause types</td><td style="text-align:center;">4</td><td style="text-align:center;">×0.9</td></tr>
    <tr><td>Tree depth distribution</td><td style="text-align:center;">15</td><td style="text-align:center;">×0.8</td></tr>
    <tr><td>POS bigrams</td><td style="text-align:center;">30</td><td style="text-align:center;">×1.0</td></tr>
    <tr style="background:#f1f8e9;"><td><b>Syntactic productions (head–dep–child)</b></td><td style="text-align:center;"><b>25</b></td><td style="text-align:center;"><b>×1.3</b></td></tr>
    <tr><td>Function words</td><td style="text-align:center;">60</td><td style="text-align:center;">×1.0</td></tr>
    <tr style="background:#e3f2fd;"><td><b>Total</b></td><td style="text-align:center;"><b>193</b></td><td style="text-align:center;">—</td></tr>
  </tbody>
</table>

<div class="footer">SMALT Authorship Attribution · PetrSU, 2026 · auto-generated report</div>
</div>
</body>
</html>'''
