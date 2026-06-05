try:
    import wave_toy
except ImportError:
    import sys
    from tests.test_performance_timeline_undo import _install_qt_stubs

    sys.modules.pop("wave_toy", None)
    _install_qt_stubs()
    import wave_toy


def test_storage_project_path_defaults_to_projects_directory(tmp_path):
    storage = wave_toy.WaveToyStorage(root=tmp_path / "WaveToyData")

    path = storage.default_project_path("Example Project")

    assert path.parent == storage.projects_dir
    assert path.name == "Example_Project.wavetoy-project.json"


def test_old_repo_local_phonemes_are_not_required_for_storage_startup(tmp_path):
    storage = wave_toy.WaveToyStorage(root=tmp_path / "WaveToyData")

    assert storage.phonemes_dir == storage.root / "Phonemes"
    assert storage.phonemes_dir.exists()
