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
