import sys

try:
    import wave_toy
except ImportError:
    sys.modules.pop("wave_toy", None)
    from tests.test_performance_timeline_undo import _install_qt_stubs

    _install_qt_stubs()
    import wave_toy


def _source() -> str:
    return wave_toy.Path(wave_toy.__file__).read_text(encoding="utf-8")


def test_top_level_tab_is_voice_lab_not_classic_controls():
    source = _source()

    assert 'self.tabs.addTab(scroll, "Voice Lab")' in source
    assert 'self.tabs.addTab(scroll, "Classic Controls")' not in source
    assert 'title = QLabel("Voice Lab Synthesis")' in source


def test_voice_lab_save_preset_is_distinct_from_save_audio():
    source = _source()

    assert '"Save Voice Preset"' in source
    assert 'def _save_voice_preset' in source
    assert 'self.save_button = make_export_import_button("Save Audio"' in source
    assert 'def _suggested_voice_preset_name' in source
