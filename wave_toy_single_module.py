#!/usr/bin/env python3
"""
Wave Toy - single-file educational waveform synthesizer GUI.

A kid-friendly Python/PySide6 app for teaching sound waves from first principles.
It generates sine, triangle, sawtooth, and square waves together, with a separate
mixer level for each waveform plus pitch/loudness changes over time.

Dependencies:
    pip install PySide6 numpy

Optional dependency for best playback:
    pip install sounddevice

Run:
    python wave_toy_single_module.py

Notes:
    - WAV export uses only the Python standard library.
    - Playback first tries sounddevice. If unavailable, it falls back to common
      command-line players: paplay, aplay, ffplay, or play.
    - The window uses a conservative default size and normal window flags so it
      should not interfere with the desktop window manager.
"""

from __future__ import annotations

import math
import shutil
import subprocess
import sys
import tempfile
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Tuple

import numpy as np

try:
    import sounddevice as sd
except Exception:  # pragma: no cover - keeps GUI usable without audio backend
    sd = None

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, QTimer
from PySide6.QtGui import QAction, QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSlider,
    QSpinBox,
    QDoubleSpinBox,
    QVBoxLayout,
    QWidget,
)

SAMPLE_RATE = 44_100
MAX_PREVIEW_SECONDS = 8.0

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
NOTE_TO_INDEX = {name: i for i, name in enumerate(NOTE_NAMES)}

WAVE_LABELS = {
    "sine": "Smooth Wave",
    "triangle": "Mountain Wave",
    "sawtooth": "Ramp Wave",
    "square": "Blocky Wave",
}

CURVE_LABELS = {
    "linear": "Steady Change",
    "exponential": "Slow Then Fast",
    "logarithmic": "Fast Then Slow",
}


@dataclass
class SynthSettings:
    wave_start_db: Dict[str, float] | None = None
    wave_end_db: Dict[str, float] | None = None
    wave_delta_time: Dict[str, float] | None = None
    note: str = "A"
    octave: int = 4
    cents: float = 0.0
    use_manual_pitch: bool = False
    pitch_start_hz: float = 440.0
    pitch_end_hz: float = 440.0
    loudness_start: float = 0.4
    loudness_end: float = 0.4
    duration_seconds: float = 1.5
    curve_type: str = "linear"


def midi_note(note: str, octave: int) -> int:
    """Convert note/octave to MIDI note number. C4 is 60, A4 is 69."""
    return 12 * (octave + 1) + NOTE_TO_INDEX[note]


def frequency_from_note(note: str, octave: int, cents: float = 0.0, a4: float = 440.0) -> float:
    base = a4 * (2.0 ** ((midi_note(note, octave) - 69) / 12.0))
    return base * (2.0 ** (cents / 1200.0))


def make_curve(start: float, end: float, samples: int, curve_type: str) -> np.ndarray:
    """Generate a time curve from start to end."""
    if samples <= 1:
        return np.array([end], dtype=np.float64)

    x = np.linspace(0.0, 1.0, samples, dtype=np.float64)

    if curve_type == "linear":
        shaped = x
    elif curve_type == "exponential":
        # Kid-friendly version: gentle ease-in curve. Works for zero and negative values too.
        shaped = x**2.5
    elif curve_type == "logarithmic":
        # Gentle ease-out curve normalized to 0..1.
        shaped = np.log1p(9.0 * x) / np.log(10.0)
    else:
        shaped = x

    return start + (end - start) * shaped


def make_partial_curve(start: float, end: float, total_samples: int, change_samples: int, curve_type: str) -> np.ndarray:
    """Change from start to end for change_samples, then hold the end value."""
    change_samples = max(1, min(int(change_samples), int(total_samples)))
    curve = make_curve(start, end, change_samples, curve_type)
    if change_samples >= total_samples:
        return curve
    hold = np.full(total_samples - change_samples, end, dtype=np.float64)
    return np.concatenate([curve, hold])


def waveform_from_phase(wave_type: str, phase: np.ndarray) -> np.ndarray:
    """Create waveform samples from phase in radians."""
    if wave_type == "sine":
        return np.sin(phase)

    phase_fraction = (phase / (2.0 * np.pi)) % 1.0

    if wave_type == "square":
        return np.where(phase_fraction < 0.5, 1.0, -1.0)
    if wave_type == "sawtooth":
        return 2.0 * phase_fraction - 1.0
    if wave_type == "triangle":
        return 1.0 - 4.0 * np.abs(phase_fraction - 0.5)

    return np.sin(phase)


def db_to_gain(db: float) -> float:
    """Convert dB to linear gain. -60 dB is treated as nearly silent."""
    if db <= -60.0:
        return 0.0
    return 10.0 ** (db / 20.0)


def generate_audio(settings: SynthSettings) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Return mixed audio, time, frequency envelope, loudness envelope."""
    duration = max(0.1, min(float(settings.duration_seconds), MAX_PREVIEW_SECONDS))
    total_samples = int(SAMPLE_RATE * duration)
    time_axis = np.arange(total_samples, dtype=np.float64) / SAMPLE_RATE

    pitch_start = max(1.0, float(settings.pitch_start_hz))
    pitch_end = max(1.0, float(settings.pitch_end_hz))
    loud_start = np.clip(float(settings.loudness_start), 0.0, 1.0)
    loud_end = np.clip(float(settings.loudness_end), 0.0, 1.0)

    freq_env = make_curve(pitch_start, pitch_end, total_samples, settings.curve_type)
    loud_env = make_curve(loud_start, loud_end, total_samples, settings.curve_type)

    # Phase accumulation makes changing pitch sound smooth instead of stepped.
    phase_step = 2.0 * np.pi * freq_env / SAMPLE_RATE
    phase = np.cumsum(phase_step)

    start_levels = settings.wave_start_db or {
        "sine": 0.0,
        "triangle": -60.0,
        "sawtooth": -60.0,
        "square": -60.0,
    }
    end_levels = settings.wave_end_db or dict(start_levels)
    delta_times = settings.wave_delta_time or {
        "sine": duration,
        "triangle": duration,
        "sawtooth": duration,
        "square": duration,
    }

    mixed = np.zeros(total_samples, dtype=np.float64)
    active_gain_total = 0.0
    for wave_type in ["sine", "triangle", "sawtooth", "square"]:
        start_db = float(start_levels.get(wave_type, -60.0))
        end_db = float(end_levels.get(wave_type, start_db))
        change_seconds = max(0.01, min(float(delta_times.get(wave_type, duration)), duration))
        change_samples = int(change_seconds * SAMPLE_RATE)
        db_env = make_partial_curve(start_db, end_db, total_samples, change_samples, settings.curve_type)
        gain_env = np.array([db_to_gain(db) for db in db_env], dtype=np.float64)
        if float(np.max(gain_env)) <= 0.0:
            continue
        mixed += waveform_from_phase(wave_type, phase) * gain_env
        active_gain_total += float(np.max(gain_env))

    # Keep combinations from becoming much louder just because several waves are active.
    if active_gain_total > 1.0:
        mixed /= active_gain_total

    audio = mixed * loud_env

    # Safety limiter. Keeps output comfortable and avoids hard clipping.
    peak = float(np.max(np.abs(audio))) if audio.size else 0.0
    if peak > 0.98:
        audio = audio / peak * 0.98

    return audio.astype(np.float32), time_axis, freq_env, loud_env


def save_wav(path: Path, audio: np.ndarray, sample_rate: int = SAMPLE_RATE) -> None:
    audio16 = np.clip(audio, -1.0, 1.0)
    audio16 = (audio16 * 32767.0).astype(np.int16)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(audio16.tobytes())


class WaveCanvas(QWidget):
    """Big toy-like waveform display."""

    def __init__(self) -> None:
        super().__init__()
        self.setMinimumHeight(260)
        self.audio = np.zeros(1, dtype=np.float32)
        self.freq_env = np.zeros(1, dtype=np.float32)
        self.loud_env = np.zeros(1, dtype=np.float32)
        self.mascot_message = "Pick a wave shape, then press Make Sound!"
        self.animation_phase = 0.0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(50)

    def _tick(self) -> None:
        self.animation_phase = (self.animation_phase + 0.05) % (2.0 * math.pi)
        self.update()

    def set_data(self, audio: np.ndarray, freq_env: np.ndarray, loud_env: np.ndarray, message: str) -> None:
        self.audio = audio if audio.size else np.zeros(1, dtype=np.float32)
        self.freq_env = freq_env if freq_env.size else np.zeros(1, dtype=np.float32)
        self.loud_env = loud_env if loud_env.size else np.zeros(1, dtype=np.float32)
        self.mascot_message = message
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt API
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(12, 12, -12, -12)

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#fff7c7"))
        painter.drawRoundedRect(rect, 28, 28)

        inner = rect.adjusted(28, 52, -28, -36)
        painter.setPen(QPen(QColor("#77c8ff"), 2, Qt.DashLine))
        mid_y = inner.center().y()
        painter.drawLine(inner.left(), mid_y, inner.right(), mid_y)

        self._draw_wave(painter, inner)
        self._draw_mascot(painter, rect)
        self._draw_caption(painter, rect)

    def _downsample(self, data: np.ndarray, points: int) -> np.ndarray:
        if data.size <= points:
            return data
        idx = np.linspace(0, data.size - 1, points).astype(np.int64)
        return data[idx]

    def _draw_wave(self, painter: QPainter, area: QRectF) -> None:
        points = max(20, int(area.width()))
        wave = self._downsample(self.audio, points)
        if wave.size < 2:
            return

        path = QPainterPath()
        amp = area.height() * 0.42
        x_step = area.width() / max(1, wave.size - 1)
        wobble = math.sin(self.animation_phase) * 2.0
        path.moveTo(area.left(), area.center().y() - float(wave[0]) * amp + wobble)

        for i, sample in enumerate(wave[1:], start=1):
            x = area.left() + i * x_step
            y = area.center().y() - float(sample) * amp + wobble
            path.lineTo(QPointF(x, y))

        painter.setPen(QPen(QColor("#ff4fa3"), 6, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.drawPath(path)

    def _draw_mascot(self, painter: QPainter, rect: QRectF) -> None:
        cx = rect.left() + 54
        cy = rect.top() + 42 + math.sin(self.animation_phase) * 3.0
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#5cdb95"))
        painter.drawEllipse(QPointF(cx, cy), 24, 24)
        painter.setBrush(QColor("white"))
        painter.drawEllipse(QPointF(cx - 8, cy - 5), 5, 5)
        painter.drawEllipse(QPointF(cx + 8, cy - 5), 5, 5)
        painter.setBrush(QColor("#222222"))
        painter.drawEllipse(QPointF(cx - 8, cy - 5), 2, 2)
        painter.drawEllipse(QPointF(cx + 8, cy - 5), 2, 2)
        painter.setPen(QPen(QColor("#222222"), 3, Qt.SolidLine, Qt.RoundCap))
        painter.drawArc(QRectF(cx - 10, cy - 2, 20, 14), 200 * 16, 140 * 16)

    def _draw_caption(self, painter: QPainter, rect: QRectF) -> None:
        painter.setPen(QColor("#263238"))
        font = QFont("Arial", 14, QFont.Bold)
        painter.setFont(font)
        text_rect = QRectF(rect.left() + 92, rect.top() + 18, rect.width() - 120, 52)
        painter.drawText(text_rect, Qt.AlignVCenter | Qt.TextWordWrap, self.mascot_message)


class ToyButton(QPushButton):
    def __init__(self, text: str, color: str) -> None:
        super().__init__(text)
        self.setMinimumHeight(58)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(
            f"""
            QPushButton {{
                background: {color};
                color: #1d1d1d;
                border: 4px solid rgba(0, 0, 0, 0.18);
                border-radius: 22px;
                font-size: 20px;
                font-weight: 800;
                padding: 10px 18px;
            }}
            QPushButton:hover {{
                border: 4px solid rgba(0, 0, 0, 0.35);
            }}
            QPushButton:pressed {{
                padding-top: 14px;
            }}
            """
        )


class WaveToyWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Wave Toy - Build Sounds by Shaping Waves")
        self.setWindowFlags(Qt.Window)
        self.resize(960, 640)
        self.setMinimumSize(QSize(720, 520))
        self.current_audio = np.zeros(1, dtype=np.float32)
        self.current_settings = SynthSettings()
        self.wave_start_sliders: Dict[str, QSlider] = {}
        self.wave_end_sliders: Dict[str, QSlider] = {}
        self.wave_time_sliders: Dict[str, QSlider] = {}
        self.wave_start_labels: Dict[str, QLabel] = {}
        self.wave_end_labels: Dict[str, QLabel] = {}
        self.wave_time_labels: Dict[str, QLabel] = {}

        self._build_actions()
        self._build_ui()
        self._apply_style()
        self._sync_note_to_pitch()
        self._generate(update_message=True)

    def _build_actions(self) -> None:
        about = QAction("About Wave Toy", self)
        about.triggered.connect(self._show_about)
        self.menuBar().addMenu("Help").addAction(about)

    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(18, 18, 18, 18)
        outer.setSpacing(14)

        title = QLabel("🌈 Wave Toy")
        title.setObjectName("title")
        subtitle = QLabel("Build sounds by shaping waves! Big controls first, grown-up words second.")
        subtitle.setObjectName("subtitle")
        outer.addWidget(title)
        outer.addWidget(subtitle)

        body = QHBoxLayout()
        body.setSpacing(14)
        outer.addLayout(body, 1)

        left = QVBoxLayout()
        center = QVBoxLayout()
        right = QVBoxLayout()
        body.addLayout(left, 1)
        body.addLayout(center, 2)
        body.addLayout(right, 1)

        wave_box = self._toy_group("1. Mix the Wave Shapes")
        wave_layout = QGridLayout(wave_box)
        wave_layout.addWidget(QLabel("Wave"), 0, 0)
        wave_layout.addWidget(QLabel("Start dB"), 0, 1)
        wave_layout.addWidget(QLabel("End dB"), 0, 2)
        wave_layout.addWidget(QLabel("Change Time"), 0, 3)
        default_start = {
            "sine": 0,
            "triangle": -60,
            "sawtooth": -60,
            "square": -60,
        }
        default_end = dict(default_start)
        for row, wave_type in enumerate(["sine", "triangle", "sawtooth", "square"], start=1):
            ui_row = row * 2 - 1
            name = QLabel(f"{self._wave_icon(wave_type)} {WAVE_LABELS[wave_type]}")

            start_label = QLabel(f"{default_start[wave_type]} dB")
            start_slider = QSlider(Qt.Horizontal)
            start_slider.setRange(-60, 0)
            start_slider.setValue(default_start[wave_type])
            start_slider.setTickInterval(6)
            start_slider.setToolTip("Starting loudness. 0 dB is full volume. -60 dB is silent.")
            start_slider.valueChanged.connect(self._generate)
            start_slider.valueChanged.connect(lambda value, wt=wave_type: self._update_wave_envelope_labels(wt))

            end_label = QLabel(f"{default_end[wave_type]} dB")
            end_slider = QSlider(Qt.Horizontal)
            end_slider.setRange(-60, 0)
            end_slider.setValue(default_end[wave_type])
            end_slider.setTickInterval(6)
            end_slider.setToolTip("Ending loudness after this wave finishes changing.")
            end_slider.valueChanged.connect(self._generate)
            end_slider.valueChanged.connect(lambda value, wt=wave_type: self._update_wave_envelope_labels(wt))

            time_label = QLabel("100%")
            time_slider = QSlider(Qt.Horizontal)
            time_slider.setRange(1, 100)
            time_slider.setValue(100)
            time_slider.setTickInterval(10)
            time_slider.setToolTip("Percent of the clip used to change from Start dB to End dB.")
            time_slider.valueChanged.connect(self._generate)
            time_slider.valueChanged.connect(lambda value, wt=wave_type: self._update_wave_envelope_labels(wt))

            self.wave_start_sliders[wave_type] = start_slider
            self.wave_end_sliders[wave_type] = end_slider
            self.wave_time_sliders[wave_type] = time_slider
            self.wave_start_labels[wave_type] = start_label
            self.wave_end_labels[wave_type] = end_label
            self.wave_time_labels[wave_type] = time_label

            wave_layout.addWidget(name, ui_row, 0, 2, 1)
            wave_layout.addWidget(start_label, ui_row, 1)
            wave_layout.addWidget(start_slider, ui_row + 1, 1)
            wave_layout.addWidget(end_label, ui_row, 2)
            wave_layout.addWidget(end_slider, ui_row + 1, 2)
            wave_layout.addWidget(time_label, ui_row, 3)
            wave_layout.addWidget(time_slider, ui_row + 1, 3)
        left.addWidget(wave_box)

        pitch_box = self._toy_group("2. Choose Pitch")
        pitch_layout = QGridLayout(pitch_box)
        self.note_combo = QComboBox()
        self.note_combo.addItems(NOTE_NAMES)
        self.note_combo.setCurrentText("A")
        self.octave_spin = QSpinBox()
        self.octave_spin.setRange(0, 8)
        self.octave_spin.setValue(4)
        self.cents_spin = QDoubleSpinBox()
        self.cents_spin.setRange(-1200.0, 1200.0)
        self.cents_spin.setSingleStep(5.0)
        self.cents_spin.setSuffix(" cents")
        self.base_pitch_label = QLabel("A4 = 440.00 Hz")
        pitch_layout.addWidget(QLabel("Note"), 0, 0)
        pitch_layout.addWidget(self.note_combo, 0, 1)
        pitch_layout.addWidget(QLabel("Octave"), 1, 0)
        pitch_layout.addWidget(self.octave_spin, 1, 1)
        pitch_layout.addWidget(QLabel("Wiggle"), 2, 0)
        pitch_layout.addWidget(self.cents_spin, 2, 1)
        pitch_layout.addWidget(self.base_pitch_label, 3, 0, 1, 2)
        left.addWidget(pitch_box)

        self.canvas = WaveCanvas()
        center.addWidget(self.canvas, 1)

        explain_box = self._toy_group("What happened?")
        explain_layout = QVBoxLayout(explain_box)
        self.explain_label = QLabel()
        self.explain_label.setWordWrap(True)
        self.explain_label.setObjectName("explain")
        explain_layout.addWidget(self.explain_label)
        center.addWidget(explain_box)

        motion_box = self._toy_group("3. Change Over Time")
        motion_layout = QGridLayout(motion_box)

        self.duration_spin = QDoubleSpinBox()
        self.duration_spin.setRange(0.1, MAX_PREVIEW_SECONDS)
        self.duration_spin.setValue(1.5)
        self.duration_spin.setSingleStep(0.1)
        self.duration_spin.setSuffix(" sec")

        self.duration_slider = QSlider(Qt.Horizontal)
        self.duration_slider.setRange(1, int(MAX_PREVIEW_SECONDS * 10))
        self.duration_slider.setValue(15)
        self.duration_slider.setToolTip("Total length of the sound clip.")
        self.duration_slider.valueChanged.connect(self._sync_duration_slider_to_spin)
        self.duration_spin.valueChanged.connect(self._sync_duration_spin_to_slider)

        self.pitch_start = QDoubleSpinBox()
        self.pitch_start.setRange(1.0, 5000.0)
        self.pitch_start.setValue(440.0)
        self.pitch_start.setSingleStep(5.0)
        self.pitch_start.setSuffix(" Hz")

        self.pitch_end = QDoubleSpinBox()
        self.pitch_end.setRange(1.0, 5000.0)
        self.pitch_end.setValue(440.0)
        self.pitch_end.setSingleStep(5.0)
        self.pitch_end.setSuffix(" Hz")

        self.loud_start = QSlider(Qt.Horizontal)
        self.loud_start.setRange(0, 100)
        self.loud_start.setValue(40)
        self.loud_end = QSlider(Qt.Horizontal)
        self.loud_end.setRange(0, 100)
        self.loud_end.setValue(40)

        self.curve_combo = QComboBox()
        for key, label in CURVE_LABELS.items():
            self.curve_combo.addItem(label, key)

        motion_layout.addWidget(QLabel("Clip Time"), 0, 0)
        motion_layout.addWidget(self.duration_spin, 0, 1)
        motion_layout.addWidget(self.duration_slider, 1, 0, 1, 2)
        motion_layout.addWidget(QLabel("Start Pitch"), 1, 0)
        motion_layout.addWidget(self.pitch_start, 1, 1)
        motion_layout.addWidget(QLabel("End Pitch"), 2, 0)
        motion_layout.addWidget(self.pitch_end, 2, 1)
        motion_layout.addWidget(QLabel("Start Loudness"), 3, 0)
        motion_layout.addWidget(self.loud_start, 3, 1)
        motion_layout.addWidget(QLabel("End Loudness"), 4, 0)
        motion_layout.addWidget(self.loud_end, 4, 1)
        motion_layout.addWidget(QLabel("Change Style"), 5, 0)
        motion_layout.addWidget(self.curve_combo, 5, 1)
        right.addWidget(motion_box)

        preset_box = self._toy_group("Sound Experiments")
        preset_layout = QVBoxLayout(preset_box)
        presets = [
            ("Pure A4", self._preset_pure_a4),
            ("Rocket Pitch 🚀", self._preset_rocket_pitch),
            ("Robot Beep 🤖", self._preset_robot_beep),
            ("Falling Star ⭐", self._preset_falling_star),
            ("Fade-In Mountain 🏔️", self._preset_fade_in_triangle),
        ]
        for label, callback in presets:
            btn = QPushButton(label)
            btn.clicked.connect(callback)
            preset_layout.addWidget(btn)
        right.addWidget(preset_box)
        right.addStretch(1)

        controls = QHBoxLayout()
        outer.addLayout(controls)
        self.make_button = ToyButton("▶ Make Sound!", "#5cdb95")
        self.stop_button = ToyButton("■ Stop!", "#ff6b6b")
        self.save_button = ToyButton("💾 Save My Sound", "#ffd166")
        controls.addWidget(self.make_button, 2)
        controls.addWidget(self.stop_button, 1)
        controls.addWidget(self.save_button, 2)

        self.make_button.clicked.connect(self._play)
        self.stop_button.clicked.connect(self._stop)
        self.save_button.clicked.connect(self._save)

        widgets_to_regenerate = [
            self.note_combo,
            self.octave_spin,
            self.cents_spin,
            self.duration_spin,
            self.pitch_start,
            self.pitch_end,
            self.loud_start,
            self.loud_end,
            self.curve_combo,
        ]
        self.note_combo.currentTextChanged.connect(self._sync_note_to_pitch)
        self.octave_spin.valueChanged.connect(self._sync_note_to_pitch)
        self.cents_spin.valueChanged.connect(self._sync_note_to_pitch)

        for widget in widgets_to_regenerate:
            if isinstance(widget, QComboBox):
                widget.currentIndexChanged.connect(self._generate)
            elif isinstance(widget, QSlider):
                widget.valueChanged.connect(self._generate)
            else:
                widget.valueChanged.connect(self._generate)

    def _toy_group(self, title: str) -> QGroupBox:
        box = QGroupBox(title)
        box.setObjectName("toyGroup")
        return box

    def _wave_icon(self, wave_type: str) -> str:
        return {
            "sine": "〰️",
            "triangle": "🔺",
            "sawtooth": "📐",
            "square": "🧱",
        }.get(wave_type, "〰️")

    def _apply_style(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow {
                background: #7bdff2;
            }
            QLabel#title {
                font-size: 42px;
                font-weight: 900;
                color: #263238;
            }
            QLabel#subtitle {
                font-size: 18px;
                font-weight: 700;
                color: #37474f;
            }
            QGroupBox#toyGroup {
                background: #ffffff;
                border: 5px solid rgba(0, 0, 0, 0.16);
                border-radius: 24px;
                margin-top: 18px;
                padding: 16px;
                font-size: 18px;
                font-weight: 900;
                color: #263238;
            }
            QGroupBox#toyGroup::title {
                subcontrol-origin: margin;
                left: 18px;
                padding: 2px 8px;
                background: #ffffff;
                border-radius: 8px;
            }
            QLabel {
                font-size: 15px;
                font-weight: 700;
                color: #263238;
            }
            QLabel#explain {
                font-size: 17px;
                font-weight: 700;
                color: #263238;
                padding: 10px;
            }
            QComboBox, QSpinBox, QDoubleSpinBox {
                min-height: 36px;
                border: 3px solid rgba(0, 0, 0, 0.18);
                border-radius: 12px;
                padding: 4px 8px;
                font-size: 15px;
                background: #f9fbff;
            }
            QSlider::groove:horizontal {
                height: 16px;
                background: #d7f3ff;
                border-radius: 8px;
            }
            QSlider::handle:horizontal {
                background: #ff4fa3;
                border: 3px solid white;
                width: 28px;
                height: 28px;
                margin: -8px 0;
                border-radius: 14px;
            }
            QRadioButton {
                background: #f3f8ff;
                border-radius: 16px;
                padding: 12px;
                font-size: 18px;
                font-weight: 900;
            }
            QRadioButton:checked {
                background: #ffd166;
            }
            QPushButton {
                min-height: 34px;
                border-radius: 14px;
                border: 3px solid rgba(0, 0, 0, 0.12);
                background: #f1f7ff;
                font-size: 15px;
                font-weight: 800;
                padding: 6px 10px;
            }
            QPushButton:hover {
                background: #e2f2ff;
            }
            """
        )

    def _wave_start_db_from_ui(self) -> Dict[str, float]:
        return {wave_type: float(slider.value()) for wave_type, slider in self.wave_start_sliders.items()}

    def _wave_end_db_from_ui(self) -> Dict[str, float]:
        return {wave_type: float(slider.value()) for wave_type, slider in self.wave_end_sliders.items()}

    def _wave_delta_time_from_ui(self) -> Dict[str, float]:
        duration = self.duration_spin.value()
        return {
            wave_type: duration * float(slider.value()) / 100.0
            for wave_type, slider in self.wave_time_sliders.items()
        }

    def _settings_from_ui(self) -> SynthSettings:
        return SynthSettings(
            wave_start_db=self._wave_start_db_from_ui(),
            wave_end_db=self._wave_end_db_from_ui(),
            wave_delta_time=self._wave_delta_time_from_ui(),
            note=self.note_combo.currentText(),
            octave=self.octave_spin.value(),
            cents=self.cents_spin.value(),
            pitch_start_hz=self.pitch_start.value(),
            pitch_end_hz=self.pitch_end.value(),
            loudness_start=self.loud_start.value() / 100.0,
            loudness_end=self.loud_end.value() / 100.0,
            duration_seconds=self.duration_spin.value(),
            curve_type=self.curve_combo.currentData(),
        )

    def _sync_note_to_pitch(self) -> None:
        hz = frequency_from_note(self.note_combo.currentText(), self.octave_spin.value(), self.cents_spin.value())
        self.base_pitch_label.setText(f"{self.note_combo.currentText()}{self.octave_spin.value()} = {hz:.2f} Hz")
        # Keep both pitch boxes aligned with note selection unless user has intentionally diverged.
        self.pitch_start.blockSignals(True)
        self.pitch_end.blockSignals(True)
        self.pitch_start.setValue(hz)
        self.pitch_end.setValue(hz)
        self.pitch_start.blockSignals(False)
        self.pitch_end.blockSignals(False)
        self._generate()

    def _generate(self, update_message: bool = False) -> None:
        self.current_settings = self._settings_from_ui()
        audio, time_axis, freq_env, loud_env = generate_audio(self.current_settings)
        self.current_audio = audio

        active_waves = [
            WAVE_LABELS[wave_type]
            for wave_type, db in (self.current_settings.wave_start_db or {}).items()
            if db > -60 or (self.current_settings.wave_end_db or {}).get(wave_type, -60) > -60
        ]
        start_pitch = self.current_settings.pitch_start_hz
        end_pitch = self.current_settings.pitch_end_hz
        start_loud = int(self.current_settings.loudness_start * 100)
        end_loud = int(self.current_settings.loudness_end * 100)

        if abs(start_pitch - end_pitch) > 0.5 and start_loud != end_loud:
            msg = "Your sound changes pitch and loudness while it plays!"
        elif abs(start_pitch - end_pitch) > 0.5:
            msg = "The waves squeeze or stretch, so the pitch changes!"
        elif start_loud != end_loud:
            msg = "The wave grows or shrinks, so loudness changes!"
        else:
            msg = f"You are mixing {len(active_waves)} wave shape(s). Move the dB sliders!"

        self.canvas.set_data(audio, freq_env, loud_env, msg)
        self._update_explanation()

    def _update_explanation(self) -> None:
        s = self.current_settings
        curve_name = CURVE_LABELS[s.curve_type]
        active = []
        for wave_type, start_db in (s.wave_start_db or {}).items():
            end_db = (s.wave_end_db or {}).get(wave_type, start_db)
            change_time = (s.wave_delta_time or {}).get(wave_type, s.duration_seconds)
            if start_db > -60 or end_db > -60:
                active.append(f"{WAVE_LABELS[wave_type]} {start_db:.0f}→{end_db:.0f} dB over {change_time:.1f}s")
        active_text = ", ".join(active) if active else "no waves yet"
        self.explain_label.setText(
            f"You are mixing: {active_text}. Pitch means how high or low the sound is. "
            f"Loudness means how tall the whole wave is. Each dB slider controls one ingredient. "
            f"This sound starts at {s.pitch_start_hz:.1f} Hz and ends at {s.pitch_end_hz:.1f} Hz "
            f"using {curve_name.lower()}. Grown-up words: waveform, frequency, decibels, amplitude, envelope."
        )

    def _play(self) -> None:
        self._generate()

        # Preferred path: direct NumPy playback through sounddevice.
        if sd is not None:
            try:
                sd.stop()
                sd.play(self.current_audio, SAMPLE_RATE, blocking=False)
                return
            except Exception:
                # Fall through to command-line players instead of failing.
                pass

        ok, message = self._play_with_system_player()
        if not ok:
            warning_text = (
                "Wave Toy could generate the sound, but could not find an audio player.\n\n"
                "Try one of these on OpenMandriva/Linux:\n\n"
                "sudo dnf install portaudio sounddevice\n"
                "pip install sounddevice\n\n"
                "Or install a command-line player such as pulseaudio-utils, alsa-utils, ffmpeg, or sox.\n\n"
                f"Details: {message}"
            )

            QMessageBox.warning(
                self,
                "Playback is not available",
                warning_text,
            )
            QMessageBox.warning(self, "Playback is not available", warning_text)

    def _play_with_system_player(self) -> Tuple[bool, str]:
        """Fallback playback using common Linux/macOS command-line tools."""
        players = [
            ("paplay", ["paplay"]),
            ("aplay", ["aplay", "-q"]),
            ("ffplay", ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet"]),
            ("play", ["play", "-q"]),
        ]

        found = [(name, cmd) for name, cmd in players if shutil.which(name)]
        if not found:
            return False, "No supported command-line audio player found."

        try:
            temp = tempfile.NamedTemporaryFile(prefix="wave_toy_", suffix=".wav", delete=False)
            temp_path = Path(temp.name)
            temp.close()
            save_wav(temp_path, self.current_audio)
        except Exception as exc:
            return False, f"Could not create temporary WAV file: {exc}"

        name, cmd = found[0]
        try:
            subprocess.Popen(
                [*cmd, str(temp_path)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            return True, f"Playing with {name}."
        except Exception as exc:
            return False, f"Could not launch {name}: {exc}"

    def _stop(self) -> None:
        if sd is not None:
            try:
                sd.stop()
            except Exception:
                pass

    def _save(self) -> None:
        self._generate()
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save My Sound",
            "wave_toy_sound.wav",
            "WAV Audio (*.wav)",
        )
        if not filename:
            return
        path = Path(filename)
        if path.suffix.lower() != ".wav":
            path = path.with_suffix(".wav")
        try:
            save_wav(path, self.current_audio)
        except Exception as exc:
            QMessageBox.warning(self, "Could not save sound", str(exc))
            return
        QMessageBox.information(self, "Saved!", f"Your sound was saved to:\n{path}")

    def _show_about(self) -> None:
        QMessageBox.information(
            self,
            "About Wave Toy",
            "Wave Toy teaches sound waves with playful controls.\n\n"
            "Kid words: pitch, loudness, wave shape.\n"
            "Grown-up words: frequency, amplitude, waveform, envelope.",
        )

    def _preset_pure_a4(self) -> None:
        self._set_wave_levels({"sine": 0, "triangle": -60, "sawtooth": -60, "square": -60})
        self.note_combo.setCurrentText("A")
        self.octave_spin.setValue(4)
        self.cents_spin.setValue(0)
        self.pitch_start.setValue(440)
        self.pitch_end.setValue(440)
        self.loud_start.setValue(35)
        self.loud_end.setValue(35)
        self.duration_spin.setValue(1.5)
        self.curve_combo.setCurrentIndex(0)
        self._generate()

    def _preset_rocket_pitch(self) -> None:
        self._set_wave_levels(
            {"sine": -18, "triangle": -60, "sawtooth": -18, "square": -24},
            {"sine": -30, "triangle": -60, "sawtooth": 0, "square": -36},
            {"sine": 100, "triangle": 100, "sawtooth": 55, "square": 80},
        )
        self.pitch_start.setValue(220)
        self.pitch_end.setValue(880)
        self.loud_start.setValue(30)
        self.loud_end.setValue(45)
        self.duration_spin.setValue(2.2)
        self._set_curve("exponential")
        self._generate()

    def _preset_robot_beep(self) -> None:
        self._set_wave_levels(
            {"sine": -30, "triangle": -60, "sawtooth": -24, "square": 0},
            {"sine": -60, "triangle": -60, "sawtooth": -18, "square": -12},
            {"sine": 35, "triangle": 100, "sawtooth": 70, "square": 20},
        )
        self.pitch_start.setValue(330)
        self.pitch_end.setValue(660)
        self.loud_start.setValue(35)
        self.loud_end.setValue(35)
        self.duration_spin.setValue(0.8)
        self._set_curve("linear")
        self._generate()

    def _preset_falling_star(self) -> None:
        self._set_wave_levels(
            {"sine": 0, "triangle": -18, "sawtooth": -60, "square": -60},
            {"sine": -24, "triangle": -36, "sawtooth": -60, "square": -60},
            {"sine": 100, "triangle": 75, "sawtooth": 100, "square": 100},
        )
        self.pitch_start.setValue(1000)
        self.pitch_end.setValue(180)
        self.loud_start.setValue(45)
        self.loud_end.setValue(10)
        self.duration_spin.setValue(2.5)
        self._set_curve("logarithmic")
        self._generate()

    def _preset_fade_in_triangle(self) -> None:
        self._set_wave_levels(
            {"sine": -60, "triangle": -60, "sawtooth": -60, "square": -60},
            {"sine": -24, "triangle": 0, "sawtooth": -60, "square": -60},
            {"sine": 100, "triangle": 100, "sawtooth": 100, "square": 100},
        )
        self.pitch_start.setValue(261.63)
        self.pitch_end.setValue(261.63)
        self.loud_start.setValue(0)
        self.loud_end.setValue(50)
        self.duration_spin.setValue(2.0)
        self._set_curve("linear")
        self._generate()

    def _set_wave_levels(
        self,
        levels: Dict[str, int],
        end_levels: Dict[str, int] | None = None,
        times: Dict[str, int] | None = None,
    ) -> None:
        end_levels = end_levels or levels
        times = times or {wave_type: 100 for wave_type in ["sine", "triangle", "sawtooth", "square"]}
        for wave_type in ["sine", "triangle", "sawtooth", "square"]:
            for slider_dict, value_dict, default_value in [
                (self.wave_start_sliders, levels, -60),
                (self.wave_end_sliders, end_levels, -60),
                (self.wave_time_sliders, times, 100),
            ]:
                slider = slider_dict[wave_type]
                slider.blockSignals(True)
                slider.setValue(int(value_dict.get(wave_type, default_value)))
                slider.blockSignals(False)
            self._update_wave_envelope_labels(wave_type)
        self._generate()

    def _update_wave_envelope_labels(self, wave_type: str) -> None:
        start_value = self.wave_start_sliders[wave_type].value()
        end_value = self.wave_end_sliders[wave_type].value()
        time_percent = self.wave_time_sliders[wave_type].value()
        self.wave_start_labels[wave_type].setText("Off" if start_value <= -60 else f"{start_value} dB")
        self.wave_end_labels[wave_type].setText("Off" if end_value <= -60 else f"{end_value} dB")
        self.wave_time_labels[wave_type].setText(f"{time_percent}%")

    def _sync_duration_slider_to_spin(self, value: int) -> None:
        self.duration_spin.blockSignals(True)
        self.duration_spin.setValue(value / 10.0)
        self.duration_spin.blockSignals(False)
        self._generate()

    def _sync_duration_spin_to_slider(self, value: float) -> None:
        self.duration_slider.blockSignals(True)
        self.duration_slider.setValue(int(round(value * 10)))
        self.duration_slider.blockSignals(False)
        self._generate()

    def _set_curve(self, curve_type: str) -> None:
        for i in range(self.curve_combo.count()):
            if self.curve_combo.itemData(i) == curve_type:
                self.curve_combo.setCurrentIndex(i)
                return


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Wave Toy")
    window = WaveToyWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

