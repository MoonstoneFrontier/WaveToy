import sys
from types import MethodType, SimpleNamespace

try:
    import wave_toy
except ImportError:
    sys.modules.pop("wave_toy", None)
    from tests.test_performance_timeline_undo import _install_qt_stubs

    _install_qt_stubs()
    import wave_toy


class _FakeSourceCombo:
    def __init__(self):
        self.values = [wave_toy.ARTICULATION_SOURCE_DEFAULT, wave_toy.ARTICULATION_SOURCE_CURRENT]
        self.current_index = 0
        self.blocked = False

    def findData(self, value):
        try:
            return self.values.index(value)
        except ValueError:
            return -1

    def blockSignals(self, blocked):
        self.blocked = bool(blocked)

    def setCurrentIndex(self, index):
        self.current_index = index

    def currentData(self):
        return self.values[self.current_index]


class _FakeLabel:
    def __init__(self):
        self.text = ""

    def setText(self, text):
        self.text = text


def _window_for_preset_selection():
    win = wave_toy.WaveToyWindow.__new__(wave_toy.WaveToyWindow)
    win.articulation_sliders = {}
    win.articulation_voiced_checkbox = None
    win.articulation_source_combo = _FakeSourceCombo()
    win.articulation_source_badge_label = _FakeLabel()
    win.current_phoneme = wave_toy.ArticulationPhoneme.from_json_dict(
        wave_toy.VOWEL_PRESETS["AH"] | {"name": "AH", "voice_pitch": 220.0, "voice_strength": 0.65}
    )
    win._settings_from_ui = MethodType(lambda self: SimpleNamespace(pitch_start_hz=220.0), win)
    win._source_metadata_for_mode = MethodType(
        lambda self, mode: {
            "source_mode": mode,
            "source_recipe_snapshot": {"source": "classic"},
            "source_start_seconds": 0.0,
            "source_duration_seconds": 0.0,
            "source_pitch_follow": True,
            "source_loop_to_fit": True,
            "source_gain": 1.0,
        },
        win,
    )
    calls = []

    def _preview(self, regenerate=True):
        calls.append(regenerate)
        self._sync_articulation_source_widgets(self.current_phoneme)

    win._update_articulation_preview = MethodType(_preview, win)
    win._phoneme_from_articulation_ui = MethodType(lambda self: self.current_phoneme, win)
    win._preview_calls = calls
    return win


def test_selecting_AH_sets_current_wave_source():
    win = _window_for_preset_selection()

    win._select_vowel_preset("AH")

    assert win.current_phoneme.name == "AH"
    assert win.current_phoneme.source_mode == wave_toy.ARTICULATION_SOURCE_CURRENT
    assert win.articulation_source_combo.currentData() == wave_toy.ARTICULATION_SOURCE_CURRENT
    assert win.articulation_source_badge_label.text == wave_toy.articulation_source_badge(wave_toy.ARTICULATION_SOURCE_CURRENT)
    assert win._preview_calls == [False]


def test_selecting_OO_sets_current_wave_source():
    win = _window_for_preset_selection()

    win._select_vowel_preset("OO")

    assert win.current_phoneme.name == "OO"
    assert win.current_phoneme.source_mode == wave_toy.ARTICULATION_SOURCE_CURRENT
    assert win.articulation_source_combo.currentData() == wave_toy.ARTICULATION_SOURCE_CURRENT
    assert win.articulation_source_badge_label.text == wave_toy.articulation_source_badge(wave_toy.ARTICULATION_SOURCE_CURRENT)
    assert win._preview_calls == [False]


def test_reset_voice_returns_default_source():
    win = _window_for_preset_selection()
    win._select_vowel_preset("AH")

    win._reset_current_phoneme_source()

    assert win.current_phoneme.source_mode == wave_toy.ARTICULATION_SOURCE_DEFAULT
    assert win.current_phoneme.source_wave_id is None
    assert win.articulation_source_combo.currentData() == wave_toy.ARTICULATION_SOURCE_DEFAULT
    assert win.articulation_source_badge_label.text == wave_toy.articulation_source_badge(wave_toy.ARTICULATION_SOURCE_DEFAULT)


def test_loading_saved_phoneme_retains_stored_source_information():
    win = _window_for_preset_selection()
    saved = wave_toy.ArticulationPhoneme.from_json_dict(
        wave_toy.VOWEL_PRESETS["AH"] | {"name": "Saved AH", "source_mode": wave_toy.ARTICULATION_SOURCE_DEFAULT}
    )

    win._load_saved_phoneme(saved)

    assert win.current_phoneme.name == "Saved AH"
    assert win.current_phoneme.source_mode == wave_toy.ARTICULATION_SOURCE_DEFAULT
    assert win.articulation_source_combo.currentData() == wave_toy.ARTICULATION_SOURCE_DEFAULT
