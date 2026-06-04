import sys

try:
    import wave_toy
except ImportError:
    sys.modules.pop("wave_toy", None)
    from tests.test_performance_timeline_undo import _install_qt_stubs

    _install_qt_stubs()
    import wave_toy


def _display(notes, root="A", spelling="Auto"):
    return wave_toy.display_pitch_class_set(notes, root, spelling)


def test_a_major_scale_returns_expected_pitch_classes_and_names():
    notes = wave_toy.scale_pitch_classes("A", "major")
    assert notes == ["A", "B", "C#", "D", "E", "F#", "G#"]
    assert _display(notes, "A", "Auto") == ["A", "B", "C#", "D", "E", "F#", "G#"]


def test_bb_major_scale_displays_flats_in_auto_mode():
    notes = wave_toy.scale_pitch_classes("Bb", "major")
    assert notes == ["A#", "C", "D", "D#", "F", "G", "A"]
    assert _display(notes, "Bb", "Auto") == ["Bb", "C", "D", "Eb", "F", "G", "A"]


def test_a_natural_minor_returns_expected_notes():
    notes = wave_toy.scale_pitch_classes("A", "natural_minor")
    assert notes == ["A", "B", "C", "D", "E", "F", "G"]
    assert _display(notes, "A", "Auto") == ["A", "B", "C", "D", "E", "F", "G"]


def test_foundational_chords_return_expected_notes():
    assert wave_toy.chord_pitch_classes("A", "major_triad") == ["A", "C#", "E"]
    assert wave_toy.chord_pitch_classes("A", "minor_triad") == ["A", "C", "E"]
    assert wave_toy.chord_pitch_classes("A", "dominant_7") == ["A", "C#", "E", "G"]


def test_scale_and_chord_degrees():
    assert wave_toy.scale_degree_for_note("C#", "A", "major") == 3
    assert wave_toy.scale_degree_for_note("C", "A", "natural_minor") == 3
    assert wave_toy.chord_degree_for_note("E", "A", "major_triad") == 5
    assert wave_toy.scale_degree_for_note("C", "A", "major") is None


def test_display_spelling_respects_sharps_and_flats_without_changing_pitch_classes():
    notes = ["A#", "C#", "D#"]
    assert _display(notes, "A", "Sharps") == ["A#", "C#", "D#"]
    assert _display(notes, "A", "Flats") == ["Bb", "Db", "Eb"]
    assert [wave_toy.normalize_note_name(note) for note in _display(notes, "A", "Flats")] == notes


def test_harmonic_summary_keeps_internal_sharp_pitch_classes():
    summary = wave_toy.harmonic_summary("Bb", ["Bb", "D", "F"])
    assert summary["root"] == "A#"
    assert summary["selected_notes"] == ["A#", "D", "F"]
    assert summary["selected_display"] == ["Bb", "D", "F"]


def test_note_picker_highlight_set_preserves_selected_pitch_class(qapp):
    picker = wave_toy.CircleOfFifthsNotePicker()
    picker.set_note("C#")
    picker.set_highlight_notes(wave_toy.scale_pitch_classes("A", "major"), "A")
    assert picker.selected_note() == "C#"
    assert "C#" in picker.highlighted_notes()
    assert picker.highlight_root() == "A"
