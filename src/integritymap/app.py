import html
import io

import pandas as pd
import streamlit as st

from integritymap import charts
from integritymap.data import ATTACK_STAGES, INTERVENTION_NAME, INTERVENTIONS, STAGE_BY_ID, STAGES, load_bundle
from integritymap.search import KeywordIndex

PER_PAGE = 12
INTERVENTION_STAGE = {i: s for i, _, s in INTERVENTIONS}
st.set_page_config(page_title="Supervision integrity explorer", page_icon="◆", layout="wide")

CSS = """
<style>
.block-container {padding-top: 1.6rem; max-width: 1180px;}
.masthead {border-bottom: 3px solid #1C2430; padding-bottom: 0.9rem; margin-bottom: 1.1rem;}
.kicker {text-transform: uppercase; letter-spacing: 0.12em; font-size: 0.74rem; color: #5B6472; font-weight: 600;}
.masthead h1 {font-family: Newsreader, Georgia, serif; font-weight: 600; font-size: 2.3rem; margin: 0.15rem 0 0.35rem 0; line-height: 1.12;}
.masthead p {color: #3D4654; font-size: 1.03rem; max-width: 50rem; margin: 0; line-height: 1.5;}
.kpis {display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.7rem; margin: 0 0 1.2rem 0;}
.kpi {background: #F6F7F9; border-radius: 6px; padding: 0.7rem 0.9rem;}
.kpi b {display: block; font-family: Newsreader, Georgia, serif; font-size: 1.75rem; font-weight: 600; color: #1C2430; line-height: 1.1;}
.kpi span {color: #5B6472; font-size: 0.86rem;}
.pill {display: inline-block; border-radius: 999px; padding: 0.05rem 0.6rem; font-size: 0.78rem; font-weight: 600; margin-right: 0.35rem; border: 1px solid #D5DAE0; color: #3D4654; background: #FFFFFF;}
.pill.stage {color: #FFFFFF; border: none;}
.ptitle {font-family: Newsreader, Georgia, serif; font-size: 1.12rem; font-weight: 600; line-height: 1.35; margin: 0.45rem 0 0.15rem 0;}
.ptitle a {color: #1C2430; text-decoration: none;} .ptitle a:hover {text-decoration: underline;}
.pmeta {color: #5B6472; font-size: 0.9rem; margin-bottom: 0.5rem;}
.facts {display: grid; grid-template-columns: 9.5rem 1fr; gap: 0.2rem 0.8rem; font-size: 0.92rem; margin: 0.3rem 0 0.2rem 0;}
.facts dt {color: #5B6472;} .facts dd {margin: 0; color: #1C2430;}
.stagecard {border-top: 5px solid; background: #FAFBFC; border-radius: 4px; padding: 0.7rem 0.85rem 0.8rem 0.85rem; height: 100%;}
.stagecard h4 {margin: 0 0 0.3rem 0; font-size: 1.02rem;}
.stagecard p {font-size: 0.88rem; color: #3D4654; margin: 0 0 0.45rem 0; line-height: 1.42;}
.stagecard .lost {color: #8A2B20; font-size: 0.86rem;}
.counts {font-size: 0.86rem; color: #5B6472; margin-bottom: 0.4rem;} .counts b {color: #1C2430;}
.item {padding: 0.45rem 0; border-bottom: 1px solid #EEF0F3; font-size: 0.93rem;}
.item small {color: #5B6472;}
.badge {display: inline-block; min-width: 4.6rem; font-size: 0.8rem; font-weight: 600; border-radius: 4px; padding: 0.05rem 0.45rem; margin-right: 0.45rem; color: #FFFFFF; text-align: center;}
.lede2 {color: #3D4654; font-size: 0.95rem; max-width: 48rem;}
.small {color: #5B6472; font-size: 0.85rem;}
.foot {color: #6B7380; font-size: 0.82rem; border-top: 1px solid #E3E7EC; margin-top: 2.2rem; padding-top: 0.7rem;}
@media (max-width: 700px) {.kpis {grid-template-columns: repeat(2, 1fr);} .masthead h1 {font-size: 1.8rem;} .facts {grid-template-columns: 1fr;}}
</style>
"""


@st.cache_resource(show_spinner=False)
def resources():
    b = load_bundle()
    by_key = {p["key"]: p for p in b.papers}
    for e in b.evaluations:
        e["label"] = by_key[e["paper"]]["label"]
    cells: dict[tuple[str, str], list[dict]] = {}
    for e in b.evaluations:
        cells.setdefault((e["row"], e["column"]), []).append(e)
    return b, by_key, cells, KeywordIndex(b.papers)


def esc(x) -> str:
    return html.escape(str(x))


def stage_of(p: dict) -> str:
    return p["stage"] if p["role"] == "attack" else INTERVENTION_STAGE[p["intervention"]]


def stage_pill(stage: str) -> str:
    return f'<span class="pill stage" style="background:{charts.STAGE_COLORS[stage]}">{esc(STAGE_BY_ID[stage].name)}</span>'


def badge(outcome: str) -> str:
    color, icon, word = charts.OUTCOME_STYLE[outcome]
    return f'<span class="badge" style="background:{color}">{icon} {word}</span>'


def link(p: dict) -> str:
    if p.get("url"):
        return p["url"]
    if p.get("arxiv_id"):
        return f"https://arxiv.org/abs/{p['arxiv_id']}"
    return f"https://doi.org/{p['doi']}" if p.get("doi") else ""


def authors_line(names: list[str]) -> str:
    return names[0] + (" and " + names[1] if len(names) == 2 else " et al." if len(names) > 2 else "") if names else ""


def pipeline_tab(papers: list[dict]) -> None:
    st.markdown('<p class="lede2">Supervision passes through four stages. An attacker can enter at the first three, '
                'and each hand-off drops evidence a defender would need to trace the corruption back.</p>', unsafe_allow_html=True)
    cols = st.columns(4, gap="small")
    for col, s in zip(cols, STAGES, strict=True):
        n_att = sum(p["role"] == "attack" and p["stage"] == s.id for p in papers)
        n_def = sum(p["role"] == "defense" and stage_of(p) == s.id for p in papers)
        col.markdown(
            f'<div class="stagecard" style="border-color:{charts.STAGE_COLORS[s.id]}"><h4>{esc(s.name)}</h4>'
            f'<div class="counts"><b>{n_att}</b> attacks enter · <b>{n_def}</b> defenses act</div>'
            f'<p>{esc(s.role)}</p><p>{esc(s.attacker)}</p><p class="lost">Lost: {esc(s.lost)}</p></div>', unsafe_allow_html=True)
    st.write("")
    choice = st.segmented_control("Show papers at", [s.id for s in STAGES], default="source", format_func=lambda i: STAGE_BY_ID[i].name,
                                  key="pipe_stage") or "source"
    left, right = st.columns(2, gap="large")
    attacks = sorted((p for p in papers if p["role"] == "attack" and p["stage"] == choice), key=lambda p: p["label"])
    defenses = sorted((p for p in papers if p["role"] == "defense" and stage_of(p) == choice), key=lambda p: (p["intervention"], p["label"]))
    with left:
        st.markdown(f"**Attacks that enter here** ({len(attacks)})")
        if not attacks:
            st.caption("No surveyed attack enters at this stage." if choice != "model" else "The trained policy is out of scope.")
        for p in attacks:
            st.markdown(f'<div class="item"><b>{esc(p["label"])}</b> · {esc(p["vector"])} <small>({esc(p["capability"])}, '
                        f'{esc(p["goal"])}, budget {esc(p["budget"])})</small></div>', unsafe_allow_html=True)
    with right:
        st.markdown(f"**Defenses that act here** ({len(defenses)})")
        if choice == "source":
            st.markdown('<div class="item"><b>Source and provenance</b> · <small>no surveyed defense records or verifies who produced each label</small></div>',
                        unsafe_allow_html=True)
        scope_word = {"attack": "tested against an attack", "noise": "tested on noise only", "theory": "theory only"}
        for p in defenses:
            st.markdown(f'<div class="item"><b>{esc(p["label"])}</b> · {esc(p["mechanism"])} <small>({esc(INTERVENTION_NAME[p["intervention"]])}; '
                        f'{scope_word[p["scope"]]})</small></div>', unsafe_allow_html=True)


def paper_card(p: dict, evals: list[dict]) -> None:
    with st.container(border=True):
        pills = stage_pill(stage_of(p)) + f'<span class="pill">{"Attack" if p["role"] == "attack" else "Defense"}</span>'
        if p["role"] == "attack":
            pills += f'<span class="pill">{esc(p["capability"])}</span><span class="pill">{esc(p["goal"])}</span>'
            facts = [("Attack vector", p["vector"]), ("Target", p["target"]), ("Budget", p["budget"]),
                     ("Reported effect", p["effect"]), ("Defense tested", "yes" if p["defense_tested"] else "no")]
        else:
            pills += f'<span class="pill">{esc(INTERVENTION_NAME[p["intervention"]])}</span>'
            facts = [("Mechanism", p["mechanism"]), ("Tested against", p["tested_against"]), ("May apply to", p["may_apply"]), ("Cost", p["cost"])]
        url = link(p)
        title = f'<a href="{esc(url)}" target="_blank">{esc(p["title"])}</a>' if url else esc(p["title"])
        dl = "".join(f"<dt>{esc(k)}</dt><dd>{esc(v)}</dd>" for k, v in facts)
        st.markdown(f'{pills}<div class="ptitle">{title}</div><div class="pmeta">{esc(authors_line(p["authors"]))} · '
                    f'{esc(p["venue"])} · {p["year"]}</div><dl class="facts">{dl}</dl>', unsafe_allow_html=True)
        tabs = st.tabs(["Abstract", f"Evaluations ({len(evals)})", "BibTeX"])
        tabs[0].markdown(p["abstract"] or "_No abstract available. Follow the title link._")
        with tabs[1]:
            if not evals:
                st.caption("This paper adds no evaluation to the coverage map.")
            for e in evals:
                st.markdown(f'<div class="item">{badge(e["outcome"])}<b>{esc(e["defense"])}</b> · '
                            f'<small>{esc(INTERVENTION_NAME[e["row"]])} vs. {esc(STAGE_BY_ID[e["column"]].name.lower())} attacks. {esc(e["note"])}</small></div>',
                            unsafe_allow_html=True)
        tabs[2].code(p["bibtex"], language="latex")


def papers_tab(papers: list[dict], evaluations: list[dict], index: KeywordIndex) -> None:
    s = st.session_state
    top = st.columns([0.55, 0.45], vertical_alignment="bottom")
    query = top[0].text_input("Search", placeholder="Try: label flip, judge injection, certificate", key="q")
    role = top[1].segmented_control("Show", ["All", "Attacks", "Defenses"], default="All", key="role", width="stretch") or "All"
    with st.expander("More filters"):
        f1, f2, f3 = st.columns(3)
        stages = f1.multiselect("Stage", [x.id for x in STAGES], format_func=lambda i: STAGE_BY_ID[i].name, key="f_stage")
        caps = f2.multiselect("Attacker capability", ["A1", "A2", "A3", "A1–A3"], key="f_cap")
        goals = f3.multiselect("Attack goal", ["backdoor", "reversal"], key="f_goal")
        g1, g2 = st.columns([0.66, 0.34])
        points = g1.multiselect("Intervention point", [i for i, _, _ in INTERVENTIONS[1:]], format_func=INTERVENTION_NAME.get, key="f_point")
        only_tested = g2.toggle("Only defenses tested against an attack", key="f_tested")
    order = list(range(len(papers)))
    if query.strip():
        order = [i for i, _ in index.search(query)]
    keep = []
    for i in order:
        p = papers[i]
        if role == "Attacks" and p["role"] != "attack" or role == "Defenses" and p["role"] != "defense":
            continue
        if stages and stage_of(p) not in stages:
            continue
        if (caps or goals) and (p["role"] != "attack" or caps and p["capability"] not in caps or goals and p["goal"] not in goals):
            continue
        if (points or only_tested) and (p["role"] != "defense" or points and p["intervention"] not in points or only_tested and p["scope"] != "attack"):
            continue
        keep.append(p)
    if not query.strip():
        keep.sort(key=lambda p: (p["role"], p["label"]))
    c1, c2, c3 = st.columns([0.5, 0.25, 0.25], vertical_alignment="center")
    c1.markdown(f'<span class="small">{len(keep)} of {len(papers)} papers{" for “" + esc(query) + "”" if query.strip() else ""}</span>',
                unsafe_allow_html=True)
    if keep:
        c2.download_button("BibTeX of these", "\n\n".join(p["bibtex"] for p in keep), "integrity_papers.bib", width="stretch")
        buf = io.StringIO()
        pd.DataFrame([{k: (", ".join(v) if isinstance(v, list) else v) for k, v in p.items() if k not in ("bibtex", "abstract")} for p in keep]).to_csv(buf, index=False)
        c3.download_button("CSV of these", buf.getvalue(), "integrity_papers.csv", width="stretch")
    if not keep:
        st.info("No paper matches. Remove a filter or try a broader word such as *backdoor* or *judge*.")
        return
    pages = (len(keep) - 1) // PER_PAGE + 1
    s.page = min(s.get("page", 1), pages)
    by_paper: dict[str, list[dict]] = {}
    for e in evaluations:
        by_paper.setdefault(e["paper"], []).append(e)
    for p in keep[(s.page - 1) * PER_PAGE: s.page * PER_PAGE]:
        paper_card(p, by_paper.get(p["key"], []))
    if pages > 1:
        n1, n2, n3 = st.columns([0.2, 0.6, 0.2])
        n1.button("← Previous", disabled=s.page == 1, on_click=lambda: s.update(page=s.page - 1), width="stretch")
        n2.markdown(f'<div class="small" style="text-align:center">Page {s.page} of {pages}</div>', unsafe_allow_html=True)
        n3.button("Next →", disabled=s.page == pages, on_click=lambda: s.update(page=s.page + 1), width="stretch")


def on_cell() -> None:
    sel = st.session_state.get("cov")
    pts = list(sel.selection.points) if sel and sel.selection else []
    if pts and (cid := pts[0].get("customdata")) and tuple(cid.split("|")) in resources()[2]:
        st.session_state["cell"] = cid


def coverage_tab(cells: dict, noise: dict, evaluations: list[dict]) -> None:
    st.markdown('<p class="lede2">Each cell counts the evaluations that test a defense (row) against attacks entering at a stage '
                '(column). The number in parentheses counts those that find the defense works. Click a cell to see every evaluation.</p>',
                unsafe_allow_html=True)
    options = [f"{r}|{c}" for (r, c) in cells]
    st.session_state.setdefault("cell", "annotation_checks|source")
    left, right = st.columns([0.56, 0.44], gap="large")
    with left:
        row, col = st.session_state["cell"].split("|")
        st.plotly_chart(charts.coverage_map(cells, noise, (row, col)), key="cov", on_select=on_cell, selection_mode="points",
                        config={"displayModeBar": False}, width="stretch")
        st.markdown('<div class="small">Darker cells hold more evaluations. Works: the attack falls by about 70% or more. '
                    'Partial: by about 25–70%. Fails: by less. The last column counts papers tested only without an adversary.</div>',
                    unsafe_allow_html=True)
    with right:
        cell = st.selectbox("Cell", options, key="cell", format_func=lambda c: f"{INTERVENTION_NAME[c.split('|')[0]]} × {STAGE_BY_ID[c.split('|')[1]].name}")
        row, col = cell.split("|")
        evs = cells[(row, col)]
        counts = {o: sum(e["outcome"] == o for e in evs) for o in charts.OUTCOME_STYLE}
        n_pap = len({e["paper"] for e in evs})
        st.markdown(f'<div class="counts"><b>{len(evs)}</b> evaluation{"s" if len(evs) > 1 else ""} in <b>{n_pap}</b> paper{"s" if n_pap > 1 else ""} · '
                    + " ".join(badge(o) + f"{n}&nbsp;&nbsp;" for o, n in counts.items() if n) + "</div>", unsafe_allow_html=True)
        for paper in dict.fromkeys(e["paper"] for e in evs):
            mine = [e for e in evs if e["paper"] == paper]
            st.markdown(f"**{mine[0]['label']}**")
            for e in mine:
                st.markdown(f'<div class="item">{badge(e["outcome"])}{esc(e["defense"])}<br><small>{esc(e["note"])}</small></div>', unsafe_allow_html=True)
    st.subheader("Outcomes by stage of entry")
    st.plotly_chart(charts.outcome_bars(evaluations), config={"displayModeBar": False}, width="stretch")
    works = sum(e["outcome"] == "works" for e in evaluations)
    st.markdown(f'<div class="small">Of {len(evaluations)} evaluations, {works} find that the defense works. '
                'None works against an attack on the reward or verification channel, and each defense that works needs extra knowledge, '
                'a large cost, or a narrow test.</div>', unsafe_allow_html=True)


def budgets_tab(budgets: list[dict], by_key: dict) -> None:
    rows = [{**b, "label": by_key[b["key"]]["label"], "stage": by_key[b["key"]]["stage"]} for b in budgets]
    small = sum(min(v for v in (r["policy"], r["proxy"]) if v is not None) <= 1 for r in rows)
    st.markdown(f'<p class="lede2"><b>{small} of {len(rows)}</b> attack papers that report a budget see an effect when the attacker controls '
                '1% of the training data or less. Each dot is the budget at which the paper reports the effect quoted in the survey.</p>',
                unsafe_allow_html=True)
    key = "".join(f'<span class="pill stage" style="background:{charts.STAGE_COLORS[s]}">{esc(STAGE_BY_ID[s].name)}</span>' for s in ATTACK_STAGES)
    st.markdown(f'{key}<span class="small">● final policy &nbsp; ○ reward model or judge only &nbsp; † share of another training set</span>',
                unsafe_allow_html=True)
    st.plotly_chart(charts.budget_dots(rows), config={"displayModeBar": False}, width="stretch")
    st.caption("Success criteria differ across papers, so compare budgets, not success rates. Joined dots show that the reward model "
               "can be corrupted at a smaller budget than the final policy.")
    table = pd.DataFrame([{"Paper": r["label"], "Stage": STAGE_BY_ID[r["stage"]].name, "Policy budget (%)": r["policy"],
                           "Reward model or judge budget (%)": r["proxy"], "Reported effect": by_key[r["key"]]["effect"]} for r in rows])
    st.dataframe(table, hide_index=True, width="stretch")


def provenance_tab(audit: list[dict]) -> None:
    ids = sum(a["annotator_id"].startswith("yes") for a in audit)
    guide = sum(a["guideline"].startswith("yes") for a in audit)
    judges = sum(a["annotator_id"].startswith("judge named") for a in audit)
    st.markdown(f'<p class="lede2">Could a user trace a label back to whoever produced it? We checked {len(audit)} widely used public '
                'preference datasets against their released files on 11 October 2026.</p>', unsafe_allow_html=True)
    st.markdown(f'<div class="kpis"><div class="kpi"><b>{ids} of {len(audit)}</b><span>release a per-label annotator ID</span></div>'
                f'<div class="kpi"><b>{guide} of {len(audit)}</b><span>tie a guideline version to each label</span></div>'
                f'<div class="kpi"><b>{judges} of {len(audit)}</b><span>LLM-judged sets that name the judge only in a card or paper</span></div>'
                '<div class="kpi"><b>2,628</b><span>UltraFeedback completions relabeled in place, with no flag</span></div></div>', unsafe_allow_html=True)
    kind = st.segmented_control("Labelers", ["All", "Human", "LLM judge"], default="All", key="prov_kind") or "All"
    rows = [a for a in audit if kind == "All" or (kind == "LLM judge") == ("judge" in a["labelers"].lower())]
    df = pd.DataFrame([{"Dataset": a["dataset"] + (" *" if a["gated"] else ""), "Labelers": a["labelers"], "Per-label ID": a["annotator_id"],
                        "Per-label date or batch": a["date"], "Guideline version per label": a["guideline"], "Upstream source kept": a["upstream"]}
                       for a in rows])

    def tint(v: str) -> str:
        v = str(v).lower()
        if v.startswith("yes"):
            return "background-color: #E3F2E8; color: #135C2E"
        if v.startswith("no") or v.startswith("judge named"):
            return "background-color: #FBE9E7; color: #8A2B20"
        return "color: #6B7380" if v.startswith("n.a") else "background-color: #FFF4DA; color: #6B4E00"

    st.dataframe(df.style.map(tint, subset=df.columns[2:]), hide_index=True, width="stretch")
    st.caption("A field counts only if it is present in the released files. n.a.: not applicable (votes without a rubric, or not a merged set). "
               "* Gated: fields taken from the card and the column list.")


def main() -> None:
    st.markdown(CSS, unsafe_allow_html=True)
    b, by_key, cells, index = resources()
    n_att = sum(p["role"] == "attack" for p in b.papers)
    works = sum(e["outcome"] == "works" for e in b.evaluations)
    st.markdown('<div class="masthead"><div class="kicker">Survey companion</div><h1>When supervision fails</h1>'
                '<p>Explore the papers behind our survey of integrity attacks and defenses in LLM alignment: where corruption enters the '
                'supervision pipeline, which defenses have been tested against it, and what evidence the pipeline keeps.</p></div>',
                unsafe_allow_html=True)
    st.markdown(f'<div class="kpis"><div class="kpi"><b>{n_att}</b><span>attack papers</span></div>'
                f'<div class="kpi"><b>{len(b.papers) - n_att}</b><span>defense papers</span></div>'
                f'<div class="kpi"><b>{len(b.evaluations)}</b><span>evaluations of a defense against an attack</span></div>'
                f'<div class="kpi"><b>{works}</b><span>of them find that the defense works</span></div></div>', unsafe_allow_html=True)
    tabs = st.tabs(["Papers", "Pipeline", "Coverage map", "Budgets", "Provenance audit"])
    with tabs[0]:
        papers_tab(b.papers, b.evaluations, index)
    with tabs[1]:
        pipeline_tab(b.papers)
    with tabs[2]:
        coverage_tab(cells, b.noise_only, b.evaluations)
    with tabs[3]:
        budgets_tab(b.budgets, by_key)
    with tabs[4]:
        provenance_tab(b.provenance)
    st.markdown('<div class="foot">Data come from Tables 1, 2, 4, 5, and 7 and Appendix B of the survey; the corpus ends on 9 October 2026. '
                '<code>scripts/build_data.py</code> rebuilds them from the paper sources.</div>', unsafe_allow_html=True)


main()
