"""NiceGUI web app: per-connection input state, one continuous Results tab, Theory last."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from nicegui import events, run as background_run, ui

from inventory_solver.common import latex_num
from inventory_solver.distributions import DISTRIBUTIONS, PARAMETERS, defaults_for
from inventory_solver.distribution_theory import DISTRIBUTION_THEORY
from inventory_solver.examples import GROUPS, HW_ORDER, ITEM_FIELDS, TITLES, example, field_caption, input_columns
from inventory_solver.excel_io import read_inputs_xlsx
from inventory_solver.math_display import equation_fragments, plain_table_rows
from inventory_solver.report import report_html
from inventory_solver.schema import Metric, ModelInputError, Solution, Step
from inventory_solver.sensitivity import (
    Study, available_parameters, dashboard_chart_options, dashboard_comparisons,
    dashboard_point, fixed_q_study, input_study,
)
from inventory_solver.numeric_input import parse_numeric
from inventory_solver.solve import solve
from inventory_solver.theory import KNOWLEDGE

TEMPLATE = Path(__file__).parent.parent / 'examples' / 'inventory_inputs.xlsx'
DISTRIBUTION_TEMPLATE = Path(__file__).parent.parent / 'examples' / 'distribution_inputs.xlsx'

STYLE = """
:root { --ink: #20344b; --sub: #6c7c90; --line: #dde5ed; --blue: #2e699b; }
html { font-size:18px; } /* one readable size larger, including Tailwind rem classes */
body { background:#f6f9fc; color:var(--ink); }
.nicegui-content { padding:0!important; }
.sidebar { background:#edf3f9; border-right:1px solid #dae5ed; }
.workspace { min-width:0; padding:26px 34px 50px; }
.soft-card { background:white; border:1px solid var(--line); border-radius:12px; box-shadow:none; }
.step-card { background:white; border:1px solid #e0e7ee; border-radius:10px; }
.step-card .q-item { font-weight:600; }
.math-chain { display:flex; flex-wrap:wrap; align-items:center; column-gap:0.45rem; row-gap:0.4rem;
              width:100%; min-width:0; max-width:100%; padding:8px 0 12px; overflow-x:visible; }
.math-chain .math-fragment { min-width:0; max-width:100%; flex:0 1 auto; margin:0!important; }
.math-chain .math-fragment p { margin:0!important; }
.math-chain .math-fragment math { max-width:100%; font-size:clamp(0.92rem,1.4vw,1.14rem); }
.math-chain .math-fragment mjx-container { max-width:100%; }
.math-chain .math-fragment mjx-container[display="true"] { margin:0!important; }
.math-chain .math-fragment > div { max-width:100%; }
.model-btn { width:100%; text-align:left; border-radius:8px; font-size:15px; }
.model-btn-active { background:#dbeaf8!important; color:#1e5c93!important; }
.meta { color:var(--sub); font-size:14px; }
/* Dashboard cards stay readable at mobile sizes without side-scrolling. */
.sensitivity-kpi { min-width:0; }
.sensitivity-kpi .q-card__section { min-width:0; }
.sensitivity-chart { min-width:0; }
/* Quasar table/input text does not uniformly follow Tailwind rem sizing. */
.q-table tbody td { font-size:0.91rem; }
.q-table thead th { font-size:0.84rem; }
.q-field__native, .q-field__input, .q-field__label { font-size:0.94rem; }
.q-tab--active { color:#1b5f91; }
.q-tab-panels, .q-tab-panel { background:transparent!important; }
.q-tab-panel { padding:16px 0!important; }
@media(max-width:850px) {.workspace {padding:18px 14px 40px!important;}
  .math-chain .math-fragment math { font-size:.96rem; }}
"""


def _mathexpression(equation: str) -> None:
    """Allow Formula = Substitution = Result to wrap *between* equalities.

    LaTeX fragments stay mathematically typeset; no horizontal scrollbar.
    """
    with ui.element('div').classes('math-chain w-full'):
        for fragment in equation_fragments(equation):
            ui.markdown('$$' + fragment + '$$', extras=['latex']).classes('math-fragment')


def _metric(metric: Metric) -> None:
    with ui.card().classes('soft-card flex-1 min-w-40 p-4'):
        ui.label(metric.label).classes('text-xs text-slate-500')
        if isinstance(metric.value, (int, float)):
            value = latex_num(float(metric.value)).replace(r'\,', ',')
        else:
            value = str(metric.value)
        ui.label(value).classes('text-xl font-semibold text-slate-800 tracking-tight')
        if metric.unit:
            ui.label(metric.unit).classes('text-xs text-slate-500')


def _step(step: Step) -> None:
    with ui.expansion(step.title, value=step.open_by_default).classes('step-card w-full'):
        with ui.column().classes('w-full px-4 pb-4 gap-1'):
            for equation in step.equations:
                _mathexpression(equation)
            if step.explanation:
                ui.label(step.explanation).classes('text-sm text-slate-500')


def _results(solution: Solution | None) -> None:
    if solution is None:
        with ui.card().classes('soft-card w-full p-8'):
            ui.icon('calculate', size='38px', color='blue-grey-4')
            ui.label('No results yet').classes('text-lg font-medium')
            ui.label('Fill in the inputs or load the homework example, then select Solve.').classes('text-sm text-slate-500')
        return
    with ui.column().classes('w-full gap-5'):
        with ui.row().classes('items-center justify-between w-full gap-2'):
            ui.label('Final answer').classes('text-lg font-semibold')
            ui.button('Export solution', icon='download', color='primary',
                      on_click=lambda: ui.download.content(report_html(solution),
                                                           f'{solution.model}_solution.html', 'text/html'))\
              .props('outline no-caps')
        with ui.row().classes('w-full gap-3 flex-wrap'):
            for metric in solution.metrics:
                _metric(metric)
        with ui.row().classes('items-center justify-between w-full'):
            ui.label('Step-by-step solution').classes('text-lg font-semibold')
            ui.label('Click a step to reveal the calculation chain').classes('meta')
        for step in solution.steps:
            _step(step)
        if solution.rows:
            with ui.expansion('Full iteration log', icon='table_rows').classes('step-card w-full'):
                with ui.column().classes('w-full px-3 pb-3'):
                    ui.label('The first two iterations are fully substituted above; the rest appear here.')\
                        .classes('text-xs text-slate-500')
                    ui.table(columns=solution.columns, rows=plain_table_rows(solution.rows),
                             pagination={'rowsPerPage': 12}, row_key='iteration' if solution.model == 'HW1' else 'j')\
                        .classes('w-full text-xs').props('dense flat')
        if solution.comparisons:
            ui.label('Policy / product comparison').classes('text-lg font-semibold')
            with ui.card().classes('soft-card w-full p-2'):
                ui.table(rows=plain_table_rows(solution.comparisons), pagination=0).classes('w-full').props('flat dense')



def _sensitivity_output(study: Study) -> None:
    """Slider-driven dashboard: all results update from precomputed scenarios.

    The slider callback contains no inventory calculations; the costly sweep
    runs only once in a background worker when Build dashboard is pressed.
    """
    preferred = {
        'HW1': ('Q', 's', 'SS', 'TC'),
        'HW3': ('Q', 's', 'SS', 'TC'),
        'HW2': ('Qp', 's', 'S', 'buffer'),
        'HW4': ('Q_total', 'spend', 'remaining', 'profit'),
        'HW6': ('Q_original', 'Q_post', 'profit_original', 'profit_post'),
        'HW5': ('Q_total', 'Q_pool', 'profit_original', 'profit_post'),
    }
    chart_keys = [key for key in preferred[study.model]
                  if any(out.key == key for out in study.outputs)]
    change_step = round(study.points[1].change - study.points[0].change, 10)
    percentage = study.mode == 'Fixed Q' or study.x_label.endswith('(% change)')
    change_unit = '%' if percentage else ''
    outputs = tuple(study.outputs)

    def present(value: float | None) -> str:
        return '—' if value is None else f'{value:,.3f}'

    with ui.column().classes('w-full gap-5'):
        with ui.card().classes('soft-card w-full p-5 gap-3'):
            ui.label('Sensitivity dashboard').classes('text-xl font-semibold')
            ui.label('Move the slider to compare all outputs with the unchanged baseline.')\
                .classes('text-base text-slate-600')
            with ui.row().classes('items-center justify-between w-full flex-wrap gap-2'):
                selected_label = ui.label('0% · Baseline').classes('text-xl font-semibold text-slate-800')
                ui.label(f'Step: {change_step:g}{change_unit}').classes('text-sm text-slate-500')
            slider = ui.slider(min=float(study.points[0].change),
                               max=float(study.points[-1].change),
                               step=change_step, value=0).classes('w-full my-1')\
                       .props('label-always snap')
            with ui.row().classes('w-full items-center justify-between'):
                ui.label(f'{study.points[0].change:+g}{change_unit}').classes('text-sm text-slate-500')
                ui.button('Reset 0', on_click=lambda: slider.set_value(0))\
                    .props('flat no-caps dense')
                ui.label(f'{study.points[-1].change:+g}{change_unit}').classes('text-sm text-slate-500')
            input_label = ui.label('').classes('text-base text-slate-700')
            error_label = ui.label('').classes('text-sm text-amber-700')
            if study.note and study.mode == 'Fixed Q':
                ui.label('Q is fixed at the selected percentage; k, s, SS and TC are recalculated.')\
                    .classes('text-sm text-slate-500')

        ui.label('Output trends').classes('text-lg font-semibold')
        charts: dict[str, Any] = {}
        with ui.element('div').classes('grid grid-cols-1 lg:grid-cols-2 gap-4 w-full'):
            for key in chart_keys:
                out = next(o for o in outputs if o.key == key)
                with ui.card().classes('soft-card sensitivity-chart w-full p-3 gap-2'):
                    ui.label(out.label + (f' ({out.unit})' if out.unit else ''))\
                        .classes('text-base font-semibold')
                    charts[key] = ui.echart(dashboard_chart_options(study, key, 0))\
                        .classes('w-full h-56')

        ui.label('All output metrics').classes('text-lg font-semibold')
        metric_labels: dict[str, tuple[Any, Any, Any]] = {}
        with ui.element('div').classes('grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-3 w-full'):
            for out in outputs:
                with ui.card().classes('soft-card sensitivity-kpi w-full p-4 gap-2'):
                    ui.label(out.label).classes('text-sm text-slate-600 leading-normal')
                    current_label = ui.label('—').classes('text-xl font-semibold text-slate-800 break-words')
                    base_label = ui.label(f'Baseline: {present(study.baseline[out.key])} {out.unit}')\
                        .classes('text-sm text-slate-500 break-words')
                    delta_label = ui.label('—').classes('text-sm font-medium text-blue-700 break-words')
                    metric_labels[out.key] = (current_label, base_label, delta_label)

        with ui.expansion('View every scenario').classes('step-card w-full'):
            with ui.column().classes('w-full px-3 pb-3 gap-2'):
                ui.label('Each row shows a precomputed slider position; invalid inputs are marked.')\
                    .classes('text-sm text-slate-500')
                columns = [
                    {'name': 'pct', 'label': 'Change', 'field': 'pct', 'align': 'right'},
                    {'name': 'value', 'label': 'Input / Q', 'field': 'value', 'align': 'right'},
                ]
                for key in chart_keys:
                    output = next(out for out in outputs if out.key == key)
                    columns.append({'name': key, 'label': output.label, 'field': key,
                                    'align': 'right'})
                columns.append({'name': 'status', 'label': 'Status', 'field': 'status'})
                rows = []
                for p in study.points:
                    row = {'pct': f'{p.change:+g}{change_unit}', 'value': present(p.value),
                           'status': p.error or p.quality or ('Baseline' if p.change == 0 else '')}
                    for key in chart_keys:
                        row[key] = present(p.metrics[key]) if p.metrics else '—'
                    rows.append(row)
                ui.table(columns=columns, rows=rows, pagination=0).classes('w-full')\
                    .props('flat dense wrap-cells')

        def update_dashboard(change: float) -> None:
            point = dashboard_point(study, change)
            selected_label.set_text(f'{change:+g}{change_unit}' +
                                    (' · Baseline' if change == 0 else ' · Scenario'))
            input_label.set_text(f'{study.variable}: {present(study.baseline_value)} → {present(point.value)}')
            error_label.set_text('Cannot solve this scenario: ' + point.error if point.metrics is None else
                                 ('Scenario status: ' + point.quality if point.quality else ''))
            for comp in dashboard_comparisons(study, change):
                value_label, _, delta_label = metric_labels[comp.key]
                value_label.set_text(present(comp.current) + (f' {comp.unit}' if comp.unit else ''))
                if comp.current is None:
                    delta_label.set_text('Unavailable for this input')
                else:
                    diff = f'{comp.delta:+,.3f}'
                    percent_text = f' ({comp.percent:+.2f}%)' if comp.percent is not None else ''
                    delta_label.set_text('Δ ' + diff + percent_text +
                                         (f' {comp.unit}' if comp.unit else ''))
            for key, chart in charts.items():
                chart.options = dashboard_chart_options(study, key, change)
                chart.update()

        def slider_preview(e: Any) -> None:
            # Quasar emits updates while dragging; NiceGUI on_value_change
            # also updates on release / when Reset sets the value.
            value = e.args[0] if isinstance(e.args, (list, tuple)) else e.args
            update_dashboard(float(value))

        slider.on('update:model-value', slider_preview, throttle=0.12)
        slider.on_value_change(lambda e: update_dashboard(float(e.value)))
        update_dashboard(0.0)


def _theory(model: str) -> None:
    """Full manual-mapped theory, divided into readable sections.

    Each topic is introduced and mathematically derived once across
    the six models; another homework may refer back to it.
    """
    knowledge = KNOWLEDGE[model]
    with ui.column().classes('w-full gap-4'):
        with ui.card().classes('soft-card w-full p-6 gap-3'):
            ui.label(f'{model} · Theory').classes('text-xl font-semibold')
            ui.label(knowledge.introduction).classes('text-base text-slate-700 leading-relaxed')
            ui.label('Open a section to read the derivation and formulas from the manual.')\
                .classes('text-sm text-slate-500')
        for index, topic in enumerate(knowledge.sections):
            with ui.expansion(topic.title, value=index == 0).classes('step-card theory-section w-full'):
                with ui.column().classes('w-full px-4 pb-4 gap-3'):
                    for line in topic.lines:
                        if line.kind == 'math':
                            _mathexpression(line.value)
                        elif line.kind == 'bullet':
                            ui.label('• ' + line.value).classes(
                                'text-base text-slate-700 leading-relaxed whitespace-normal w-full')
                        else:
                            ui.label(line.value).classes(
                                'text-base text-slate-700 leading-relaxed whitespace-normal w-full')
        if model in ('HW4', 'HW5', 'HW6'):
            with ui.expansion('Part III · Distribution formulas and critical quantiles').classes('step-card w-full'):
                with ui.column().classes('w-full gap-2 px-3 pb-3'):
                    ui.label('Reusable formulas from Complete Manual Parts I, III and VII.')\
                        .classes('meta')
                    for section_title, equations in DISTRIBUTION_THEORY:
                        if model == 'HW5' and not any(key in section_title for key in ('Normal', 'Poisson', 'Critical', 'aggregation')):
                            continue
                        with ui.expansion(section_title).classes('step-card w-full'):
                            with ui.column().classes('w-full px-3 pb-3'):
                                for equation in equations:
                                    _mathexpression(equation)


def create_page() -> None:
    """Construct one independent client page; no mutable global user data.

    NiceGUI's page mode forbids creating UI at global/script scope. Both the
    palette and stylesheet are page-scoped, like every other UI component.
    """
    ui.colors(primary='#2d6a9f', secondary='#607e99', positive='#257b63')
    ui.add_css(STYLE)
    state: dict[str, Any] = {'model': 'HW1', 'draft': example('HW1'), 'result': None, 'tab': 'Input', 'revision': 0,
                             'sensitivity': None, 'sensitivity_config': {}, 'sensitivity_revision': -1}

    def select_model(model: str) -> None:
        if model not in HW_ORDER:
            return
        state.update(model=model, draft=example(model), result=None, tab='Input', revision=state['revision'] + 1,
                     sensitivity=None, sensitivity_config={}, sensitivity_revision=-1)
        sidebar_items.refresh()
        workspace.refresh()

    def store_value(key: str, value: Any, idx: int | None = None) -> None:
        if idx is None:
            state['draft'][key] = value
        else:
            state['draft']['items'][idx][key] = value
        state['revision'] += 1
        state['sensitivity'] = None
        sensitivity_results.refresh()

    def change_distribution(name: str, idx: int | None = None) -> None:
        if idx is None:
            target = state['draft']
        else:
            target = state['draft']['items'][idx]
        target['distribution'] = name
        target.update(defaults_for(name, target))
        state['result'] = None
        state['sensitivity'] = None
        state['revision'] += 1
        workspace.refresh()

    def distribution_inputs(raw: dict, idx: int | None = None) -> None:
        name = str(raw.get('distribution', 'Normal'))
        choices = ('Normal', 'Poisson') if state['model'] == 'HW5' else DISTRIBUTIONS
        ui.select(list(choices), label='Demand distribution', value=name,
                  on_change=lambda e, i=idx: change_distribution(str(e.value), i))\
            .classes('w-full md:max-w-sm').props('outlined dense')
        if name != 'Normal':
            with ui.element('div').classes('grid grid-cols-1 md:grid-cols-2 w-full gap-3 mt-2'):
                for key, label in PARAMETERS[name]:
                    ui.input(label, value=str(raw.get(key, '')),
                             on_change=lambda e, k=key, i=idx: store_value(k, e.value, i))\
                        .classes('w-full').props('outlined dense')
        else:
            ui.label('Normal demand: use mean μ and standard deviation σ below.')\
                .classes('meta')

    def add_item() -> None:
        model = state['model']
        if len(state['draft']['items']) >= 20:
            ui.notify('Maximum 20 products', color='negative')
            return
        new_item = deepcopy(state['draft']['items'][-1])
        new_item['name'] = f"Item {len(state['draft']['items'])+1}"
        state['draft']['items'].append(new_item)
        state['revision'] += 1
        state['sensitivity'] = None
        workspace.refresh()

    def remove_item() -> None:
        if len(state['draft'].get('items', [])) <= 2:
            ui.notify('At least two products are needed.', color='warning')
            return
        state['draft']['items'].pop()
        state['sensitivity'] = None
        state['revision'] += 1
        workspace.refresh()

    @ui.refreshable
    def sidebar_items() -> None:
        with ui.column().classes('w-full px-4 py-6 gap-3'):
            with ui.row().classes('w-full items-center justify-between mb-2'):
                ui.label('Models').classes('font-semibold text-base px-2')
                ui.button(icon='chevron_left', on_click=lambda: drawer.hide()).props('flat round dense')\
                  .tooltip('Collapse sidebar')
            for group, models in GROUPS.items():
                ui.label(group.upper()).classes('text-[10px] font-bold text-slate-500 tracking-wider px-2 mt-2')
                for model in models:
                    active = state['model'] == model
                    classes = 'model-btn text-left px-2 ' + ('model-btn-active ' if active else 'text-slate-700 ')
                    ui.button(f"{model}  ·  {TITLES[model].split(' · ')[0]}",
                              on_click=lambda m=model: select_model(m))\
                        .props('flat no-caps align=left').classes(classes)

    async def run_solver() -> None:
        model = state['model']
        revision = state['revision']
        payload = deepcopy(state['draft'])
        try:
            result = await background_run.io_bound(solve, model, payload)
        except ModelInputError as exc:
            ui.notify(str(exc), color='negative', timeout=7500)
            return
        except (ValueError, OverflowError, ZeroDivisionError) as exc:
            ui.notify(f'Invalid input or unstable calculation: {exc}', color='negative', timeout=7500)
            return
        if state['model'] != model or state['revision'] != revision:
            ui.notify('Inputs changed during computation. Solve again to use current values.', color='warning')
            return
        state['result'] = result
        state['tab'] = 'Results'
        workspace.refresh()
        ui.notify('Solution completed. Review the calculation steps.', color='positive')

    async def on_upload(e: events.UploadEventArguments) -> None:
        uploaded_for = state['model']
        try:
            payload = e.file.read()
            if hasattr(payload, '__await__'):
                payload = await payload
            data, description = read_inputs_xlsx(payload, uploaded_for)
        except ModelInputError as exc:
            ui.notify(str(exc), color='negative', timeout=8000)
            return
        preview = [{"Field": k, "Value": str(v) if k != 'items' else f'{len(v)} product rows'}
                   for k, v in data.items()]
        with ui.dialog() as dlg, ui.card().classes('w-full max-w-2xl p-5'):
            ui.label('Excel import preview').classes('text-lg font-semibold')
            ui.label(description).classes('text-sm text-slate-500')
            ui.table(rows=preview, pagination=0).classes('w-full').props('dense flat')
            ui.label('Applying will replace this model\'s current inputs. Teacher examples are not homework data.')\
                .classes('text-sm text-slate-500')
            with ui.row().classes('justify-end w-full'):
                ui.button('Cancel', on_click=dlg.close).props('flat no-caps')
                def apply() -> None:
                    if state['model'] != uploaded_for:
                        dlg.close()
                        ui.notify('Selected model changed; please upload again.', color='warning')
                        return
                    state['draft'] = data
                    state['revision'] += 1
                    state['result'] = None
                    state['sensitivity'] = None
                    state['tab'] = 'Input'
                    dlg.close()
                    workspace.refresh()
                ui.button('Apply inputs', on_click=apply).props('no-caps')
        dlg.open()

    @ui.refreshable
    def sensitivity_results() -> None:
        current: Study | None = state['sensitivity']
        if current is None or state['sensitivity_revision'] != state['revision'] or current.model != state['model']:
            ui.label('Choose a parameter and select Build dashboard to activate the 5% slider.')                .classes('text-sm text-slate-500')
        else:
            _sensitivity_output(current)

    async def run_sensitivity() -> None:
        model = state['model']
        revision = state['revision']
        config = dict(state['sensitivity_config'])
        raw = deepcopy(state['draft'])
        try:
            mode = str(config.get('mode', 'Input'))
            scale = str(config.get('scale', 'Percent'))
            if mode == 'Input' and scale == 'Absolute':
                radius = parse_numeric(config.get('absolute_radius', '5'), field='Absolute range')
                points = 11
            else:
                radius = float(config.get('radius', 25))
                if radius not in (10, 25, 50):
                    raise ModelInputError('Choose a percent range of ±10%, ±25%, or ±50%.')
                points = int(2 * radius / 5) + 1  # every 5%, including zero
            if mode == 'Fixed Q':
                study = await background_run.io_bound(
                    fixed_q_study, model, raw,
                    radius=radius, points=points,
                    reference=str(config.get('reference', 'EOQ')),
                    specific_pct=5.0,
                )
            else:
                parameter = str(config.get('parameter', ''))
                if not parameter:
                    parameters = available_parameters(model, raw)
                    parameter = parameters[0].path if parameters else ''
                study = await background_run.io_bound(
                    input_study, model, raw, parameter,
                    radius=radius, points=points, scale=scale,
                )
        except (ModelInputError, ValueError, OverflowError, ZeroDivisionError) as exc:
            ui.notify(str(exc), color='negative', timeout=8000)
            return
        if model != state['model'] or revision != state['revision'] or config != state['sensitivity_config']:
            ui.notify('Inputs or sensitivity settings changed during calculation. Build again.', color='warning')
            return
        state['sensitivity'] = study
        state['sensitivity_revision'] = revision
        sensitivity_results.refresh()
        ui.notify('Dashboard ready: move the slider to compare outputs.', color='positive')

    def update_sensitivity_option(key: str, value: Any, *, layout: bool = False) -> None:
        state['sensitivity_config'][key] = value
        state['sensitivity'] = None
        if layout:
            workspace.refresh()
        else:
            sensitivity_results.refresh()

    def sensitivity_panel(model: str) -> None:
        config = state['sensitivity_config']
        with ui.column().classes('w-full gap-5'):
            with ui.card().classes('soft-card w-full p-5 gap-4'):
                ui.label('Sensitivity analysis').classes('text-lg font-semibold')
                ui.label('Build the scenario dashboard once, then slide in 5% increments. '
                         'All outputs and charts respond together.')\
                    .classes('text-sm text-slate-600')
                with ui.element('div').classes('grid grid-cols-1 md:grid-cols-2 w-full gap-4'):
                    if model in ('HW1', 'HW3'):
                        mode = config.get('mode', 'Input')
                        ui.select({'Input': 'Change an input', 'Fixed Q': 'Change Q / EOQ (%)'},
                                  value=mode, label='Analysis mode',
                                  on_change=lambda e: update_sensitivity_option('mode', e.value, layout=True))\
                            .classes('w-full').props('outlined dense')
                    else:
                        config['mode'] = 'Input'
                    if config.get('mode', 'Input') == 'Input':
                        try:
                            params = available_parameters(model, state['draft'])
                        except ModelInputError as exc:
                            ui.label(f'Correct Input values first: {exc}').classes('text-amber-700')
                            return
                        choices = {p.path: p.label for p in params}
                        previous = config.get('parameter')
                        if previous not in choices:
                            previous = params[0].path if params else None
                            config['parameter'] = previous
                        ui.select(choices, value=previous, label='Input parameter',
                                  on_change=lambda e: update_sensitivity_option('parameter', e.value))\
                            .classes('w-full').props('outlined dense')
                        ui.select(['Percent', 'Absolute'], value=config.get('scale', 'Percent'),
                                  label='Variation type',
                                  on_change=lambda e: update_sensitivity_option('scale', e.value, layout=True))\
                            .classes('w-full').props('outlined dense')
                    elif model == 'HW1':
                        ui.select({'EOQ': 'EOQ from ordering + holding',
                                   'Optimized Q*': 'Simultaneously optimized Q*'},
                                  value=config.get('reference', 'EOQ'), label='Reference quantity',
                                  on_change=lambda e: update_sensitivity_option('reference', e.value))\
                            .classes('w-full').props('outlined dense')
                    if config.get('mode') == 'Input' and config.get('scale', 'Percent') == 'Absolute':
                        ui.input('Absolute range (±)', value=str(config.get('absolute_radius', '5')),
                                 on_change=lambda e: update_sensitivity_option('absolute_radius', e.value))\
                            .classes('w-full').props('outlined dense')
                    else:
                        ui.select({10: '±10% (5% steps)', 25: '±25% (5% steps)',
                                   50: '±50% (5% steps)'},
                                  value=config.get('radius', 25), label='Slider range',
                                  on_change=lambda e: update_sensitivity_option('radius', e.value))\
                            .classes('w-full').props('outlined dense')
                with ui.row().classes('items-center gap-3'):
                    ui.button('Build dashboard', icon='dashboard', on_click=run_sensitivity)\
                        .props('no-caps').classes('px-6')
                    ui.label('The slider starts at 0% (unchanged baseline).')\
                        .classes('text-sm text-slate-500')
            sensitivity_results()

    @ui.refreshable
    def workspace() -> None:
        model = state['model']
        with ui.column().classes('workspace flex-1 w-full gap-3'):
            with ui.row().classes('w-full items-center gap-2 flex-wrap'):
                ui.button(icon='menu', on_click=lambda: drawer.toggle()).props('flat round dense')\
                  .tooltip('Show / hide sidebar')
                ui.label(f'{model}  /  {TITLES[model]}')\
                    .classes('text-xl md:text-2xl font-semibold tracking-tight min-w-0')
            with ui.tabs(on_change=lambda e: state.update(tab=e.value)).classes('w-full text-slate-500 mt-3') as tabs:
                for name in ('Input', 'Results', 'Sensitivity', 'Theory'):
                    ui.tab(name).props('no-caps')
            with ui.tab_panels(tabs, value=state['tab']).classes('w-full'):
                with ui.tab_panel('Input'):
                    with ui.column().classes('gap-5 w-full'):
                        with ui.card().classes('soft-card w-full p-5 gap-4'):
                            with ui.row().classes('justify-between items-center w-full gap-3'):
                                ui.label('Model inputs').classes('text-lg font-semibold')
                                with ui.row().classes('gap-2'):
                                    ui.button('Load HW example', icon='refresh',
                                              on_click=lambda: (state.update(draft=example(model),result=None,sensitivity=None,revision=state['revision']+1),workspace.refresh()))\
                                        .props('outline no-caps')
                                    if model in ('HW4', 'HW5', 'HW6') and DISTRIBUTION_TEMPLATE.exists():
                                        ui.button('Distribution template', icon='download',
                                                  on_click=lambda: ui.download.file(str(DISTRIBUTION_TEMPLATE)))\
                                            .props('outline no-caps')
                                    if TEMPLATE.exists():
                                        ui.button('Excel template', icon='download',
                                                  on_click=lambda: ui.download.file(str(TEMPLATE)))\
                                            .props('outline no-caps')
                            ui.label('Enter integers, decimals, fractions or arithmetic: 2500, 0.125, 1/52, (20+5)*2, sqrt(2), 2^3. Use 0.25 for 25% (no % sign).')\
                                .classes('meta')
                            if model in ('HW1', 'HW3', 'HW2'):
                                ui.label('Demand distribution: Normal (required by this model).').classes('meta')
                            elif model == 'HW6':
                                distribution_inputs(state['draft'])
                            with ui.element('div').classes('grid grid-cols-1 md:grid-cols-2 w-full gap-5'):
                                for column_fields in input_columns(model):
                                    with ui.column().classes('w-full gap-3'):
                                        for key, label in column_fields:
                                            if model == 'HW6' and key in ('mu', 'sigma') and state['draft'].get('distribution', 'Normal') != 'Normal':
                                                continue
                                            ui.input(field_caption(key, label), value=str(state['draft'].get(key, '')),
                                                     on_change=lambda e, k=key: store_value(k, e.value))\
                                                .classes('w-full').props('outlined dense')
                            if model in ITEM_FIELDS:
                                ui.separator().classes('my-3')
                                with ui.row().classes('justify-between items-center w-full'):
                                    ui.label('Products / designs').classes('font-semibold')
                                    with ui.row().classes('gap-2'):
                                        ui.button('Add', icon='add',on_click=add_item).props('outline no-caps dense')
                                        ui.button('Remove last',icon='remove',on_click=remove_item).props('outline no-caps dense')
                                for j,item in enumerate(state['draft']['items']):
                                    with ui.expansion(f"{j+1}. {item.get('name',f'Item {j+1}')}",
                                                      value=j<2).classes('step-card w-full'):
                                        with ui.column().classes('w-full px-3 pt-3'):
                                            distribution_inputs(item, idx=j)
                                        with ui.element('div').classes('grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 w-full p-3 gap-3'):
                                            for key,label in ITEM_FIELDS[model]:
                                                if key in ('mu', 'sigma') and item.get('distribution', 'Normal') != 'Normal':
                                                    continue
                                                if key == 'name':
                                                    ui.input(label,value=item.get(key),
                                                             on_change=lambda e, ii=j,k=key: store_value(k,e.value,ii))\
                                                        .classes('w-full').props('outlined dense')
                                                else:
                                                    ui.input(field_caption(key, label), value=str(item.get(key, '')),
                                                             on_change=lambda e, ii=j,k=key: store_value(k, e.value, ii))\
                                                        .classes('w-full').props('outlined dense')
                            with ui.row().classes('justify-start gap-3 mt-4'):
                                ui.button('Solve', icon='calculate', on_click=run_solver).props('no-caps').classes('px-8')
                        with ui.card().classes('soft-card w-full p-5 gap-3'):
                            ui.label('Import from Excel').classes('font-semibold')
                            ui.label('Upload an edited template (.xlsx). You can also import supported instructor example sheets. Preview before applying.')\
                                .classes('text-sm text-slate-500')
                            ui.upload(on_upload=on_upload, auto_upload=True, max_file_size=2_000_000,
                                      on_rejected=lambda: ui.notify('Excel file rejected (>2 MB or unsupported)',color='negative'))\
                                .props('accept=.xlsx').classes('w-full')
                with ui.tab_panel('Results'):
                    _results(state['result'])
                with ui.tab_panel('Sensitivity'):
                    sensitivity_panel(model)
                with ui.tab_panel('Theory'):
                    _theory(model)

    # Use a Quasar drawer so the content width expands when the sidebar closes.
    # The menu button lives in the workspace so it remains reachable while closed.
    with ui.left_drawer(fixed=True, bordered=True).props('width=270 breakpoint=850').classes('sidebar') as drawer:
        sidebar_items()
    workspace()


def run() -> None:
    import os
    ui.page('/')(create_page)
    port = int(os.getenv('PORT', '8080'))
    # Keep reloading off for reliable startup on Windows and when launched through
    # an imported run() function. NiceGUI's reload subprocess would otherwise
    # re-import main.py without calling run() (main guard), failing at startup.
    # This is safe on Render too; redeploy/restart to apply source changes.
    ui.run(host='0.0.0.0', port=port, title='Inventory Solver',
           favicon='📦', reload=False, show=False)
