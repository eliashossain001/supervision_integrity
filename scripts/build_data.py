"""Build data/ from the survey's LaTeX sources.

Run by the authors only: `uv run --group build scripts/build_data.py --paper-dir ..`.
It parses Tables 1, 4, 5 and 7 of main.tex, the bibliography, and the budget figure script,
joins scripts/evaluations.csv (the evidence behind Table 2), and fetches abstracts once from
Semantic Scholar. Readers never need it: data/ is committed.
"""

import argparse
import ast
import csv
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

from pylatexenc.latex2text import LatexNodes2Text

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "data"
CACHE = HERE / "cache" / "s2.json"
S2 = "https://api.semanticscholar.org/graph/v1/paper/search/match?fields=title,abstract,externalIds,url&query="

ATTACK_GROUPS = {"Annotation source": "source", "Preference dataset": "dataset", "Reward or verification channel": "channel"}
DEFENSE_GROUPS = {"Annotation checks": "annotation_checks", "Dataset filtering": "dataset_filtering",
                  "Robust objectives": "robust_objectives", "Channel validation": "channel_validation",
                  "Post-training forensics": "forensics"}
# Table 7 rows follow the order of the citation list in Appendix B.6.
AUDIT_KEYS = ["bai2022training", "stiennon2020learning", "nakano2021webgpt", "ethayarajh2022understanding",
              "kopf2023openassistant", "wang2024helpsteer2", "ji2025pkusaferlhf", "zheng2023judging", "chiang2024chatbot",
              "kirk2024prism", "cui2024ultrafeedback", "zhu2024starling", "lambert2025tulu3", "liu2024skywork"]

# Published titles that differ from the arXiv title, so the title search cannot find them.
ARXIV_IDS = {"fu2025poisonbench": "2410.08811"}

l2t = LatexNodes2Text()
MACROS = [(r"\nr{}", "n/r"), (r"\nr", "n/r"), (r"$^\dagger$", "†"), (r"$^\ast$", "*"), (r"$\leq$", "≤"),
          (r"$\geq$", "≥"), (r"$\times$", "×"), (r"$\to$", "→"), (r"$\chi$", "χ"), ("--", "–")]


def plain(tex: str) -> str:
    tex = re.sub(r"\\texttt\{([^}]*)\}", r"\1", tex).replace(r"\_", "_")
    for a, b in MACROS:
        tex = tex.replace(a, b)
    return re.sub(r"\s+", " ", l2t.latex_to_text(tex)).strip()


def live(text: str) -> str:
    return "\n".join(line for line in text.split("\n") if not line.lstrip().startswith("%"))


def table_body(tex: str, label: str) -> str:
    end = tex.index(r"\label{" + label + "}")
    return tex[tex.rindex(r"\begin{table", 0, end):end]


def rows(body: str, groups: dict[str, str] | None = None) -> list[tuple[str | None, list[str]]]:
    """(group id, cells) for every `\\citet{key} & ... \\\\` row; groups come from \\multicolumn headers."""
    out, group = [], None
    for line in body.split("\\\\"):
        line = line.strip()
        if groups and r"\multicolumn" in line and (m := re.search(r"\\emph\{([^(}]+)", line)):
            group = groups[m.group(1).strip()]
            continue
        if line.startswith(r"\citet{"):
            out.append((group, [c.strip() for c in line.split("&")]))
    return out


def key_of(cell: str) -> str:
    return re.match(r"\\citet\{([^}]+)\}", cell).group(1)


def braced(text: str, start: int) -> tuple[str, int]:
    depth = 0
    for i in range(start, len(text)):
        depth += {"{": 1, "}": -1}.get(text[i], 0)
        if depth == 0:
            return text[start + 1:i], i + 1
    raise ValueError("unbalanced braces")


def parse_bib(text: str) -> dict[str, dict]:
    entries = {}
    for m in re.finditer(r"@(\w+)\s*\{\s*([^,\s]+)\s*,", text):
        body, end = braced(text, text.index("{", m.start()))
        fields = {}
        for f in re.finditer(r"(\w+)\s*=\s*\{", body):
            fields[f.group(1).lower()] = braced(body, f.end() - 1)[0]
        entries[m.group(2)] = {"type": m.group(1).lower(), "fields": fields, "raw": text[m.start():end]}
    return entries


def bbl_labels(bbl: str) -> dict[str, str]:
    """natbib labels such as 'Wang et al. (2024b)' from main.bbl, so names match the paper."""
    labels = {}
    for m in re.finditer(r"\\bibitem\[\{(.*?)\}\]\{([^}]+)\}", bbl, re.S):
        head = re.sub(r"\s+", " ", m.group(1))
        lm = re.match(r"(.*?)\((\d{4})(\{\\natexlab\{(\w)\}\})?\)", head)
        if lm:
            name = plain(lm.group(1).replace("~", " ")).replace("{", "").replace("}", "").strip()
            labels[m.group(2)] = f"{name} ({lm.group(2)}{lm.group(4) or ''})"
    return labels


def authors(field: str) -> list[str]:
    names = []
    for name in re.split(r"\s+and\s+", field):
        last, _, first = name.partition(",")
        names.append(plain(f"{first} {last}" if first else last))
    return [n for n in names if n != "others"]


def venue(fields: dict) -> str:
    v = fields.get("booktitle") or fields.get("journal") or ""
    return plain(v) if v else "arXiv preprint"


def arxiv_id(fields: dict) -> str | None:
    m = re.search(r"(\d{4}\.\d{4,5})", fields.get("journal", "") + " " + fields.get("eprint", ""))
    return m.group(1) if m else None


def norm(t: str) -> str:
    return re.sub(r"[^a-z0-9]", "", t.lower())


def s2_lookup(title: str, cache: dict) -> dict:
    if title in cache:
        return cache[title]
    for attempt in range(4):
        try:
            with urllib.request.urlopen(S2 + urllib.parse.quote(title), timeout=30) as r:
                hit = (json.load(r).get("data") or [{}])[0]
            break
        except Exception:  # rate limit or no match: back off, then give up quietly
            hit = {}
            time.sleep(3 * (attempt + 1))
    same = norm(hit.get("title", "")) == norm(title)  # a fuzzy match can return a different paper
    cache[title] = {"abstract": hit.get("abstract") if same else None, "ids": (hit.get("externalIds") or {}) if same else {},
                    "url": hit.get("url") if same else None, "s2_title": hit.get("title")}
    time.sleep(1.1)
    return cache[title]


def arxiv_abstract(title: str, aid: str | None) -> tuple[str, str | None]:
    """Fallback when Semantic Scholar has no abstract: the arXiv API, by ID or by exact title."""
    q = f"id_list={aid}" if aid else "search_query=" + urllib.parse.quote(f'ti:"{title}"') + "&max_results=3"
    try:
        with urllib.request.urlopen("http://export.arxiv.org/api/query?" + q, timeout=30) as r:
            feed = r.read().decode()
    except Exception:
        return "", aid
    time.sleep(3)
    for entry in re.findall(r"<entry>(.*?)</entry>", feed, re.S):
        t = re.search(r"<title>(.*?)</title>", entry, re.S).group(1)
        if aid or norm(t) == norm(title):
            summary = re.sub(r"\s+", " ", re.search(r"<summary>(.*?)</summary>", entry, re.S).group(1)).strip()
            return summary, aid or re.search(r"abs/(\d{4}\.\d{4,5})", entry).group(1)
    return "", aid


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--paper-dir", type=Path, default=HERE.parents[1])
    ap.add_argument("--bbl", type=Path, help="main.bbl of a compiled build (default: <paper-dir>/main.bbl)")
    args = ap.parse_args()
    tex = live((args.paper_dir / "main.tex").read_text())
    bib = parse_bib((args.paper_dir / "references.bib").read_text())
    labels = bbl_labels((args.bbl or args.paper_dir / "main.bbl").read_text())

    papers: dict[str, dict] = {}
    for stage, c in rows(table_body(tex, "tab:attack-main"), ATTACK_GROUPS):
        papers[key_of(c[0])] = {"role": "attack", "stage": stage, "capability": plain(c[1]), "goal": plain(c[2]),
                                "budget": plain(c[3]), "defense_tested": plain(c[4]) == "yes"}
    for _, c in rows(table_body(tex, "tab:attack-papers")):
        papers[key_of(c[0])].update(first_year=int(c[1]), vector=plain(c[2]), target=plain(c[3]), effect=plain(c[4]))
    for group, c in rows(table_body(tex, "tab:defense-papers"), DEFENSE_GROUPS):
        papers[key_of(c[0])] = {"role": "defense", "intervention": group, "first_year": int(c[1]), "mechanism": plain(c[2]),
                                "tested_against": plain(c[3]), "may_apply": plain(c[4]), "cost": plain(c[5])}

    evaluations = list(csv.DictReader((HERE / "evaluations.csv").open()))
    tested = {e["paper"] for e in evaluations}
    noise_only: dict[str, list[str]] = {}
    for k, p in papers.items():
        if p["role"] == "defense":
            p["scope"] = "attack" if k in tested else "theory" if "(theory)" in p["tested_against"] and "random" not in p["tested_against"] else "noise"
            if p["scope"] == "noise":
                noise_only.setdefault(p["intervention"], []).append(k)

    cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    for k, p in papers.items():
        e = bib[k]["fields"]
        title = plain(e["title"])
        s2 = s2_lookup(title, cache)
        if not s2["abstract"]:
            s2["abstract"], found = arxiv_abstract(re.sub(r"^Poster:\s*", "", title),
                                                   ARXIV_IDS.get(k) or arxiv_id(e) or s2["ids"].get("ArXiv"))
            s2["ids"] = {**s2["ids"], **({"ArXiv": found} if found else {})}
        p.update(key=k, label=labels.get(k, k), title=title, authors=authors(e.get("author", "")), year=int(e["year"]),
                 venue=venue(e), abstract=s2["abstract"] or "", arxiv_id=arxiv_id(e) or s2["ids"].get("ArXiv"),
                 doi=e.get("doi") or s2["ids"].get("DOI"), url=e.get("url") or s2["url"], bibtex=bib[k]["raw"])
    CACHE.parent.mkdir(exist_ok=True)
    CACHE.write_text(json.dumps(cache, indent=1))

    for ev in evaluations:
        assert ev["paper"] in papers, ev["paper"]
    budget_src = (args.paper_dir / "figures" / "gen_fig_budgets.py").read_text()
    figure_rows = ast.literal_eval(re.search(r"PAPERS = (\[.*?\n\])", budget_src, re.S).group(1))
    by_label = {p["label"]: k for k, p in papers.items()}
    budgets = [{"key": by_label[label.rstrip("†")], "policy": pol, "proxy": prx, "other_set": label.endswith("†")}
               for label, _, pol, prx in figure_rows]

    audit = []
    for line, key in zip([r for r in table_body(tex, "tab:provenance-audit").split("\\\\") if "&" in r][1:], AUDIT_KEYS, strict=True):
        cells = [plain(c) for c in line.replace(r"\midrule", "").replace(r"\addlinespace", "").split("&")]
        audit.append({"dataset": cells[0].rstrip("*"), "gated": cells[0].endswith("*"), "key": key, "labelers": cells[1],
                      "annotator_id": cells[2], "date": cells[3], "guideline": cells[4], "upstream": cells[5]})

    OUT.mkdir(exist_ok=True)
    order = sorted(papers.values(), key=lambda p: (p["role"], p["label"]))
    (OUT / "papers.json").write_text(json.dumps(order, indent=1, ensure_ascii=False))
    (OUT / "coverage.json").write_text(json.dumps({"evaluations": evaluations, "noise_only": noise_only}, indent=1))
    (OUT / "budgets.json").write_text(json.dumps(budgets, indent=1))
    (OUT / "provenance.json").write_text(json.dumps(audit, indent=1, ensure_ascii=False))
    n_abs = sum(bool(p["abstract"]) for p in order)
    print(f"{len(order)} papers ({n_abs} with abstracts), {len(evaluations)} evaluations, {len(budgets)} budgets, {len(audit)} datasets")


if __name__ == "__main__":
    main()
