import sys
from types import MethodType

try:
    import wave_toy
except ImportError:
    sys.modules.pop("wave_toy", None)
    from tests.test_performance_timeline_undo import _install_qt_stubs

    _install_qt_stubs()
    import wave_toy

from tests.test_articulation_chain_card_workflow import _phoneme, _window_with_chain


def _source() -> str:
    return wave_toy.Path(wave_toy.__file__).read_text(encoding="utf-8")


def test_fresh_speech_builder_render_and_live_preview_defaults_are_continuous():
    source = _source()

    assert "DEFAULT_CHAIN_PHONEME_DURATION_MS = 250" in source
    assert '"word_render_mode": ARTICULATION_WORD_RENDER_CONTINUOUS' in source
    assert 'current_mode = str(self.articulation_word_render_settings.get("word_render_mode", ARTICULATION_WORD_RENDER_CONTINUOUS))' in source
    assert 'self.articulation_word_render_mode_combo.setCurrentText(current_mode)' in source
    assert 'self.live_preview_enabled = True' in source
    assert 'QCheckBox("Live Preview — debounced, no overlap")' in source


def test_musical_timing_defaults_are_enabled_and_practical_for_speech_testing():
    settings = wave_toy.MusicalTimingSettings()

    assert settings.enabled is True
    assert settings.bpm == 80.0
    assert settings.time_signature_numerator == 4
    assert settings.time_signature_denominator == 4
    assert settings.snap_enabled is True
    assert settings.snap_subdivision == "1/4"
    assert settings.count_in_enabled is True
    assert settings.grid_visible is True
    assert settings.beat_unit_ms == 750.0


def test_continuous_tuning_defaults_and_reset_use_max_requested_values():
    source = _source()

    assert "CONTINUOUS_DEFAULT_FORMANT_INTENSITY = 1.0" in source
    assert "CONTINUOUS_DEFAULT_PITCH_SMOOTHING_MS = 120" in source
    assert '"continuous_formant_intensity": CONTINUOUS_DEFAULT_FORMANT_INTENSITY' in source
    assert '"continuous_pitch_smoothing_ms": CONTINUOUS_DEFAULT_PITCH_SMOOTHING_MS' in source
    assert 'self.continuous_formant_intensity_spin.setValue(CONTINUOUS_DEFAULT_FORMANT_INTENSITY)' in source
    assert 'self.continuous_pitch_smoothing_spin.setValue(CONTINUOUS_DEFAULT_PITCH_SMOOTHING_MS)' in source


def test_new_chain_add_paths_use_shorter_default_duration_without_rewriting_loads():
    win = _window_with_chain()
    win.articulation_word_render_settings = {"auto_apply_current_wave_to_new_chain_items": False}
    win.current_phoneme = _phoneme("M")
    win._phoneme_from_articulation_ui = MethodType(lambda self: _phoneme("M"), win)
    win._settings_from_ui = MethodType(lambda self: type("Settings", (), {"pitch_start_hz": 220.0})(), win)
    win.pitch_start = object()
    win._set_articulation_ui_from_phoneme = MethodType(lambda self, phoneme, regenerate=True: None, win)

    win._add_current_phoneme_to_chain()
    win._add_preset_phoneme_to_chain("AH")

    assert win.articulation_chain_items[-2].duration_ms == wave_toy.DEFAULT_CHAIN_PHONEME_DURATION_MS
    assert win.articulation_chain_items[-1].duration_ms == wave_toy.DEFAULT_CHAIN_PHONEME_DURATION_MS

    loaded = wave_toy.ArticulationChainItem.from_json_dict(_phoneme("Saved").to_json_dict() | {"duration_ms": 640})
    assert loaded.duration_ms == 640


def test_cv_vc_and_saved_phoneme_add_paths_use_default_chain_duration():
    win = _window_with_chain()
    win._set_articulation_ui_from_phoneme = MethodType(lambda self, phoneme, regenerate=True: None, win)

    items = win._cv_vc_items_for_presets([wave_toy.CV_VC_COMBINATION_LIBRARY[0]])
    assert items
    assert all(item.duration_ms == wave_toy.DEFAULT_CHAIN_PHONEME_DURATION_MS for item in items)

    before = len(win.articulation_chain_items)
    win._add_saved_phoneme_to_chain(_phoneme("Saved"))
    assert len(win.articulation_chain_items) == before + 1
    assert win.articulation_chain_items[-1].duration_ms == wave_toy.DEFAULT_CHAIN_PHONEME_DURATION_MS


def test_performance_timing_labels_are_clear_and_not_ambiguous():
    source = _source()

    for text in (
        'QCheckBox("Use Musical Timing")',
        'QCheckBox("Enable Count-in")',
        'QCheckBox("Show Beat Grid")',
        'QCheckBox("Enable Singing Preview")',
        'QLabel("Tempo BPM")',
        'QLabel("Time Signature")',
        'QLabel("Snap to Note Value")',
        'mode_label = QLabel("Word Render Mode")',
        'voice_progress_label = QLabel("Voice Progress")',
    ):
        assert text in source

    assert 'QCheckBox("Musical Timing")' not in source
    assert 'QCheckBox("Singing Preview")' not in source


def test_live_preview_stops_previous_playback_instead_of_overlapping():
    source = _source()

    assert '[WaveToy Live Preview] stop previous target=' in source
    assert 'reason=no_overlap' in source
    assert 'self._stop_phoneme_preview()' in source
    assert 'self._stop_articulation_motion()' in source
