# Supervision integrity explorer

An interactive companion to the survey *When Supervision Fails: A Survey of Integrity Attacks and Defenses in LLM Alignment*. It covers the 68 surveyed papers (28 attacks, 40 defenses), the coverage map of Table 2, and the provenance audit of Appendix B.6. It runs on a CPU, needs no API key, and works offline.

## Run it

1. Install [uv](https://docs.astral.sh/uv/getting-started/installation/). uv also installs Python if needed.
2. In this folder, run:

   ```bash
   uv run integritymap
   ```

3. Open http://localhost:8501.

With Docker instead:

```bash
docker build -t integritymap . && docker run -p 8501:8501 integritymap
```

## Tabs

- **Pipeline:** the four supervision stages. For each stage: who can attack it (A1 to A3), which defenses act there, and which evidence the next hand-off drops. Pick a stage to list its papers.
- **Papers:** keyword search (BM25 over titles, abstracts, and the survey's table entries) with filters for stage, attacker capability, goal, intervention point, and whether a defense was tested against an attack. Each card shows the facts from Tables 1, 4, and 5, the abstract, its evaluations, and its BibTeX. Download the current list as BibTeX or CSV.
- **Coverage map:** Table 2 as a clickable grid. Click a cell to see every evaluation behind it, with its outcome (works, partial, fails) and a one-line note.
- **Budgets:** the smallest poisoning budget at which each attack paper reports its effect (Figure 4 of the paper).
- **Provenance audit:** which of 14 public preference datasets keep the fields needed to trace a label to its source.

## Data

`data/` holds everything the app reads:

- `papers.json`: the 68 papers with the survey's table entries, abstracts, links, and BibTeX.
- `coverage.json`: the 73 evaluations behind Table 2, and the defenses tested only without an adversary.
- `budgets.json` and `provenance.json`: the data of Figure 4 and Table 7.

`scripts/evaluations.csv` records each evaluation by hand, following Appendix B.5. Its counts match Table 6 cell by cell; `tests/test_data.py` checks this. `scripts/build_data.py` rebuilds `data/` from the paper's LaTeX sources and fetches abstracts once from Semantic Scholar and arXiv. Readers do not need to run it.

## Tests

```bash
uv run pytest
```
