import sys

try:
    import wave_toy
except ImportError:
    sys.modules.pop("wave_toy", None)
    from tests.test_performance_timeline_undo import _install_qt_stubs

    _install_qt_stubs()
    import wave_toy


def test_c_sharp_relative_to_a_is_major_third():
    assert wave_toy.interval_theory_name("C#", "A") == "Major Third"
    assert wave_toy.interval_semitones("C#", "A") == 4


def test_c_sharp_relative_to_b_flat_is_minor_third():
    assert wave_toy.interval_theory_name("C#", "Bb") == "Minor Third"
    assert wave_toy.interval_semitones("C#", "Bb") == 3


def test_auto_mode_uses_flats_for_b_flat_oriented_keys():
    assert wave_toy.note_spelling_mode_for_key("Bb", "Auto") == "Flats"
    assert wave_toy.display_note_name("A#", "Bb", "Auto") == "Bb"


def test_manual_spelling_modes_force_enharmonic_names():
    assert wave_toy.display_note_name("A#", "Bb", "Sharps") == "A#"
    assert wave_toy.display_note_name("A#", "A", "Flats") == "Bb"


def test_interval_layout_order_starts_with_home_root():
    assert wave_toy.note_wheel_order("A", wave_toy.NOTE_WHEEL_LAYOUT_INTERVALS) == [
        "A", "A#", "B", "C", "C#", "D", "D#", "E", "F", "F#", "G", "G#"
    ]


def test_circle_of_fifths_layout_preserves_fifths_order():
    assert wave_toy.note_wheel_order("A", wave_toy.NOTE_WHEEL_LAYOUT_FIFTHS) == wave_toy.NOTE_FIFTHS_ORDER


def test_selected_pitch_class_survives_spelling_and_layout_changes():
    note = wave_toy.normalize_note_name("Bb")
    assert note == "A#"
    assert wave_toy.display_note_name(note, "Bb", "Auto") == "Bb"
    assert wave_toy.display_note_name(note, "Bb", "Sharps") == "A#"
    assert note in wave_toy.note_wheel_order("Bb", wave_toy.NOTE_WHEEL_LAYOUT_INTERVALS)
    assert note in wave_toy.note_wheel_order("Bb", wave_toy.NOTE_WHEEL_LAYOUT_FIFTHS)


def test_voice_range_label_changes_with_note_octave_frequency():
    low = wave_toy.voice_register_label_for_frequency(wave_toy.frequency_from_note("C", 2))
    high = wave_toy.voice_register_label_for_frequency(wave_toy.frequency_from_note("C", 6))
    assert low != high
    assert "low" in low.lower()
    assert "high" in high.lower() or "soprano" in high.lower()


def test_home_change_relabels_c_sharp_from_major_to_minor_third():
    before = wave_toy.note_interval_summary("C#", "A", "Auto")
    after = wave_toy.note_interval_summary("C#", "Bb", "Auto")
    assert "Major Third" in before
    assert "Minor Third" in after
    assert before != after


def test_interval_role_color_changes_when_home_changes():
    a_color = wave_toy.note_emotion("C#", "A")["color"]
    bb_color = wave_toy.note_emotion("C#", "Bb")["color"]
    assert wave_toy.interval_role("C#", "A") != wave_toy.interval_role("C#", "Bb")
    assert a_color != bb_color


def test_auto_spelling_display_updates_after_home_key_changes():
    pitch_class = wave_toy.normalize_note_name("A#")
    assert wave_toy.display_note_name(pitch_class, "A", "Auto") == "A#"
    assert wave_toy.display_note_name(pitch_class, "Bb", "Auto") == "Bb"


def test_selected_pitch_class_survives_explicit_spelling_mode_changes():
    pitch_class = wave_toy.normalize_note_name("Bb")
    for spelling_mode in ("Auto", "Sharps", "Flats"):
        displayed = wave_toy.display_note_name(pitch_class, "Bb", spelling_mode)
        assert wave_toy.normalize_note_name(displayed) == pitch_class


def test_selected_pitch_class_survives_layout_mode_changes():
    pitch_class = wave_toy.normalize_note_name("C#")
    for layout_mode in (wave_toy.NOTE_WHEEL_LAYOUT_INTERVALS, wave_toy.NOTE_WHEEL_LAYOUT_FIFTHS):
        assert pitch_class in wave_toy.note_wheel_order("Bb", layout_mode)


def test_interval_wheel_order_starts_with_current_home_after_home_changes():
    assert wave_toy.note_wheel_order("Bb", wave_toy.NOTE_WHEEL_LAYOUT_INTERVALS)[0] == "A#"


def test_visible_dialog_refresh_helper_preserves_selected_pitch_class():
    class FakeCombo:
        def __init__(self, note):
            self.note = note

        def currentText(self):
            return self.note

    class FakePicker:
        def __init__(self):
            self.updated = False

        def update(self):
            self.updated = True

    class FakeDialog:
        def __init__(self):
            self.picker = FakePicker()
            self.calls = []

        def isVisible(self):
            return True

        def refresh_labels(self, selected_note, main_note):
            self.calls.append((wave_toy.normalize_note_name(selected_note), wave_toy.normalize_note_name(main_note)))

    window = object.__new__(wave_toy.WaveToyWindow)
    dialog = FakeDialog()
    window.note_combo = FakeCombo("Bb")
    window.wave_note_combos = {"sine": FakeCombo("C#")}
    window.note_wheel_dialogs = {"sine": dialog}

    wave_toy.WaveToyWindow._refresh_note_wheel_dialogs(window)

    assert dialog.calls == [("C#", "A#")]
    assert dialog.picker.updated is True


def test_voice_range_label_changes_when_frequency_changes():
    low = wave_toy.voice_register_label_for_frequency(70.0)
    high = wave_toy.voice_register_label_for_frequency(1200.0)
    assert low != high


def test_highlight_set_preserves_selected_pitch_class_without_selecting_root(qapp):
    picker = wave_toy.CircleOfFifthsNotePicker()
    picker.set_note("C#")
    picker.set_highlight_notes(["A", "C#", "E"], "A")
    assert picker.selected_note() == "C#"
    assert picker.highlighted_notes() == {"A", "C#", "E"}
    assert picker.highlight_root() == "A"
