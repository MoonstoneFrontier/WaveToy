import sys

try:
    import wave_toy
except ImportError:
    sys.modules.pop("wave_toy", None)
    from tests.test_performance_timeline_undo import _install_qt_stubs

    _install_qt_stubs()
    import wave_toy


class _FakeEvent:
    def __init__(self):
        self.ignored = False
        self.accepted = False

    def ignore(self):
        self.ignored = True

    def accept(self):
        self.accepted = True


class _FakeParentScrollArea:
    def __init__(self):
        self.wheel_events = 0

    def parent(self):
        return None

    def verticalScrollBar(self):
        return object()

    def wheelEvent(self, event):
        self.wheel_events += 1
        event.accept()


class _FakeWheelControl:
    def __init__(self, focused=False, parent=None):
        self._focused = focused
        self._parent = parent
        self.value = 0

    def hasFocus(self):
        return self._focused

    def parent(self):
        return self._parent

    def wheelEvent(self, event):
        if wave_toy._wheel_requires_explicit_focus(self, event):
            return
        self.value += 1
        event.accept()


def _source() -> str:
    return wave_toy.Path(wave_toy.__file__).read_text(encoding="utf-8")


def test_wheel_without_focus_does_not_change_value_and_reaches_parent_scroll_area():
    parent = _FakeParentScrollArea()
    control = _FakeWheelControl(focused=False, parent=parent)
    event = _FakeEvent()

    control.wheelEvent(event)

    assert control.value == 0
    assert event.ignored is True
    assert parent.wheel_events == 1
    assert event.accepted is True


def test_wheel_with_focus_changes_value_and_does_not_scroll_parent():
    parent = _FakeParentScrollArea()
    control = _FakeWheelControl(focused=True, parent=parent)
    event = _FakeEvent()

    control.wheelEvent(event)

    assert control.value == 1
    assert parent.wheel_events == 0
    assert event.accepted is True


def test_no_direct_wheel_capturing_widget_constructors_remain():
    source = _source()

    assert "class NoWheelComboBox(QComboBox):" in source
    assert "class NoWheelSpinBox(QSpinBox):" in source
    assert "class NoWheelDoubleSpinBox(QDoubleSpinBox):" in source
    assert "class NoWheelSlider(QSlider):" in source
    assert "class NoWheelListWidget(QListWidget):" in source
    for forbidden in ("QComboBox(", "QSpinBox(", "QDoubleSpinBox(", "QSlider(", "QListWidget("):
        assert forbidden not in source.replace(f"class NoWheel{forbidden.split('(')[0][1:]}({forbidden[:-1]}):", "")
