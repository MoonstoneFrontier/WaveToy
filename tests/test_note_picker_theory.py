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
