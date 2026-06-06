import json
import os
from pathlib import Path

try:
    import wave_toy
except ImportError:
    import sys
    from tests.test_performance_timeline_undo import _install_qt_stubs

    sys.modules.pop("wave_toy", None)
    _install_qt_stubs()
    import wave_toy


def test_wavetoy_data_dir_env_overrides_config_and_default(tmp_path, monkeypatch):
    env_root = tmp_path / "env-data"
    config_root = tmp_path / "config-data"
    config_dir = tmp_path / "config"
    config_root.mkdir()
    config_dir.mkdir()
    (config_dir / "settings.json").write_text(json.dumps({"data_root": str(config_root), "version": 1}), encoding="utf-8")

    monkeypatch.setenv("WAVETOY_DATA_DIR", str(env_root))
    monkeypatch.setenv("WAVETOY_CONFIG_DIR", str(config_dir))

    root, source = wave_toy.resolve_wavetoy_data_root()

    assert root == env_root
    assert source == "environment override"


def test_saved_config_data_root_is_used_when_env_absent(tmp_path, monkeypatch):
    config_root = tmp_path / "config-data"
    config_root.mkdir()
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "settings.json").write_text(json.dumps({"data_root": str(config_root), "version": 1}), encoding="utf-8")

    monkeypatch.delenv("WAVETOY_DATA_DIR", raising=False)
    monkeypatch.setenv("WAVETOY_CONFIG_DIR", str(config_dir))

    root, source = wave_toy.resolve_wavetoy_data_root()

    assert root == config_root
    assert source == "saved config"


def test_missing_config_falls_back_without_dialog(tmp_path, monkeypatch):
    monkeypatch.delenv("WAVETOY_DATA_DIR", raising=False)
    monkeypatch.setenv("WAVETOY_CONFIG_DIR", str(tmp_path / "empty-config"))
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    root, source = wave_toy.resolve_wavetoy_data_root()

    assert root == wave_toy.platform_default_wavetoy_data_root()
    assert source == "platform default"
    assert wave_toy.is_headless_wavetoy_session()


def test_storage_layout_is_created_under_selected_root(tmp_path):
    storage = wave_toy.WaveToyStorage(root=tmp_path / "WaveToyData")

    for name in [
        "Projects",
        "Assets",
        "Exports",
        "Cache",
        "Recovery",
        "LegacyImports",
        "Audio",
        "Voices",
        "Chains",
        "Words",
        "Analyses",
        "Phonemes",
        "Animations",
        "Visemes",
    ]:
        assert (storage.root / name).is_dir()


def test_new_project_and_asset_paths_default_under_data_root(tmp_path):
    storage = wave_toy.WaveToyStorage(root=tmp_path / "WaveToyData")
    project_path = storage.default_project_path("My Project")
    asset = wave_toy.AssetLibraryRecord(asset_type="phoneme", name="AH", payload={"name": "AH"})
    asset_path = storage.save_asset(asset)

    assert project_path.parent == storage.projects_dir
    assert asset_path.is_file()
    assert storage.root in asset_path.parents
    assert asset_path.parent == storage.asset_dir("phoneme")


def test_gitignore_contains_generated_data_patterns():
    ignore = Path(".gitignore").read_text(encoding="utf-8")

    for pattern in [
        "/audio_files/",
        "/animations/",
        "/visemes/",
        "/phonemes/",
        "/Chords/",
        "/*.wav",
        "/*.ogg",
        "/*.flac",
        "/*.mp3",
        "/*.wave-toy*.json",
        "/articulation_chain.json",
        "/.wavetoy_speech_cache/",
        "/wave_toy_single_module.py",
        "/task_*.patch",
    ]:
        assert pattern in ignore
