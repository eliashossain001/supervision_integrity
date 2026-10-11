# Supervision integrity explorer

Interactive companion to the survey *When Supervision Fails: A Survey of Integrity Attacks and Defenses in LLM Alignment*. It covers the 68 surveyed papers, the coverage map (Table 2), the attack budgets (Figure 4), and the provenance audit (Table 7). It runs on a CPU, offline, with no API key.

## Run

```bash
uv run integritymap
```

Then open http://localhost:8501. This needs [uv](https://docs.astral.sh/uv/getting-started/installation/), which also installs Python. The first run installs about 400 MB of packages.

With Docker instead: `docker build -t integritymap . && docker run -p 8501:8501 integritymap`

## Tabs

- **Papers:** search and filter the 68 papers; download them as BibTeX or CSV.
- **Pipeline:** the four supervision stages, who can attack each, and what evidence each hand-off loses.
- **Coverage map:** click a cell of Table 2 to see every evaluation behind it and its outcome.
- **Budgets:** the smallest poisoning budget at which each attack paper reports an effect.
- **Provenance audit:** what 14 public preference datasets record about each label.

## Data

`scripts/build_data.py` builds `data/` from the paper's LaTeX tables; readers do not need to run it. `scripts/evaluations.csv` lists the 73 evaluations behind Table 2, and `uv run pytest` checks that they match Table 6.
