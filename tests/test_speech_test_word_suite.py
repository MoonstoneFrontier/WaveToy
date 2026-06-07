import json
from pathlib import Path


def test_speech_test_word_suite_json_exists_and_has_required_words():
    path = Path("test_assets/speech_test_words.json")

    assert path.is_file()
    data = json.loads(path.read_text(encoding="utf-8"))
    categories = data["categories"]
    all_entries = {entry for words in categories.values() for entry in words}

    for expected in ["strength", "squirrel", "communication", "she sells seashells by the seashore"]:
        assert expected in all_entries


def test_speech_test_word_suite_includes_strength_chain():
    data = json.loads(Path("test_assets/speech_test_words.json").read_text(encoding="utf-8"))
    chains = {entry["label"]: entry["chain"] for entry in data["explicit_phoneme_chains"]}

    assert chains["strength stress"] == ["S", "T", "R", "EE", "NG", "TH"]


def test_speech_test_word_suite_documentation_exists():
    doc = Path("docs/speech_test_word_suite.md").read_text(encoding="utf-8")

    assert "Speech Test Word Suite" in doc
    assert "strength stress" in doc


def test_regression_suite_benchmark_labels_and_status_are_clear():
    source = Path("wave_toy.py").read_text(encoding="utf-8")

    assert 'make_transport_button("▶ Audition Benchmark", self._preview_speech_regression_entry' in source
    assert 'make_primary_action_button("Render Benchmark", self._render_speech_regression_entry' in source
    assert 'self.speech_regression_suite_status_label = QLabel("Benchmark loaded: none' in source
    assert 'message = f"Benchmark loaded: {label}' in source
