import sys

try:
    import wave_toy
except ImportError:
    sys.modules.pop("wave_toy", None)
    from tests.test_performance_timeline_undo import _install_qt_stubs

    _install_qt_stubs()
    import wave_toy


def test_passive_wheel_widgets_are_defined_for_scroll_capture_policy():
    assert hasattr(wave_toy, "NoWheelComboBox")
    assert hasattr(wave_toy, "PassiveWheelTextEdit")
    assert hasattr(wave_toy, "PassiveWheelTableWidget")


def test_passive_selectors_use_click_focus_and_ignore_unfocused_wheel_events():
    source = wave_toy.Path(wave_toy.__file__).read_text(encoding="utf-8")

    assert "self.setFocusPolicy(Qt.ClickFocus)" in source
    assert "if self.hasFocus():" in source
    assert "event.ignore()" in source


def test_articulation_and_library_passive_controls_use_no_wheel_classes():
    source = wave_toy.Path(wave_toy.__file__).read_text(encoding="utf-8")

    assert "variation_combo = NoWheelComboBox()" in source
    assert "curve_combo = NoWheelComboBox()" in source
    assert "self.articulation_source_combo = NoWheelComboBox()" in source
    assert "self.timeline_stretch_quality_combo = NoWheelComboBox()" in source
    assert "self.asset_library_summary = PassiveWheelTextEdit()" in source
    assert "self.asset_library_table = PassiveWheelTableWidget(0, 6)" in source
