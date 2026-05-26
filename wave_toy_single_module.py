#!/usr/bin/env python3
"""
Wave Toy - single-file educational waveform synthesizer GUI.

A kid-friendly Python/PySide6 app for teaching sound waves from first principles.

Features:
- Four waveform mixer: sine, triangle, sawtooth, square
- Per-waveform start dB, end dB, and change-time controls
- Musical note tuning with cents detune
- Pitch and loudness changes over time
- Beginner-mode explanations
- Colorful dimensional stereo waveform viewer
- Stereo pan, width, and auto-pan controls
- Save WAV directly
- Save MP3, OGG, or FLAC through ffmpeg if installed
- Save sidecar recipe metadata as .wave-toy.json
- Saved recipes are added to Sound Experiments

Dependencies:
    pip install PySide6 numpy

Optional for direct playback:
    pip install sounddevice

Optional for MP3/OGG/FLAC export:
    ffmpeg
"""

from __future__ import annotations

import json
import math
import shutil
import subprocess
import sys
import tempfile
import wave
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

try:
    import sounddevice as sd
except Exception:
    sd = None

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, QTimer
from PySide6.QtGui import QAction, QColor, QFont, QKeySequence, QLinearGradient, QPainter, QPainterPath, QPen, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QDoubleSpinBox,
    QVBoxLayout,
    QWidget,
)

SAMPLE_RATE = 44_100
MAX_PREVIEW_SECONDS = 8.0
WAVE_ORDER = ["sine", "triangle", "sawtooth", "square"]

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
    pitch_start_hz: float = 440.0
    pitch_end_hz: float = 440.0
    loudness_start: float = 0.4
    loudness_end: float = 0.4
    duration_seconds: float = 1.5
    curve_type: str = "linear"
    pan_start: float = 0.0
    pan_end: float = 0.0
    stereo_width: float = 0.45
    auto_pan_depth: float = 0.0
    auto_pan_rate: float = 0.50


def midi_note(note: str, octave: int) -> int:
    return 12 * (octave + 1) + NOTE_TO_INDEX[note]


def frequency_from_note(note: str, octave: int, cents: float = 0.0, a4: float = 440.0) -> float:
    base = a4 * (2.0 ** ((midi_note(note, octave) - 69) / 12.0))
    return base * (2.0 ** (cents / 1200.0))


def make_curve(start: float, end: float, samples: int, curve_type: str) -> np.ndarray:
    if samples <= 1:
        return np.array([end], dtype=np.float64)

    x = np.linspace(0.0, 1.0, samples, dtype=np.float64)

    if curve_type == "linear":
        shaped = x
    elif curve_type == "exponential":
        shaped = x**2.5
    elif curve_type == "logarithmic":
        shaped = np.log1p(9.0 * x) / np.log(10.0)
    else:
        shaped = x

    return start + (end - start) * shaped


def make_partial_curve(start: float, end: float, total_samples: int, change_samples: int, curve_type: str) -> np.ndarray:
    change_samples = max(1, min(int(change_samples), int(total_samples)))
    curve = make_curve(start, end, change_samples, curve_type)

    if change_samples >= total_samples:
        return curve

    hold = np.full(total_samples - change_samples, end, dtype=np.float64)
    return np.concatenate([curve, hold])


def waveform_from_phase(wave_type: str, phase: np.ndarray) -> np.ndarray:
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
    if db <= -20.0:
        return 0.0
    return 10.0 ** (db / 20.0)


def equal_power_pan(mono: np.ndarray, pan: np.ndarray) -> np.ndarray:
    pan = np.clip(pan, -1.0, 1.0)
    angle = (pan + 1.0) * (math.pi / 4.0)
    left = mono * np.cos(angle)
    right = mono * np.sin(angle)
    return np.column_stack([left, right])


def generate_audio(settings: SynthSettings) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    duration = max(0.1, min(float(settings.duration_seconds), MAX_PREVIEW_SECONDS))
    total_samples = int(SAMPLE_RATE * duration)

    time_axis = np.arange(total_samples, dtype=np.float64) / SAMPLE_RATE

    pitch_start = max(1.0, float(settings.pitch_start_hz))
    pitch_end = max(1.0, float(settings.pitch_end_hz))
    loud_start = np.clip(float(settings.loudness_start), 0.0, 1.0)
    loud_end = np.clip(float(settings.loudness_end), 0.0, 1.0)

    freq_env = make_curve(pitch_start, pitch_end, total_samples, settings.curve_type)
    loud_env = make_curve(loud_start, loud_end, total_samples, settings.curve_type)

    phase_step = 2.0 * np.pi * freq_env / SAMPLE_RATE
    phase = np.cumsum(phase_step)

    start_levels = settings.wave_start_db or {
        "sine": 0.0,
        "triangle": -20.0,
        "sawtooth": -20.0,
        "square": -20.0,
    }
    end_levels = settings.wave_end_db or dict(start_levels)
    delta_times = settings.wave_delta_time or {wave_type: duration for wave_type in WAVE_ORDER}

    mixed_stereo = np.zeros((total_samples, 2), dtype=np.float64)

    width = np.clip(float(settings.stereo_width), 0.0, 1.0)
    base_pan_offsets = {
        "sine": -0.45 * width,
        "triangle": 0.45 * width,
        "sawtooth": -0.85 * width,
        "square": 0.85 * width,
    }

    pan_base = make_curve(float(settings.pan_start), float(settings.pan_end), total_samples, settings.curve_type)

    auto_depth = np.clip(float(settings.auto_pan_depth), 0.0, 1.0)
    auto_rate = max(0.01, float(settings.auto_pan_rate))
    auto_pan = auto_depth * np.sin(2.0 * np.pi * auto_rate * time_axis)

    active_gain_total = 0.0

    for wave_type in WAVE_ORDER:
        start_db = float(start_levels.get(wave_type, -20.0))
        end_db = float(end_levels.get(wave_type, start_db))

        change_seconds = max(0.01, min(float(delta_times.get(wave_type, duration)), duration))
        change_samples = int(change_seconds * SAMPLE_RATE)

        db_env = make_partial_curve(start_db, end_db, total_samples, change_samples, settings.curve_type)
        gain_env = np.array([db_to_gain(db) for db in db_env], dtype=np.float64)

        if float(np.max(gain_env)) <= 0.0:
            continue

        mono_wave = waveform_from_phase(wave_type, phase) * gain_env
        wave_pan = np.clip(pan_base + auto_pan + base_pan_offsets[wave_type], -1.0, 1.0)
        mixed_stereo += equal_power_pan(mono_wave, wave_pan)
        active_gain_total += float(np.max(gain_env))

    if active_gain_total > 1.0:
        mixed_stereo /= active_gain_total

    audio = mixed_stereo * loud_env[:, None]

    peak = float(np.max(np.abs(audio))) if audio.size else 0.0
    if peak > 0.98:
        audio = audio / peak * 0.98

    return audio.astype(np.float32), time_axis, freq_env, loud_env


def save_wav(path: Path, audio: np.ndarray, sample_rate: int = SAMPLE_RATE) -> None:
    audio = np.asarray(audio)

    if audio.ndim == 1:
        audio = audio[:, None]

    audio16 = np.clip(audio, -1.0, 1.0)
    audio16 = (audio16 * 32767.0).astype(np.int16)

    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(audio16.shape[1])
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio16.tobytes())


def convert_with_ffmpeg(wav_path: Path, output_path: Path) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("MP3/OGG/FLAC export requires ffmpeg. Install ffmpeg or save as WAV instead.")

    cmd = [ffmpeg, "-y", "-loglevel", "error", "-i", str(wav_path), str(output_path)]
    subprocess.run(cmd, check=True)


def save_audio_file(path: Path, audio: np.ndarray, sample_rate: int = SAMPLE_RATE) -> None:
    suffix = path.suffix.lower()

    if suffix == ".wav":
        save_wav(path, audio, sample_rate)
        return

    if suffix in {".mp3", ".ogg", ".flac"}:
        with tempfile.NamedTemporaryFile(prefix="wave_toy_export_", suffix=".wav", delete=False) as temp:
            temp_wav = Path(temp.name)

        try:
            save_wav(temp_wav, audio, sample_rate)
            convert_with_ffmpeg(temp_wav, path)
        finally:
            try:
                temp_wav.unlink()
            except OSError:
                pass
        return

    raise ValueError(f"Unsupported audio format: {suffix}")


class WaveCanvas(QWidget):
    def __init__(self) -> None:
        super().__init__()

        self.setMinimumSize(QSize(420, 300))
        self.audio = np.zeros((1, 2), dtype=np.float32)
        self.freq_env = np.zeros(1, dtype=np.float32)
        self.loud_env = np.zeros(1, dtype=np.float32)
        self.mascot_message = "Move the sliders, then press Make Sound!"
        self.animation_phase = 0.0

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(50)

    def _tick(self) -> None:
        self.animation_phase = (self.animation_phase + 0.05) % (2.0 * math.pi)
        self.update()

    def set_data(self, audio: np.ndarray, freq_env: np.ndarray, loud_env: np.ndarray, message: str) -> None:
        if audio.size:
            audio = np.asarray(audio, dtype=np.float32)
            if audio.ndim == 1:
                audio = np.column_stack([audio, audio])
            self.audio = audio
        else:
            self.audio = np.zeros((1, 2), dtype=np.float32)

        self.freq_env = freq_env if freq_env.size else np.zeros(1, dtype=np.float32)
        self.loud_env = loud_env if loud_env.size else np.zeros(1, dtype=np.float32)
        self.mascot_message = message
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = self.rect().adjusted(12, 12, -12, -12)

        gradient = QLinearGradient(rect.topLeft(), rect.bottomRight())
        gradient.setColorAt(0.0, QColor("#fff7c7"))
        gradient.setColorAt(0.55, QColor("#d7f3ff"))
        gradient.setColorAt(1.0, QColor("#ffd6e7"))

        painter.setPen(Qt.NoPen)
        painter.setBrush(gradient)
        painter.drawRoundedRect(rect, 28, 28)

        inner = rect.adjusted(28, 62, -28, -42)

        self._draw_grid(painter, inner)
        self._draw_wave(painter, inner)
        self._draw_mascot(painter, rect)
        self._draw_caption(painter, rect)

    def _draw_grid(self, painter: QPainter, area: QRectF) -> None:
        painter.setPen(QPen(QColor(255, 255, 255, 125), 2))

        for i in range(1, 6):
            x = area.left() + area.width() * i / 6.0
            painter.drawLine(QPointF(x, area.top()), QPointF(x, area.bottom()))

        for i in range(1, 4):
            y = area.top() + area.height() * i / 4.0
            painter.drawLine(QPointF(area.left(), y), QPointF(area.right(), y))

        painter.setPen(QPen(QColor("#77c8ff"), 3, Qt.DashLine))
        painter.drawLine(QPointF(area.left(), area.center().y()), QPointF(area.right(), area.center().y()))

    def _downsample(self, data: np.ndarray, points: int) -> np.ndarray:
        if data.size <= points:
            return data

        idx = np.linspace(0, data.size - 1, points).astype(np.int64)
        return data[idx]

    def _path_for_wave(self, data: np.ndarray, area: QRectF, vertical_offset: float) -> QPainterPath:
        wave = self._downsample(data, max(20, int(area.width())))
        path = QPainterPath()

        if wave.size < 2:
            return path

        amp = area.height() * 0.34
        x_step = area.width() / max(1, wave.size - 1)
        wobble = math.sin(self.animation_phase) * 2.0

        path.moveTo(area.left(), area.center().y() + vertical_offset - float(wave[0]) * amp + wobble)

        for i, sample in enumerate(wave[1:], start=1):
            x = area.left() + i * x_step
            y = area.center().y() + vertical_offset - float(sample) * amp + wobble
            path.lineTo(QPointF(x, y))

        return path

    def _draw_wave(self, painter: QPainter, area: QRectF) -> None:
        if self.audio.ndim == 1:
            left = right = self.audio
        else:
            left = self.audio[:, 0]
            right = self.audio[:, 1]

        mono = (left + right) * 0.5

        shadow_path = self._path_for_wave(mono, area.adjusted(8, 8, 8, 8), 8)
        painter.setPen(QPen(QColor(0, 0, 0, 55), 12, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.drawPath(shadow_path)

        left_path = self._path_for_wave(left, area, -area.height() * 0.08)
        right_path = self._path_for_wave(right, area, area.height() * 0.08)
        mono_path = self._path_for_wave(mono, area, 0)

        painter.setPen(QPen(QColor("#00a8ff"), 5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.drawPath(left_path)

        painter.setPen(QPen(QColor("#ff4fa3"), 5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.drawPath(right_path)

        painter.setPen(QPen(QColor("#fff176"), 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.drawPath(mono_path)

        painter.setPen(QColor("#263238"))
        painter.setFont(QFont("Arial", 10, QFont.Bold))
        painter.drawText(
            QRectF(area.left(), area.bottom() + 4, area.width(), 20),
            Qt.AlignCenter,
            "Blue = left ear    Pink = right ear    Yellow = middle",
        )

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
        painter.setFont(QFont("Arial", 14, QFont.Bold))

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
        self.resize(1280, 820)
        self.setMinimumSize(QSize(960, 680))

        self.current_audio = np.zeros((1, 2), dtype=np.float32)
        self.current_settings = SynthSettings()
        self.live_loop_enabled = False
        self.live_loop_is_refreshing = False
        self.live_loop_timer = QTimer(self)
        self.live_loop_timer.timeout.connect(self._live_loop_tick)

        self.user_presets_path = Path.home() / ".wave_toy_sound_experiments.json"
        self.user_preset_buttons: List[QPushButton] = []
        self.user_preset_layout: QVBoxLayout | None = None

        self.wave_start_sliders: Dict[str, QSlider] = {}
        self.wave_end_sliders: Dict[str, QSlider] = {}
        self.wave_time_sliders: Dict[str, QSlider] = {}
        self.wave_start_labels: Dict[str, QLabel] = {}
        self.wave_end_labels: Dict[str, QLabel] = {}
        self.wave_time_labels: Dict[str, QLabel] = {}

        self._build_actions()
        self._build_ui()
        self._build_shortcuts()
        self._apply_style()
        self._sync_note_to_pitch()
        self._generate(update_message=True)

    def _build_actions(self) -> None:
        about = QAction("About Wave Toy", self)
        about.triggered.connect(self._show_about)
        self.menuBar().addMenu("Help").addAction(about)

    def _build_shortcuts(self) -> None:
        """Install application-level shortcuts so focused sliders/buttons do not swallow Space."""
        play_shortcut = QShortcut(QKeySequence(Qt.Key_Space), self)
        play_shortcut.setContext(Qt.ApplicationShortcut)
        play_shortcut.activated.connect(self._play)

        loop_shortcut = QShortcut(QKeySequence(Qt.SHIFT | Qt.Key_Space), self)
        loop_shortcut.setContext(Qt.ApplicationShortcut)
        loop_shortcut.activated.connect(self._toggle_live_loop)

    def _build_ui(self) -> None:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        self.setCentralWidget(scroll)

        root = QWidget()
        root.setMinimumSize(QSize(940, 660))
        scroll.setWidget(root)

        outer = QVBoxLayout(root)
        outer.setContentsMargins(22, 22, 22, 22)
        outer.setSpacing(18)

        title = QLabel("🌈 Wave Toy")
        title.setObjectName("title")

        subtitle = QLabel("Build sounds by shaping waves! Space = play. Shift+Space = live loop. Wave sliders use picture labels; numbers appear only in grown-up explanations.")
        subtitle.setObjectName("subtitle")

        outer.addWidget(title)
        outer.addWidget(subtitle)

        body = QHBoxLayout()
        body.setSpacing(18)
        outer.addLayout(body, 1)

        left = QVBoxLayout()
        center = QVBoxLayout()
        right = QVBoxLayout()
        left.setSpacing(16)
        center.setSpacing(16)
        right.setSpacing(16)

        body.addLayout(left, 3)
        body.addLayout(center, 4)
        body.addLayout(right, 3)

        wave_box = self._toy_group("1. Mix the Wave Shapes")
        wave_box.setMinimumWidth(360)
        wave_layout = QGridLayout(wave_box)
        wave_layout.setHorizontalSpacing(12)
        wave_layout.setVerticalSpacing(8)
        wave_layout.setColumnStretch(0, 1)
        wave_layout.setColumnStretch(1, 2)
        wave_layout.setColumnStretch(2, 2)
        wave_layout.setColumnStretch(3, 2)

        wave_layout.addWidget(QLabel("Wave"), 0, 0)
        wave_layout.addWidget(QLabel("Start 🌱"), 0, 1)
        wave_layout.addWidget(QLabel("End 🌳"), 0, 2)
        wave_layout.addWidget(QLabel("Change 🐢→🐇"), 0, 3)

        default_start = {
            "sine": 0,
            "triangle": -60,
            "sawtooth": -60,
            "square": -60,
        }
        default_end = dict(default_start)

        for row, wave_type in enumerate(WAVE_ORDER, start=1):
            ui_row = row * 2 - 1

            name = QLabel(f"{self._wave_icon(wave_type)} {WAVE_LABELS[wave_type]}")
            name.setMinimumWidth(118)
            name.setWordWrap(True)

            start_label = QLabel(self._slider_picture_text(default_start[wave_type], "loudness"))
            start_slider = QSlider(Qt.Horizontal)
            start_slider.setRange(-20, 0)
            start_slider.setValue(default_start[wave_type])
            start_slider.setTickInterval(6)
            start_slider.setMinimumWidth(90)
            start_slider.setToolTip("Starting loudness. 0 dB is full volume. -60 dB is silent.")
            start_slider.valueChanged.connect(self._generate)
            start_slider.valueChanged.connect(lambda value, wt=wave_type: self._update_wave_envelope_labels(wt))

            end_label = QLabel(self._slider_picture_text(default_end[wave_type], "loudness"))
            end_slider = QSlider(Qt.Horizontal)
            end_slider.setRange(-20, 0)
            end_slider.setValue(default_end[wave_type])
            end_slider.setTickInterval(6)
            end_slider.setMinimumWidth(90)
            end_slider.setToolTip("Ending size of this wave.")
            end_slider.valueChanged.connect(self._generate)
            end_slider.valueChanged.connect(lambda value, wt=wave_type: self._update_wave_envelope_labels(wt))

            time_label = QLabel("🐢 Slow")
            time_slider = QSlider(Qt.Horizontal)
            time_slider.setRange(1, 100)
            time_slider.setValue(100)
            time_slider.setTickInterval(10)
            time_slider.setMinimumWidth(90)
            time_slider.setToolTip("How slowly or quickly this wave changes.")
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
        pitch_box.setMinimumWidth(360)
        pitch_layout = QGridLayout(pitch_box)
        pitch_layout.setHorizontalSpacing(12)
        pitch_layout.setVerticalSpacing(10)
        pitch_layout.setColumnStretch(0, 1)
        pitch_layout.setColumnStretch(1, 2)

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
        explain_box.setMinimumHeight(150)
        explain_layout = QVBoxLayout(explain_box)
        explain_layout.setSpacing(10)

        self.beginner_mode = QCheckBox("Beginner mode: explain it like first grade")
        self.beginner_mode.setChecked(True)
        self.beginner_mode.stateChanged.connect(self._update_explanation)

        self.explain_label = QLabel()
        self.explain_label.setWordWrap(True)
        self.explain_label.setObjectName("explain")

        explain_layout.addWidget(self.beginner_mode)
        explain_layout.addWidget(self.explain_label)

        center.addWidget(explain_box)

        motion_box = self._toy_group("3. Change Over Time")
        motion_box.setMinimumWidth(300)
        motion_layout = QGridLayout(motion_box)
        motion_layout.setHorizontalSpacing(12)
        motion_layout.setVerticalSpacing(10)
        motion_layout.setColumnStretch(0, 1)
        motion_layout.setColumnStretch(1, 2)

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
        motion_layout.addWidget(QLabel("Start Pitch"), 2, 0)
        motion_layout.addWidget(self.pitch_start, 2, 1)
        motion_layout.addWidget(QLabel("End Pitch"), 3, 0)
        motion_layout.addWidget(self.pitch_end, 3, 1)
        motion_layout.addWidget(QLabel("Start Wiggle"), 4, 0)
        motion_layout.addWidget(self.loud_start, 4, 1)
        motion_layout.addWidget(QLabel("End Wiggle"), 5, 0)
        motion_layout.addWidget(self.loud_end, 5, 1)
        motion_layout.addWidget(QLabel("Change Style"), 6, 0)
        motion_layout.addWidget(self.curve_combo, 6, 1)

        right.addWidget(motion_box)

        stereo_box = self._toy_group("4. Stereo Space")
        stereo_box.setMinimumWidth(300)
        stereo_layout = QGridLayout(stereo_box)
        stereo_layout.setHorizontalSpacing(12)
        stereo_layout.setVerticalSpacing(10)
        stereo_layout.setColumnStretch(0, 1)
        stereo_layout.setColumnStretch(1, 2)

        self.pan_start_slider = self._make_percent_slider(-100, 100, 0)
        self.pan_end_slider = self._make_percent_slider(-100, 100, 0)
        self.width_slider = self._make_percent_slider(0, 100, 45)
        self.auto_pan_depth_slider = self._make_percent_slider(0, 100, 0)

        self.auto_pan_rate = QDoubleSpinBox()
        self.auto_pan_rate.setRange(0.05, 8.0)
        self.auto_pan_rate.setValue(0.5)
        self.auto_pan_rate.setSingleStep(0.05)
        self.auto_pan_rate.setSuffix(" Hz")

        stereo_layout.addWidget(QLabel("Start Pan"), 0, 0)
        stereo_layout.addWidget(self.pan_start_slider, 0, 1)
        stereo_layout.addWidget(QLabel("End Pan"), 1, 0)
        stereo_layout.addWidget(self.pan_end_slider, 1, 1)
        stereo_layout.addWidget(QLabel("Ear Spread"), 2, 0)
        stereo_layout.addWidget(self.width_slider, 2, 1)
        stereo_layout.addWidget(QLabel("Ear Dance"), 3, 0)
        stereo_layout.addWidget(self.auto_pan_depth_slider, 3, 1)
        stereo_layout.addWidget(QLabel("Wiggle Speed"), 4, 0)
        stereo_layout.addWidget(self.auto_pan_rate, 4, 1)

        right.addWidget(stereo_box)

        preset_box = self._toy_group("Sound Experiments")
        preset_box.setMinimumWidth(300)
        preset_layout = QVBoxLayout(preset_box)
        preset_layout.setSpacing(8)

        presets = [
            ("Pure A4", self._preset_pure_a4),
            ("Rocket Pitch 🚀", self._preset_rocket_pitch),
            ("Robot Beep 🤖", self._preset_robot_beep),
            ("Falling Star ⭐", self._preset_falling_star),
            ("Fade-In Mountain 🏔️", self._preset_fade_in_triangle),
        ]

        for label, callback in presets:
            button = QPushButton(label)
            button.clicked.connect(callback)
            preset_layout.addWidget(button)

        self.user_preset_layout = preset_layout
        self._load_user_preset_buttons()

        right.addWidget(preset_box)
        right.addStretch(1)

        controls = QHBoxLayout()
        controls.setSpacing(12)
        outer.addLayout(controls)

        self.make_button = ToyButton("▶ Make Sound!", "#5cdb95")
        self.stop_button = ToyButton("■ Stop!", "#ff6b6b")
        self.save_button = ToyButton("💾 Save My Sound", "#ffd166")
        self.load_button = ToyButton("📂 Load Sound", "#b8f2e6")
        self.make_button.setMinimumWidth(180)
        self.stop_button.setMinimumWidth(120)
        self.save_button.setMinimumWidth(190)
        self.load_button.setMinimumWidth(180)
        self.loop_status_label = QLabel("Loop: Off")
        self.loop_status_label.setObjectName("loopStatus")

        controls.addWidget(self.make_button, 2)
        controls.addWidget(self.stop_button, 1)
        controls.addWidget(self.save_button, 2)
        controls.addWidget(self.load_button, 2)
        controls.addWidget(self.loop_status_label, 1)

        self.make_button.clicked.connect(self._play)
        self.stop_button.clicked.connect(self._stop)
        self.save_button.clicked.connect(self._save)
        self.load_button.clicked.connect(self._load_sound)

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
            self.pan_start_slider,
            self.pan_end_slider,
            self.width_slider,
            self.auto_pan_depth_slider,
            self.auto_pan_rate,
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
        box.setMinimumHeight(90)
        return box

    def _make_percent_slider(self, minimum: int, maximum: int, value: int) -> QSlider:
        slider = QSlider(Qt.Horizontal)
        slider.setRange(minimum, maximum)
        slider.setValue(value)
        slider.setTickInterval(10)
        return slider

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
            QScrollArea {
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
                margin-top: 22px;
                padding: 18px;
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
                font-size: 14px;
                font-weight: 700;
                color: #263238;
            }
            QLabel#explain {
                font-size: 17px;
                font-weight: 700;
                color: #263238;
                padding: 10px;
            }
            QLabel#loopStatus {
                font-size: 16px;
                font-weight: 900;
                color: #263238;
                background: #ffffff;
                border: 3px solid rgba(0, 0, 0, 0.14);
                border-radius: 16px;
                padding: 10px;
            }
            QCheckBox {
                font-size: 16px;
                font-weight: 800;
                color: #263238;
            }
            QComboBox, QSpinBox, QDoubleSpinBox {
                min-height: 38px;
                border: 3px solid rgba(0, 0, 0, 0.18);
                border-radius: 12px;
                padding: 4px 8px;
                font-size: 14px;
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
            QPushButton {
                min-height: 34px;
                border-radius: 14px;
                border: 3px solid rgba(0, 0, 0, 0.12);
                background: #f1f7ff;
                font-size: 14px;
                font-weight: 800;
                padding: 6px 10px;
            }
            QPushButton:hover {
                background: #e2f2ff;
            }
            """
        )

    def _db_text(self, value: int) -> str:
        return "Off" if value <= -20 else f"{value} dB"

    def _slider_picture_text(self, value: int, kind: str) -> str:
        """Child-facing slider labels. No numerical values here."""
        if kind == "time":
            if value <= 25:
                return "🐇 Fast"
            if value <= 65:
                return "🚶 Medium"
            return "🐢 Slow"

        if value <= -20:
            return "🤫 Silent"
        if value <= -14:
            return "🌱 Tiny"
        if value <= -8:
            return "🌿 Medium"
        return "🌳 Big"

    def _wave_start_db_from_ui(self) -> Dict[str, float]:
        return {
            wave_type: float(slider.value())
            for wave_type, slider in self.wave_start_sliders.items()
        }

    def _wave_end_db_from_ui(self) -> Dict[str, float]:
        return {
            wave_type: float(slider.value())
            for wave_type, slider in self.wave_end_sliders.items()
        }

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
            pan_start=self.pan_start_slider.value() / 100.0,
            pan_end=self.pan_end_slider.value() / 100.0,
            stereo_width=self.width_slider.value() / 100.0,
            auto_pan_depth=self.auto_pan_depth_slider.value() / 100.0,
            auto_pan_rate=self.auto_pan_rate.value(),
        )

    def _sync_note_to_pitch(self) -> None:
        hz = frequency_from_note(
            self.note_combo.currentText(),
            self.octave_spin.value(),
            self.cents_spin.value(),
        )

        self.base_pitch_label.setText(f"{self.note_combo.currentText()}{self.octave_spin.value()} = {hz:.2f} Hz")

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

        active_count = sum(
            1
            for wave_type, db in (self.current_settings.wave_start_db or {}).items()
            if db > -60 or (self.current_settings.wave_end_db or {}).get(wave_type, -20) > -60
        )

        if self.current_settings.auto_pan_depth > 0:
            msg = "The sound wiggles between your left and right ears!"
        elif abs(self.current_settings.pitch_start_hz - self.current_settings.pitch_end_hz) > 0.5:
            msg = "The waves squeeze or stretch, so the pitch changes!"
        else:
            msg = f"You are mixing {active_count} wave shape(s). Move the sliders!"

        self.canvas.set_data(audio, freq_env, loud_env, msg)
        self._update_explanation()

        if self.live_loop_enabled and not self.live_loop_is_refreshing:
            self._restart_live_loop(regenerate=False)

    def _update_explanation(self) -> None:
        s = self.current_settings
        curve_name = CURVE_LABELS[s.curve_type]

        active = []
        for wave_type, start_db in (s.wave_start_db or {}).items():
            end_db = (s.wave_end_db or {}).get(wave_type, start_db)
            change_time = (s.wave_delta_time or {}).get(wave_type, s.duration_seconds)

            if start_db > -60 or end_db > -60:
                active.append(
                    f"{WAVE_LABELS[wave_type]} {start_db:.0f}→{end_db:.0f} dB over {change_time:.1f}s"
                )

        active_text = ", ".join(active) if active else "no waves yet"

        if self.beginner_mode.isChecked():
            simple_wave_words = []

            for wave_type, start_db in (s.wave_start_db or {}).items():
                end_db = (s.wave_end_db or {}).get(wave_type, start_db)

                if start_db > -60 or end_db > -60:
                    simple_wave_words.append(WAVE_LABELS[wave_type].lower())

            if not simple_wave_words:
                wave_sentence = "You have not turned on any waves yet."
            elif len(simple_wave_words) == 1:
                wave_sentence = f"You are playing a {simple_wave_words[0]}."
            else:
                wave_sentence = (
                    "You mixed these waves together: "
                    + ", ".join(simple_wave_words[:-1])
                    + " and "
                    + simple_wave_words[-1]
                    + "."
                )

            if abs(s.pitch_start_hz - s.pitch_end_hz) > 0.5:
                pitch_sentence = (
                    "The sound changes as it plays. "
                    "It starts deeper and moves higher, or starts higher and moves deeper."
                )
            else:
                pitch_sentence = "The sound stays about the same pitch while it plays."

            if s.auto_pan_depth > 0 or abs(s.pan_start - s.pan_end) > 0.05:
                stereo_sentence = (
                    "The sound moves between the left ear and the right ear like it is dancing."
                )
            else:
                stereo_sentence = (
                    "The sound stays mostly in the middle between both ears."
                )

            self.explain_label.setText(
                wave_sentence + " "
                + pitch_sentence + " "
                + "Big wiggles sound louder. Tiny wiggles sound quieter. "
                + stereo_sentence + " "
                + "Blue shows the left side. Pink shows the right side."
            )
        else:
            self.explain_label.setText(
                f"You are mixing: {active_text}. Pitch moves from {s.pitch_start_hz:.1f} Hz to "
                f"{s.pitch_end_hz:.1f} Hz using {curve_name.lower()}. Global loudness moves from "
                f"{s.loudness_start:.2f} to {s.loudness_end:.2f}. Stereo pan moves from "
                f"{s.pan_start:.2f} to {s.pan_end:.2f}, width is {s.stereo_width:.2f}, and "
                f"auto-pan depth/rate are {s.auto_pan_depth:.2f}/{s.auto_pan_rate:.2f} Hz. "
                f"Grown-up words: waveform, frequency, decibels, amplitude envelope, stereo field."
            )

    def keyPressEvent(self, event) -> None:
        """Fallback keyboard handler. QShortcut handles this more reliably."""
        if event.key() == Qt.Key_Space:
            if event.modifiers() & Qt.ShiftModifier:
                self._toggle_live_loop()
            else:
                self._play()
            event.accept()
            return

        super().keyPressEvent(event)

    def _play(self) -> None:
        """Play the current sound once."""
        self._generate()
        self._play_current_audio_once()

    def _play_current_audio_once(self) -> None:
        """Play already-generated audio once."""
        if sd is not None:
            try:
                sd.stop()
                sd.play(self.current_audio, SAMPLE_RATE, blocking=False)
                return
            except Exception:
                pass

        ok, message = self._play_with_system_player()

        if not ok:
            self._show_playback_warning(message)

    def _show_playback_warning(self, message: str) -> None:
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

    def _toggle_live_loop(self) -> None:
        """Toggle continuous live playback. Requires sounddevice for clean looping."""
        if self.live_loop_enabled:
            self._disable_live_loop()
            return

        if sd is None:
            self._show_playback_warning("Live loop mode requires sounddevice. Run: pip install sounddevice")
            return

        self.live_loop_enabled = True
        self.loop_status_label.setText("Loop: On")
        self._restart_live_loop(regenerate=True)

    def _disable_live_loop(self) -> None:
        self.live_loop_enabled = False
        self.live_loop_timer.stop()
        self.live_loop_is_refreshing = False
        if sd is not None:
            try:
                sd.stop()
            except Exception:
                pass
        self.loop_status_label.setText("Loop: Off")

    def _live_loop_tick(self) -> None:
        """Timer callback: rebuild the sound and play the next loop."""
        self._restart_live_loop(regenerate=True)

    def _restart_live_loop(self, regenerate: bool = True) -> None:
        """Regenerate and restart playback so slider changes are heard live."""
        if not self.live_loop_enabled or sd is None:
            return

        try:
            self.live_loop_is_refreshing = True
            if regenerate:
                self._generate()
            self.live_loop_is_refreshing = False

            sd.stop()
            sd.play(self.current_audio, SAMPLE_RATE, blocking=False)

            duration_ms = max(100, int(self.current_settings.duration_seconds * 1000))
            self.live_loop_timer.start(duration_ms)
        except Exception as exc:
            self._disable_live_loop()
            self._show_playback_warning(str(exc))

    def _play_with_system_player(self) -> Tuple[bool, str]:
        players = [
            ("paplay", ["paplay"]),
            ("aplay", ["aplay", "-q"]),
            ("ffplay", ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet"]),
            ("play", ["play", "-q"]),
        ]

        found = [
            (name, command)
            for name, command in players
            if shutil.which(name)
        ]

        if not found:
            return False, "No supported command-line audio player found."

        try:
            temp = tempfile.NamedTemporaryFile(prefix="wave_toy_", suffix=".wav", delete=False)
            temp_path = Path(temp.name)
            temp.close()
            save_wav(temp_path, self.current_audio)
        except Exception as exc:
            return False, f"Could not create temporary WAV file: {exc}"

        name, command = found[0]

        try:
            subprocess.Popen(
                [*command, str(temp_path)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            return True, f"Playing with {name}."
        except Exception as exc:
            return False, f"Could not launch {name}: {exc}"

    def _stop(self) -> None:
        self._disable_live_loop()

    def _save(self) -> None:
        self._generate()

        filename, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Save My Sound",
            "wave_toy_sound.wav",
            "WAV Audio (*.wav);;Ogg Vorbis (*.ogg);;MP3 Audio (*.mp3);;FLAC Audio (*.flac)",
        )

        if not filename:
            return

        path = Path(filename)

        if not path.suffix:
            if "Ogg" in selected_filter:
                path = path.with_suffix(".ogg")
            elif "MP3" in selected_filter:
                path = path.with_suffix(".mp3")
            elif "FLAC" in selected_filter:
                path = path.with_suffix(".flac")
            else:
                path = path.with_suffix(".wav")

        try:
            save_audio_file(path, self.current_audio)

            recipe = self._settings_to_recipe(path.stem)
            recipe_path = path.with_suffix(path.suffix + ".wave-toy.json")
            recipe_path.write_text(json.dumps(recipe, indent=2), encoding="utf-8")

            self._add_recipe_to_sound_experiments(recipe)
        except Exception as exc:
            QMessageBox.warning(self, "Could not save sound", str(exc))
            return

        saved_text = (
            f"Your sound was saved to:\n{path}\n\n"
            f"The recipe metadata was saved to:\n{recipe_path}"
        )
        QMessageBox.information(self, "Saved!", saved_text)

    def _settings_to_recipe(self, name: str) -> Dict[str, object]:
        return {
            "name": name,
            "version": 2,
            "sample_rate": SAMPLE_RATE,
            "settings": asdict(self._settings_from_ui()),
            "ui": {
                "note": self.note_combo.currentText(),
                "octave": self.octave_spin.value(),
                "cents": self.cents_spin.value(),
                "loudness_start_slider": self.loud_start.value(),
                "loudness_end_slider": self.loud_end.value(),
                "duration_slider": self.duration_slider.value(),
                "pan_start_slider": self.pan_start_slider.value(),
                "pan_end_slider": self.pan_end_slider.value(),
                "width_slider": self.width_slider.value(),
                "auto_pan_depth_slider": self.auto_pan_depth_slider.value(),
                "auto_pan_rate": self.auto_pan_rate.value(),
                "curve_type": self.curve_combo.currentData(),
                "waves": {
                    wave_type: {
                        "start_db": self.wave_start_sliders[wave_type].value(),
                        "end_db": self.wave_end_sliders[wave_type].value(),
                        "change_time_percent": self.wave_time_sliders[wave_type].value(),
                    }
                    for wave_type in WAVE_ORDER
                },
            },
        }

    def _add_recipe_to_sound_experiments(self, recipe: Dict[str, object]) -> None:
        recipes = self._read_user_recipes()

        recipe_name = str(recipe.get("name", "Saved Sound"))
        recipes = [
            existing_recipe
            for existing_recipe in recipes
            if str(existing_recipe.get("name", "")) != recipe_name
        ]

        recipes.append(recipe)
        self.user_presets_path.write_text(json.dumps(recipes, indent=2), encoding="utf-8")
        self._load_user_preset_buttons()

    def _read_user_recipes(self) -> List[Dict[str, object]]:
        if not self.user_presets_path.exists():
            return []

        try:
            data = json.loads(self.user_presets_path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return [
                    item
                    for item in data
                    if isinstance(item, dict)
                ]
        except Exception:
            return []

        return []

    def _load_user_preset_buttons(self) -> None:
        if self.user_preset_layout is None:
            return

        for button in self.user_preset_buttons:
            self.user_preset_layout.removeWidget(button)
            button.deleteLater()

        self.user_preset_buttons.clear()

        recipes = self._read_user_recipes()

        if recipes:
            label = QLabel("Saved Sounds")
            label.setObjectName("savedSoundsLabel")
            self.user_preset_layout.addWidget(label)
            self.user_preset_buttons.append(label)

        for recipe in recipes[-8:]:
            name = str(recipe.get("name", "Saved Sound"))
            button = QPushButton(f"💾 {name}")
            button.clicked.connect(lambda checked=False, r=recipe: self._apply_recipe(r))
            self.user_preset_layout.addWidget(button)
            self.user_preset_buttons.append(button)

    def _apply_recipe(self, recipe: Dict[str, object]) -> None:
        ui = recipe.get("ui", {})
        settings = recipe.get("settings", {})

        if not isinstance(ui, dict):
            ui = {}
        if not isinstance(settings, dict):
            settings = {}

        waves = ui.get("waves", {})
        if not isinstance(waves, dict):
            waves = {}

        self.note_combo.setCurrentText(str(ui.get("note", settings.get("note", "A"))))
        self.octave_spin.setValue(int(ui.get("octave", settings.get("octave", 4))))
        self.cents_spin.setValue(float(ui.get("cents", settings.get("cents", 0.0))))
        self.pitch_start.setValue(float(settings.get("pitch_start_hz", 440.0)))
        self.pitch_end.setValue(float(settings.get("pitch_end_hz", 440.0)))
        self.duration_spin.setValue(float(settings.get("duration_seconds", 1.5)))
        self.loud_start.setValue(int(ui.get("loudness_start_slider", 40)))
        self.loud_end.setValue(int(ui.get("loudness_end_slider", 40)))
        self.pan_start_slider.setValue(int(ui.get("pan_start_slider", 0)))
        self.pan_end_slider.setValue(int(ui.get("pan_end_slider", 0)))
        self.width_slider.setValue(int(ui.get("width_slider", 45)))
        self.auto_pan_depth_slider.setValue(int(ui.get("auto_pan_depth_slider", 0)))
        self.auto_pan_rate.setValue(float(ui.get("auto_pan_rate", 0.5)))

        self._set_curve(str(ui.get("curve_type", settings.get("curve_type", "linear"))))

        start_levels: Dict[str, int] = {}
        end_levels: Dict[str, int] = {}
        times: Dict[str, int] = {}

        for wave_type in WAVE_ORDER:
            wave_data = waves.get(wave_type, {})
            if isinstance(wave_data, dict):
                start_levels[wave_type] = int(wave_data.get("start_db", -20))
                end_levels[wave_type] = int(wave_data.get("end_db", -20))
                times[wave_type] = int(wave_data.get("change_time_percent", 100))

        self._set_wave_levels(start_levels, end_levels, times)
        self._generate()


    def _load_sound(self) -> None:
        """Load a Wave Toy recipe or audio file."""
        filename, selected_filter = QFileDialog.getOpenFileName(
            self,
            "Load Sound or Recipe",
            "",
            (
                "Wave Toy Recipe (*.json *.wave-toy.json);;"
                "Audio Files (*.wav *.mp3 *.ogg *.flac);;"
                "All Files (*)"
            ),
        )

        if not filename:
            return

        path = Path(filename)

        if path.suffix.lower() == ".json" or path.name.endswith(".wave-toy.json"):
            try:
                recipe = json.loads(path.read_text(encoding="utf-8"))
                if not isinstance(recipe, dict):
                    raise ValueError("Recipe file does not contain a valid recipe object.")
                self._apply_recipe(recipe)
                QMessageBox.information(
                    self,
                    "Recipe Loaded",
                    f"Loaded Wave Toy recipe:\n{path.name}"
                )
            except Exception as exc:
                QMessageBox.warning(
                    self,
                    "Could not load recipe",
                    str(exc),
                )
            return

        # Audio-only loading for playback/visual reference.
        try:
            if sd is not None:
                try:
                    sd.stop()
                    QMessageBox.information(
                        self,
                        "Audio File Selected",
                        (
                            f"Loaded audio file:\n{path.name}\n\n"
                            "Direct waveform analysis/import is not implemented yet, "
                            "but recipe loading is fully supported."
                        ),
                    )
                except Exception:
                    pass
            else:
                QMessageBox.information(
                    self,
                    "Audio File Selected",
                    (
                        f"Loaded audio file:\n{path.name}\n\n"
                        "Recipe loading is supported. "
                        "Audio waveform reverse-analysis is planned for a future update."
                    ),
                )
        except Exception as exc:
            QMessageBox.warning(
                self,
                "Could not load audio file",
                str(exc),
            )

    def _show_about(self) -> None:
        QMessageBox.information(
            self,
            "About Wave Toy",
            "Wave Toy teaches sound waves with playful controls.\n\n"
            "Kid words: pitch, loudness, wave shape, left ear, right ear.\n"
            "Grown-up words: frequency, amplitude, waveform, envelope, stereo field.",
        )

    def _preset_pure_a4(self) -> None:
        self._set_wave_levels(
            {"sine": 0, "triangle": -60, "sawtooth": -60, "square": -60},
        )
        self.note_combo.setCurrentText("A")
        self.octave_spin.setValue(4)
        self.cents_spin.setValue(0)
        self.pitch_start.setValue(440)
        self.pitch_end.setValue(440)
        self.loud_start.setValue(35)
        self.loud_end.setValue(35)
        self.duration_spin.setValue(1.5)
        self.pan_start_slider.setValue(0)
        self.pan_end_slider.setValue(0)
        self.width_slider.setValue(20)
        self.auto_pan_depth_slider.setValue(0)
        self._set_curve("linear")
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
        self.pan_start_slider.setValue(-40)
        self.pan_end_slider.setValue(40)
        self.width_slider.setValue(70)
        self.auto_pan_depth_slider.setValue(15)
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
        self.width_slider.setValue(80)
        self.auto_pan_depth_slider.setValue(30)
        self.auto_pan_rate.setValue(2.0)
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
        self.pan_start_slider.setValue(45)
        self.pan_end_slider.setValue(-45)
        self.width_slider.setValue(60)
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
        self.width_slider.setValue(40)
        self._set_curve("linear")
        self._generate()

    def _set_wave_levels(
        self,
        levels: Dict[str, int],
        end_levels: Dict[str, int] | None = None,
        times: Dict[str, int] | None = None,
    ) -> None:
        end_levels = end_levels or levels
        times = times or {wave_type: 100 for wave_type in WAVE_ORDER}

        for wave_type in WAVE_ORDER:
            for slider_dict, value_dict, default_value in [
                (self.wave_start_sliders, levels, -20),
                (self.wave_end_sliders, end_levels, -20),
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

        self.wave_start_labels[wave_type].setText(self._slider_picture_text(start_value, "loudness"))
        self.wave_end_labels[wave_type].setText(self._slider_picture_text(end_value, "loudness"))
        self.wave_time_labels[wave_type].setText(self._slider_picture_text(time_percent, "time"))

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
        for index in range(self.curve_combo.count()):
            if self.curve_combo.itemData(index) == curve_type:
                self.curve_combo.setCurrentIndex(index)
                return


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Wave Toy")

    window = WaveToyWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
