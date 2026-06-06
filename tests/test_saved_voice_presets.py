import json
import sys
from types import MethodType

try:
    import wave_toy
except ImportError:
    sys.modules.pop("wave_toy", None)
    from tests.test_performance_timeline_undo import _install_qt_stubs

    _install_qt_stubs()
    import wave_toy

from tests.test_articulation_chain_card_workflow import _window_with_chain


class _Value:
    def __init__(self, value):
        self._value = value

    def value(self):
        return self._value

    def currentText(self):
        return str(self._value)

    def currentData(self):
        return self._value

    def isChecked(self):
        return bool(self._value)


def _voice_window(tmp_path):
    win = _window_with_chain()
    win.storage = wave_toy.WaveToyStorage(root=tmp_path / "data")
    win.user_presets_path = tmp_path / "sound_experiments.json"
    win.user_preset_layout = None
    win.user_preset_buttons = []
    win.note_combo = _Value("Charles")
    win.pitch_start = _Value(440 * wave_toy.MIDI_SLIDER_SCALE)
    win.pitch_end = _Value(440 * wave_toy.MIDI_SLIDER_SCALE)
    win.octave_slider = _Value(0)
    win.cents_slider = _Value(0)
    win.loud_start = _Value(80)
    win.loud_end = _Value(80)
    win.duration_slider = _Value(1000)
    win.pan_start_slider = _Value(0)
    win.pan_end_slider = _Value(0)
    win.width_slider = _Value(100)
    win.auto_pan_depth_slider = _Value(0)
    win.auto_pan_rate = _Value(1.0)
    win.curve_combo = _Value("linear")
    win.tuning_method_combo = _Value("equal")
    win.tuning_root_combo = _Value("A")
    win.tuning_reference_spin = _Value(440.0)
    win.paulstretch_enabled = _Value(False)
    win.paul_amount_slider = _Value(4)
    win.paul_evolution_slider = _Value(50)
    win.wave_row_order = ["sine"]
    win.user_wave_ids = set()
    win.wave_start_sliders = {"sine": _Value(0)}
    win.wave_end_sliders = {"sine": _Value(0)}
    win.wave_time_sliders = {"sine": _Value(50)}
    win.wave_pan_sliders = {"sine": _Value(0)}
    win.wave_width_sliders = {"sine": _Value(100)}
    win.wave_dance_sliders = {"sine": _Value(0)}
    win.wave_mute_buttons = {"sine": _Value(False)}
    win.wave_follow_pitch_buttons = {"sine": _Value(True)}
    win.wave_note_combos = {"sine": _Value("A")}
    win.wave_octave_spins = {"sine": _Value(4)}
    win.wave_cents_sliders = {"sine": _Value(0)}
    win._wave_shapes_from_ui = MethodType(lambda self: {"sine": "sine"}, win)
    win._solo_wave_from_ui = MethodType(lambda self: None, win)
    win._load_user_preset_buttons = MethodType(lambda self: None, win)
    return win


def test_save_voice_preset_writes_voice_json_under_data_root(tmp_path):
    win = _voice_window(tmp_path)

    path = win._save_voice_preset_document("Charles flat!")

    assert path.parent == win.storage.voices_dir
    assert path.name == "Charles_flat.voice.json"
    assert path.is_file()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["name"] == "Charles_flat"
    assert data["source"] == "Voice Lab"
    assert data["created_at"]
    assert data["updated_at"]
    assert data["recipe_snapshot"]["settings"]
    assert data["wave_settings"]
    assert data["preview_color"]
    assert "rendered_audio" not in data


def test_save_voice_preset_does_not_silently_overwrite_existing_file(tmp_path):
    win = _voice_window(tmp_path)

    first = win._save_voice_preset_document("Charles")
    second = win._save_voice_preset_document("Charles")

    assert first != second
    assert first.name == "Charles.voice.json"
    assert second.name == "Charles_2.voice.json"
    assert first.is_file() and second.is_file()


def test_saved_voice_file_appears_in_voice_source_options(tmp_path):
    win = _voice_window(tmp_path)
    win._save_voice_preset_document("Charles_flat")

    options = win.available_chain_voice_wave_variations()

    assert "Charles_flat" in {option["label"] for option in options}
    assert f"{wave_toy.ARTICULATION_SOURCE_VOICE_PRESET_ID_PREFIX}Charles_flat" in {option["id"] for option in options}


def test_saved_voice_metadata_is_used_as_source_recipe_snapshot(tmp_path):
    win = _voice_window(tmp_path)
    win._save_voice_preset_document("Charles_flat")

    metadata = win._source_metadata_for_variation_id(f"{wave_toy.ARTICULATION_SOURCE_VOICE_PRESET_ID_PREFIX}Charles_flat")

    assert metadata["source_mode"] == wave_toy.ARTICULATION_SOURCE_CURRENT
    assert metadata["source_recipe_snapshot"]["name"] == "Charles_flat"
    assert metadata["source_recipe_snapshot"]["voice_metadata"]["source"] == "Voice Lab"
