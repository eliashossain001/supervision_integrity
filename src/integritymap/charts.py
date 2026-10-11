import plotly.graph_objects as go

from integritymap.data import ATTACK_STAGES, INTERVENTIONS, STAGE_BY_ID

# Stage colors of the paper's Figure 1 and Table 2; grey marks the trained policy, which no attack in scope enters.
STAGE_COLORS = {"source": "#2E7D32", "dataset": "#C79100", "channel": "#2563C4", "model": "#A0A6AE"}
# Outcome badges always carry an icon and a word, so color is never the only cue.
OUTCOME_STYLE = {
    "works": ("#1B7F4B", "✓", "Works"),
    "partial": ("#B7791F", "◐", "Partial"),
    "fails": ("#C0392B", "✗", "Fails"),
    "unclear": ("#8C959F", "?", "Unclear"),
}
# One-hue ramp for "how many evaluations", kept apart from the stage hues.
HEAT = ["#EFEAF8", "#CDBDEB", "#7E5CC0"]
INK, MUTED, RULE = "#1C2430", "#5B6472", "#E3E7EC"
FONT = "Public Sans, sans-serif"
COLUMNS = ATTACK_STAGES + ["none"]
COLUMN_NAMES = {"source": "Source", "dataset": "Dataset", "channel": "Channel", "none": "None"}


def _base(fig: go.Figure, height: int) -> go.Figure:
    fig.update_layout(
        height=height, margin=dict(l=4, r=4, t=4, b=4), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT, size=14, color=INK), showlegend=False,
        hoverlabel=dict(bgcolor="#FFFFFF", bordercolor=RULE, font=dict(family=FONT, size=13, color=INK)),
    )
    return fig


def heat_color(n: int) -> str:
    return HEAT[0] if n <= 2 else HEAT[1] if n < 10 else HEAT[2]


def coverage_map(cells: dict, noise: dict, selected: tuple[str, str] | None) -> go.Figure:
    """Table 2 as clickable cells: evaluations against each stage of entry, plus the no-adversary column.

    Rectangles carry the fill; an invisible marker in each cell carries the hover and the click.
    """
    fig = go.Figure()
    rows = [r for r, _, _ in INTERVENTIONS]
    xs, ys, ids, hovers = [], [], [], []
    for yi, (rid, _, stage) in enumerate(INTERVENTIONS):
        y = len(rows) - 1 - yi
        fig.add_shape(type="rect", x0=-0.62, x1=-0.56, y0=y - 0.36, y1=y + 0.36, fillcolor=STAGE_COLORS[stage], line_width=0)
        for xi, col in enumerate(COLUMNS):
            evs = cells.get((rid, col), [])
            if col == "none":
                n = len(noise.get(rid, []))
                fill, label, color = "#F6F7F9", str(n) if n else "·", MUTED
                hover = f"{n} papers tested only on noise or over-optimization" if n else "None"
            elif rid == "provenance":
                xs.append(xi); ys.append(y); ids.append(f"{rid}|{col}")
                hovers.append("No surveyed paper evaluates a provenance defense.")
                continue
            elif rid == "channel_validation" and col == "dataset":
                fill, label, color, hover = "#FFFFFF", "<i>untested</i>", MUTED, "May apply, never tested."
            elif evs:
                works = sum(e["outcome"] == "works" for e in evs)
                fill = heat_color(len(evs))
                color = "#FFFFFF" if fill == HEAT[2] else INK
                label = f"<b>{len(evs)}</b> ({works})"
                papers = len({e["paper"] for e in evs})
                hover = f"{len(evs)} evaluations in {papers} papers<br>{works} find that the defense works"
            else:
                fill, label, color, hover = "#FFFFFF", "·", "#B6BDC6", "No evaluation"
            on = selected == (rid, col)
            fig.add_shape(type="rect", x0=xi - 0.47, x1=xi + 0.47, y0=y - 0.42, y1=y + 0.42, fillcolor=fill,
                          line=dict(color=INK if on else RULE, width=2.4 if on else 1))
            fig.add_annotation(x=xi, y=y, text=label, showarrow=False, font=dict(size=15, color=color))
            xs.append(xi); ys.append(y); ids.append(f"{rid}|{col}"); hovers.append(hover)
    top = len(rows) - 1
    fig.add_shape(type="rect", x0=-0.47, x1=2.47, y0=top - 0.42, y1=top + 0.42, fillcolor="#FFFFFF", line=dict(color=RULE, width=1))
    fig.add_annotation(x=1, y=top, text="<i>no surveyed defense</i>", showarrow=False, font=dict(size=14, color="#B23A2E"))
    fig.add_scatter(x=xs, y=ys, mode="markers", marker=dict(size=46, color="rgba(0,0,0,0)", symbol="square"),
                    customdata=ids, hovertext=hovers, hovertemplate="%{hovertext}<extra></extra>")
    _base(fig, 420)
    # Real axes, not annotations, so Plotly reserves room for the labels on narrow screens.
    fig.update_xaxes(side="top", range=[-0.7, len(COLUMNS) - 0.45], fixedrange=True, showgrid=False, zeroline=False, showline=False,
                     tickvals=list(range(len(COLUMNS))), ticktext=[f"<b>{COLUMN_NAMES[c]}</b>" for c in COLUMNS], ticks="",
                     tickfont=dict(size=13, color=INK), title=dict(text="Attack enters at  ·  None = no adversary", font=dict(size=12, color=MUTED)))
    fig.update_yaxes(range=[-0.6, len(rows) - 0.45], fixedrange=True, showgrid=False, zeroline=False, showline=False, ticks="",
                     tickvals=[len(rows) - 1 - i for i in range(len(rows))], ticktext=[n for _, n, _ in INTERVENTIONS],
                     tickfont=dict(size=14, color=INK), automargin=True)
    return fig


def outcome_bars(evaluations: list[dict]) -> go.Figure:
    """Outcomes of the 73 evaluations, one bar per stage of entry."""
    fig = go.Figure()
    for outcome, (color, icon, word) in OUTCOME_STYLE.items():
        counts = [sum(e["outcome"] == outcome and e["column"] == s for e in evaluations) for s in ATTACK_STAGES]
        fig.add_bar(y=[STAGE_BY_ID[s].name for s in ATTACK_STAGES], x=counts, orientation="h", name=f"{icon} {word}",
                    marker=dict(color=color, line=dict(color="#FFFFFF", width=2)),
                    text=[str(c) if c else "" for c in counts], textposition="inside", insidetextanchor="middle",
                    textfont=dict(color="#FFFFFF", size=13), hovertemplate=f"{word}: %{{x}}<extra></extra>")
    _base(fig, 190)
    fig.update_layout(barmode="stack", bargap=0.35, showlegend=True,
                      legend=dict(orientation="h", y=1.18, x=0, font=dict(color=MUTED, size=13), itemclick=False, itemdoubleclick=False))
    fig.update_xaxes(showgrid=True, gridcolor=RULE, zeroline=False, tickfont=dict(color=MUTED), title=None)
    fig.update_yaxes(autorange="reversed", tickfont=dict(color=INK))
    return fig


def budget_dots(rows: list[dict]) -> go.Figure:
    """Smallest reported budget per attack paper; filled = final policy, hollow = reward model or judge only."""
    rows = sorted(rows, key=lambda r: min(v for v in (r["policy"], r["proxy"]) if v is not None))
    fig = go.Figure()
    for i, r in enumerate(rows):
        c = STAGE_COLORS[r["stage"]]
        if r["policy"] is not None and r["proxy"] is not None:
            fig.add_scatter(x=[r["proxy"], r["policy"]], y=[i, i], mode="lines", line=dict(color="#C3C9D1", width=2), hoverinfo="skip")
        for v, filled, what in ((r["proxy"], False, "reward model or judge"), (r["policy"], True, "final policy")):
            if v is not None:
                fig.add_scatter(x=[v], y=[i], mode="markers",
                                marker=dict(size=12, color=c if filled else "#FFFFFF", line=dict(color=c, width=2.2)),
                                hovertemplate=f"<b>{r['label']}</b><br>{what}: {v:g}%<extra></extra>")
    fig.add_vline(x=1, line=dict(color=MUTED, width=1, dash="dot"))
    _base(fig, 34 * len(rows) + 60)
    fig.update_xaxes(type="log", range=[-0.75, 1.2], tickvals=[0.3, 0.5, 1, 2, 5, 10], ticktext=["0.3%", "0.5%", "1%", "2%", "5%", "10%"],
                     showgrid=True, gridcolor=RULE, tickfont=dict(color=MUTED), title=dict(text="Share of training data controlled by the attacker (log scale)", font=dict(color=MUTED, size=13)))
    fig.update_yaxes(tickvals=list(range(len(rows))), ticktext=[r["label"] + ("†" if r["other_set"] else "") for r in rows],
                     autorange="reversed", tickfont=dict(color=INK), showgrid=False)
    return fig
