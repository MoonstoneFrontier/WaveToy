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
    def __init__(self, x, y, *, button=None, buttons=None, modifiers=0):
        self._pos = _Point(x, y)
        self._button = wave_toy.Qt.LeftButton if button is None else button
        self._buttons = wave_toy.Qt.LeftButton if buttons is None else buttons
        self._modifiers = modifiers
        self.accepted = False

    def button(self):
        return self._button

    def buttons(self):
        return self._buttons

    def pos(self):
        return self._pos

    def position(self):
        return self._pos

    def modifiers(self):
        return self._modifiers

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


def _group_for_canvas(win, clip_ids=(1,), name="communication", group_type="word"):
    clips = [clip for clip in win.timeline_clips if clip.clip_id in set(clip_ids)]
    group = wave_toy.TimelineGroup(
        group_id="group-1",
        name=name,
        group_type=group_type,
        clip_ids=list(clip_ids),
        start_time_seconds=min([clip.start_time_seconds for clip in clips] or [0.0]),
        end_time_seconds=max([clip.end_time_seconds for clip in clips] or [0.0]),
        created_at=123.0,
    )
    win.timeline_groups = [group]
    win.timeline_selected_clip_ids = []
    win.timeline_selected_group_id = None
    return group




def _patch_canvas_clip_at_for_test(canvas):
    def clip_at(self, pos):
        point_x = pos.x() if hasattr(pos, "x") else 0.0
        point_y = pos.y() if hasattr(pos, "y") else 0.0
        for clip in reversed(self.owner.timeline_clips):
            rect = self._clip_hit_rect(clip)
            if rect.left() <= point_x <= rect.right() and rect.top() <= point_y <= rect.bottom():
                return clip
        return None
    canvas._clip_at = MethodType(clip_at, canvas)

def test_group_label_visible(qapp):
    win, canvas, clip = _canvas_for_clip(qapp)
    group = _group_for_canvas(win, [clip.clip_id], name="communication", group_type="word")

    text = canvas._group_label_text(group)
    rect = _Rect(canvas._time_to_x(group.start_time_seconds) + 8, canvas._lane_top(clip.lane) + 6, 220, 24)
    canvas._group_label_rect = MethodType(lambda self, candidate: rect, canvas)

    assert text == "[WORD] communication (1 clips)"
    assert canvas._group_label_rect(group).width() > 0


def test_group_selection_from_canvas(qapp):
    win, canvas, clip = _canvas_for_clip(qapp)
    group = _group_for_canvas(win, [clip.clip_id], name="communication", group_type="word")
    rect = _Rect(canvas._time_to_x(group.start_time_seconds) + 8, canvas._lane_top(clip.lane) + 6, 220, 24)
    canvas._group_label_rect = MethodType(lambda self, candidate: rect, canvas)

    canvas.mousePressEvent(_MouseEvent(rect.center().x(), rect.center().y()))

    assert win.timeline_selected_group_id == group.group_id
    assert win.timeline_selected_clip_ids == [clip.clip_id]
    assert "Group type: word" in win.inspector_text


def test_ctrl_click_multiselect(qapp):
    if wave_toy.Qt.ControlModifier == 0:
        wave_toy.Qt.ControlModifier = 2
    win, canvas, first = _canvas_for_clip(qapp)
    second = _clip(2)
    second.start_time_seconds = first.start_time_seconds + 1.25
    win.timeline_clips.append(second)
    win.timeline_next_clip_id = 3
    _patch_canvas_clip_at_for_test(canvas)

    first_rect = canvas._clip_hit_rect(first)
    second_rect = canvas._clip_hit_rect(second)
    canvas.mousePressEvent(_MouseEvent(first_rect.center().x(), first_rect.center().y()))
    canvas.mouseReleaseEvent(_MouseEvent(first_rect.center().x(), first_rect.center().y()))
    canvas.mousePressEvent(_MouseEvent(second_rect.center().x(), second_rect.center().y(), modifiers=wave_toy.Qt.ControlModifier))

    assert win.timeline_selected_clip_ids == [first.clip_id, second.clip_id]
    assert "2 clips selected" in win.inspector_text


def test_shift_click_range_select(qapp):
    if wave_toy.Qt.ShiftModifier == 0:
        wave_toy.Qt.ShiftModifier = 4
    win, canvas, first = _canvas_for_clip(qapp)
    second = _clip(2)
    second.start_time_seconds = first.start_time_seconds + 1.25
    third = _clip(3)
    third.start_time_seconds = first.start_time_seconds + 2.5
    win.timeline_clips.extend([second, third])
    win.timeline_next_clip_id = 4
    _patch_canvas_clip_at_for_test(canvas)

    first_rect = canvas._clip_hit_rect(first)
    third_rect = canvas._clip_hit_rect(third)
    canvas.mousePressEvent(_MouseEvent(first_rect.center().x(), first_rect.center().y()))
    canvas.mouseReleaseEvent(_MouseEvent(first_rect.center().x(), first_rect.center().y()))
    canvas.mousePressEvent(_MouseEvent(third_rect.center().x(), third_rect.center().y(), modifiers=wave_toy.Qt.ShiftModifier))

    assert win.timeline_selected_clip_ids == [first.clip_id, second.clip_id, third.clip_id]
    assert "3 clips selected" in win.inspector_text
