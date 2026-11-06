"""Portable calculation report, suitable for browser Print -> Save as PDF."""
from __future__ import annotations

import html
from datetime import date

from inventory_solver.common import latex_num
from inventory_solver.math_display import equation_fragments, plain_table_rows
from inventory_solver.schema import Solution


def report_html(solution: Solution) -> str:
    def e(value: object) -> str:
        return html.escape(str(value))

    metrics = "".join(f"<tr><th>{e(m.label)}</th><td>{e(latex_num(float(m.value)).replace(r'\,', ',') if isinstance(m.value,(int,float)) else m.value)} {e(m.unit)}</td></tr>" for m in solution.metrics)
    parts = []
    for step in solution.steps:
        equations = "".join(
            "<div class='math-chain'>" + "".join(
                f"<span class='math-part'>\\({e(fragment)}\\)</span>"
                for fragment in equation_fragments(eq)
            ) + "</div>"
            for eq in step.equations
        )
        parts.append(f"<section><h3>{e(step.title)}</h3>{equations}<p>{e(step.explanation)}</p></section>")
    if solution.comparisons:
        comparisons = plain_table_rows(solution.comparisons)
        cols = list(comparisons[0])
        head = "".join(f"<th>{e(k)}</th>" for k in cols)
        body = "".join("<tr>"+"".join(f"<td>{e(row.get(k,''))}</td>" for k in cols)+"</tr>" for row in comparisons)
        parts.append(f"<h2>Comparison</h2><table><tr>{head}</tr>{body}</table>")
    if solution.rows:
        table_rows = plain_table_rows(solution.rows)
        # Compact iteration table; all iterations retained for auditability.
        cols = [c["field"] for c in solution.columns]
        body = "".join("<tr>"+"".join(f"<td>{e(r.get(k,''))}</td>" for k in cols)+"</tr>" for r in table_rows)
        parts.append(f"<h2>Iteration log</h2><table><tr>{''.join(f'<th>{e(k)}</th>' for k in cols)}</tr>{body}</table>")
    return f"""<!doctype html><html lang='en'><head><meta charset='utf-8'>
<title>{e(solution.model)} solution</title>
<style>body{{font:17px/1.6 system-ui,Arial;max-width:1000px;margin:35px auto;color:#182336;padding:0 18px}}
h1{{font-size:27px}}h2{{font-size:20px;margin-top:27px}}h3{{font-size:17px}}section{{padding:14px;border:1px solid #ddd;border-radius:7px;margin:12px 0}}
.math-chain{{display:flex;flex-wrap:wrap;align-items:center;gap:6px 8px;max-width:100%;margin:8px 0;overflow-x:visible}}
.math-part{{min-width:0;max-width:100%;overflow-wrap:anywhere}}
table{{width:100%;border-collapse:collapse;margin:16px 0}}td,th{{border:1px solid #ddd;text-align:left;padding:7px;font-size:15px}}
th{{background:#f2f6fb}}p,li{{color:#4b5563}}@media print{{body{{margin:0}}section{{break-inside:avoid}}}}</style>
<script>window.MathJax={{tex:{{inlineMath:[['\\\\(','\\\\)']]}}}};</script>
<script defer src='https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-chtml.js'></script>
</head><body><h1>{e(solution.model)} — {e(solution.title)}</h1><small>Generated {date.today().isoformat()} · Values displayed to 3 decimals; computed with unrounded inputs</small>
<h2>Final results</h2><table>{metrics}</table><h2>Step-by-step solution</h2>{''.join(parts)}
<p>Print this report from the browser to save a PDF.</p>
</body></html>"""
