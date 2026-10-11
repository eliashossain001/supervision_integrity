from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parents[1] / "src" / "integritymap" / "app.py")


def count_line(at: AppTest) -> str:
    return next(m.value for m in at.markdown if " of 68 papers" in m.value)


@pytest.fixture
def app():
    at = AppTest.from_file(APP, default_timeout=60).run()
    assert not at.exception
    return at


def test_five_tabs_render(app):
    assert len(app.tabs) >= 5
    assert "68 of 68 papers" in count_line(app)


def test_search_and_role_filter(app):
    app.text_input(key="q").set_value("backdoor").run()
    hits = int(count_line(app).split(">")[1].split()[0])
    assert 0 < hits < 68
    app.segmented_control(key="role").set_value("Defenses").run()
    assert not app.exception
    assert int(count_line(app).split(">")[1].split()[0]) < hits


def test_coverage_cell_selection(app):
    app.selectbox(key="cell").set_value("forensics|channel").run()
    assert not app.exception
    assert any("4</b> evaluations" in m.value for m in app.markdown)
