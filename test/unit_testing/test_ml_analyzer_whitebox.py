import os
import builtins
from types import SimpleNamespace
from unittest.mock import mock_open

import pandas as pd
import pytest

import modules.analyzer.ml_analyzer as ml_module
from modules.analyzer.ml_analyzer import MLAnalyzer
from modules.analyzer.ml_roles import AnalyzerRole


class DummyAnalyzer(MLAnalyzer):
    """Concrete analyzer per testare i metodi base isolandoli dalle dipendenze."""

    def check_library(self, file, **kwargs):
        return [], [], []


@pytest.fixture
def to_csv_spy(monkeypatch):
    """
    Intercetta TUTTE le chiamate a DataFrame.to_csv (sia results.csv che metrics.csv),
    evitando IO reale e permettendo assert sui path.
    """
    calls = []

    def fake_to_csv(self, path, *args, **kwargs):
        calls.append(path)

    monkeypatch.setattr(pd.DataFrame, "to_csv", fake_to_csv, raising=True)
    return calls


# -----------------------
# analyze_single_file (4 path)
# 1. File non esiste (os.path.isfile == False) → early return
# 2. Errore in open/read (eccezione in open) → return con libs/keywords ma metriche a 0
# 3. Open ok, eccezione in CC e MI (cc_visit e mi_visit falliscono) + keywords non vuote → rami “except” + ramo if keywords
# 4. Tutto ok, keywords vuote (cc_visit e mi_visit ok) → ramo if keywords falso
# -----------------------


def test_analyze_single_file_not_a_file(monkeypatch):
    analyzer = DummyAnalyzer(role=AnalyzerRole.PRODUCER)

    monkeypatch.setattr(ml_module.os.path, "isfile", lambda _: False)

    libs, keywords, load_kw, cc_blocks, mi, sloc = analyzer.analyze_single_file(
        "X.py", "repo"
    )
    assert libs == []
    assert keywords == []
    assert load_kw == []
    assert cc_blocks == []
    assert mi == 0
    assert sloc == 0


def test_analyze_single_file_open_error(monkeypatch):
    analyzer = DummyAnalyzer(role=AnalyzerRole.PRODUCER)

    monkeypatch.setattr(ml_module.os.path, "isfile", lambda _: True)

    # check_library avviene PRIMA di open: vogliamo verificare che torni comunque libs/keywords
    expected_libs = ["torch"]
    expected_keywords = [{"library": "torch", "keyword": "fit", "line_number": 10}]
    expected_load = ["load_model"]

    monkeypatch.setattr(
        analyzer,
        "check_library",
        lambda *_args, **_kw: (expected_libs, expected_keywords, expected_load),
    )

    def raising_open(*_a, **_kw):
        raise Exception("boom")

    monkeypatch.setattr(builtins, "open", raising_open)

    libs, keywords, load_kw, cc_blocks, mi, sloc = analyzer.analyze_single_file(
        "X.py", "repo"
    )
    assert libs == expected_libs
    assert keywords == expected_keywords
    assert load_kw == expected_load
    assert cc_blocks == []
    assert mi == 0
    assert sloc == 0


def test_analyze_single_file_cc_mi_exceptions_keywords_true(monkeypatch):
    analyzer = DummyAnalyzer(role=AnalyzerRole.PRODUCER)

    monkeypatch.setattr(ml_module.os.path, "isfile", lambda _: True)

    expected_libs = ["sklearn"]
    expected_keywords = [{"library": "sklearn", "keyword": "fit", "line_number": 1}]
    monkeypatch.setattr(
        analyzer,
        "check_library",
        lambda *_a, **_kw: (expected_libs, expected_keywords, []),
    )

    code = "a = 1\n# comment\n\nb = 2\n"
    monkeypatch.setattr(builtins, "open", mock_open(read_data=code))

    # Forziamo i rami di eccezione in CC e MI
    def cc_raises(_code):
        raise Exception("cc fail")

    def mi_raises(_code, multi=False):
        raise Exception("mi fail")

    monkeypatch.setattr(ml_module, "cc_visit", cc_raises)
    monkeypatch.setattr(ml_module, "mi_visit", mi_raises)

    libs, keywords, load_kw, cc_blocks, mi, sloc = analyzer.analyze_single_file(
        "X.py", "repo"
    )

    assert libs == expected_libs
    assert keywords == expected_keywords
    assert load_kw == []
    assert cc_blocks == []  # perché cc_visit ha lanciato eccezione
    assert mi == 0  # perché mi_visit ha lanciato eccezione
    assert sloc == 2  # conta solo righe non vuote e non commento: a=1, b=2


def test_analyze_single_file_success_keywords_false(monkeypatch):
    analyzer = DummyAnalyzer(role=AnalyzerRole.PRODUCER)

    monkeypatch.setattr(ml_module.os.path, "isfile", lambda _: True)
    monkeypatch.setattr(
        analyzer, "check_library", lambda *_a, **_kw: (["x"], [], [])
    )  # keywords vuote

    code = "a = 1\n# comment\n\nb = 2\n"
    monkeypatch.setattr(builtins, "open", mock_open(read_data=code))

    dummy_cc = [SimpleNamespace(complexity=3)]
    monkeypatch.setattr(ml_module, "cc_visit", lambda _code: dummy_cc)
    monkeypatch.setattr(ml_module, "mi_visit", lambda _code, multi=False: 42.0)

    libs, keywords, load_kw, cc_blocks, mi, sloc = analyzer.analyze_single_file(
        "X.py", "repo"
    )

    assert libs == ["x"]
    assert keywords == []
    assert load_kw == []
    assert cc_blocks == dummy_cc
    assert mi == 42.0
    assert sloc == 2


# -----------------------
# analyze_project (2 path)
# 1. Role = METRICS, nello stesso giro di os.walk includi:
#   un file non valido → ramo continue
#   un file valido con keywords sì e sloc>0 → crea righe + metrics (sloc branch True)
#   un file valido con keywords no e sloc==0 → metrics ma sloc branch False → df non vuoto ⇒ ramo df.to_csv
# 2. Role != METRICS e nessuna keyword → ramo role-metrics falso + df.empty vero (niente CSV)
# -----------------------


def test_analyze_project_metrics_mixed_files(monkeypatch, to_csv_spy):
    analyzer = DummyAnalyzer(role=AnalyzerRole.METRICS)

    # os.walk controllato
    monkeypatch.setattr(
        ml_module.os, "walk", lambda _repo: [("ROOT", [], ["a.py", "b.txt", "c.py"])]
    )

    # un file non valido -> continue
    def fake_is_valid_file(filename, _filters):
        return filename.endswith(".py")

    monkeypatch.setattr(
        ml_module.ProjectScanner, "is_valid_file", staticmethod(fake_is_valid_file)
    )

    # analyze_single_file isolato: ritorniamo valori diversi a seconda del file
    def fake_analyze_single_file(file_path, _repo, **_kw):
        base = os.path.basename(file_path)
        if base == "a.py":
            cc = [SimpleNamespace(complexity=2), SimpleNamespace(complexity=3)]
            kw = [{"library": "torch", "keyword": "fit", "line_number": 7}]
            return [], kw, [], cc, 50.0, 10  # sloc>0 -> mi_weighted + sloc_list
        if base == "c.py":
            cc = [SimpleNamespace(complexity=1)]
            return [], [], [], cc, 20.0, 0  # sloc==0 -> niente mi_weighted
        raise AssertionError("Non dovrei arrivare qui (b.txt dovrebbe essere filtrato)")

    monkeypatch.setattr(analyzer, "analyze_single_file", fake_analyze_single_file)

    df, all_cc, mi_weighted, sloc_list = analyzer.analyze_project(
        repo="REPO", project="P", directory="D", output_folder="OUT"
    )

    # Metriche raccolte
    assert all_cc == [2, 3, 1]
    assert mi_weighted == [(50.0, 10)]
    assert sloc_list == [10]


def test_analyze_project_non_metrics_df_empty(monkeypatch, to_csv_spy):
    analyzer = DummyAnalyzer(role=AnalyzerRole.PRODUCER)

    monkeypatch.setattr(
        ml_module.os, "walk", lambda _repo: [("ROOT", [], ["a.py", "b.txt"])]
    )

    monkeypatch.setattr(
        ml_module.ProjectScanner,
        "is_valid_file",
        staticmethod(lambda filename, _filters: filename.endswith(".py")),
    )

    # Nessuna keyword -> df vuoto
    monkeypatch.setattr(
        analyzer, "analyze_single_file", lambda *_a, **_kw: ([], [], [], [], 0, 1)
    )

    df, all_cc, mi_weighted, sloc_list = analyzer.analyze_project(
        repo="REPO", project="P", directory="D", output_folder="OUT"
    )

    assert df.empty
    assert all_cc == []
    assert mi_weighted == []
    assert sloc_list == []
    # df vuoto -> nessun csv
    assert not any(os.path.basename(p).startswith("P_D_ml_") for p in to_csv_spy)


# -----------------------
# analyze_projects_set (2 path)
# 1. Role != METRICS, con:
#   un “project” che non è dir → continue
#   un dir_path che non è dir → continue
#   un dir valido che ritorna df non vuoto → results.csv scritto
# 2. Role = METRICS, con 2 progetti:
#   progetto A: cc/sloc vuoti → cc_avg ramo “else 0” e mi_avg ramo “else 0”
#   progetto B: cc non vuoti e sloc>0 → rami “true” delle medie
#   tutti i df vuoti → niente results.csv
#   ma project_metrics popolato → metrics.csv scritto
# -----------------------


def test_analyze_projects_set_non_metrics_writes_results(monkeypatch, to_csv_spy):
    analyzer = DummyAnalyzer(role=AnalyzerRole.PRODUCER)

    input_folder = "IN"
    output_folder = "OUT"

    # Struttura: IN -> [projA (dir), not_a_dir (file)]
    # projA -> [sub1 (dir), not_dir (file)]
    def fake_listdir(path):
        if path == input_folder:
            return ["projA", "not_a_dir"]
        if path == os.path.join(input_folder, "projA"):
            return ["sub1", "not_dir"]
        return []

    def fake_isdir(path):
        return path in {
            os.path.join(input_folder, "projA"),
            os.path.join(input_folder, "projA", "sub1"),
        }

    monkeypatch.setattr(ml_module.os, "listdir", fake_listdir)
    monkeypatch.setattr(ml_module.os.path, "isdir", fake_isdir)

    # analyze_project ritorna df non vuoto per sub1
    df_one = pd.DataFrame([{"ProjectName": "projA/sub1", "keyword": "fit"}])

    monkeypatch.setattr(
        analyzer, "analyze_project", lambda *_a, **_kw: (df_one, [], [], [])
    )

    final_df = analyzer.analyze_projects_set(input_folder, output_folder)

    assert not final_df.empty
    # deve scrivere results.csv (non metrics.csv perché role != METRICS)
    assert any(os.path.basename(p) == "results.csv" for p in to_csv_spy)
    assert not any(os.path.basename(p) == "metrics.csv" for p in to_csv_spy)


def test_analyze_projects_set_metrics_writes_metrics_not_results(
    monkeypatch, to_csv_spy
):
    analyzer = DummyAnalyzer(role=AnalyzerRole.METRICS)

    input_folder = "IN"
    output_folder = "OUT"

    # Struttura: IN -> [proj1, proj2] (entrambi dir)
    # ciascuno ha [d1] (dir)
    def fake_listdir(path):
        if path == input_folder:
            return ["proj1", "proj2"]
        if path == os.path.join(input_folder, "proj1"):
            return ["d1"]
        if path == os.path.join(input_folder, "proj2"):
            return ["d1"]
        return ["d1"]

    def fake_isdir(path):
        return path in {
            os.path.join(input_folder, "proj1"),
            os.path.join(input_folder, "proj2"),
            os.path.join(input_folder, "proj1", "d1"),
            os.path.join(input_folder, "proj2", "d1"),
        }

    monkeypatch.setattr(ml_module.os, "listdir", fake_listdir)
    monkeypatch.setattr(ml_module.os.path, "isdir", fake_isdir)

    # Per proj1: cc/sloc vuoti -> medie 0
    # Per proj2: cc e sloc > 0 -> medie non-zero
    empty_df = pd.DataFrame([])

    def fake_analyze_project(_full_dir_path, project, _dir_path, _out, **_kw):
        if project == "proj1":
            return empty_df, [], [], []
        if project == "proj2":
            cc_vals = [1, 2]
            mi_vals = [(30.0, 10)]
            sloc_vals = [10]
            return empty_df, cc_vals, mi_vals, sloc_vals
        raise AssertionError("progetto inatteso")

    monkeypatch.setattr(analyzer, "analyze_project", fake_analyze_project)

    final_df = analyzer.analyze_projects_set(input_folder, output_folder)

    assert final_df.empty  # nessuna keyword -> niente results.csv
    # Deve scrivere metrics.csv (project_metrics non vuoto), ma NON results.csv
    assert any(os.path.basename(p) == "metrics.csv" for p in to_csv_spy)
    assert not any(os.path.basename(p) == "results.csv" for p in to_csv_spy)

    # Assert sui valori metriche calcolate (round a 2 decimali nel codice)
    assert len(analyzer.project_metrics) == 2
    m1 = next(m for m in analyzer.project_metrics if m["ProjectName"] == "proj1")
    m2 = next(m for m in analyzer.project_metrics if m["ProjectName"] == "proj2")

    assert m1["CC_avg"] == 0
    assert m1["MI_avg"] == 0
    assert m2["CC_avg"] == 1.5
    assert m2["MI_avg"] == 30.0
