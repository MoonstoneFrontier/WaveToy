import sys
from types import MethodType, SimpleNamespace

import numpy as np

try:
    import wave_toy
except ImportError:
    sys.modules.pop("wave_toy", None)
    from tests.test_performance_timeline_undo import _install_qt_stubs

    _install_qt_stubs()
    import wave_toy


def _clip(clip_id=1):
    audio = np.column_stack([
        np.linspace(-1.0, 1.0, wave_toy.SAMPLE_RATE, dtype=np.float32),
        np.linspace(1.0, -1.0, wave_toy.SAMPLE_RATE, dtype=np.float32),
    ])
    return wave_toy.TimelineClip(
        clip_id=clip_id,
        name=f"Clip {clip_id}",
        audio=audio,
        start_time_seconds=1.0,
        lane=0,
        sample_rate=wave_toy.SAMPLE_RATE,
        source_path="/tmp/source.wav",
        source_type="test_source",
    )


def _window(clips=None):
    win = wave_toy.WaveToyWindow.__new__(wave_toy.WaveToyWindow)
    win.timeline_clips = list(clips or [_clip()])
    win.timeline_lane_count = 4
    win.timeline_selected_clip_id = None
    win.timeline_playhead_seconds = 0.0
    win.timeline_duration_seconds = 0.0
    win.timeline_snap_enabled = False
    win.timeline_snap_seconds = 0.05
    win.timeline_canvas = None
    win.timeline_status_label = None
    win.timeline_inspector_label = SimpleNamespace(setText=lambda text: setattr(win, "inspector_text", text))
    win.timeline_edit_tool = "select"
    win.timeline_tool_buttons = {}
    win.timeline_preserve_pitch = True
    win.timeline_next_clip_id = max([clip.clip_id for clip in win.timeline_clips] or [0]) + 1
    win._timeline_debug = MethodType(lambda self, message: setattr(self, "last_timeline_debug", message), win)
    return win


def test_selecting_clip_sets_selected_clip_id():
    win = _window()

    win._timeline_select_clip(1)

    assert win.timeline_selected_clip_id == 1
    assert "ID: 1" in win.inspector_text


def test_moving_clip_changes_start_time_only():
    win = _window()
    win._timeline_select_clip(1)
    clip = win.timeline_clips[0]
    before_audio = clip.audio.copy()
    before_trim = (clip.trim_start_seconds, clip.trim_end_seconds, clip.playback_rate)

    assert win._timeline_move_selected_clip(2.25, lane=2) is True

    assert clip.start_time_seconds == 2.25
    assert clip.lane == 2
    assert (clip.trim_start_seconds, clip.trim_end_seconds, clip.playback_rate) == before_trim
    np.testing.assert_array_equal(clip.audio, before_audio)


def test_trim_left_changes_start_source_offset_and_duration_correctly():
    win = _window()
    win._timeline_select_clip(1)
    clip = win.timeline_clips[0]

    assert win._timeline_trim_selected_left(1.25) is True

    assert clip.start_time_seconds == 1.25
    assert clip.trim_start_seconds == 0.25
    assert round(clip.duration_seconds, 6) == 0.75
    assert clip.source_path == "/tmp/source.wav"


def test_trim_right_changes_duration_correctly():
    win = _window()
    win._timeline_select_clip(1)
    clip = win.timeline_clips[0]

    assert win._timeline_trim_selected_right(1.6) is True

    assert round(clip.duration_seconds, 6) == 0.6
    assert round(clip.trim_end_seconds, 6) == 0.4
    assert clip.start_time_seconds == 1.0


def test_split_at_playhead_creates_two_valid_adjacent_clips(monkeypatch):
    monkeypatch.setattr(wave_toy.QMessageBox, "information", lambda *args, **kwargs: None, raising=False)
    win = _window()
    win._timeline_select_clip(1)
    win.timeline_playhead_seconds = 1.4

    win._timeline_split_selected()

    left = win._timeline_clip_by_id(1)
    right = win._timeline_clip_by_id(2)
    assert left is not None and right is not None
    assert round(left.end_time_seconds, 6) == round(right.start_time_seconds, 6)
    assert round(left.duration_seconds, 6) == 0.4
    assert round(right.trim_start_seconds, 6) == 0.4
    assert right.source_path == left.source_path


def test_split_outside_clip_is_rejected_safely(monkeypatch):
    messages = []
    monkeypatch.setattr(wave_toy.QMessageBox, "information", lambda *args, **kwargs: messages.append(args), raising=False)
    win = _window()
    win._timeline_select_clip(1)
    win.timeline_playhead_seconds = 3.0

    win._timeline_split_selected()

    assert len(win.timeline_clips) == 1
    assert messages


def test_time_stretch_changes_duration_and_stretch_ratio():
    win = _window()
    win._timeline_select_clip(1)
    clip = win.timeline_clips[0]

    assert win._timeline_stretch_selected_clip(2.0) is True

    assert round(clip.duration_seconds, 6) == 2.0
    assert round(clip.stretch_ratio, 6) == 2.0
    assert round(clip.playback_rate, 6) == 0.5
    assert clip.source_path == "/tmp/source.wav"


def test_edited_clips_persist_through_timeline_save_load_if_supported():
    win = _window()
    win._timeline_select_clip(1)
    win._timeline_trim_selected_left(1.2)
    win._timeline_stretch_selected_clip(1.5)
    clip = win.timeline_clips[0]
    metadata = clip.metadata()

    reloaded = win._rehydrate_timeline_clips([metadata])

    assert len(reloaded) == 1
    restored = reloaded[0]
    assert restored.clip_id == clip.clip_id
    assert restored.start_time_seconds == clip.start_time_seconds
    assert restored.trim_start_seconds == clip.trim_start_seconds
    assert restored.trim_end_seconds == clip.trim_end_seconds
    assert restored.playback_rate == clip.playback_rate
    assert restored.source_path == clip.source_path

class _Point:
    def __init__(self, x, y):
        self._x = float(x)
        self._y = float(y)

    def x(self):
        return self._x

    def y(self):
        return self._y

    def __sub__(self, other):
        return _Point(self._x - other.x(), self._y - other.y())

    def manhattanLength(self):
        return abs(self._x) + abs(self._y)


class _Rect:
    def __init__(self, left, top, width, height):
        self._left = float(left)
        self._top = float(top)
        self._width = float(width)
        self._height = float(height)

    def left(self):
        return self._left

    def right(self):
        return self._left + self._width

    def top(self):
        return self._top

    def bottom(self):
        return self._top + self._height

    def width(self):
        return self._width

    def height(self):
        return self._height

    def center(self):
        return _Point(self._left + self._width / 2.0, self._top + self._height / 2.0)

    def contains(self, point):
        if not hasattr(point, "x") or not hasattr(point, "y"):
            return True
        try:
            return self.left() <= point.x() <= self.right() and self.top() <= point.y() <= self.bottom()
        except TypeError:
            return True


class _MouseEvent:
    def __init__(self, x, y, *, button=None, buttons=None):
        self._pos = _Point(x, y)
        self._button = wave_toy.Qt.LeftButton if button is None else button
        self._buttons = wave_toy.Qt.LeftButton if buttons is None else buttons
        self.accepted = False

    def button(self):
        return self._button

    def buttons(self):
        return self._buttons

    def pos(self):
        return self._pos

    def position(self):
        return self._pos

    def accept(self):
        self.accepted = True


def _window_for_canvas():
    win = _window()
    win.timeline_status_label = SimpleNamespace(setText=lambda text: setattr(win, "status_text", text))
    win.timeline_mix_dirty = False
    win.timeline_lane_count = 4
    return win


def _canvas_for_clip(qapp, *, tool="select"):
    if wave_toy.Qt.LeftButton == 0:
        wave_toy.Qt.LeftButton = 1
    if not hasattr(wave_toy.QApplication, "startDragDistance"):
        wave_toy.QApplication.startDragDistance = staticmethod(lambda: 4)
    win = _window_for_canvas()
    win.timeline_edit_tool = tool
    canvas = wave_toy.TimelineCanvas(win)
    win.timeline_canvas = canvas

    def hit_rect(self, clip):
        return _Rect(
            self._time_to_x(clip.start_time_seconds),
            self._lane_top(clip.lane) + 10,
            max(24.0, clip.duration_seconds / self.seconds_per_pixel),
            92.0,
        )

    canvas._clip_hit_rect = MethodType(hit_rect, canvas)
    canvas._clip_rect = MethodType(hit_rect, canvas)
    canvas._refresh_size()
    return win, canvas, win.timeline_clips[0]


def test_mouse_clicking_clip_selects_it_and_updates_inspector(qapp):
    win, canvas, clip = _canvas_for_clip(qapp)
    rect = canvas._clip_hit_rect(clip)

    canvas.mousePressEvent(_MouseEvent(rect.center().x(), rect.center().y()))
    canvas.mouseReleaseEvent(_MouseEvent(rect.center().x(), rect.center().y()))

    assert win.timeline_selected_clip_id == clip.clip_id
    assert canvas.selected_clip_id == clip.clip_id
    assert "ID: 1" in win.inspector_text


def test_mouse_dragging_clip_body_moves_clip_and_updates_inspector(qapp):
    win, canvas, clip = _canvas_for_clip(qapp)
    rect = canvas._clip_hit_rect(clip)
    start_x = rect.center().x()
    y = rect.center().y()

    canvas.mousePressEvent(_MouseEvent(start_x, y))
    canvas.mouseMoveEvent(_MouseEvent(start_x + 120, y, buttons=wave_toy.Qt.LeftButton))

    assert clip.start_time_seconds > 1.0
    assert "Start time:" in win.inspector_text
    assert win.timeline_mix_dirty is False  # dirty is committed on release, not while previewing the drag

    canvas.mouseReleaseEvent(_MouseEvent(start_x + 120, y))

    assert win.timeline_mix_dirty is True


def test_mouse_trim_handle_drag_changes_source_offset_and_inspector(qapp):
    win, canvas, clip = _canvas_for_clip(qapp, tool="trim")
    rect = canvas._clip_hit_rect(clip)
    left_x = rect.left()
    y = rect.center().y()

    canvas.mousePressEvent(_MouseEvent(left_x, y))
    canvas.mouseMoveEvent(_MouseEvent(left_x + 30, y, buttons=wave_toy.Qt.LeftButton))

    assert clip.trim_start_seconds > 0.0
    assert clip.start_time_seconds > 1.0
    assert "Source offset:" in win.inspector_text

    canvas.mouseReleaseEvent(_MouseEvent(left_x + 30, y))
    assert win.timeline_mix_dirty is True


def test_mouse_stretch_handle_drag_changes_duration_and_inspector(qapp):
    win, canvas, clip = _canvas_for_clip(qapp, tool="stretch")
    rect = canvas._clip_hit_rect(clip)
    right_x = rect.right()
    y = rect.center().y()

    canvas.mousePressEvent(_MouseEvent(right_x, y))
    canvas.mouseMoveEvent(_MouseEvent(right_x + 60, y, buttons=wave_toy.Qt.LeftButton))

    assert clip.duration_seconds > 1.0
    assert clip.stretch_ratio > 1.0
    assert "Playback/stretch ratio:" in win.inspector_text

    canvas.mouseReleaseEvent(_MouseEvent(right_x + 60, y))
    assert win.timeline_mix_dirty is True


def test_split_at_playhead_toolbar_action_uses_selected_clip(monkeypatch, qapp):
    monkeypatch.setattr(wave_toy.QMessageBox, "information", lambda *args, **kwargs: None, raising=False)
    win, canvas, clip = _canvas_for_clip(qapp)
    rect = canvas._clip_hit_rect(clip)
    canvas.mousePressEvent(_MouseEvent(rect.center().x(), rect.center().y()))
    canvas.mouseReleaseEvent(_MouseEvent(rect.center().x(), rect.center().y()))
    win.timeline_playhead_seconds = clip.start_time_seconds + 0.5

    win._timeline_split_selected()

    assert len(win.timeline_clips) == 2
    assert win.timeline_selected_clip_id == 2
    assert win.timeline_clips[0].source_path == win.timeline_clips[1].source_path
