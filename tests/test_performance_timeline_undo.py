import sys
import types

import numpy as np
import pytest


class _QtConstants:
    def __getattr__(self, name):
        return 0


class _DummyQtBase:
    def __init__(self, *args, **kwargs):
        pass

    def __getattr__(self, name):
        return _DummyQtBase()

    def __call__(self, *args, **kwargs):
        return _DummyQtBase()

    def __bool__(self):
        return False

    def __or__(self, other):
        return self

    def __and__(self, other):
        return self

    def __invert__(self):
        return self


class _DummySignal:
    def __init__(self, *args, **kwargs):
        pass

    def connect(self, *args, **kwargs):
        pass

    def emit(self, *args, **kwargs):
        pass


def _install_qt_stubs():
    pyside = types.ModuleType("PySide6")
    qtcore = types.ModuleType("PySide6.QtCore")
    qtgui = types.ModuleType("PySide6.QtGui")
    qtsvg = types.ModuleType("PySide6.QtSvg")
    qtwidgets = types.ModuleType("PySide6.QtWidgets")
    qtcore.Qt = _QtConstants()
    qtcore.Signal = _DummySignal
    for module, names in {
        qtcore: "QEvent QMimeData QPoint QPointF QRect QRectF QSize QTimer QByteArray".split(),
        qtgui: "QAction QColor QDrag QFont QKeySequence QLinearGradient QPainter QPainterPath QPen QPixmap QShortcut".split(),
        qtsvg: "QSvgRenderer".split(),
        qtwidgets: "QApplication QAbstractButton QAbstractSpinBox QCheckBox QComboBox QDialog QFileDialog QGraphicsDropShadowEffect QGridLayout QInputDialog QGroupBox QHBoxLayout QLabel QLayout QLineEdit QListWidget QMainWindow QMessageBox QMenu QProgressDialog QPushButton QScrollArea QAbstractItemView QHeaderView QSlider QStyle QStackedWidget QTabWidget QToolButton QSpinBox QDoubleSpinBox QDockWidget QSizePolicy QTableWidget QTableWidgetItem QTextEdit QVBoxLayout QWidget".split(),
    }.items():
        for name in names:
            setattr(module, name, type(name, (_DummyQtBase,), {}))
    sys.modules.update({
        "PySide6": pyside,
        "PySide6.QtCore": qtcore,
        "PySide6.QtGui": qtgui,
        "PySide6.QtSvg": qtsvg,
        "PySide6.QtWidgets": qtwidgets,
    })


try:
    from wave_toy import (  # noqa: E402
        MusicalTimingSettings,
        PerformanceAsset,
        PerformanceTimelineEngine,
        PitchAutomationPoint,
        SyllableStressMarker,
        TimelineParameterPoint,
        TimelineParameterTrack,
        WaveToyWindow,
        pitch_timeline_track_from_pitch_automation_points,
        stress_timeline_track_from_syllable_stress_markers,
    )
except ImportError:
    sys.modules.pop("wave_toy", None)
    _install_qt_stubs()
    from wave_toy import (  # noqa: E402
        MusicalTimingSettings,
        PerformanceAsset,
        PerformanceTimelineEngine,
        PitchAutomationPoint,
        SyllableStressMarker,
        TimelineParameterPoint,
        TimelineParameterTrack,
        WaveToyWindow,
        pitch_timeline_track_from_pitch_automation_points,
        stress_timeline_track_from_syllable_stress_markers,
    )


def make_harness(tracks=None):
    window = object.__new__(WaveToyWindow)
    window.musical_timing_settings = MusicalTimingSettings()
    window.performance_timeline_engine = PerformanceTimelineEngine(list(tracks or []), window.musical_timing_settings)
    window.timeline_tracks = window.performance_timeline_engine.timeline_tracks
    window.performance_asset = PerformanceAsset(name="Test Performance", timeline_tracks=window.timeline_tracks)
    window.automation_tracks = []
    window.selected_automation_track_id = None
    window.selected_timeline_point_index = None
    window.performance_playhead_ms = 0
    window.pitch_automation_points = []
    window.syllable_stress_markers = []
    window.articulation_word_render_settings = {}
    window.articulation_timeline_canvas = None
    window.articulation_word_render_audio = np.zeros((0, 2), dtype=np.float32)
    window.articulation_word_render_signature = None
    window.articulation_last_word_render_path = None
    window.articulation_last_word_render_created_at = None
    window.current_phoneme = None
    window.project_dirty = False
    window.performance_undo_stack = []
    window.performance_redo_stack = []
    window.performance_undo_stack_limit = 50
    window._performance_pending_transaction = None
    window._performance_restoring_transaction = False
    window._last_performance_transaction_monotonic = 0.0
    window.performance_last_undo_redo_label = "Undo/redo idle"
    window.performance_undo_action = None
    window.performance_redo_action = None

    def mark_project_dirty(self, reason="project change"):
        self.project_dirty = True
        self.last_dirty_reason = reason

    window._mark_project_dirty = types.MethodType(mark_project_dirty, window)
    window._refresh_performance_tables = types.MethodType(lambda self: None, window)
    window._refresh_musical_timing_controls = types.MethodType(lambda self: None, window)
    window._update_articulation_word_status = types.MethodType(lambda self: None, window)
    window._update_articulation_waveform_diagnostics_canvas = types.MethodType(lambda self: None, window)
    window._update_speech_diagnostics_panel = types.MethodType(lambda self, phoneme: None, window)
    return window


def make_track(track_id="track_a"):
    return TimelineParameterTrack(
        track_id=track_id,
        name="Accent",
        target_parameter="accentuation_db",
        points=[TimelineParameterPoint(time_ms=0, value=0.0)],
    )


def transact(window, label, mutation):
    before = window._performance_edit_snapshot()
    mutation()
    window._push_performance_transaction(label, label.lower(), before)


def test_add_track_undo_redo_transaction():
    window = make_harness()
    track = make_track()

    transact(window, "Add Track", lambda: window.performance_timeline_engine.set_tracks([track], reason="test add"))

    assert len(window.performance_timeline_engine.timeline_tracks) == 1
    window._undo_performance_edit()
    assert window.performance_timeline_engine.timeline_tracks == []
    window._redo_performance_edit()
    assert [track.track_id for track in window.performance_timeline_engine.timeline_tracks] == ["track_a"]


def test_delete_track_undo_redo_transaction():
    track = make_track()
    window = make_harness([track])

    transact(window, "Delete Track", lambda: window.performance_timeline_engine.set_tracks([], reason="test delete"))

    assert window.performance_timeline_engine.timeline_tracks == []
    window._undo_performance_edit()
    assert [track.track_id for track in window.performance_timeline_engine.timeline_tracks] == ["track_a"]
    window._redo_performance_edit()
    assert window.performance_timeline_engine.timeline_tracks == []


def test_add_point_undo_redo_transaction():
    track = make_track()
    window = make_harness([track])

    transact(window, "Add Point", lambda: track.points.append(TimelineParameterPoint(time_ms=250, value=3.0)))

    assert len(track.points) == 2
    window._undo_performance_edit()
    assert len(window.performance_timeline_engine.timeline_tracks[0].points) == 1
    window._redo_performance_edit()
    assert [point.time_ms for point in window.performance_timeline_engine.timeline_tracks[0].points] == [0, 250]


def test_delete_point_undo_redo_transaction():
    track = make_track()
    track.points.append(TimelineParameterPoint(time_ms=250, value=3.0))
    window = make_harness([track])

    transact(window, "Delete Point", lambda: track.points.pop())

    assert len(track.points) == 1
    window._undo_performance_edit()
    assert len(window.performance_timeline_engine.timeline_tracks[0].points) == 2
    window._redo_performance_edit()
    assert len(window.performance_timeline_engine.timeline_tracks[0].points) == 1


def test_drag_point_undo_redo_transaction():
    track = make_track()
    window = make_harness([track])

    transact(window, "Move Point", lambda: setattr(track.points[0], "time_ms", 500))

    assert track.points[0].time_ms == 500
    window._undo_performance_edit()
    assert window.performance_timeline_engine.timeline_tracks[0].points[0].time_ms == 0
    window._redo_performance_edit()
    assert window.performance_timeline_engine.timeline_tracks[0].points[0].time_ms == 500


def test_mute_track_undo_redo_transaction():
    track = make_track()
    window = make_harness([track])

    transact(window, "Mute Track", lambda: setattr(track, "muted", True))

    assert track.muted is True
    window._undo_performance_edit()
    assert window.performance_timeline_engine.timeline_tracks[0].muted is False
    window._redo_performance_edit()
    assert window.performance_timeline_engine.timeline_tracks[0].muted is True


def test_rapid_timing_changes_coalesce_into_one_transaction():
    window = make_harness()

    before = window._performance_edit_snapshot()
    window.musical_timing_settings.bpm = 130.0
    window.performance_timeline_engine.set_musical_timing_settings(window.musical_timing_settings)
    window._push_performance_transaction("Musical Timing Change", "musical timing changed", before)
    before = window._performance_edit_snapshot()
    window.musical_timing_settings.bpm = 140.0
    window.performance_timeline_engine.set_musical_timing_settings(window.musical_timing_settings)
    window._push_performance_transaction("Musical Timing Change", "musical timing changed", before)

    assert len(window.performance_undo_stack) == 1
    assert window.performance_undo_stack[0].before_state.musical_timing_settings["bpm"] == 80.0
    assert window.performance_undo_stack[0].after_state.musical_timing_settings["bpm"] == 140.0
    window._undo_performance_edit()
    assert window.musical_timing_settings.bpm == 80.0


def test_bridge_restore_deduplicates_tracks_and_updates_source_marker():
    window = make_harness()
    marker = SyllableStressMarker(marker_id="stress_1", start_ms=0.0, end_ms=100.0, stress_level=0.25)
    window.syllable_stress_markers = [marker]
    original_bridge = stress_timeline_track_from_syllable_stress_markers([marker])
    edited_bridge = stress_timeline_track_from_syllable_stress_markers([marker])
    edited_bridge.points[0].value = 0.9
    snapshot = window._normalized_performance_snapshot(
        window._performance_edit_snapshot().__class__(
            timeline_tracks=[original_bridge.to_json_dict(), edited_bridge.to_json_dict()],
            musical_timing_settings=window.musical_timing_settings.to_json_dict(),
        )
    )

    window._apply_performance_edit_snapshot(snapshot, "restore bridge")

    bridge_tracks = [track for track in window.performance_timeline_engine.timeline_tracks if track.track_id == "stress_bridge_syllable_markers"]
    assert len(bridge_tracks) == 1
    assert window.syllable_stress_markers[0].stress_level == pytest.approx(0.9)


def test_undo_redo_after_project_reload_are_runtime_only():
    original = make_harness()
    track = make_track()
    transact(original, "Add Track", lambda: original.performance_timeline_engine.set_tracks([track], reason="test add"))
    persisted_tracks = [TimelineParameterTrack.from_json_dict(item.to_json_dict()) for item in original.performance_timeline_engine.timeline_tracks]
    reloaded = make_harness(persisted_tracks)

    reloaded._undo_performance_edit()
    assert [track.track_id for track in reloaded.performance_timeline_engine.timeline_tracks] == ["track_a"]
    reloaded._redo_performance_edit()
    assert [track.track_id for track in reloaded.performance_timeline_engine.timeline_tracks] == ["track_a"]
    assert reloaded.performance_undo_stack == []
    assert reloaded.performance_redo_stack == []


class _FakeAction:
    def __init__(self):
        self.text = ""
        self.enabled = None

    def setText(self, text):
        self.text = text

    def setEnabled(self, enabled):
        self.enabled = bool(enabled)


def test_stack_limit_evicts_oldest_transaction_safely():
    window = make_harness()
    window.performance_undo_stack_limit = 3

    for index in range(5):
        track = make_track(f"track_{index}")
        transact(window, f"Add Track {index}", lambda track=track: window.performance_timeline_engine.set_tracks([*window.performance_timeline_engine.timeline_tracks, track], reason="stress add"))

    assert len(window.performance_undo_stack) == 3
    assert [transaction.label for transaction in window.performance_undo_stack] == ["Add Track 2", "Add Track 3", "Add Track 4"]

    window._undo_performance_edit()
    window._undo_performance_edit()
    window._undo_performance_edit()

    assert [track.track_id for track in window.performance_timeline_engine.timeline_tracks] == ["track_0", "track_1"]
    assert window.performance_undo_stack == []
    assert len(window.performance_redo_stack) == 3


def test_redo_stack_clears_after_new_edit_and_labels_update():
    window = make_harness()
    window.performance_undo_action = _FakeAction()
    window.performance_redo_action = _FakeAction()
    first = make_track("first")
    second = make_track("second")
    replacement = make_track("replacement")

    transact(window, "Add First", lambda: window.performance_timeline_engine.set_tracks([first], reason="first"))
    transact(window, "Add Second", lambda: window.performance_timeline_engine.set_tracks([first, second], reason="second"))
    assert window.performance_undo_action.text == "Undo Performance Edit: Add Second"
    assert window.performance_redo_action.text == "Redo Performance Edit"
    assert window.performance_redo_action.enabled is False

    window._undo_performance_edit()
    assert window.performance_redo_action.text == "Redo Performance Edit: Add Second"
    assert window.performance_redo_action.enabled is True

    transact(window, "Add Replacement", lambda: window.performance_timeline_engine.set_tracks([first, replacement], reason="replacement"))

    assert window.performance_redo_stack == []
    assert window.performance_undo_action.text == "Undo Performance Edit: Add Replacement"
    assert window.performance_redo_action.text == "Redo Performance Edit"
    assert window.performance_redo_action.enabled is False


def test_selection_index_clamps_after_point_deletion_restore():
    track = make_track()
    track.points.extend([
        TimelineParameterPoint(time_ms=250, value=2.0),
        TimelineParameterPoint(time_ms=500, value=4.0),
    ])
    window = make_harness([track])
    window.performance_timeline_engine.set_selected_point(track.track_id, 2)

    before = window._performance_edit_snapshot()
    del track.points[2]
    window.performance_timeline_engine.set_selected_point(track.track_id, 2)
    window._push_performance_transaction("Delete Point", "delete selected", before)

    assert window.performance_timeline_engine.selected_point_index == 1
    window._undo_performance_edit()
    assert window.performance_timeline_engine.selected_point_index == 2
    window._redo_performance_edit()
    assert window.performance_timeline_engine.selected_point_index == 1


def test_selection_only_change_does_not_create_transaction():
    track = make_track()
    track.points.append(TimelineParameterPoint(time_ms=250, value=2.0))
    window = make_harness([track])

    before = window._performance_edit_snapshot()
    window.performance_timeline_engine.set_selected_point(track.track_id, 1)
    window._push_performance_transaction("Select Point", "selection only", before)

    assert window.performance_undo_stack == []


def test_no_recursive_transaction_during_undo_restore():
    track = make_track()
    window = make_harness([track])
    transact(window, "Move Point", lambda: setattr(track.points[0], "time_ms", 500))

    original_apply = window._apply_performance_edit_snapshot

    def recursive_apply(snapshot, reason):
        original_apply(snapshot, reason)
        before = window._performance_edit_snapshot()
        window.performance_timeline_engine.mark_tracks_dirty("callback-like dirty")
        window._push_performance_transaction("Recursive Dirty", "callback-like dirty", before)

    window._apply_performance_edit_snapshot = types.MethodType(lambda self, snapshot, reason: recursive_apply(snapshot, reason), window)

    window._undo_performance_edit()

    assert [transaction.label for transaction in window.performance_undo_stack] == []
    assert [transaction.label for transaction in window.performance_redo_stack] == ["Move Point"]


def test_pitch_bridge_restore_deduplicates_tracks_and_updates_source_points():
    window = make_harness()
    pitch_point = PitchAutomationPoint(time_ms=0.0, pitch_hz=220.0, curve="linear", source="manual")
    window.pitch_automation_points = [pitch_point]
    original_bridge = pitch_timeline_track_from_pitch_automation_points([pitch_point])
    edited_bridge = pitch_timeline_track_from_pitch_automation_points([pitch_point])
    edited_bridge.points[0].value = 440.0
    edited_bridge.points[0].time_ms = 125
    snapshot = window._normalized_performance_snapshot(
        window._performance_edit_snapshot().__class__(
            timeline_tracks=[original_bridge.to_json_dict(), edited_bridge.to_json_dict()],
            musical_timing_settings=window.musical_timing_settings.to_json_dict(),
        )
    )

    window._apply_performance_edit_snapshot(snapshot, "restore pitch bridge")

    bridge_tracks = [track for track in window.performance_timeline_engine.timeline_tracks if track.track_id == "pitch_bridge_pitch_curve"]
    assert len(bridge_tracks) == 1
    assert window.pitch_automation_points[0].pitch_hz == pytest.approx(440.0)
    assert window.pitch_automation_points[0].time_ms == pytest.approx(125.0)


def test_timing_coalescing_starts_new_entry_after_window():
    window = make_harness()

    before = window._performance_edit_snapshot()
    window.musical_timing_settings.bpm = 130.0
    window.performance_timeline_engine.set_musical_timing_settings(window.musical_timing_settings)
    window._push_performance_transaction("Musical Timing Change", "musical timing changed", before)

    window._last_performance_transaction_monotonic -= 999.0
    before = window._performance_edit_snapshot()
    window.musical_timing_settings.bpm = 150.0
    window.performance_timeline_engine.set_musical_timing_settings(window.musical_timing_settings)
    window._push_performance_transaction("Musical Timing Change", "musical timing changed", before)

    assert len(window.performance_undo_stack) == 2
    assert window.performance_undo_stack[0].after_state.musical_timing_settings["bpm"] == 130.0
    assert window.performance_undo_stack[1].before_state.musical_timing_settings["bpm"] == 130.0
    assert window.performance_undo_stack[1].after_state.musical_timing_settings["bpm"] == 150.0

    window._undo_performance_edit()
    assert window.musical_timing_settings.bpm == 130.0
    window._redo_performance_edit()
    assert window.musical_timing_settings.bpm == 150.0
