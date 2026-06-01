#!/usr/bin/env python3
"""
WaveToy - single-file educational waveform synthesis and articulation lab.

A professional educational Python/PySide6 app for teaching sound waves, stereo imaging, and articulatory synthesis from first principles.

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
import time
import uuid
import wave
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

try:
    import sounddevice as sd
except Exception:
    sd = None

from PySide6.QtCore import QEvent, QMimeData, QPoint, QPointF, QRect, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QColor, QDrag, QFont, QKeySequence, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QGraphicsDropShadowEffect,
    QGridLayout,
    QInputDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLayout,
    QMainWindow,
    QMessageBox,
    QMenu,
    QPushButton,
    QScrollArea,
    QSlider,
    QStackedWidget,
    QTabWidget,
    QToolButton,
    QSpinBox,
    QDoubleSpinBox,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

SAMPLE_RATE = 44_100


class FlowLayout(QLayout):
    """Small wrapping layout for button toolbars."""

    def __init__(self, parent: QWidget | None = None, margin: int = 0, spacing: int = 8) -> None:
        super().__init__(parent)
        self._items: list = []
        self.setContentsMargins(margin, margin, margin, margin)
        self.setSpacing(spacing)

    def addItem(self, item) -> None:
        self._items.append(item)

    def count(self) -> int:
        return len(self._items)

    def itemAt(self, index: int):
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index: int):
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None

    def expandingDirections(self) -> Qt.Orientations:
        return Qt.Orientations(Qt.Orientation(0))

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        return self._do_layout(QRect(0, 0, width, 0), test_only=True)

    def setGeometry(self, rect: QRect) -> None:
        super().setGeometry(rect)
        self._do_layout(rect, test_only=False)

    def sizeHint(self) -> QSize:
        return self.minimumSize()

    def minimumSize(self) -> QSize:
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        left, top, right, bottom = self.getContentsMargins()
        size += QSize(left + right, top + bottom)
        return size

    def _do_layout(self, rect: QRect, *, test_only: bool) -> int:
        left, top, right, bottom = self.getContentsMargins()
        effective = rect.adjusted(left, top, -right, -bottom)
        x = effective.x()
        y = effective.y()
        line_height = 0
        for item in self._items:
            space_x = self.spacing()
            space_y = self.spacing()
            item_size = item.sizeHint()
            next_x = x + item_size.width() + space_x
            if next_x - space_x > effective.right() and line_height > 0:
                x = effective.x()
                y = y + line_height + space_y
                next_x = x + item_size.width() + space_x
                line_height = 0
            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), item_size))
            x = next_x
            line_height = max(line_height, item_size.height())
        return y + line_height - rect.y() + bottom

ARTICULATION_SOURCE_DEFAULT = "default_voice"
ARTICULATION_SOURCE_CURRENT = "current_wavetoy_sound"
ARTICULATION_SOURCE_MIX_WAVE = "selected_mix_wave"
ARTICULATION_SOURCE_IMPORTED = "imported_audio"
ARTICULATION_SOURCE_MODES = {
    ARTICULATION_SOURCE_DEFAULT: "Default Voice",
    ARTICULATION_SOURCE_CURRENT: "WaveToy Sound",
    ARTICULATION_SOURCE_MIX_WAVE: "Selected Mix Wave",
    ARTICULATION_SOURCE_IMPORTED: "Imported WAV",
}

ARTICULATION_INTERPOLATED_FIELDS = (
    "mouth_open",
    "tongue_height",
    "tongue_frontness",
    "lip_rounding",
    "voice_strength",
    "air_pressure",
    "teeth_gap",
    "closure",
    "burst_strength",
    "nasal_open",
)
ARTICULATION_TRANSITION_RULE_MS = {
    ("vowel", "vowel"): 70,
    ("vowel", "glide"): 60,
    ("glide", "vowel"): 70,
    ("liquid", "vowel"): 60,
    ("nasal", "vowel"): 45,
    ("fricative", "vowel"): 35,
    ("affricate", "vowel"): 35,
    ("vowel", "fricative"): 35,
    ("vowel", "affricate"): 35,
    ("stop", "vowel"): 12,
    ("vowel", "stop"): 18,
    ("stop", "stop"): 8,
}
ARTICULATION_DEFAULT_TRANSITION_MS = 35
ARTICULATION_MOTION_FRAME_MS = 5
ARTICULATION_MIN_WORD_CROSSFADE_MS = 12
ARTICULATION_DEFAULT_WORD_CROSSFADE_MS = 24
ARTICULATION_WORD_RENDER_CLIP_CROSSFADE = "Clip Crossfade"
ARTICULATION_WORD_RENDER_CONTINUOUS = "Continuous Mouth Motion"
ARTICULATION_WORD_RENDER_MODES = (ARTICULATION_WORD_RENDER_CLIP_CROSSFADE, ARTICULATION_WORD_RENDER_CONTINUOUS)
ARTICULATION_TRANSITION_CURVES = ("Linear", "Smoothstep", "Ease In", "Ease Out", "Ease In Out", "Sigmoid")
ARTICULATION_DEFAULT_TRANSITION_CURVE = "Smoothstep"
ARTICULATION_ENVELOPE_TRACKS = (
    "mouth_open",
    "tongue_height",
    "tongue_frontness",
    "lip_rounding",
    "voice_strength",
    "air_pressure",
    "closure",
    "nasal_open",
)



def articulation_source_badge(source_mode: str, source_wave_id: str | None = None, source_audio_path: str | None = None) -> str:
    if source_mode == ARTICULATION_SOURCE_CURRENT:
        return "WaveToy Sound"
    if source_mode == ARTICULATION_SOURCE_MIX_WAVE:
        return f"Mix Wave {source_wave_id or '?'}"
    if source_mode == ARTICULATION_SOURCE_IMPORTED:
        return Path(str(source_audio_path)).name if source_audio_path else "Imported WAV"
    return "Default Voice"

MAX_PREVIEW_SECONDS = 8.0
WAVE_ORDER = ["sine", "triangle", "sawtooth", "square"]
DEFAULT_WAVE_ORDER = list(WAVE_ORDER)
MAX_WAVE_ROWS = 12
TIMELINE_MIN_CLIP_SECONDS = 0.01
TIMELINE_TIME_STEP_SECONDS = 0.005

# Internal UI resolution. Sliders remain child-friendly visually, but internally
# they have fine enough resolution for tuned harmonies and subtle modulation.
DB_SLIDER_SCALE = 100          # -2000..0 => -20.00 dB..0.00 dB
MIDI_SLIDER_SCALE = 100        # 3600..8400 => MIDI 36.00..84.00
OCTAVE_SLIDER_SCALE = 100      # 200..600 => octave 2.00..6.00
SECONDS_SLIDER_SCALE = 200     # 2..1600 => 0.01s..8.00s in 0.005s steps
PERCENT_SLIDER_SCALE = 10      # 0..1000 => 0.0%..100.0%
RATE_SLIDER_SCALE = 100        # 5..800 => 0.05Hz..8.00Hz
PAULSTRETCH_SCALE = 100        # 100..3000 => 1.00x..30.00x

# Centralized touch-friendly slider metrics. These affect only Qt styling and
# widget hit area; they do not change synthesis ranges, saved recipe values, or
# audio generation behavior.
SLIDER_MIN_HEIGHT = 44
SLIDER_GROOVE_HEIGHT = 18
SLIDER_GROOVE_RADIUS = 9
SLIDER_HANDLE_SIZE = 34
SLIDER_HANDLE_RADIUS = 17
SLIDER_HANDLE_MARGIN = -8
GENERATION_DEBOUNCE_MS = 90

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
NOTE_TO_INDEX = {name: i for i, name in enumerate(NOTE_NAMES)}

NOTE_EMOTIONS = {
    "C": {"emoji": "🙂", "label": "Balanced", "color": "#F4F1DE"},
    "G": {"emoji": "😁", "label": "Confident", "color": "#FFD166"},
    "D": {"emoji": "🚀", "label": "Adventurous", "color": "#F8961E"},
    "A": {"emoji": "🔥", "label": "Energetic", "color": "#F94144"},
    "E": {"emoji": "⚡", "label": "Excited", "color": "#F3722C"},
    "B": {"emoji": "🤩", "label": "Brilliant", "color": "#F9C74F"},
    "F#": {"emoji": "🌌", "label": "Cosmic", "color": "#577590"},
    "C#": {"emoji": "🔮", "label": "Mysterious", "color": "#6A4C93"},
    "G#": {"emoji": "🌙", "label": "Dreamy", "color": "#4361EE"},
    "D#": {"emoji": "🥲", "label": "Melancholy", "color": "#4D908E"},
    "A#": {"emoji": "😢", "label": "Sad", "color": "#277DA1"},
    "F": {"emoji": "🫂", "label": "Warm", "color": "#90BE6D"},
}


def note_emotion(note: str) -> Dict[str, str]:
    return NOTE_EMOTIONS.get(note, NOTE_EMOTIONS["A"])


def note_relationship(note: str, main_note: str) -> str:
    fifths_order = ["C", "G", "D", "A", "E", "B", "F#", "C#", "G#", "D#", "A#", "F"]
    if note not in fifths_order or main_note not in fifths_order:
        return "🧭 Far Away"
    forward = (fifths_order.index(note) - fifths_order.index(main_note)) % len(fifths_order)
    backward = (fifths_order.index(main_note) - fifths_order.index(note)) % len(fifths_order)
    if forward == 0:
        return "🏠 Home"
    if forward == 1:
        return "🤝 Best Friend"
    if backward == 1:
        return "🫂 Comfort"
    if forward == 2:
        return "🚶 Adventure"
    if forward == 3:
        return "🔥 Energy"
    if forward == 4:
        return "⚡ Excitement"
    if backward == 2:
        return "😢 Tension"
    if forward in (5, 6, 7) or backward in (5, 6, 7):
        return "🧭 Far Away"
    return "🌈 Partner"


def emotional_note_text(note: str) -> str:
    emotion = note_emotion(note)
    return f"{emotion['emoji']} {note}"

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

TUNING_METHODS = {
    "equal_temperament_12": {
        "label": "Piano Steps",
        "tooltip": "Modern piano-style tuning: 12 equal steps per octave.",
        "kind": "equal",
        "divisions": 12,
    },
    "just_intonation_major": {
        "label": "Sweet Simple Ratios",
        "tooltip": "Simple whole-number ratios for sweet chords near the root note.",
        "kind": "ratios12",
        "ratios": [1, 16/15, 9/8, 6/5, 5/4, 4/3, 45/32, 3/2, 8/5, 5/3, 9/5, 15/8],
    },
    "pythagorean": {
        "label": "Stacked Fifths",
        "tooltip": "Built from stacked perfect fifths.",
        "kind": "ratios12",
        "ratios": [1, 256/243, 9/8, 32/27, 81/64, 4/3, 729/512, 3/2, 128/81, 27/16, 16/9, 243/128],
    },
    "quarter_comma_meantone": {
        "label": "Old Keyboard Glow",
        "tooltip": "Historical keyboard temperament with smooth thirds.",
        "kind": "cents12",
        "cents": [0, 76, 193, 310, 386, 503, 579, 697, 773, 890, 1007, 1083],
    },
    "werkmeister_iii": {
        "label": "Baroque Adventure",
        "tooltip": "Historical well temperament often associated with Baroque keyboard color.",
        "kind": "cents12",
        "cents": [0, 90, 192, 294, 390, 498, 588, 696, 792, 888, 996, 1092],
    },
    "kirnberger_iii": {
        "label": "Old Harpsichord",
        "tooltip": "Historical well temperament with gentler home-key color.",
        "kind": "cents12",
        "cents": [0, 90, 193, 294, 386, 498, 590, 697, 792, 890, 996, 1088],
    },
    "pelog": {
        "label": "Island Bells",
        "tooltip": "Approximate Indonesian pelog-inspired scale; a playful approximation, not an authoritative model.",
        "kind": "cents12",
        "cents": [0, 70, 140, 270, 400, 520, 650, 680, 820, 950, 1080, 1120],
    },
    "slendro": {
        "label": "Five Smooth Steps",
        "tooltip": "Approximate Indonesian slendro-inspired five-tone scale; a playful approximation, not an authoritative model.",
        "kind": "subset_equal",
        "steps": [0, 2, 5, 7, 10],
        "divisions": 5,
    },
    "pentatonic_equal": {
        "label": "Five-Step Playground",
        "tooltip": "Five evenly spaced notes per octave, mapped to the nearest toy note step.",
        "kind": "subset_equal",
        "steps": [0, 2, 4, 7, 9],
        "divisions": 5,
    },
    "nineteen_equal": {
        "label": "Tiny 19-Step Ladder",
        "tooltip": "19 equal steps per octave, with note names mapped to nearby steps.",
        "kind": "equal_mapped",
        "divisions": 19,
    },
    "twenty_four_equal": {
        "label": "Quarter-Tone Sprinkle",
        "tooltip": "24 equal steps per octave, with note names mapped to quarter-tone positions.",
        "kind": "equal_mapped",
        "divisions": 24,
    },
    "harmonic_series": {
        "label": "Nature Ladder",
        "tooltip": "Notes based on natural harmonic ratios.",
        "kind": "ratios12",
        "ratios": [1, 17/16, 9/8, 19/16, 5/4, 21/16, 11/8, 3/2, 13/8, 5/3, 7/4, 15/8],
    },
}




@dataclass
class AudioPaletteItem:
    """Imported reusable audio source for the Timeline Audio Assets."""

    id: int
    name: str
    source_path: str
    audio_data: np.ndarray
    sample_rate: int
    duration_seconds: float
    waveform_peaks: List[float]
    color: str

    @property
    def item_id(self) -> int:
        return self.id

    def metadata(self) -> Dict[str, object]:
        return {
            "id": self.id,
            "name": self.name,
            "source_path": self.source_path,
            "sample_rate": self.sample_rate,
            "duration_seconds": self.duration_seconds,
            "color": self.color,
        }


@dataclass
class SpeechBinItem:
    """Created articulation audio source available inside the Timeline Speech Assets panel."""

    id: int
    name: str
    item_type: str
    ipa_sequence: str
    display_sequence: str
    duration_seconds: float
    audio_cache_path: str | None
    articulation_metadata: Dict[str, object]
    source_mode: str
    created_at: float
    audio_data: np.ndarray

    def __post_init__(self) -> None:
        if self.audio_data.size:
            self.duration_seconds = max(0.0, float(len(self.audio_data)) / float(SAMPLE_RATE))

    @property
    def icon(self) -> str:
        return {
            "phoneme": "🔤",
            "syllable": "🔡",
            "word": "🧩",
            "chain": "🧬",
        }.get(self.item_type, "🗣")

    @property
    def source_type(self) -> str:
        return {
            "phoneme": "articulation_phoneme",
            "syllable": "articulation_syllable_render",
            "word": "articulation_word_render",
            "chain": "articulation_chain_raw",
        }.get(self.item_type, "articulation_word_render")

    def metadata(self) -> Dict[str, object]:
        actual_duration = max(0.0, float(len(self.audio_data)) / float(SAMPLE_RATE)) if self.audio_data.size else self.duration_seconds
        self.duration_seconds = actual_duration
        return {
            "id": self.id,
            "name": self.name,
            "item_type": self.item_type,
            "ipa_sequence": self.ipa_sequence,
            "display_sequence": self.display_sequence,
            "duration_seconds": actual_duration,
            "audio_cache_path": self.audio_cache_path,
            "articulation_metadata": self.articulation_metadata,
            "source_mode": self.source_mode,
            "created_at": self.created_at,
        }


@dataclass
class TimelineClip:
    """Audio clip placed on the Timeline."""

    clip_id: int
    name: str
    audio: np.ndarray
    start_time_seconds: float
    lane: int
    sample_rate: int = SAMPLE_RATE
    recipe: Dict[str, object] | None = None
    source_path: str | None = None
    import_metadata: Dict[str, object] | None = None
    source_type: str = "generated_wavetoy_sound"
    speech_metadata: Dict[str, object] | None = None
    muted_warning: str | None = None
    source_audio_full_length_samples: int = 0
    trim_start_seconds: float = 0.0
    trim_end_seconds: float = 0.0
    playback_rate: float = 1.0
    rendered_duration_seconds: float = 0.0
    stretch_mode: str = "preserve_pitch"
    stretch_algorithm: str = "numpy_phase_vocoder"
    stretched_audio_cache: np.ndarray | None = field(default=None, repr=False, compare=False)
    _stretch_cache_key: tuple | None = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.source_audio_full_length_samples <= 0:
            self.source_audio_full_length_samples = int(len(self.audio))
        source_duration = self.source_duration_seconds
        self.trim_start_seconds = float(np.clip(float(self.trim_start_seconds), 0.0, source_duration))
        self.trim_end_seconds = float(np.clip(float(self.trim_end_seconds), 0.0, max(0.0, source_duration - self.trim_start_seconds)))
        self.playback_rate = float(np.clip(float(self.playback_rate or 1.0), 0.25, 4.0))
        self.stretch_mode = str(self.stretch_mode or "preserve_pitch")
        self.stretch_algorithm = str(self.stretch_algorithm or "numpy_phase_vocoder")
        self.rendered_duration_seconds = self.duration_seconds

    @property
    def source_duration_seconds(self) -> float:
        return max(0.0, float(self.source_audio_full_length_samples or len(self.audio)) / float(self.sample_rate))

    @property
    def source_visible_duration_seconds(self) -> float:
        return max(0.0, self.source_duration_seconds - self.trim_start_seconds - self.trim_end_seconds)

    @property
    def duration_seconds(self) -> float:
        return max(0.0, self.source_visible_duration_seconds / max(0.25, float(self.playback_rate or 1.0)))

    @property
    def stretch_ratio(self) -> float:
        trimmed = max(1e-9, self.source_visible_duration_seconds)
        return max(0.0, self.duration_seconds / trimmed)

    @property
    def pitch_preserve_enabled(self) -> bool:
        return self.stretch_mode != "speed_change"

    @property
    def stretch_badge(self) -> str:
        return f"{self.stretch_ratio:.2f}x duration"

    @property
    def end_time_seconds(self) -> float:
        return self.start_time_seconds + self.duration_seconds

    def visible_audio(self) -> np.ndarray:
        audio = np.asarray(self.audio, dtype=np.float32)
        start = int(round(self.trim_start_seconds * self.sample_rate))
        end_trim = int(round(self.trim_end_seconds * self.sample_rate))
        end = max(start, len(audio) - end_trim)
        return np.array(audio[start:end], dtype=np.float32, copy=True)

    def metadata(self) -> Dict[str, object]:
        self.rendered_duration_seconds = self.duration_seconds
        data = {
            "id": self.clip_id,
            "name": self.name,
            "start_time_seconds": self.start_time_seconds,
            "lane": self.lane,
            "duration_seconds": self.duration_seconds,
            "source_duration_seconds": self.source_duration_seconds,
            "visible_duration_seconds": self.duration_seconds,
            "source_audio_full_length_samples": self.source_audio_full_length_samples,
            "trim_start_seconds": self.trim_start_seconds,
            "trim_end_seconds": self.trim_end_seconds,
            "playback_rate": self.playback_rate,
            "stretch_ratio": self.stretch_ratio,
            "stretch_mode": self.stretch_mode,
            "stretch_algorithm": self.stretch_algorithm,
            "pitch_preserve_enabled": self.pitch_preserve_enabled,
            "rendered_duration_seconds": self.rendered_duration_seconds,
            "sample_rate": self.sample_rate,
            "source_type": self.source_type,
            "recipe": self.recipe or {},
        }
        if self.source_path:
            data["source_path"] = self.source_path
        if self.import_metadata:
            data["import_metadata"] = self.import_metadata
        if self.speech_metadata:
            data["speech_metadata"] = self.speech_metadata
        if self.muted_warning:
            data["muted_warning"] = self.muted_warning
        return data


@dataclass
class ArticulationPhoneme:
    """Reusable toy articulation definition for vowels and consonants."""

    name: str
    ipa: str
    mouth_open: float
    tongue_height: float
    tongue_frontness: float
    lip_rounding: float
    voice_pitch: float = 220.0
    voice_strength: float = 0.65
    duration_ms: int = 500
    preview_color: str = "#ffd166"
    phoneme_family: str = "vowel"
    air_pressure: float = 0.45
    teeth_gap: float = 0.50
    closure: float = 0.0
    burst_strength: float = 0.0
    nasal_open: float = 0.0
    voiced: bool = True
    noise_color: float = 0.50
    attack_ms: int = 18
    release_ms: int = 28
    source_mode: str = ARTICULATION_SOURCE_DEFAULT
    source_wave_id: str | None = None
    source_recipe_snapshot: Dict[str, object] | None = None
    source_audio_path: str | None = None
    source_start_seconds: float = 0.0
    source_duration_seconds: float = 0.0
    source_pitch_follow: bool = True
    source_loop_to_fit: bool = True
    source_gain: float = 1.0

    def clamped(self) -> "ArticulationPhoneme":
        family = str(self.phoneme_family or "vowel").lower()
        if family not in {"vowel", "fricative", "stop", "nasal", "glide", "liquid", "affricate"}:
            family = "vowel"
        return ArticulationPhoneme(
            name=str(self.name or "untitled_phoneme"),
            ipa=str(self.ipa or "?"),
            mouth_open=float(np.clip(self.mouth_open, 0.0, 1.0)),
            tongue_height=float(np.clip(self.tongue_height, 0.0, 1.0)),
            tongue_frontness=float(np.clip(self.tongue_frontness, 0.0, 1.0)),
            lip_rounding=float(np.clip(self.lip_rounding, 0.0, 1.0)),
            voice_pitch=float(np.clip(self.voice_pitch, 60.0, 880.0)),
            voice_strength=float(np.clip(self.voice_strength, 0.0, 1.0)),
            duration_ms=int(np.clip(self.duration_ms, 80, 5000)),
            preview_color=str(self.preview_color or "#ffd166"),
            phoneme_family=family,
            air_pressure=float(np.clip(self.air_pressure, 0.0, 1.0)),
            teeth_gap=float(np.clip(self.teeth_gap, 0.0, 1.0)),
            closure=float(np.clip(self.closure, 0.0, 1.0)),
            burst_strength=float(np.clip(self.burst_strength, 0.0, 1.0)),
            nasal_open=float(np.clip(self.nasal_open, 0.0, 1.0)),
            voiced=bool(self.voiced),
            noise_color=float(np.clip(self.noise_color, 0.0, 1.0)),
            attack_ms=int(np.clip(self.attack_ms, 1, 250)),
            release_ms=int(np.clip(self.release_ms, 1, 500)),
            source_mode=str(self.source_mode if self.source_mode in ARTICULATION_SOURCE_MODES else ARTICULATION_SOURCE_DEFAULT),
            source_wave_id=str(self.source_wave_id) if self.source_wave_id else None,
            source_recipe_snapshot=dict(self.source_recipe_snapshot or {}),
            source_audio_path=str(self.source_audio_path) if self.source_audio_path else None,
            source_start_seconds=float(max(0.0, self.source_start_seconds)),
            source_duration_seconds=float(max(0.0, self.source_duration_seconds)),
            source_pitch_follow=bool(self.source_pitch_follow),
            source_loop_to_fit=bool(self.source_loop_to_fit),
            source_gain=float(np.clip(self.source_gain, 0.0, 4.0)),
        )

    def to_json_dict(self) -> Dict[str, object]:
        return asdict(self.clamped())

    @classmethod
    def from_json_dict(cls, data: Dict[str, object]) -> "ArticulationPhoneme":
        family = str(data.get("phoneme_family", data.get("family", "vowel"))).lower()
        default_voiced = family in {"vowel", "nasal"}
        return cls(
            name=str(data.get("name", "untitled_phoneme")),
            ipa=str(data.get("ipa", "?")),
            mouth_open=float(data.get("mouth_open", 0.45)),
            tongue_height=float(data.get("tongue_height", 0.45)),
            tongue_frontness=float(data.get("tongue_frontness", 0.50)),
            lip_rounding=float(data.get("lip_rounding", 0.10)),
            voice_pitch=float(data.get("voice_pitch", 220.0)),
            voice_strength=float(data.get("voice_strength", 0.65)),
            duration_ms=int(data.get("duration_ms", 500)),
            preview_color=str(data.get("preview_color", "#ffd166")),
            phoneme_family=family,
            air_pressure=float(data.get("air_pressure", 0.45)),
            teeth_gap=float(data.get("teeth_gap", 0.50)),
            closure=float(data.get("closure", 0.0)),
            burst_strength=float(data.get("burst_strength", 0.0)),
            nasal_open=float(data.get("nasal_open", 0.0)),
            voiced=bool(data.get("voiced", default_voiced)),
            noise_color=float(data.get("noise_color", 0.50)),
            attack_ms=int(data.get("attack_ms", 18)),
            release_ms=int(data.get("release_ms", 28)),
            source_mode=str(data.get("source_mode", ARTICULATION_SOURCE_DEFAULT)),
            source_wave_id=str(data.get("source_wave_id")) if data.get("source_wave_id") else None,
            source_recipe_snapshot=dict(data.get("source_recipe_snapshot") or {}),
            source_audio_path=str(data.get("source_audio_path")) if data.get("source_audio_path") else None,
            source_start_seconds=float(data.get("source_start_seconds", 0.0)),
            source_duration_seconds=float(data.get("source_duration_seconds", 0.0)),
            source_pitch_follow=bool(data.get("source_pitch_follow", True)),
            source_loop_to_fit=bool(data.get("source_loop_to_fit", True)),
            source_gain=float(data.get("source_gain", 1.0)),
        ).clamped()


def smoothstep(value: float) -> float:
    t = float(np.clip(value, 0.0, 1.0))
    return t * t * (3.0 - 2.0 * t)


def articulation_curve_progress(value: float, curve: str = ARTICULATION_DEFAULT_TRANSITION_CURVE) -> float:
    """Map a boundary-local 0..1 progress through the selected transition curve."""
    t = float(np.clip(value, 0.0, 1.0))
    curve = str(curve or ARTICULATION_DEFAULT_TRANSITION_CURVE)
    if curve == "Linear":
        return t
    if curve == "Ease In":
        return t * t
    if curve == "Ease Out":
        return 1.0 - (1.0 - t) * (1.0 - t)
    if curve == "Ease In Out":
        return 2.0 * t * t if t < 0.5 else 1.0 - ((-2.0 * t + 2.0) ** 2) / 2.0
    if curve == "Sigmoid":
        lo = 1.0 / (1.0 + math.exp(6.0))
        hi = 1.0 / (1.0 + math.exp(-6.0))
        raw = 1.0 / (1.0 + math.exp(-12.0 * (t - 0.5)))
        return float(np.clip((raw - lo) / (hi - lo), 0.0, 1.0))
    return smoothstep(t)


@dataclass
class ArticulationBoundary:
    """Editable articulation boundary shared by timeline, renderer, and save files."""

    transition_ms: int = ARTICULATION_DEFAULT_TRANSITION_MS
    transition_curve: str = ARTICULATION_DEFAULT_TRANSITION_CURVE

    def clamped(self) -> "ArticulationBoundary":
        curve = self.transition_curve if self.transition_curve in ARTICULATION_TRANSITION_CURVES else ARTICULATION_DEFAULT_TRANSITION_CURVE
        return ArticulationBoundary(transition_ms=int(np.clip(int(self.transition_ms), 0, 250)), transition_curve=curve)


def interpolate_articulation_phoneme(left: ArticulationPhoneme, right: ArticulationPhoneme, progress: float, curve: str = ARTICULATION_DEFAULT_TRANSITION_CURVE) -> ArticulationPhoneme:
    """Return a clamped non-mutating slider snapshot between two phonemes."""
    start = left.clamped()
    end = right.clamped()
    t = articulation_curve_progress(progress, curve)
    data = start.to_json_dict()
    for field_name in ARTICULATION_INTERPOLATED_FIELDS:
        data[field_name] = float(np.clip(float(getattr(start, field_name)) + (float(getattr(end, field_name)) - float(getattr(start, field_name))) * t, 0.0, 1.0))
    data["voice_pitch"] = float(np.clip(start.voice_pitch + (end.voice_pitch - start.voice_pitch) * t, 60.0, 880.0))
    data["noise_color"] = float(np.clip(start.noise_color + (end.noise_color - start.noise_color) * t, 0.0, 1.0))
    data["attack_ms"] = int(round(start.attack_ms + (end.attack_ms - start.attack_ms) * t))
    data["release_ms"] = int(round(start.release_ms + (end.release_ms - start.release_ms) * t))
    data["duration_ms"] = int(round(start.duration_ms + (end.duration_ms - start.duration_ms) * t))
    data["voiced"] = bool(start.voiced if progress < 0.5 else end.voiced)
    data["phoneme_family"] = start.phoneme_family if progress < 0.5 else end.phoneme_family
    data["name"] = f"{start.name}→{end.name}"
    data["ipa"] = f"{start.ipa}→{end.ipa}"
    data["preview_color"] = start.preview_color if progress < 0.5 else end.preview_color
    if progress >= 0.5:
        data["source_mode"] = end.source_mode
        data["source_wave_id"] = end.source_wave_id
        data["source_recipe_snapshot"] = end.source_recipe_snapshot or {}
        data["source_audio_path"] = end.source_audio_path
        data["source_start_seconds"] = end.source_start_seconds
        data["source_duration_seconds"] = end.source_duration_seconds
        data["source_pitch_follow"] = end.source_pitch_follow
        data["source_loop_to_fit"] = end.source_loop_to_fit
        data["source_gain"] = end.source_gain
    return ArticulationPhoneme.from_json_dict(data).clamped()


@dataclass
class ArticulationChainItem:
    """One editable phoneme card in an Articulation Chain."""

    phoneme: ArticulationPhoneme
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    duration_ms: int | None = None
    gap_after_ms: int = 0
    crossfade_ms: int = ARTICULATION_DEFAULT_WORD_CROSSFADE_MS
    transition_to_next_ms: int | None = None
    transition_curve: str = ARTICULATION_DEFAULT_TRANSITION_CURVE

    @property
    def transition_ms(self) -> int | None:
        """Backward-compatible alias for saved chains that used transition_ms."""
        return self.transition_to_next_ms

    @transition_ms.setter
    def transition_ms(self, value: int | None) -> None:
        self.transition_to_next_ms = value

    def __post_init__(self) -> None:
        self.phoneme = self.phoneme.clamped()
        if self.duration_ms is None:
            self.duration_ms = self.phoneme.duration_ms
        self.duration_ms = int(np.clip(int(self.duration_ms), 80, 5000))
        self.gap_after_ms = int(np.clip(int(self.gap_after_ms), 0, 2000))
        self.crossfade_ms = int(np.clip(int(self.crossfade_ms), 0, 250))
        if self.transition_to_next_ms is not None:
            self.transition_to_next_ms = int(np.clip(int(self.transition_to_next_ms), 0, 250))
        if self.transition_curve not in ARTICULATION_TRANSITION_CURVES:
            self.transition_curve = ARTICULATION_DEFAULT_TRANSITION_CURVE

    def phoneme_for_render(self) -> ArticulationPhoneme:
        data = self.phoneme.to_json_dict()
        data["duration_ms"] = int(self.duration_ms or self.phoneme.duration_ms)
        return ArticulationPhoneme.from_json_dict(data)

    def to_json_dict(self) -> Dict[str, object]:
        phoneme = self.phoneme_for_render()
        data = phoneme.to_json_dict()
        data.update(
            {
                "id": self.id,
                "phoneme_name": phoneme.name,
                "ipa": phoneme.ipa,
                "articulation_snapshot": phoneme.to_json_dict(),
                "duration_ms": int(self.duration_ms or phoneme.duration_ms),
                "gap_after_ms": int(self.gap_after_ms),
                "crossfade_ms": int(self.crossfade_ms),
                "transition_to_next_ms": int(self.transition_to_next_ms) if self.transition_to_next_ms is not None else None,
                "transition_ms": int(self.transition_to_next_ms) if self.transition_to_next_ms is not None else None,
                "transition_curve": self.transition_curve,
                "source_mode": phoneme.source_mode,
                "source_wave_id": phoneme.source_wave_id,
                "source_recipe_snapshot": phoneme.source_recipe_snapshot or {},
                "source_audio_path": phoneme.source_audio_path,
            }
        )
        return data

    @classmethod
    def from_json_dict(cls, data: Dict[str, object]) -> "ArticulationChainItem":
        snapshot = data.get("articulation_snapshot")
        phoneme_data = snapshot if isinstance(snapshot, dict) else data
        phoneme = ArticulationPhoneme.from_json_dict(phoneme_data)
        duration_ms = int(data.get("duration_ms", phoneme.duration_ms))
        phoneme.duration_ms = duration_ms
        return cls(
            phoneme=phoneme,
            id=str(data.get("id") or uuid.uuid4().hex),
            duration_ms=duration_ms,
            gap_after_ms=int(data.get("gap_after_ms", 0)),
            crossfade_ms=int(data.get("crossfade_ms", ARTICULATION_DEFAULT_WORD_CROSSFADE_MS)),
            transition_to_next_ms=int(data["transition_to_next_ms"]) if data.get("transition_to_next_ms") is not None else (int(data["transition_ms"]) if data.get("transition_ms") is not None else None),
            transition_curve=str(data.get("transition_curve", ARTICULATION_DEFAULT_TRANSITION_CURVE)),
        )


@dataclass
class ArticulationChain:
    """Serializable articulation-chain metadata, including the latest word render."""

    items: List[ArticulationChainItem] = field(default_factory=list)
    last_word_render_path: str | None = None
    last_word_render_created_at: float | None = None
    word_render_settings: Dict[str, object] = field(default_factory=dict)
    syllable_markers: List[Dict[str, object]] = field(default_factory=list)
    phrase_markers: List[Dict[str, object]] = field(default_factory=list)

    def to_json_dict(self) -> Dict[str, object]:
        return {
            "items": [item.to_json_dict() for item in self.items],
            "last_word_render_path": self.last_word_render_path,
            "last_word_render_created_at": self.last_word_render_created_at,
            "word_render_settings": self.word_render_settings,
            "syllable_markers": self.syllable_markers,
            "phrase_markers": self.phrase_markers,
        }


VOWEL_PRESETS: Dict[str, Dict[str, object]] = {
    "EE": {"emoji": "😀", "ipa": "i", "tongue_height": 0.95, "tongue_frontness": 0.95, "mouth_open": 0.20, "lip_rounding": 0.05, "preview_color": "#b8f2e6"},
    "EH": {"emoji": "🙂", "ipa": "e", "tongue_height": 0.70, "tongue_frontness": 0.85, "mouth_open": 0.40, "lip_rounding": 0.05, "preview_color": "#caffbf"},
    "AH": {"emoji": "😮", "ipa": "a", "tongue_height": 0.20, "tongue_frontness": 0.40, "mouth_open": 0.95, "lip_rounding": 0.00, "preview_color": "#ffadad"},
    "OH": {"emoji": "😯", "ipa": "o", "tongue_height": 0.50, "tongue_frontness": 0.20, "mouth_open": 0.55, "lip_rounding": 0.60, "preview_color": "#ffd6a5"},
    "OO": {"emoji": "😗", "ipa": "u", "tongue_height": 0.90, "tongue_frontness": 0.10, "mouth_open": 0.15, "lip_rounding": 1.00, "preview_color": "#a0c4ff"},
    "UH": {"emoji": "😐", "ipa": "ʌ", "tongue_height": 0.38, "tongue_frontness": 0.42, "mouth_open": 0.55, "lip_rounding": 0.12, "preview_color": "#d7b9ff"},
    "AE": {"emoji": "😺", "ipa": "æ", "tongue_height": 0.32, "tongue_frontness": 0.86, "mouth_open": 0.78, "lip_rounding": 0.02, "preview_color": "#ffb3c6"},
    "IH": {"emoji": "🙂", "ipa": "ɪ", "tongue_height": 0.78, "tongue_frontness": 0.82, "mouth_open": 0.30, "lip_rounding": 0.04, "preview_color": "#b9fbc0"},
    "IY": {"emoji": "😁", "ipa": "i", "tongue_height": 0.96, "tongue_frontness": 0.96, "mouth_open": 0.18, "lip_rounding": 0.03, "preview_color": "#98f5e1"},
    "ER": {"emoji": "🌀", "ipa": "ɝ", "tongue_height": 0.56, "tongue_frontness": 0.36, "mouth_open": 0.42, "lip_rounding": 0.32, "voice_pitch": 210.0, "preview_color": "#cdb4db"},
}

FRICATIVE_PRESETS: Dict[str, Dict[str, object]] = {
    "S": {"emoji": "🦷", "ipa": "s", "phoneme_family": "fricative", "voiced": False, "voice_strength": 0.20, "air_pressure": 0.85, "teeth_gap": 0.15, "tongue_frontness": 0.85, "mouth_open": 0.28, "tongue_height": 0.72, "lip_rounding": 0.0, "duration_ms": 420, "noise_color": 0.85, "preview_color": "#d7f9ff"},
    "Z": {"emoji": "🦷", "ipa": "z", "phoneme_family": "fricative", "voiced": True, "voice_strength": 0.72, "air_pressure": 0.75, "teeth_gap": 0.18, "tongue_frontness": 0.85, "mouth_open": 0.28, "tongue_height": 0.70, "duration_ms": 420, "noise_color": 0.80, "preview_color": "#c7f9cc"},
    "SH": {"emoji": "🤫", "ipa": "ʃ", "phoneme_family": "fricative", "voiced": False, "voice_strength": 0.32, "air_pressure": 0.80, "teeth_gap": 0.25, "tongue_frontness": 0.45, "mouth_open": 0.32, "tongue_height": 0.62, "lip_rounding": 0.55, "duration_ms": 460, "noise_color": 0.62, "preview_color": "#bde0fe"},
    "F": {"emoji": "🌬", "ipa": "f", "phoneme_family": "fricative", "voiced": False, "voice_strength": 0.18, "air_pressure": 0.75, "teeth_gap": 0.20, "tongue_frontness": 0.50, "mouth_open": 0.22, "tongue_height": 0.45, "lip_rounding": 0.15, "duration_ms": 380, "noise_color": 0.55, "preview_color": "#e0fbfc"},
    "V": {"emoji": "🌬", "ipa": "v", "phoneme_family": "fricative", "voiced": True, "voice_strength": 0.76, "air_pressure": 0.65, "teeth_gap": 0.22, "tongue_frontness": 0.50, "mouth_open": 0.22, "tongue_height": 0.45, "duration_ms": 380, "noise_color": 0.50, "preview_color": "#caffbf"},
    "H": {"emoji": "💨", "ipa": "h", "phoneme_family": "fricative", "voiced": False, "voice_strength": 0.24, "air_pressure": 0.60, "teeth_gap": 0.75, "tongue_frontness": 0.45, "mouth_open": 0.55, "tongue_height": 0.35, "duration_ms": 360, "noise_color": 0.35, "preview_color": "#f1faee"},
}

STOP_PRESETS: Dict[str, Dict[str, object]] = {
    "P": {"emoji": "💥", "ipa": "p", "phoneme_family": "stop", "voiced": False, "closure": 1.0, "burst_strength": 0.75, "mouth_open": 0.12, "tongue_height": 0.35, "tongue_frontness": 0.50, "lip_rounding": 0.20, "duration_ms": 180, "noise_color": 0.50, "preview_color": "#ffd6a5"},
    "B": {"emoji": "💥", "ipa": "b", "phoneme_family": "stop", "voiced": True, "closure": 1.0, "burst_strength": 0.55, "mouth_open": 0.12, "tongue_height": 0.35, "tongue_frontness": 0.50, "duration_ms": 200, "noise_color": 0.45, "preview_color": "#fdffb6"},
    "T": {"emoji": "⚡", "ipa": "t", "phoneme_family": "stop", "voiced": False, "air_pressure": 0.70, "teeth_gap": 0.18, "closure": 1.0, "burst_strength": 0.68, "tongue_frontness": 0.90, "mouth_open": 0.18, "tongue_height": 0.72, "duration_ms": 170, "noise_color": 0.75, "preview_color": "#ffadad"},
    "D": {"emoji": "⚡", "ipa": "d", "phoneme_family": "stop", "voiced": True, "air_pressure": 0.42, "teeth_gap": 0.38, "closure": 0.90, "burst_strength": 0.35, "voice_strength": 0.70, "tongue_frontness": 0.90, "mouth_open": 0.18, "tongue_height": 0.70, "duration_ms": 200, "noise_color": 0.40, "preview_color": "#ffc6ff"},
    "K": {"emoji": "🪨", "ipa": "k", "phoneme_family": "stop", "voiced": False, "closure": 1.0, "burst_strength": 0.80, "tongue_frontness": 0.20, "mouth_open": 0.20, "tongue_height": 0.65, "duration_ms": 190, "noise_color": 0.38, "preview_color": "#a0c4ff"},
    "G": {"emoji": "🪨", "ipa": "g", "phoneme_family": "stop", "voiced": True, "closure": 1.0, "burst_strength": 0.55, "tongue_frontness": 0.20, "mouth_open": 0.20, "tongue_height": 0.65, "duration_ms": 220, "noise_color": 0.34, "preview_color": "#bdb2ff"},
}

NASAL_PRESETS: Dict[str, Dict[str, object]] = {
    "M": {"emoji": "👃", "ipa": "m", "phoneme_family": "nasal", "voiced": True, "nasal_open": 0.95, "closure": 0.90, "mouth_open": 0.10, "tongue_height": 0.45, "tongue_frontness": 0.45, "lip_rounding": 0.35, "duration_ms": 460, "preview_color": "#cdb4db"},
    "N": {"emoji": "👃", "ipa": "n", "phoneme_family": "nasal", "voiced": True, "nasal_open": 0.90, "closure": 0.80, "tongue_frontness": 0.85, "mouth_open": 0.12, "tongue_height": 0.65, "duration_ms": 460, "preview_color": "#bde0fe"},
    "NG": {"emoji": "👃", "ipa": "ŋ", "phoneme_family": "nasal", "voiced": True, "nasal_open": 0.90, "closure": 0.80, "tongue_frontness": 0.20, "mouth_open": 0.12, "tongue_height": 0.72, "duration_ms": 500, "preview_color": "#a2d2ff"},
}

GLIDE_PRESETS: Dict[str, Dict[str, object]] = {
    "W": {"emoji": "〰️", "ipa": "w", "phoneme_family": "glide", "voiced": True, "mouth_open": 0.28, "tongue_height": 0.82, "tongue_frontness": 0.18, "lip_rounding": 0.92, "duration_ms": 260, "preview_color": "#a0c4ff"},
    "Y": {"emoji": "➰", "ipa": "j", "phoneme_family": "glide", "voiced": True, "mouth_open": 0.24, "tongue_height": 0.90, "tongue_frontness": 0.92, "lip_rounding": 0.05, "duration_ms": 240, "preview_color": "#b8f2e6"},
}

LIQUID_PRESETS: Dict[str, Dict[str, object]] = {
    "L": {"emoji": "👅", "ipa": "l", "phoneme_family": "liquid", "voiced": True, "mouth_open": 0.42, "tongue_height": 0.68, "tongue_frontness": 0.88, "lip_rounding": 0.10, "duration_ms": 360, "preview_color": "#fdffb6"},
    "R": {"emoji": "🌀", "ipa": "ɹ", "phoneme_family": "liquid", "voiced": True, "mouth_open": 0.38, "tongue_height": 0.58, "tongue_frontness": 0.35, "lip_rounding": 0.36, "duration_ms": 380, "preview_color": "#ffc6ff"},
}

AFFRICATE_PRESETS: Dict[str, Dict[str, object]] = {
    "CH": {"emoji": "💥", "ipa": "tʃ", "phoneme_family": "affricate", "voiced": False, "air_pressure": 0.84, "teeth_gap": 0.24, "closure": 0.82, "burst_strength": 0.74, "tongue_frontness": 0.72, "mouth_open": 0.26, "tongue_height": 0.68, "lip_rounding": 0.34, "duration_ms": 260, "noise_color": 0.68, "preview_color": "#ffadad"},
    "JH": {"emoji": "💥", "ipa": "dʒ", "phoneme_family": "affricate", "voiced": True, "air_pressure": 0.72, "teeth_gap": 0.25, "closure": 0.74, "burst_strength": 0.56, "tongue_frontness": 0.70, "mouth_open": 0.28, "tongue_height": 0.66, "lip_rounding": 0.30, "duration_ms": 280, "noise_color": 0.62, "preview_color": "#ffd6a5"},
}

EXTRA_FRICATIVE_PRESETS: Dict[str, Dict[str, object]] = {
    "TH": {"emoji": "🦷", "ipa": "θ", "phoneme_family": "fricative", "voiced": False, "air_pressure": 0.78, "teeth_gap": 0.32, "tongue_frontness": 0.96, "mouth_open": 0.24, "tongue_height": 0.52, "lip_rounding": 0.02, "duration_ms": 390, "noise_color": 0.72, "preview_color": "#e0fbfc"},
    "DH": {"emoji": "🦷", "ipa": "ð", "phoneme_family": "fricative", "voiced": True, "air_pressure": 0.68, "teeth_gap": 0.34, "tongue_frontness": 0.95, "mouth_open": 0.24, "tongue_height": 0.52, "lip_rounding": 0.02, "duration_ms": 390, "noise_color": 0.68, "preview_color": "#caffbf"},
    "ZH": {"emoji": "🤫", "ipa": "ʒ", "phoneme_family": "fricative", "voiced": True, "air_pressure": 0.70, "teeth_gap": 0.28, "tongue_frontness": 0.42, "mouth_open": 0.30, "tongue_height": 0.62, "lip_rounding": 0.48, "duration_ms": 440, "noise_color": 0.58, "preview_color": "#bde0fe"},
}

CONSONANT_PRESET_SECTIONS: Tuple[Tuple[str, Dict[str, Dict[str, object]]], ...] = (
    ("🌬 Friction Sounds", FRICATIVE_PRESETS),
    ("💥 Pop Sounds", STOP_PRESETS),
    ("👃 Nose Sounds", NASAL_PRESETS),
    ("〰️ Glides", GLIDE_PRESETS),
    ("👅 Liquids", LIQUID_PRESETS),
    ("💥 Affricates", AFFRICATE_PRESETS),
    ("🦷 Extra Fricatives", EXTRA_FRICATIVE_PRESETS),
)



def articulation_summary(phoneme: ArticulationPhoneme) -> str:
    family_word = phoneme.phoneme_family.title()
    open_word = "Open Mouth" if phoneme.mouth_open >= 0.66 else "Small Mouth" if phoneme.mouth_open <= 0.28 else "Medium Mouth"
    height_word = "High Tongue" if phoneme.tongue_height >= 0.66 else "Low Tongue" if phoneme.tongue_height <= 0.34 else "Mid Tongue"
    front_word = "Front Tongue" if phoneme.tongue_frontness >= 0.66 else "Back Tongue" if phoneme.tongue_frontness <= 0.34 else "Center Tongue"
    round_word = "Rounded Lips" if phoneme.lip_rounding >= 0.55 else "Relaxed Lips"
    voice_word = "Voiced" if phoneme.voiced else "Unvoiced"
    if phoneme.phoneme_family == "fricative":
        return f"{family_word} | {voice_word} | Air {phoneme.air_pressure:.2f} | Teeth Gap {phoneme.teeth_gap:.2f}"
    if phoneme.phoneme_family == "stop":
        sharpness = 1.0 - float(np.clip(phoneme.teeth_gap, 0.0, 1.0))
        return f"{family_word} | {voice_word} | Closure {phoneme.closure:.2f} | Burst {phoneme.burst_strength:.2f} | Air {phoneme.air_pressure:.2f} | Release sharpness {sharpness:.2f}"
    if phoneme.phoneme_family == "nasal":
        return f"{family_word} | {voice_word} | Nose Open {phoneme.nasal_open:.2f} | {front_word}"
    return f"{family_word} | {open_word} | {height_word} | {front_word} | {round_word}"


def formants_from_articulation(phoneme: ArticulationPhoneme) -> Tuple[float, float, float]:
    mouth = float(np.clip(phoneme.mouth_open, 0.0, 1.0))
    front = float(np.clip(phoneme.tongue_frontness, 0.0, 1.0))
    height = float(np.clip(phoneme.tongue_height, 0.0, 1.0))
    rounding = float(np.clip(phoneme.lip_rounding, 0.0, 1.0))
    f1 = 260.0 + mouth * 620.0 - height * 90.0
    f2 = 850.0 + front * 1450.0 - rounding * 380.0
    f3 = 2300.0 + height * 650.0 - rounding * 280.0
    return max(180.0, f1), max(500.0, f2), max(1400.0, f3)


def apply_simple_formant_layer(audio: np.ndarray, phoneme: ArticulationPhoneme) -> np.ndarray:
    if audio.size == 0:
        return audio
    mono = np.asarray(audio, dtype=np.float64)
    if mono.ndim == 2:
        mono = mono.mean(axis=1)
    window = np.hanning(mono.size) if mono.size > 8 else np.ones(mono.size)
    spectrum = np.fft.rfft(mono * window)
    freqs = np.fft.rfftfreq(mono.size, 1.0 / SAMPLE_RATE)
    f1, f2, f3 = formants_from_articulation(phoneme)
    envelope = np.full_like(freqs, 0.10, dtype=np.float64)
    for center, width, gain in ((f1, 120.0, 1.8), (f2, 210.0, 1.25), (f3, 330.0, 0.85)):
        envelope += gain * np.exp(-0.5 * ((freqs - center) / width) ** 2)
    envelope *= 1.0 - 0.35 * float(np.clip(phoneme.lip_rounding, 0.0, 1.0)) * np.clip((freqs - 1800.0) / 5000.0, 0.0, 1.0)
    filtered = np.fft.irfft(spectrum * envelope, n=mono.size)
    peak = float(np.max(np.abs(filtered))) if filtered.size else 0.0
    if peak > 0.0:
        filtered = (filtered / peak) * (0.75 * float(np.clip(phoneme.voice_strength, 0.0, 1.0)))
    return np.column_stack([filtered, filtered]).astype(np.float32)


def _fade_and_normalize_mono(mono: np.ndarray, attack_ms: int, release_ms: int, peak: float = 0.78, normalize: bool = True) -> np.ndarray:
    mono = np.asarray(mono, dtype=np.float64)
    if mono.size == 0:
        return np.zeros((0, 2), dtype=np.float32)
    attack = min(max(1, int(SAMPLE_RATE * attack_ms / 1000.0)), max(1, mono.size // 2))
    release = min(max(1, int(SAMPLE_RATE * release_ms / 1000.0)), max(1, mono.size // 2))
    mono[:attack] *= np.linspace(0.0, 1.0, attack, dtype=np.float64)
    mono[-release:] *= np.linspace(1.0, 0.0, release, dtype=np.float64)
    current_peak = float(np.max(np.abs(mono))) if mono.size else 0.0
    if normalize and current_peak > 0.0:
        mono = mono / current_peak * peak
    elif not normalize:
        mono = np.clip(mono, -peak, peak)
    return np.column_stack([mono, mono]).astype(np.float32)


def _colored_noise(sample_count: int, phoneme: ArticulationPhoneme) -> np.ndarray:
    rng_seed = abs(hash((phoneme.name, phoneme.ipa, phoneme.phoneme_family))) % (2 ** 32)
    rng = np.random.default_rng(rng_seed)
    noise = rng.normal(0.0, 1.0, sample_count)
    spectrum = np.fft.rfft(noise)
    freqs = np.fft.rfftfreq(sample_count, 1.0 / SAMPLE_RATE)
    brightness = float(np.clip((phoneme.noise_color + phoneme.tongue_frontness + (1.0 - phoneme.lip_rounding)) / 3.0, 0.0, 1.0))
    center = 650.0 + brightness * 6100.0
    width = 420.0 + phoneme.teeth_gap * 2400.0 + phoneme.air_pressure * 1200.0
    envelope = 0.08 + np.exp(-0.5 * ((freqs - center) / max(180.0, width)) ** 2)
    envelope += 0.35 * np.clip(freqs / 8000.0, 0.0, 1.0) * brightness
    return np.fft.irfft(spectrum * envelope, n=sample_count)


def _stop_burst_parameters(phoneme: ArticulationPhoneme) -> Dict[str, float]:
    """Map stop articulation controls to a short release burst."""
    phoneme = phoneme.clamped()
    name = phoneme.name.upper()
    air = float(np.clip(phoneme.air_pressure, 0.0, 1.0))
    teeth = float(np.clip(phoneme.teeth_gap, 0.0, 1.0))
    closure = float(np.clip(phoneme.closure, 0.0, 1.0))
    burst = float(np.clip(phoneme.burst_strength, 0.0, 1.0))
    voiced_gain = _articulation_voiced_gain(phoneme)
    voiced_stop = bool(phoneme.voiced and voiced_gain > 0.0)

    place_brightness = {"P": 0.38, "B": 0.30, "T": 0.88, "D": 0.48, "K": 0.58, "G": 0.34}.get(
        name,
        0.36 + phoneme.tongue_frontness * 0.42 + phoneme.tongue_height * 0.14,
    )
    voice_darkening = 0.26 if voiced_stop else 0.0
    burst_brightness = float(np.clip(place_brightness + (1.0 - teeth) * 0.32 + phoneme.noise_color * 0.16 + air * 0.08 - voice_darkening, 0.08, 1.0))
    if voiced_stop:
        noise_multiplier = {"B": 0.48, "D": 0.42, "G": 0.45}.get(name, 0.50)
        duration_min, duration_max = {"D": (12.0, 28.0), "B": (12.0, 24.0), "G": (14.0, 30.0)}.get(name, (12.0, 30.0))
    else:
        noise_multiplier = {"T": 1.0, "P": 0.82, "K": 0.90}.get(name, 0.88)
        duration_min, duration_max = {"T": (35.0, 55.0), "P": (24.0, 42.0), "K": (30.0, 50.0)}.get(name, (24.0, 48.0))
    burst_ms = float(duration_min + (duration_max - duration_min) * burst)
    closure_samples = int(max(1, round((0.10 + closure * 0.42) * max(1, phoneme.duration_ms) * SAMPLE_RATE / 1000.0)))
    burst_samples = int(max(1, round(burst_ms * SAMPLE_RATE / 1000.0)))
    burst_gain = float(np.clip((air ** 1.35) * (burst ** 1.15) * (0.35 + closure * 0.65) * noise_multiplier, 0.0, 1.25))
    voiced_onset_gain = float(np.clip(voiced_gain * (0.28 + closure * 0.32 + (1.0 - burst) * 0.14), 0.0, 1.0)) if voiced_stop else 0.0
    return {
        "air_pressure": air,
        "teeth_gap": teeth,
        "closure": closure,
        "burst_strength": burst,
        "closure_samples": float(closure_samples),
        "burst_samples": float(burst_samples),
        "burst_ms": burst_ms,
        "burst_gain": burst_gain,
        "burst_brightness": burst_brightness,
        "voiced_onset_gain": voiced_onset_gain,
        "noise_multiplier": noise_multiplier,
    }


def _stop_burst_noise(sample_count: int, phoneme: ArticulationPhoneme) -> np.ndarray:
    """Generate stop-only transient noise instead of sustained fricative hiss."""
    if sample_count <= 0:
        return np.zeros(0, dtype=np.float64)
    params = _stop_burst_parameters(phoneme)
    rng_seed = abs(hash(("stop_burst", phoneme.name, phoneme.ipa, round(params["burst_brightness"], 2)))) % (2 ** 32)
    rng = np.random.default_rng(rng_seed)
    noise = rng.normal(0.0, 1.0, sample_count)
    spectrum = np.fft.rfft(noise)
    freqs = np.fft.rfftfreq(sample_count, 1.0 / SAMPLE_RATE)
    brightness = float(params["burst_brightness"])
    center = 700.0 + brightness * 6200.0
    width = 360.0 + (1.0 - float(params["teeth_gap"])) * 1200.0 + brightness * 1800.0
    envelope = 0.015 + np.exp(-0.5 * ((freqs - center) / max(160.0, width)) ** 2)
    high_shelf = np.clip((freqs - 2400.0) / 5200.0, 0.0, 1.0)
    envelope += high_shelf * brightness * (0.18 + (1.0 - float(params["teeth_gap"])) * 0.46)
    if phoneme.voiced:
        lowpass = 1.0 / (1.0 + (freqs / (1800.0 + brightness * 2600.0)) ** 2)
        envelope *= 0.34 + lowpass * 0.92
    shaped = np.fft.irfft(spectrum * envelope, n=sample_count)
    peak = float(np.max(np.abs(shaped))) if shaped.size else 0.0
    if peak > 1.0e-9:
        shaped = shaped / peak
    return shaped


def _log_stop_render(phoneme: ArticulationPhoneme, params: Dict[str, float], sample_count: int) -> None:
    print(
        "[WaveToy Stop] "
        f"phoneme={phoneme.name} voiced={bool(phoneme.voiced)} "
        f"air_pressure={params['air_pressure']:.2f} teeth_gap={params['teeth_gap']:.2f} "
        f"closure={params['closure']:.2f} burst_strength={params['burst_strength']:.2f} "
        f"closure_samples={int(params['closure_samples'])} burst_samples={int(params['burst_samples'])} "
        f"burst_gain={params['burst_gain']:.3f} burst_brightness={params['burst_brightness']:.3f} "
        f"voiced_onset_gain={params['voiced_onset_gain']:.3f} total_samples={int(sample_count)}"
    )


def _voiced_tone(sample_count: int, phoneme: ArticulationPhoneme) -> np.ndarray:
    t = np.arange(sample_count, dtype=np.float64) / SAMPLE_RATE
    pitch = float(np.clip(phoneme.voice_pitch, 60.0, 880.0))
    tone = np.sin(2.0 * np.pi * pitch * t)
    tone += 0.35 * np.sin(2.0 * np.pi * pitch * 2.0 * t)
    tone += 0.18 * np.sin(2.0 * np.pi * pitch * 3.0 * t)
    return tone * float(np.clip(phoneme.voice_strength, 0.0, 1.0))


def _articulation_voiced_gain(phoneme: ArticulationPhoneme) -> float:
    """Boolean Voice On gate times continuous Voice Strength."""
    return float(np.clip(phoneme.voice_strength, 0.0, 1.0)) if phoneme.voiced else 0.0


def _fricative_family_mix(phoneme: ArticulationPhoneme) -> Dict[str, float]:
    """Return independent source gains for the modular fricative model."""
    name = phoneme.name.upper()
    voiced_gain = _articulation_voiced_gain(phoneme)
    air = float(np.clip(phoneme.air_pressure, 0.0, 1.0))
    noise_base = {"S": 1.05, "Z": 0.86, "SH": 0.92, "F": 0.98, "V": 0.62, "H": 0.70}.get(name, 0.82)
    tone_base = {"S": 0.10, "Z": 0.42, "SH": 0.28, "F": 0.14, "V": 0.58, "H": 0.18}.get(name, 0.26)
    turbulent_gain = (0.08 + air * air * 1.18) * noise_base
    airflow_gain = (0.03 + air * 0.34) * (0.35 + phoneme.teeth_gap * 0.65)
    tonal_gain = tone_base * (0.18 + voiced_gain * 0.82)
    return {
        "voiced_gain": voiced_gain,
        "noise_gain": float(np.clip(turbulent_gain + airflow_gain, 0.0, 1.8)),
        "tonal_gain": float(np.clip(tonal_gain, 0.0, 1.0)),
        "air_pressure": air,
        "voice_strength": float(np.clip(phoneme.voice_strength, 0.0, 1.0)),
    }


def articulation_synthesis_debug(phoneme: ArticulationPhoneme) -> Dict[str, object]:
    phoneme = phoneme.clamped()
    if phoneme.phoneme_family in {"fricative", "affricate"}:
        mix = _fricative_family_mix(phoneme)
    elif phoneme.phoneme_family == "stop":
        voiced_gain = _articulation_voiced_gain(phoneme)
        stop_params = _stop_burst_parameters(phoneme)
        residual_noise = float(stop_params["burst_gain"] * (0.10 if phoneme.voiced else 0.18))
        mix = {
            "voiced_gain": voiced_gain,
            "noise_gain": residual_noise,
            "tonal_gain": float(voiced_gain * (0.58 if phoneme.voiced else 0.0)),
            "air_pressure": float(stop_params["air_pressure"]),
            "voice_strength": float(np.clip(phoneme.voice_strength, 0.0, 1.0)),
            "burst_gain": float(stop_params["burst_gain"]),
            "burst_brightness": float(stop_params["burst_brightness"]),
            "closure_samples": int(stop_params["closure_samples"]),
            "burst_samples": int(stop_params["burst_samples"]),
            "voiced_onset_gain": float(stop_params["voiced_onset_gain"]),
        }
    else:
        voiced_gain = _articulation_voiced_gain(phoneme)
        air = float(np.clip(phoneme.air_pressure, 0.0, 1.0))
        family = phoneme.phoneme_family
        noise_gain = air * (0.10 if family in {"vowel", "liquid", "glide"} else 0.35)
        tonal_gain = voiced_gain * (0.70 if family in {"vowel", "nasal", "liquid", "glide"} else 0.38)
        mix = {
            "voiced_gain": voiced_gain,
            "noise_gain": float(noise_gain),
            "tonal_gain": float(tonal_gain),
            "air_pressure": air,
            "voice_strength": float(np.clip(phoneme.voice_strength, 0.0, 1.0)),
        }
    mix["source_mode"] = phoneme.source_mode
    return mix


def _centered_tone(sample_count: int, phoneme: ArticulationPhoneme) -> np.ndarray:
    t = np.arange(sample_count, dtype=np.float64) / SAMPLE_RATE
    pitch = float(np.clip(phoneme.voice_pitch, 60.0, 880.0))
    tone = np.sin(2.0 * np.pi * pitch * t)
    tone += 0.16 * np.sin(2.0 * np.pi * pitch * 2.0 * t)
    return tone


def prepare_articulation_source_audio(
    source_audio: np.ndarray,
    phoneme: ArticulationPhoneme,
    duration_seconds: float | None = None,
) -> np.ndarray:
    """Trim, loop, fade, and normalize arbitrary audio for articulation shaping."""
    duration = max(0.08, float(duration_seconds if duration_seconds is not None else phoneme.duration_ms / 1000.0))
    target_samples = max(1, int(round(duration * SAMPLE_RATE)))
    audio = _ensure_stereo_float(source_audio)
    if audio.size == 0:
        return np.zeros((target_samples, 2), dtype=np.float32)

    start = min(len(audio), max(0, int(round(phoneme.source_start_seconds * SAMPLE_RATE))))
    requested = int(round(phoneme.source_duration_seconds * SAMPLE_RATE)) if phoneme.source_duration_seconds > 0 else 0
    if requested > 0:
        audio = audio[start:min(len(audio), start + requested)]
    else:
        audio = audio[start:]
    if audio.size == 0:
        audio = _ensure_stereo_float(source_audio)

    if len(audio) < target_samples and phoneme.source_loop_to_fit:
        repeats = int(math.ceil(target_samples / max(1, len(audio))))
        audio = np.tile(audio, (repeats, 1))
    if len(audio) < target_samples:
        padding = np.zeros((target_samples - len(audio), 2), dtype=np.float32)
        audio = np.vstack([audio, padding])
    audio = np.array(audio[:target_samples], dtype=np.float32, copy=True)

    fade = min(max(1, int(0.012 * SAMPLE_RATE)), max(1, target_samples // 3))
    if target_samples > fade * 2:
        audio[:fade] *= np.linspace(0.0, 1.0, fade, dtype=np.float32)[:, None]
        audio[-fade:] *= np.linspace(1.0, 0.0, fade, dtype=np.float32)[:, None]
    peak = float(np.max(np.abs(audio))) if audio.size else 0.0
    if peak > 1e-7:
        audio = (audio / peak) * float(np.clip(phoneme.source_gain, 0.0, 4.0))
    return np.clip(audio, -1.0, 1.0).astype(np.float32)


def _shape_articulation_source(source_audio: np.ndarray, phoneme: ArticulationPhoneme, duration_seconds: float | None = None) -> np.ndarray:
    """Use an external waveform as the vocal excitation, preserving consonant character."""
    source = prepare_articulation_source_audio(source_audio, phoneme, duration_seconds)
    if source.size == 0:
        return render_articulation_phoneme(phoneme)

    family = phoneme.phoneme_family
    if family in {"fricative", "affricate"}:
        shaped = apply_simple_formant_layer(source, phoneme)
        noise = _render_fricative_phoneme(phoneme)
        noise = prepare_articulation_source_audio(noise, phoneme, len(source) / SAMPLE_RATE)
        source_mix = float(np.clip(1.0 - phoneme.air_pressure * 0.65, 0.20, 0.80))
        return normalize_audio(shaped * source_mix + noise * (1.0 - source_mix)).astype(np.float32)

    if family == "stop":
        base = _render_stop_phoneme(phoneme)
        base = prepare_articulation_source_audio(base, phoneme, len(source) / SAMPLE_RATE)
        if _articulation_voiced_gain(phoneme) > 0.0:
            onset = apply_simple_formant_layer(source, phoneme) * 0.55
            closure_samples = min(len(source) - 1, int(len(source) * (0.25 + phoneme.closure * 0.30)))
            base[closure_samples:] += onset[closure_samples:]
        return normalize_audio(base).astype(np.float32)

    if family == "nasal":
        mono = source.mean(axis=1).astype(np.float64)
        spectrum = np.fft.rfft(mono)
        freqs = np.fft.rfftfreq(mono.size, 1.0 / SAMPLE_RATE)
        nasal_center = 240.0 + (1.0 - phoneme.tongue_frontness) * 180.0
        envelope = 0.12 + (1.10 + phoneme.nasal_open * 0.75) * np.exp(-0.5 * ((freqs - nasal_center) / 110.0) ** 2)
        envelope *= 1.0 / (1.0 + (freqs / (1200.0 + phoneme.nasal_open * 1400.0)) ** 2)
        mono = np.fft.irfft(spectrum * envelope, n=mono.size)
        return _fade_and_normalize_mono(mono, phoneme.attack_ms, phoneme.release_ms, peak=0.72)

    return apply_simple_formant_layer(source, phoneme)


def _render_fricative_phoneme(phoneme: ArticulationPhoneme) -> np.ndarray:
    phoneme = phoneme.clamped()
    duration = float(np.clip(phoneme.duration_ms / 1000.0, 0.30, 0.60))
    sample_count = max(1, int(duration * SAMPLE_RATE))
    mix = _fricative_family_mix(phoneme)

    noise_source = _colored_noise(sample_count, phoneme)
    noise_peak = float(np.max(np.abs(noise_source))) if noise_source.size else 0.0
    if noise_peak > 0.0:
        noise_source = noise_source / noise_peak
    tonal_source = _centered_tone(sample_count, phoneme)
    voiced_source = _voiced_tone(sample_count, phoneme) if phoneme.voiced else np.zeros(sample_count, dtype=np.float64)

    mono = (
        noise_source * float(mix["noise_gain"])
        + tonal_source * float(mix["tonal_gain"])
        + voiced_source * float(mix["voiced_gain"]) * 0.32
    )
    peak = 0.18 + float(mix["air_pressure"]) * 0.62 + float(mix["tonal_gain"]) * 0.12
    return _fade_and_normalize_mono(mono, phoneme.attack_ms, phoneme.release_ms, peak=float(np.clip(peak, 0.16, 0.88)))


def _render_stop_phoneme(phoneme: ArticulationPhoneme) -> np.ndarray:
    phoneme = phoneme.clamped()
    duration = float(np.clip(phoneme.duration_ms / 1000.0, 0.12, 0.25))
    sample_count = max(1, int(duration * SAMPLE_RATE))
    mono = np.zeros(sample_count, dtype=np.float64)
    params = _stop_burst_parameters(phoneme)
    closure_samples = min(sample_count - 1, int(params["closure_samples"]))
    burst_samples = min(sample_count - closure_samples, max(1, int(params["burst_samples"])))
    _log_stop_render(phoneme, {**params, "closure_samples": float(closure_samples), "burst_samples": float(burst_samples)}, sample_count)

    if burst_samples > 0 and params["burst_gain"] > 0.0:
        burst = _stop_burst_noise(burst_samples, phoneme)
        burst_env = np.exp(-np.linspace(0.0, 5.0, burst_samples, dtype=np.float64))
        burst_env *= np.linspace(1.0, 0.25, burst_samples, dtype=np.float64)
        mono[closure_samples:closure_samples + burst_samples] += burst * burst_env * params["burst_gain"]

    voiced_gain = _articulation_voiced_gain(phoneme)
    if voiced_gain > 0.0:
        tone = _voiced_tone(sample_count, phoneme)
        if closure_samples > 0:
            leak_gain = voiced_gain * (1.0 - params["closure"]) * 0.12
            mono[:closure_samples] += tone[:closure_samples] * leak_gain
        if closure_samples < sample_count:
            onset = tone[closure_samples:]
            onset_env = np.linspace(0.35, 1.0, onset.size, dtype=np.float64)
            mono[closure_samples:] += onset * onset_env * params["voiced_onset_gain"]

    peak = float(np.clip(0.10 + params["burst_gain"] * 0.62 + params["voiced_onset_gain"] * 0.36, 0.08, 0.82))
    release_ms = int(np.clip(params["burst_ms"] + 10.0, 18.0, 65.0))
    return _fade_and_normalize_mono(mono, 2, max(phoneme.release_ms, release_ms), peak=peak)


def _render_nasal_phoneme(phoneme: ArticulationPhoneme) -> np.ndarray:
    duration = float(np.clip(phoneme.duration_ms / 1000.0, 0.30, 0.60))
    sample_count = max(1, int(duration * SAMPLE_RATE))
    tone = _voiced_tone(sample_count, phoneme) if phoneme.voiced else _colored_noise(sample_count, phoneme) * 0.04
    spectrum = np.fft.rfft(tone)
    freqs = np.fft.rfftfreq(sample_count, 1.0 / SAMPLE_RATE)
    nasal_center = 240.0 + (1.0 - phoneme.tongue_frontness) * 180.0
    envelope = 0.18 + 1.55 * np.exp(-0.5 * ((freqs - nasal_center) / 95.0) ** 2)
    envelope += 0.45 * np.exp(-0.5 * ((freqs - 950.0) / 260.0) ** 2)
    envelope *= 1.0 / (1.0 + (freqs / (1500.0 + phoneme.nasal_open * 1200.0)) ** 2)
    mono = np.fft.irfft(spectrum * envelope, n=sample_count) * (0.45 + phoneme.nasal_open * 0.55)
    return _fade_and_normalize_mono(mono, phoneme.attack_ms, phoneme.release_ms, peak=0.70)


def render_articulation_phoneme(phoneme: ArticulationPhoneme, source_audio: np.ndarray | None = None) -> np.ndarray:
    phoneme = phoneme.clamped()
    if source_audio is not None and phoneme.source_mode != ARTICULATION_SOURCE_DEFAULT:
        return _shape_articulation_source(source_audio, phoneme)
    if phoneme.phoneme_family in {"fricative", "affricate"}:
        return _render_fricative_phoneme(phoneme)
    if phoneme.phoneme_family == "stop":
        return _render_stop_phoneme(phoneme)
    if phoneme.phoneme_family == "nasal":
        return _render_nasal_phoneme(phoneme)

    duration = max(0.12, phoneme.duration_ms / 1000.0)
    voiced_gain = _articulation_voiced_gain(phoneme)
    settings = SynthSettings(
        wave_start_db={"sine": -7.0, "triangle": -12.0, "sawtooth": -10.0, "square": -20.0},
        wave_end_db={"sine": -7.0, "triangle": -12.0, "sawtooth": -10.0, "square": -20.0},
        wave_delta_time={wave: duration for wave in WAVE_ORDER},
        pitch_start_hz=phoneme.voice_pitch,
        pitch_end_hz=phoneme.voice_pitch,
        loudness_start=voiced_gain,
        loudness_end=voiced_gain,
        duration_seconds=duration,
        curve_type="linear",
        pan_start=0.0,
        pan_end=0.0,
        stereo_width=0.15,
        wave_pan={wave: 0.0 for wave in WAVE_ORDER},
        wave_width={wave: 0.0 for wave in WAVE_ORDER},
        wave_dance={wave: 0.0 for wave in WAVE_ORDER},
        wave_muted={wave: False for wave in WAVE_ORDER},
        enabled_modules={"paulstretch": False},
    )
    audio, _time_axis, _freq_env, _loud_env = generate_audio(settings)
    audio = apply_simple_formant_layer(audio, phoneme)
    if len(audio):
        breath_gain = float(np.clip(phoneme.air_pressure, 0.0, 1.0)) * (0.025 if voiced_gain > 0.0 else 0.12)
        if breath_gain > 0.0:
            breath = _colored_noise(len(audio), phoneme)
            breath_peak = float(np.max(np.abs(breath))) if breath.size else 0.0
            if breath_peak > 0.0:
                breath = breath / breath_peak * breath_gain
                audio += np.column_stack([breath, breath]).astype(np.float32)
    fade_samples = min(int(0.025 * SAMPLE_RATE), max(1, len(audio) // 3))
    if len(audio) > fade_samples * 2:
        fade_in = np.linspace(0.0, 1.0, fade_samples, dtype=np.float32)
        fade_out = np.linspace(1.0, 0.0, fade_samples, dtype=np.float32)
        audio[:fade_samples] *= fade_in[:, None]
        audio[-fade_samples:] *= fade_out[:, None]
    return audio


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
    wave_pan: Dict[str, float] | None = None
    wave_width: Dict[str, float] | None = None
    wave_dance: Dict[str, float] | None = None
    wave_muted: Dict[str, bool] | None = None
    solo_wave: str | None = None
    muted_modules: Dict[str, bool] | None = None
    tuning_method: str = "equal_temperament_12"
    tuning_root_note: str = "A"
    tuning_reference_hz: float = 440.0
    wave_note: Dict[str, str] | None = None
    wave_octave: Dict[str, int] | None = None
    wave_cents: Dict[str, float] | None = None
    wave_follow_main_pitch: Dict[str, bool] | None = None
    wave_shapes: Dict[str, str] | None = None
    wave_order: List[str] | None = None
    paulstretch_enabled: bool = False
    paulstretch_amount: float = 1.0
    paulstretch_evolution: float = 0.0
    enabled_modules: Dict[str, bool] | None = None


def midi_note(note: str, octave: int) -> int:
    return 12 * (octave + 1) + NOTE_TO_INDEX[note]


def frequency_from_note(note: str, octave: int, cents: float = 0.0, a4: float = 440.0) -> float:
    base = a4 * (2.0 ** ((midi_note(note, octave) - 69) / 12.0))
    return base * (2.0 ** (cents / 1200.0))


def _nearest_subset_degree(chromatic_degree: int, available_steps: List[int]) -> int:
    return min(available_steps, key=lambda step: min((chromatic_degree - step) % 12, (step - chromatic_degree) % 12))


def frequency_for_note(
    note: str,
    octave: int,
    cents: float,
    tuning_method: str,
    root_note: str,
    reference_hz: float,
) -> float:
    """Return note frequency with a selectable tuning map and cents fine-tune."""
    if note not in NOTE_TO_INDEX or root_note not in NOTE_TO_INDEX:
        return frequency_from_note("A", 4, cents, reference_hz)

    method = TUNING_METHODS.get(tuning_method, TUNING_METHODS["equal_temperament_12"])
    if tuning_method == "equal_temperament_12" or method.get("kind") == "equal":
        return frequency_from_note(note, octave, cents, reference_hz)

    root_midi = midi_note(root_note, 4)
    target_midi = midi_note(note, octave)
    semitone_delta = target_midi - root_midi
    octave_delta, chromatic_degree = divmod(semitone_delta, 12)
    root_frequency = frequency_from_note(root_note, 4, 0.0, reference_hz)
    kind = str(method.get("kind", "equal"))

    if kind == "ratios12":
        ratios = method.get("ratios", [])
        ratio = float(ratios[chromatic_degree]) if len(ratios) == 12 else 2.0 ** (chromatic_degree / 12.0)
    elif kind == "cents12":
        cent_map = method.get("cents", [])
        degree_cents = float(cent_map[chromatic_degree]) if len(cent_map) == 12 else chromatic_degree * 100.0
        ratio = 2.0 ** (degree_cents / 1200.0)
    elif kind == "equal_mapped":
        divisions = max(1, int(method.get("divisions", 12)))
        mapped_step = round(chromatic_degree * divisions / 12.0)
        ratio = 2.0 ** (mapped_step / divisions)
    elif kind == "subset_equal":
        divisions = max(1, int(method.get("divisions", 5)))
        steps = [int(step) for step in method.get("steps", [0, 2, 4, 7, 9])]
        nearest = _nearest_subset_degree(chromatic_degree, steps)
        subset_index = steps.index(nearest)
        ratio = 2.0 ** (subset_index / divisions)
    else:
        return frequency_from_note(note, octave, cents, reference_hz)

    return root_frequency * (2.0 ** octave_delta) * ratio * (2.0 ** (cents / 1200.0))


def active_wave_order(settings: SynthSettings) -> List[str]:
    order = list(settings.wave_order or [])
    if not order:
        keys: List[str] = []
        for mapping in (settings.wave_start_db, settings.wave_end_db, settings.wave_pan):
            if isinstance(mapping, dict):
                keys.extend(str(key) for key in mapping)
        order = [wave for wave in DEFAULT_WAVE_ORDER if wave in keys or not keys]
        order.extend(key for key in keys if key not in order)
    if not order:
        order = list(DEFAULT_WAVE_ORDER)
    return order[:MAX_WAVE_ROWS]


def wave_shape_for(settings: SynthSettings, wave_id: str) -> str:
    shapes = settings.wave_shapes or {}
    shape = str(shapes.get(wave_id, wave_id))
    return shape if shape in DEFAULT_WAVE_ORDER else "sine"


def default_wave_pan_for(wave_id: str, index: int = 0) -> float:
    defaults = {"sine": -0.45, "triangle": 0.45, "sawtooth": -0.85, "square": 0.85}
    if wave_id in defaults:
        return defaults[wave_id]
    spread = [-0.65, 0.65, -0.25, 0.25, -0.90, 0.90]
    return spread[index % len(spread)]


def effective_wave_frequency_env(settings: SynthSettings, wave_type: str, global_freq_env: np.ndarray) -> np.ndarray:
    """Return the global pitch curve or a per-wave custom pitch curve."""
    follow_map = settings.wave_follow_main_pitch or {name: True for name in WAVE_ORDER}
    if follow_map.get(wave_type, True):
        return global_freq_env

    notes = settings.wave_note or {name: "A" for name in WAVE_ORDER}
    octaves = settings.wave_octave or {name: 4 for name in WAVE_ORDER}
    cents_map = settings.wave_cents or {name: 0.0 for name in WAVE_ORDER}
    note = str(notes.get(wave_type, settings.note if settings.note in NOTE_TO_INDEX else "A"))
    if note not in NOTE_TO_INDEX:
        note = "A"
    try:
        octave = int(octaves.get(wave_type, settings.octave))
    except Exception:
        octave = 4
    try:
        cents = float(cents_map.get(wave_type, 0.0))
    except Exception:
        cents = 0.0

    frequency = frequency_for_note(
        note,
        octave,
        cents,
        settings.tuning_method,
        settings.tuning_root_note,
        settings.tuning_reference_hz,
    )
    return np.full_like(global_freq_env, max(1.0, float(frequency)), dtype=np.float64)


def wave_effective_frequency_env(settings: SynthSettings, wave_type: str, global_freq_env: np.ndarray) -> np.ndarray:
    """Backward-compatible alias for the per-wave pitch helper."""
    return effective_wave_frequency_env(settings, wave_type, global_freq_env)


def wave_label_for(settings: SynthSettings, wave_id: str) -> str:
    base = WAVE_LABELS.get(wave_shape_for(settings, wave_id), "Smooth Wave")
    if wave_id in DEFAULT_WAVE_ORDER:
        return base
    return f"Extra {base}"

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


def build_wave_preview_samples(settings: SynthSettings, wave_type: str, sample_count: int = 160) -> Dict[str, np.ndarray | Dict[str, float | bool]]:
    """Build compact cached preview samples without running the full audio render."""
    sample_count = max(120, min(240, int(sample_count)))
    duration = max(TIMELINE_MIN_CLIP_SECONDS, min(float(settings.duration_seconds), MAX_PREVIEW_SECONDS))
    wave_order = active_wave_order(settings)

    start_levels = settings.wave_start_db or {"sine": 0.0, "triangle": -20.0, "sawtooth": -20.0, "square": -20.0}
    end_levels = settings.wave_end_db or dict(start_levels)
    delta_times = settings.wave_delta_time or {name: duration for name in wave_order}
    muted = settings.wave_muted or {name: False for name in wave_order}
    solo_wave = settings.solo_wave if settings.solo_wave in wave_order else None
    is_audible = not muted.get(wave_type, False) and (solo_wave is None or solo_wave == wave_type)

    start_db = float(start_levels.get(wave_type, -20.0))
    end_db = float(end_levels.get(wave_type, start_db))
    change_seconds = max(0.01, min(float(delta_times.get(wave_type, duration)), duration))
    change_samples = max(1, int(round(sample_count * change_seconds / duration)))

    db_env = make_partial_curve(start_db, end_db, sample_count, change_samples, settings.curve_type)
    gain_env = np.array([db_to_gain(db) for db in db_env], dtype=np.float64)

    # Draw a short, readable oscillator strip using the same waveform function as
    # the audio engine. The phase count is intentionally display-oriented rather
    # than SAMPLE_RATE-sized, so paintEvent never performs full synthesis.
    global_freq = make_curve(float(settings.pitch_start_hz), float(settings.pitch_end_hz), sample_count, settings.curve_type)
    wave_freq = effective_wave_frequency_env(settings, wave_type, global_freq)
    preview_anchor = max(1.0, float(np.mean(global_freq))) if global_freq.size else 440.0
    cycles = 2.35 * max(0.25, min(4.0, float(np.mean(wave_freq)) / preview_anchor))
    phase = np.linspace(0.0, 2.0 * np.pi * cycles, sample_count, dtype=np.float64)
    raw_wave = waveform_from_phase(wave_shape_for(settings, wave_type), phase)
    mono = raw_wave * gain_env
    if not is_audible:
        mono = np.zeros_like(mono)
        gain_env = np.zeros_like(gain_env)

    wave_index = wave_order.index(wave_type) if wave_type in wave_order else 0
    wave_pan = settings.wave_pan or {name: default_wave_pan_for(name, idx) for idx, name in enumerate(wave_order)}
    wave_width = settings.wave_width or {name: 1.0 for name in wave_order}
    wave_dance = settings.wave_dance or {name: 0.0 for name in wave_order}

    time_axis = np.linspace(0.0, duration, sample_count, endpoint=False, dtype=np.float64)
    pan_base = make_curve(float(settings.pan_start), float(settings.pan_end), sample_count, settings.curve_type)
    global_width = np.clip(float(settings.stereo_width), 0.0, 1.0)
    auto_depth = np.clip(float(settings.auto_pan_depth), 0.0, 1.0)
    auto_rate = max(0.01, float(settings.auto_pan_rate))
    auto_pan = auto_depth * np.sin(2.0 * np.pi * auto_rate * time_axis)

    individual_pan = np.clip(float(wave_pan.get(wave_type, default_wave_pan_for(wave_type, wave_index))), -1.0, 1.0)
    individual_width = np.clip(float(wave_width.get(wave_type, 1.0)), 0.0, 1.0)
    individual_dance = np.clip(float(wave_dance.get(wave_type, 0.0)), 0.0, 1.0)
    dance_phase = wave_index * (math.pi / 2.0)
    dance_pan = individual_dance * np.sin(2.0 * np.pi * auto_rate * time_axis + dance_phase)
    pan_env = np.clip(pan_base + auto_pan + (individual_pan * global_width * individual_width) + dance_pan, -1.0, 1.0)

    stereo = equal_power_pan(mono, pan_env)
    peak = max(float(np.max(np.abs(mono))) if mono.size else 0.0, 1.0)
    left_level = np.abs(stereo[:, 0]) / peak
    right_level = np.abs(stereo[:, 1]) / peak
    return {
        "shape": raw_wave.astype(np.float32),
        "envelope": gain_env.astype(np.float32),
        "pan": pan_env.astype(np.float32),
        "left_level": left_level.astype(np.float32),
        "right_level": right_level.astype(np.float32),
        "mono": (mono / peak).astype(np.float32),
        "left": (stereo[:, 0] / peak).astype(np.float32),
        "right": (stereo[:, 1] / peak).astype(np.float32),
        "metadata": {
            "active": bool(is_audible and np.max(gain_env) > 0.0),
            "muted": bool(muted.get(wave_type, False)),
            "soloed": bool(solo_wave == wave_type),
            "amplitude": float(np.max(gain_env)) if gain_env.size else 0.0,
            "start_gain": float(gain_env[0]) if gain_env.size else 0.0,
            "end_gain": float(gain_env[-1]) if gain_env.size else 0.0,
            "change_fraction": float(change_seconds / duration),
            "pan": float(individual_pan),
            "width": float(individual_width),
            "dance": float(individual_dance),
        },
    }


def normalize_audio(audio: np.ndarray) -> np.ndarray:
    """Normalize audio safely without changing silence."""
    peak = float(np.max(np.abs(audio))) if audio.size else 0.0
    if peak > 0.98:
        return (audio / peak * 0.98).astype(np.float32)
    return audio.astype(np.float32)


def paulstretch_process(
    audio: np.ndarray,
    stretch: float = 8.0,
    window_seconds: float = 0.25,
    evolution: float = 0.15,
) -> np.ndarray:
    """
    Educational Paulstretch-style time stretcher.

    This is not a full clone of the standalone Paulstretch program. It is a
    lightweight spectral smear/stretch module intended for drones, pads, and
    sci-fi ambience inside this toy synth.
    """
    stretch = max(1.0, float(stretch))
    if stretch <= 1.01:
        return audio.astype(np.float32)

    audio = np.asarray(audio, dtype=np.float32)

    if audio.ndim == 1:
        audio = audio[:, None]

    total_samples, channels = audio.shape
    if total_samples < 32:
        return audio.astype(np.float32)

    window_size = int(max(1024, min(SAMPLE_RATE * window_seconds, total_samples)))
    # Use a power of two for cleaner FFT work.
    window_size = 2 ** int(np.floor(np.log2(window_size)))
    window_size = max(512, min(window_size, total_samples))

    hop_in = max(128, window_size // 8)
    hop_out = max(128, int(hop_in * stretch))

    window = np.hanning(window_size).astype(np.float32)
    output_length = int(total_samples * stretch) + window_size * 2
    output = np.zeros((output_length, channels), dtype=np.float32)

    rng = np.random.default_rng()

    for channel in range(channels):
        source = audio[:, channel]
        out_pos = 0

        for start in range(0, max(1, total_samples - window_size + 1), hop_in):
            chunk = source[start:start + window_size]

            if len(chunk) < window_size:
                padded = np.zeros(window_size, dtype=np.float32)
                padded[:len(chunk)] = chunk
                chunk = padded

            spectrum = np.fft.rfft(chunk * window)
            magnitude = np.abs(spectrum)

            phase_noise = rng.uniform(0.0, 2.0 * np.pi, len(magnitude))
            shimmer = evolution * np.sin(np.linspace(0.0, 8.0 * np.pi, len(magnitude)))
            random_phase = np.exp(1j * (phase_noise + shimmer))

            rebuilt = np.fft.irfft(magnitude * random_phase, n=window_size).astype(np.float32)
            rebuilt *= window

            end_pos = min(output_length, out_pos + window_size)
            output[out_pos:end_pos, channel] += rebuilt[:end_pos - out_pos]
            out_pos += hop_out

    return normalize_audio(output)


MODULE_DESCRIPTIONS = {
    "paulstretch": "Dreamy ambient time stretching for space drones and cinematic pads.",
}


def apply_modules(audio: np.ndarray, settings: SynthSettings) -> np.ndarray:
    """Apply enabled audio-processing modules in order.

    Future effects can follow the same pattern: keep slider state in settings,
    then skip processing when the module is listed in muted_modules.
    """
    modules = settings.enabled_modules or {}
    muted_modules = settings.muted_modules or {}

    if modules.get("paulstretch", False) and not muted_modules.get("paulstretch", False) and settings.paulstretch_amount > 1.01:
        audio = paulstretch_process(
            audio,
            stretch=settings.paulstretch_amount,
            evolution=settings.paulstretch_evolution,
        )

    return audio

def generate_audio(settings: SynthSettings) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    duration = max(TIMELINE_MIN_CLIP_SECONDS, min(float(settings.duration_seconds), MAX_PREVIEW_SECONDS))
    total_samples = int(SAMPLE_RATE * duration)

    time_axis = np.arange(total_samples, dtype=np.float64) / SAMPLE_RATE

    pitch_start = max(1.0, float(settings.pitch_start_hz))
    pitch_end = max(1.0, float(settings.pitch_end_hz))
    loud_start = np.clip(float(settings.loudness_start), 0.0, 1.0)
    loud_end = np.clip(float(settings.loudness_end), 0.0, 1.0)

    freq_env = make_curve(pitch_start, pitch_end, total_samples, settings.curve_type)
    loud_env = make_curve(loud_start, loud_end, total_samples, settings.curve_type)

    start_levels = settings.wave_start_db or {
        "sine": 0.0,
        "triangle": -20.0,
        "sawtooth": -20.0,
        "square": -20.0,
    }
    end_levels = settings.wave_end_db or dict(start_levels)
    wave_order = active_wave_order(settings)
    delta_times = settings.wave_delta_time or {wave_type: duration for wave_type in wave_order}

    mixed_stereo = np.zeros((total_samples, 2), dtype=np.float64)

    width = np.clip(float(settings.stereo_width), 0.0, 1.0)
    wave_pan = settings.wave_pan or {wave_type: default_wave_pan_for(wave_type, idx) for idx, wave_type in enumerate(wave_order)}
    wave_width = settings.wave_width or {wave_type: 1.0 for wave_type in wave_order}
    wave_dance = settings.wave_dance or {wave_type: 0.0 for wave_type in wave_order}
    wave_muted = settings.wave_muted or {wave_type: False for wave_type in wave_order}
    solo_wave = settings.solo_wave if settings.solo_wave in wave_order else None

    pan_base = make_curve(float(settings.pan_start), float(settings.pan_end), total_samples, settings.curve_type)

    auto_depth = np.clip(float(settings.auto_pan_depth), 0.0, 1.0)
    auto_rate = max(0.01, float(settings.auto_pan_rate))
    auto_pan = auto_depth * np.sin(2.0 * np.pi * auto_rate * time_axis)

    active_gain_total = 0.0

    for wave_index, wave_type in enumerate(wave_order):
        if wave_muted.get(wave_type, False) or (solo_wave is not None and solo_wave != wave_type):
            continue

        start_db = float(start_levels.get(wave_type, -20.0))
        end_db = float(end_levels.get(wave_type, start_db))

        change_seconds = max(0.01, min(float(delta_times.get(wave_type, duration)), duration))
        change_samples = int(change_seconds * SAMPLE_RATE)

        db_env = make_partial_curve(start_db, end_db, total_samples, change_samples, settings.curve_type)
        gain_env = np.array([db_to_gain(db) for db in db_env], dtype=np.float64)

        if float(np.max(gain_env)) <= 0.0:
            continue

        wave_freq_env = effective_wave_frequency_env(settings, wave_type, freq_env)
        if not (settings.wave_follow_main_pitch or {}).get(wave_type, True):
            note_map = settings.wave_note or {}
            octave_map = settings.wave_octave or {}
            print(
                f"[WaveToy] pitch {wave_type} follow_main=False "
                f"note={note_map.get(wave_type, settings.note)}{octave_map.get(wave_type, settings.octave)} "
                f"freq≈{float(np.mean(wave_freq_env)):.1f}"
            )
        phase = np.cumsum(2.0 * np.pi * wave_freq_env / SAMPLE_RATE)
        mono_wave = waveform_from_phase(wave_shape_for(settings, wave_type), phase) * gain_env
        individual_pan = np.clip(float(wave_pan.get(wave_type, default_wave_pan_for(wave_type, wave_index))), -1.0, 1.0)
        individual_width = np.clip(float(wave_width.get(wave_type, 1.0)), 0.0, 1.0)
        individual_dance = np.clip(float(wave_dance.get(wave_type, 0.0)), 0.0, 1.0)
        dance_phase = wave_index * (math.pi / 2.0)
        individual_auto_pan = individual_dance * np.sin(2.0 * np.pi * auto_rate * time_axis + dance_phase)
        wave_pan_env = np.clip(
            pan_base + auto_pan + (individual_pan * width * individual_width) + individual_auto_pan,
            -1.0,
            1.0,
        )
        mixed_stereo += equal_power_pan(mono_wave, wave_pan_env)
        active_gain_total += float(np.max(gain_env))

    if active_gain_total > 1.0:
        mixed_stereo /= active_gain_total

    audio = mixed_stereo * loud_env[:, None]
    audio = apply_modules(audio, settings)
    audio = normalize_audio(audio)

    output_time_axis = np.arange(audio.shape[0], dtype=np.float64) / SAMPLE_RATE
    return audio.astype(np.float32), output_time_axis, freq_env, loud_env


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


def _decode_pcm_frames(raw: bytes, sample_width: int, channels: int) -> np.ndarray:
    if sample_width == 1:
        audio = (np.frombuffer(raw, dtype=np.uint8).astype(np.float32) - 128.0) / 128.0
    elif sample_width == 2:
        audio = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
    elif sample_width == 3:
        data = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 3).astype(np.int32)
        values = data[:, 0] | (data[:, 1] << 8) | (data[:, 2] << 16)
        values = np.where(values & 0x800000, values - 0x1000000, values)
        audio = values.astype(np.float32) / 8388608.0
    elif sample_width == 4:
        audio = np.frombuffer(raw, dtype="<i4").astype(np.float32) / 2147483648.0
    else:
        raise ValueError(f"Unsupported WAV sample width: {sample_width * 8}-bit")

    if channels <= 0:
        raise ValueError("Audio file has no channels")
    return audio.reshape(-1, channels)


def _ensure_stereo_float(audio: np.ndarray) -> np.ndarray:
    audio = np.asarray(audio, dtype=np.float32)
    if audio.ndim == 1:
        audio = audio[:, None]
    if audio.ndim != 2 or audio.shape[0] == 0:
        return np.zeros((0, 2), dtype=np.float32)
    if audio.shape[1] == 1:
        audio = np.repeat(audio, 2, axis=1)
    elif audio.shape[1] > 2:
        audio = audio[:, :2]
    return np.clip(audio, -1.0, 1.0).astype(np.float32, copy=False)


def _resample_audio(audio: np.ndarray, source_rate: int, target_rate: int = SAMPLE_RATE) -> np.ndarray:
    if int(source_rate) == int(target_rate) or len(audio) == 0:
        return audio.astype(np.float32, copy=False)
    duration = len(audio) / float(source_rate)
    target_len = max(1, int(round(duration * target_rate)))
    old_x = np.linspace(0.0, duration, num=len(audio), endpoint=False)
    new_x = np.linspace(0.0, duration, num=target_len, endpoint=False)
    channels = [np.interp(new_x, old_x, audio[:, channel]) for channel in range(audio.shape[1])]
    return np.column_stack(channels).astype(np.float32)



def _fit_audio_length(audio: np.ndarray, target_len: int) -> np.ndarray:
    audio = _ensure_stereo_float(audio)
    target_len = max(0, int(target_len))
    if target_len <= 0:
        return np.zeros((0, 2), dtype=np.float32)
    if len(audio) == target_len:
        return audio.astype(np.float32, copy=False)
    if len(audio) > target_len:
        return audio[:target_len].astype(np.float32, copy=True)
    pad = np.zeros((target_len - len(audio), 2), dtype=np.float32)
    return np.vstack([audio, pad]).astype(np.float32, copy=False)


def _fade_audio_edges(audio: np.ndarray, sample_rate: int, max_fade_ms: float = 6.0) -> np.ndarray:
    audio = _ensure_stereo_float(audio).astype(np.float32, copy=True)
    if len(audio) < 4:
        return audio
    fade_len = min(len(audio) // 2, max(2, int(round(float(sample_rate) * max_fade_ms / 1000.0))))
    if fade_len <= 1:
        return audio
    fade_in = np.linspace(0.0, 1.0, fade_len, dtype=np.float32)[:, None]
    fade_out = np.linspace(1.0, 0.0, fade_len, dtype=np.float32)[:, None]
    audio[:fade_len] *= fade_in
    audio[-fade_len:] *= fade_out
    return audio


def _phase_vocoder_channel(samples: np.ndarray, stretch_factor: float, quality: str = "Balanced") -> np.ndarray:
    samples = np.asarray(samples, dtype=np.float32).reshape(-1)
    if samples.size == 0:
        return samples
    quality_key = str(quality or "Balanced").lower()
    n_fft = 1024 if quality_key == "fast" else 4096 if quality_key.startswith("best") else 2048
    n_fft = min(n_fft, max(256, 2 ** int(math.floor(math.log2(max(256, len(samples)))))))
    hop = max(64, n_fft // 4)
    if len(samples) < n_fft * 2 or stretch_factor <= 0.0:
        return _ola_time_stretch_channel(samples, stretch_factor, n_fft=max(128, min(512, n_fft)), hop=max(32, min(128, hop)))

    padded = np.pad(samples, (0, n_fft), mode="constant")
    frame_count = 1 + max(0, (len(padded) - n_fft) // hop)
    if frame_count < 2:
        return _ola_time_stretch_channel(samples, stretch_factor, n_fft=max(128, min(512, n_fft)), hop=max(32, min(128, hop)))
    window = np.hanning(n_fft).astype(np.float32)
    frames = np.empty((frame_count, n_fft), dtype=np.float32)
    for frame in range(frame_count):
        start = frame * hop
        frames[frame] = padded[start:start + n_fft] * window
    spectrum = np.fft.rfft(frames, axis=1).T
    bins = spectrum.shape[0]
    speed = 1.0 / max(1e-6, float(stretch_factor))
    time_steps = np.arange(0, max(1, spectrum.shape[1] - 1), speed, dtype=np.float32)
    if time_steps.size == 0:
        return np.zeros((0,), dtype=np.float32)
    omega = 2.0 * np.pi * hop * np.arange(bins, dtype=np.float32) / float(n_fft)
    phase = np.angle(spectrum[:, 0]).astype(np.float32)
    stretched = np.empty((bins, len(time_steps)), dtype=np.complex64)
    for out_index, step in enumerate(time_steps):
        left = int(np.floor(step))
        right = min(left + 1, spectrum.shape[1] - 1)
        frac = float(step - left)
        left_spec = spectrum[:, left]
        right_spec = spectrum[:, right]
        magnitude = (1.0 - frac) * np.abs(left_spec) + frac * np.abs(right_spec)
        stretched[:, out_index] = magnitude * np.exp(1.0j * phase)
        delta = np.angle(right_spec) - np.angle(left_spec) - omega
        delta = delta - 2.0 * np.pi * np.round(delta / (2.0 * np.pi))
        phase += omega + delta
    out_len = n_fft + hop * (stretched.shape[1] - 1)
    output = np.zeros(out_len, dtype=np.float32)
    norm = np.zeros(out_len, dtype=np.float32)
    for frame in range(stretched.shape[1]):
        chunk = np.fft.irfft(stretched[:, frame], n=n_fft).astype(np.float32)
        start = frame * hop
        output[start:start + n_fft] += chunk * window
        norm[start:start + n_fft] += window * window
    valid = norm > 1e-8
    output[valid] /= norm[valid]
    return output.astype(np.float32, copy=False)


def _ola_time_stretch_channel(samples: np.ndarray, stretch_factor: float, n_fft: int = 512, hop: int = 128) -> np.ndarray:
    samples = np.asarray(samples, dtype=np.float32).reshape(-1)
    if samples.size == 0:
        return samples
    stretch_factor = max(0.25, min(4.0, float(stretch_factor or 1.0)))
    n_fft = max(64, min(int(n_fft), max(64, len(samples))))
    hop = max(16, min(int(hop), n_fft // 2))
    target_len = max(1, int(round(len(samples) * stretch_factor)))
    window = np.hanning(n_fft).astype(np.float32)
    output = np.zeros(target_len + n_fft, dtype=np.float32)
    norm = np.zeros_like(output)
    out_pos = 0
    while out_pos < target_len:
        source_pos = int(round(out_pos / stretch_factor))
        source_pos = min(max(0, source_pos), max(0, len(samples) - n_fft))
        chunk = samples[source_pos:source_pos + n_fft]
        if len(chunk) < n_fft:
            chunk = np.pad(chunk, (0, n_fft - len(chunk)), mode="constant")
        output[out_pos:out_pos + n_fft] += chunk * window
        norm[out_pos:out_pos + n_fft] += window * window
        out_pos += hop
    valid = norm > 1e-8
    output[valid] /= norm[valid]
    return output[:target_len].astype(np.float32, copy=False)


def time_stretch_preserve_pitch(audio: np.ndarray, source_rate: int, target_duration_seconds: float, quality: str = "Balanced") -> np.ndarray:
    """Stretch audio to a target duration without changing sample rate or intentional pitch."""
    source_rate = max(1, int(source_rate or SAMPLE_RATE))
    audio = _ensure_stereo_float(audio)
    target_len = max(1, int(round(max(0.0, float(target_duration_seconds)) * source_rate)))
    if audio.size == 0:
        return np.zeros((0, 2), dtype=np.float32)
    source_duration = len(audio) / float(source_rate)
    if source_duration <= 0.0:
        return np.zeros((0, 2), dtype=np.float32)
    if abs(target_len - len(audio)) <= 1:
        return _fit_audio_length(audio, target_len)
    stretch_factor = float(target_len) / float(len(audio))
    channels = []
    for channel in range(2):
        stretched = _phase_vocoder_channel(audio[:, channel], stretch_factor, quality)
        channels.append(stretched)
    min_len = min(len(channels[0]), len(channels[1])) if channels else 0
    if min_len <= 0:
        return np.zeros((0, 2), dtype=np.float32)
    stretched_audio = np.column_stack([channels[0][:min_len], channels[1][:min_len]]).astype(np.float32)
    stretched_audio = _fit_audio_length(stretched_audio, target_len)
    stretched_audio = _fade_audio_edges(stretched_audio, source_rate)
    peak = float(np.max(np.abs(stretched_audio))) if stretched_audio.size else 0.0
    if peak > 1.0:
        stretched_audio = stretched_audio / peak
    return np.clip(stretched_audio, -1.0, 1.0).astype(np.float32, copy=False)


def compute_waveform_peaks(audio: np.ndarray, bins: int = 36) -> List[float]:
    audio = _ensure_stereo_float(audio)
    if audio.size == 0:
        return [0.0] * bins
    mono = np.abs(audio.mean(axis=1))
    peaks: List[float] = []
    for chunk in np.array_split(mono, max(1, bins)):
        peaks.append(float(np.max(chunk)) if chunk.size else 0.0)
    peak = max(peaks) if peaks else 0.0
    if peak > 1e-9:
        peaks = [value / peak for value in peaks]
    return peaks


def load_audio_file(path: Path) -> Tuple[np.ndarray, int]:
    suffix = path.suffix.lower()
    if suffix == ".wav":
        with wave.open(str(path), "rb") as wav_file:
            channels = wav_file.getnchannels()
            sample_width = wav_file.getsampwidth()
            source_rate = wav_file.getframerate()
            raw = wav_file.readframes(wav_file.getnframes())
        audio = _decode_pcm_frames(raw, sample_width, channels)
    elif suffix in {".mp3", ".ogg", ".flac"}:
        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            raise RuntimeError(f"{suffix.upper()[1:]} import requires ffmpeg. Install ffmpeg or import WAV files instead.")
        with tempfile.NamedTemporaryFile(prefix="wave_toy_import_", suffix=".wav", delete=False) as temp:
            temp_wav = Path(temp.name)
        try:
            subprocess.run(
                [ffmpeg, "-y", "-loglevel", "error", "-i", str(path), "-ac", "2", "-ar", str(SAMPLE_RATE), str(temp_wav)],
                check=True,
            )
            audio, source_rate = load_audio_file(temp_wav)
        finally:
            try:
                temp_wav.unlink()
            except OSError:
                pass
    else:
        raise ValueError(f"Unsupported audio import format: {suffix or 'unknown'}")

    audio = _ensure_stereo_float(audio)
    audio = _resample_audio(audio, source_rate, SAMPLE_RATE)
    return _ensure_stereo_float(audio), SAMPLE_RATE


class WaveCanvas(QWidget):
    def __init__(self) -> None:
        super().__init__()

        self.setMinimumSize(QSize(260, 180))
        self.audio = np.zeros((1, 2), dtype=np.float32)
        self.freq_env = np.zeros(1, dtype=np.float32)
        self.loud_env = np.zeros(1, dtype=np.float32)
        self.mascot_message = "Move the sliders, then press Make Sound!"
        self.visual_conditions = {}
        self.animation_phase = 0.0
        self.zoom_factor = 1.0
        self.zoom_center = 0.5
        self.playhead_fraction: float | None = None
        self.playhead_sample_index: int | None = None
        self.playhead_sample_count = 0
        self.setMouseTracking(True)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(50)

    def _tick(self) -> None:
        self.animation_phase = (self.animation_phase + 0.05) % (2.0 * math.pi)
        self.update()

    def wheelEvent(self, event) -> None:
        """Mouse wheel zooms the waveform time view."""
        delta = event.angleDelta().y()
        if delta == 0:
            return

        # Cursor position chooses the zoom center inside the drawing area.
        rect = self.rect().adjusted(40, 72, -40, -58)
        if rect.width() > 0:
            relative_x = (event.position().x() - rect.left()) / rect.width()
            self.zoom_center = float(np.clip(relative_x, 0.05, 0.95))

        if delta > 0:
            self.zoom_factor = min(64.0, self.zoom_factor * 1.25)
        else:
            self.zoom_factor = max(1.0, self.zoom_factor / 1.25)

        self.update()
        event.accept()

    def mouseDoubleClickEvent(self, event) -> None:
        """Double-click resets waveform zoom."""
        self.reset_zoom()
        event.accept()

    def zoom_by(self, multiplier: float) -> None:
        self.zoom_factor = float(np.clip(self.zoom_factor * multiplier, 1.0, 64.0))
        self.update()

    def pan_view(self, direction: float) -> None:
        if self.zoom_factor <= 1.01:
            return
        step = max(0.02, 0.18 / self.zoom_factor)
        self.zoom_center = float(np.clip(self.zoom_center + (step * direction), 0.02, 0.98))
        self.update()

    def reset_zoom(self) -> None:
        self.zoom_factor = 1.0
        self.zoom_center = 0.5
        self.update()

    def set_playhead_fraction(self, fraction: float | None) -> None:
        """Set the displayed playback playhead without changing the user's zoom level."""
        if fraction is None:
            self.playhead_fraction = None
            self.playhead_sample_index = None
        else:
            self.playhead_fraction = float(np.clip(fraction, 0.0, 1.0))
            self.playhead_sample_count = int(max(1, self.audio.shape[0]))
            self.playhead_sample_index = int(round(self.playhead_fraction * max(0, self.playhead_sample_count - 1)))
        self.update()

    def set_playhead_sample(self, sample_index: int | None, sample_count: int | None = None) -> None:
        """Set playback playhead by sample index for callers that track sample counts."""
        if sample_index is None:
            self.set_playhead_fraction(None)
            return
        total = int(sample_count or self.audio.shape[0] or 1)
        self.playhead_sample_count = max(1, total)
        self.playhead_sample_index = int(np.clip(sample_index, 0, self.playhead_sample_count - 1))
        self.playhead_fraction = self.playhead_sample_index / max(1, self.playhead_sample_count - 1)
        self.update()

    def center_on_playback_fraction(self, fraction: float) -> None:
        """Approximate playback-follow scrolling for zoomed Wave Explorer views."""
        fraction = float(np.clip(fraction, 0.0, 1.0))
        self.set_playhead_fraction(fraction)
        if self.zoom_factor > 1.01:
            # Keep the current position visible while preserving zoom. A centered
            # target feels stable for this vertical waveform time view.
            self.zoom_center = float(np.clip(fraction, 0.02, 0.98))
        self.update()

    def center_on_sample(self, sample_index: int) -> None:
        total = int(max(1, self.audio.shape[0]))
        fraction = float(np.clip(sample_index, 0, total - 1)) / max(1, total - 1)
        self.center_on_playback_fraction(fraction)

    def _visible_bounds(self, total: int) -> Tuple[int, int]:
        if total <= 0 or self.zoom_factor <= 1.01:
            return 0, max(0, total)
        visible = max(32, int(total / self.zoom_factor))
        visible = min(visible, total)
        center = int(total * self.zoom_center)
        start = max(0, min(total - visible, center - visible // 2))
        return start, start + visible

    def _visible_slice(self, data: np.ndarray) -> np.ndarray:
        if data.size == 0:
            return data
        start, end = self._visible_bounds(data.shape[0])
        return data[start:end]

    def set_data(
        self,
        audio: np.ndarray,
        freq_env: np.ndarray,
        loud_env: np.ndarray,
        message: str,
        visual_conditions: dict | None = None,
    ) -> None:
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
        self.visual_conditions = visual_conditions or {}
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

    def _path_for_vertical_wave(self, data: np.ndarray, area: QRectF, center_x: float, width_scale: float) -> QPainterPath:
        wave = self._downsample(data, max(20, int(area.height())))
        path = QPainterPath()

        if wave.size < 2:
            return path

        amp = area.width() * width_scale
        y_step = area.height() / max(1, wave.size - 1)
        wobble = math.sin(self.animation_phase) * 2.0

        path.moveTo(center_x + float(wave[0]) * amp + wobble, area.top())

        for i, sample in enumerate(wave[1:], start=1):
            x = center_x + float(sample) * amp + wobble
            y = area.top() + i * y_step
            path.lineTo(QPointF(x, y))

        return path

    def _draw_wave_column(
        self,
        painter: QPainter,
        area: QRectF,
        center_x: float,
        label: str,
        color: QColor,
        data: np.ndarray,
        thick: int,
    ) -> None:
        painter.setPen(QPen(QColor(0, 0, 0, 45), thick + 7, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        width_scale = min(0.16, 0.09 + math.log2(max(1.0, self.zoom_factor)) * 0.012)
        painter.drawPath(self._path_for_vertical_wave(data, area.adjusted(4, 4, 4, 4), center_x + 4, width_scale))

        painter.setPen(QPen(color, thick, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.drawPath(self._path_for_vertical_wave(data, area, center_x, width_scale))

        painter.setPen(QColor("#263238"))
        painter.setFont(QFont("Arial", 11, QFont.Bold))
        label_rect = QRectF(center_x - area.width() * 0.13, area.bottom() + 4, area.width() * 0.26, 24)
        painter.drawText(label_rect, Qt.AlignCenter, label)

    def _draw_wave(self, painter: QPainter, area: QRectF) -> None:
        visible_audio = self._visible_slice(self.audio)

        if visible_audio.ndim == 1:
            left = right = visible_audio
        else:
            left = visible_audio[:, 0]
            right = visible_audio[:, 1]

        common = (left + right) * 0.5

        left_x = area.left() + area.width() * 0.22
        common_x = area.left() + area.width() * 0.50
        right_x = area.left() + area.width() * 0.78

        painter.setPen(QPen(QColor(255, 255, 255, 150), 3, Qt.DashLine))
        for x in [left_x, common_x, right_x]:
            painter.drawLine(QPointF(x, area.top()), QPointF(x, area.bottom()))

        self._draw_wave_column(painter, area, left_x, "Left", QColor("#00a8ff"), left, 6)
        self._draw_wave_column(painter, area, common_x, "Common", QColor("#fff176"), common, 5)
        self._draw_wave_column(painter, area, right_x, "Right", QColor("#ff4fa3"), right, 6)

        self._draw_condition_overlay(painter, area, left_x, common_x, right_x)
        self._draw_playhead(painter, area)

        painter.setPen(QColor("#263238"))
        painter.setFont(QFont("Arial", 10, QFont.Bold))
        if self.zoom_factor <= 1.01:
            zoom_text = "Mouse wheel: zoom waveform    Double-click: reset"
        else:
            zoom_text = f"Zoomed view ×{self.zoom_factor:.1f}    Mouse wheel: zoom    Double-click: reset"
        painter.drawText(
            QRectF(area.left(), area.top() - 28, area.width(), 22),
            Qt.AlignCenter,
            zoom_text,
        )

    def _draw_playhead(self, painter: QPainter, area: QRectF) -> None:
        if self.playhead_fraction is None or self.audio.size == 0:
            return
        total = int(max(1, self.audio.shape[0]))
        start, end = self._visible_bounds(total)
        sample_index = int(np.clip(round(self.playhead_fraction * max(0, total - 1)), 0, max(0, total - 1)))
        if sample_index < start or sample_index > max(start, end - 1):
            return
        visible = max(1, end - start - 1)
        y = area.top() + ((sample_index - start) / visible) * area.height()
        painter.setPen(QPen(QColor("#ff2d55"), 4, Qt.SolidLine, Qt.RoundCap))
        painter.drawLine(QPointF(area.left() - 6, y), QPointF(area.right() + 6, y))
        painter.setBrush(QColor("#ff2d55"))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QPointF(area.left() - 12, y), 6, 6)
        painter.setPen(QColor("#7a0030"))
        painter.setFont(QFont("Arial", 9, QFont.Bold))
        painter.drawText(QRectF(area.right() - 94, y - 22, 88, 18), Qt.AlignRight | Qt.AlignVCenter, "▶ playhead")

    def _draw_condition_overlay(
        self,
        painter: QPainter,
        area: QRectF,
        left_x: float,
        common_x: float,
        right_x: float,
    ) -> None:
        if not self.visual_conditions:
            return

        colors = {
            "sine": QColor("#2ecc71"),
            "triangle": QColor("#f1c40f"),
            "sawtooth": QColor("#3498db"),
            "square": QColor("#e84393"),
        }
        icons = {
            "sine": "〰 Smooth",
            "triangle": "△ Mountain",
            "sawtooth": "▱ Ramp",
            "square": "▣ Blocky",
        }

        panel = QRectF(area.left() + 10, area.top() + 8, area.width() - 20, 112)
        painter.setPen(QPen(QColor(255, 255, 255, 170), 2))
        painter.setBrush(QColor(255, 255, 255, 110))
        painter.drawRoundedRect(panel, 16, 16)

        row_h = panel.height() / 4.0
        x_min = left_x
        x_mid = common_x
        x_max = right_x

        painter.setFont(QFont("Arial", 8, QFont.Bold))
        for index, wave_type in enumerate(["sine", "triangle", "sawtooth", "square"]):
            condition = self.visual_conditions.get(wave_type, {})
            row_top = panel.top() + index * row_h
            row_center = row_top + row_h * 0.52

            color = colors[wave_type]
            active = bool(condition.get("active", False))
            start_db = float(condition.get("start_db", -20.0))
            end_db = float(condition.get("end_db", -20.0))
            pan = float(condition.get("pan", 0.0))
            spread = float(condition.get("spread", 0.0))
            dance = float(condition.get("dance", 0.0))
            change_fraction = float(condition.get("change_fraction", 1.0))

            painter.setPen(QColor("#263238"))
            painter.drawText(QRectF(panel.left() + 10, row_top + 2, 88, row_h - 2), Qt.AlignVCenter, icons[wave_type])

            # On/off condition: colored bead means the wave contributes to the sound.
            painter.setPen(Qt.NoPen)
            painter.setBrush(color if active else QColor(160, 160, 160, 110))
            painter.drawEllipse(QPointF(panel.left() + 106, row_center), 6 if active else 4, 6 if active else 4)

            # Start-to-end loudness condition: small-to-big beads show envelope direction.
            start_size = 4 + max(0.0, min(1.0, (start_db + 20.0) / 20.0)) * 9
            end_size = 4 + max(0.0, min(1.0, (end_db + 20.0) / 20.0)) * 9
            x_a = panel.left() + 130
            x_b = panel.left() + 168
            painter.setPen(QPen(color, 3, Qt.SolidLine, Qt.RoundCap))
            painter.drawLine(QPointF(x_a, row_center), QPointF(x_b, row_center))
            painter.setBrush(color)
            painter.drawEllipse(QPointF(x_a, row_center), start_size, start_size)
            painter.drawEllipse(QPointF(x_b, row_center), end_size, end_size)

            # Change-time condition: pictorial progress bar.
            bar = QRectF(panel.left() + 194, row_center - 5, 60, 10)
            painter.setPen(QPen(QColor("#263238"), 1))
            painter.setBrush(QColor(255, 255, 255, 160))
            painter.drawRoundedRect(bar, 5, 5)
            fill = QRectF(bar.left(), bar.top(), bar.width() * max(0.02, min(1.0, change_fraction)), bar.height())
            painter.setPen(Qt.NoPen)
            painter.setBrush(color)
            painter.drawRoundedRect(fill, 5, 5)

            # Stereo condition: ring is placed left/common/right, spread changes ring size, dance adds halo.
            x = x_mid + pan * (x_max - x_min) * 0.5
            x = max(x_min, min(x_max, x))
            ring = 8 + spread * 16
            dance_ring = ring + dance * (8 + 5 * math.sin(self.animation_phase + index))

            painter.setPen(QPen(color, 2))
            painter.setBrush(QColor(color.red(), color.green(), color.blue(), 55))
            painter.drawEllipse(QPointF(x, row_center), ring, ring)

            if dance > 0.05:
                painter.setPen(QPen(QColor(color.red(), color.green(), color.blue(), 130), 2, Qt.DashLine))
                painter.setBrush(Qt.NoBrush)
                painter.drawEllipse(QPointF(x, row_center), dance_ring, dance_ring)

            painter.setPen(QPen(QColor(color.red(), color.green(), color.blue(), 90), 1, Qt.DotLine))
            painter.drawLine(QPointF(panel.left() + 260, row_center), QPointF(x, row_center))

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
        painter.setFont(QFont("Arial", 13, QFont.Bold))

        text_rect = QRectF(rect.left() + 92, rect.top() + 18, rect.width() - 120, 52)
        painter.drawText(text_rect, Qt.AlignVCenter | Qt.TextWordWrap, self.mascot_message)



class WaveToySizing:
    """Central professional sizing tokens for WaveToy's educational interface."""

    COMPACT_SPACING = 6
    NORMAL_SPACING = 10
    SECTION_SPACING = 16
    MIN_TOUCH_TARGET = 36
    BUTTON_HEIGHT = 40
    LARGE_BUTTON_HEIGHT = 52
    ICON_STANDARD = 24
    ICON_LARGE = 32
    ICON_HERO = 48
    CARD_MIN_HEIGHT = 76
    SCROLLBAR_WIDTH = 14
    PAGE_MARGIN = 16
    CARD_PADDING = 10


class WaveToyTheme:
    """Shared color, spacing, and style helpers for the WaveToy interface."""

    BACKGROUND = "#eef3f8"
    SURFACE = "#ffffff"
    CARD = "#f7fafc"
    INK = "#1f2933"
    MUTED = "#5f6f7a"
    ACCENT = "#2563eb"
    ACCENT_DARK = "#1d4ed8"
    BLUE = "#e6f0fb"

    @classmethod
    def scroll_area_style(cls) -> str:
        width = WaveToySizing.SCROLLBAR_WIDTH
        return f"""
            WaveToyScrollArea {{
                background: transparent;
                border: 0;
            }}
            QScrollArea#waveToyScrollArea {{
                background: transparent;
                border: 0;
            }}
            QScrollBar:vertical {{
                background: rgba(255, 255, 255, 0.44);
                border: 1px solid rgba(31, 41, 51, 0.16);
                border-radius: {width // 2}px;
                width: {width}px;
                margin: 2px;
            }}
            QScrollBar::handle:vertical {{
                background: {cls.ACCENT};
                border: 1px solid white;
                border-radius: {max(6, (width - 2) // 2)}px;
                min-height: 36px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {cls.ACCENT_DARK};
            }}
            QScrollBar:horizontal {{
                background: rgba(255, 255, 255, 0.44);
                border: 1px solid rgba(31, 41, 51, 0.16);
                border-radius: {width // 2}px;
                height: {width}px;
                margin: 2px;
            }}
            QScrollBar::handle:horizontal {{
                background: {cls.ACCENT};
                border: 1px solid white;
                border-radius: {max(8, (width - 6) // 2)}px;
                min-width: 48px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background: {cls.ACCENT_DARK};
            }}
            QScrollBar::add-line, QScrollBar::sub-line {{
                width: 0;
                height: 0;
                border: 0;
                background: transparent;
            }}
            QScrollBar::add-page, QScrollBar::sub-page {{
                background: transparent;
            }}
        """

    @classmethod
    def global_control_style(cls) -> str:
        return f"""
            QPushButton {{
                min-height: {WaveToySizing.MIN_TOUCH_TARGET}px;
                padding: 5px 10px;
                border-radius: 8px;
                font-size: 13px;
                font-weight: 700;
            }}
            QComboBox, QSpinBox, QDoubleSpinBox {{
                min-height: {WaveToySizing.MIN_TOUCH_TARGET}px;
                padding: 3px 8px;
                border-radius: 7px;
            }}
            QCheckBox {{
                min-height: {WaveToySizing.MIN_TOUCH_TARGET}px;
                spacing: 6px;
                font-size: 13px;
                font-weight: 700;
            }}
            QGroupBox#toyGroup, QWidget#timelineInspector, QWidget#timelineAudioPalette, QWidget#explorerDashboardPanel {{
                margin-top: 8px;
            }}
        """


class WaveToyScrollArea(QScrollArea):
    """Unified scroll area with wheel, drag, kinetic scrolling, and accessible handles."""

    def __init__(self, *, scroll_speed: float = 1.0, content_drag_scroll: bool = True, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("waveToyScrollArea")
        self.setFrameShape(QScrollArea.NoFrame)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setStyleSheet(WaveToyTheme.scroll_area_style())
        self.scroll_speed = max(0.15, float(scroll_speed))
        self.content_drag_scroll = content_drag_scroll
        self._drag_active = False
        self._drag_scrolling = False
        self._drag_start = QPoint()
        self._last_pos = QPoint()
        self._last_time = time.monotonic()
        self._velocity_x = 0.0
        self._velocity_y = 0.0
        self._kinetic_timer = QTimer(self)
        self._kinetic_timer.timeout.connect(self._kinetic_tick)
        self.viewport().installEventFilter(self)
        self.viewport().setCursor(Qt.OpenHandCursor)

    def setWidget(self, widget: QWidget) -> None:  # noqa: N802 - Qt override name
        super().setWidget(widget)
        if self.content_drag_scroll:
            widget.installEventFilter(self)

    def set_scroll_speed(self, speed: float) -> None:
        self.scroll_speed = max(0.15, float(speed))

    def wheelEvent(self, event) -> None:
        delta = event.angleDelta()
        pixel_delta = event.pixelDelta()
        x_delta = pixel_delta.x() if not pixel_delta.isNull() else delta.x()
        y_delta = pixel_delta.y() if not pixel_delta.isNull() else delta.y()
        if x_delta == 0 and y_delta == 0:
            event.ignore()
            return
        horizontal = abs(x_delta) > abs(y_delta) and self.horizontalScrollBar().maximum() > 0
        if horizontal:
            self._scroll_by(dx=-(x_delta / 120.0) * 72.0 * self.scroll_speed, dy=0.0)
        elif self.verticalScrollBar().maximum() > 0:
            self._scroll_by(dx=0.0, dy=-(y_delta / 120.0) * 72.0 * self.scroll_speed)
        elif self.horizontalScrollBar().maximum() > 0:
            self._scroll_by(dx=-(y_delta / 120.0) * 72.0 * self.scroll_speed, dy=0.0)
        else:
            event.ignore()
            return
        event.accept()

    def keyPressEvent(self, event) -> None:
        step = int(72 * self.scroll_speed)
        if event.key() in (Qt.Key_Down, Qt.Key_PageDown):
            self._scroll_by(dy=step * (5 if event.key() == Qt.Key_PageDown else 1))
            event.accept()
            return
        if event.key() in (Qt.Key_Up, Qt.Key_PageUp):
            self._scroll_by(dy=-step * (5 if event.key() == Qt.Key_PageUp else 1))
            event.accept()
            return
        if event.key() == Qt.Key_Right:
            self._scroll_by(dx=step)
            event.accept()
            return
        if event.key() == Qt.Key_Left:
            self._scroll_by(dx=-step)
            event.accept()
            return
        super().keyPressEvent(event)

    def eventFilter(self, watched, event) -> bool:
        event_type = event.type()
        if event_type == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
            self._kinetic_timer.stop()
            self._drag_active = True
            self._drag_scrolling = False
            self._drag_start = event.globalPosition().toPoint()
            self._last_pos = self._drag_start
            self._last_time = time.monotonic()
            self._velocity_x = 0.0
            self._velocity_y = 0.0
            return False
        if event_type == QEvent.MouseMove and self._drag_active and event.buttons() & Qt.LeftButton:
            pos = event.globalPosition().toPoint()
            delta = pos - self._last_pos
            if not self._drag_scrolling and (pos - self._drag_start).manhattanLength() < QApplication.startDragDistance():
                return False
            self._drag_scrolling = True
            now = time.monotonic()
            elapsed = max(0.001, now - self._last_time)
            can_x = self.horizontalScrollBar().maximum() > 0
            can_y = self.verticalScrollBar().maximum() > 0
            dx = -delta.x() if can_x and (abs(delta.x()) >= abs(delta.y()) or not can_y) else 0
            dy = -delta.y() if can_y and (abs(delta.y()) >= abs(delta.x()) or not can_x) else 0
            self._scroll_by(dx=dx, dy=dy)
            self._velocity_x = dx / elapsed
            self._velocity_y = dy / elapsed
            self._last_pos = pos
            self._last_time = now
            self.viewport().setCursor(Qt.ClosedHandCursor)
            event.accept()
            return True
        if event_type == QEvent.MouseButtonRelease and self._drag_active:
            was_scrolling = self._drag_scrolling
            self._drag_active = False
            self._drag_scrolling = False
            self.viewport().setCursor(Qt.OpenHandCursor)
            if was_scrolling and (abs(self._velocity_x) > 80.0 or abs(self._velocity_y) > 80.0):
                self._kinetic_timer.start(16)
            return was_scrolling
        return super().eventFilter(watched, event)

    def _scroll_by(self, dx: float = 0.0, dy: float = 0.0) -> None:
        if dx:
            bar = self.horizontalScrollBar()
            bar.setValue(int(max(bar.minimum(), min(bar.maximum(), bar.value() + dx))))
        if dy:
            bar = self.verticalScrollBar()
            bar.setValue(int(max(bar.minimum(), min(bar.maximum(), bar.value() + dy))))

    def _kinetic_tick(self) -> None:
        self._velocity_x *= 0.88
        self._velocity_y *= 0.88
        if abs(self._velocity_x) < 8.0 and abs(self._velocity_y) < 8.0:
            self._kinetic_timer.stop()
            return
        old_x = self.horizontalScrollBar().value()
        old_y = self.verticalScrollBar().value()
        self._scroll_by(dx=self._velocity_x * 0.016, dy=self._velocity_y * 0.016)
        if old_x == self.horizontalScrollBar().value() and old_y == self.verticalScrollBar().value():
            self._kinetic_timer.stop()


class CollapsibleSection(QWidget):
    """Touch-friendly collapsible card used to reduce Articulation Lab density."""

    def __init__(self, title: str, content: QWidget, *, expanded: bool = True) -> None:
        super().__init__()
        self.setObjectName("collapsibleSection")
        self.content = content
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        self.toggle = QToolButton()
        self.toggle.setObjectName("collapsibleHeader")
        self.toggle.setText(title)
        self.toggle.setCheckable(True)
        self.toggle.setChecked(expanded)
        self.toggle.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.toggle.setArrowType(Qt.DownArrow if expanded else Qt.RightArrow)
        self.toggle.setMinimumHeight(WaveToySizing.BUTTON_HEIGHT)
        self.toggle.clicked.connect(self._toggle_content)
        outer.addWidget(self.toggle)
        outer.addWidget(self.content)
        self.content.setVisible(expanded)

    def _toggle_content(self, checked: bool) -> None:
        self.toggle.setArrowType(Qt.DownArrow if checked else Qt.RightArrow)
        self.content.setVisible(checked)


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
                border: 1px solid rgba(0, 0, 0, 0.18);
                border-radius: 10px;
                font-size: 15px;
                font-weight: 800;
                padding: 10px 18px;
            }}
            QPushButton:hover {{
                border: 1px solid rgba(0, 0, 0, 0.35);
            }}
            QPushButton:pressed {{
                padding-top: 14px;
            }}
            """
        )




class StoryboardClipWidget(QWidget):
    """Large touch-friendly storyboard clip card for the Timeline tab."""

    def __init__(self, icon: str, name: str, duration_text: str, wave_type: str, color: str) -> None:
        super().__init__()
        self.setObjectName("storyboardClip")
        self.setCursor(Qt.OpenHandCursor)
        self.setMinimumSize(QSize(260, 96))
        self.setToolTip("Drag this clip card to rearrange the Timeline. Duplicate, mute, and solo actions remain available.")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(12)

        icon_label = QLabel(icon)
        icon_label.setObjectName("storyboardClipIcon")
        icon_label.setFixedSize(QSize(58, 58))
        icon_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon_label)

        waveform = MiniWavePreview(wave_type, size=QSize(108, 58))
        waveform.set_amplitude(0.9)
        layout.addWidget(waveform)

        text_stack = QVBoxLayout()
        text_stack.setSpacing(2)
        name_label = QLabel(name)
        name_label.setObjectName("storyboardClipName")
        duration_label = QLabel(duration_text)
        duration_label.setObjectName("storyboardClipDuration")
        text_stack.addWidget(name_label)
        text_stack.addWidget(duration_label)
        layout.addLayout(text_stack, 1)

        action_stack = QVBoxLayout()
        action_stack.setSpacing(6)
        for label in ("⧉", "🔇", "⭐"):
            button = QPushButton(label)
            button.setObjectName("storyboardTinyAction")
            button.setMinimumSize(QSize(WaveToySizing.MIN_TOUCH_TARGET, WaveToySizing.MIN_TOUCH_TARGET))
            button.setToolTip({"⧉": "Duplicate this sound card.", "🔇": "Mute this sound card.", "⭐": "Solo this sound card."}[label])
            action_stack.addWidget(button)
        layout.addLayout(action_stack)
        self.setStyleSheet(
            f"""
            QWidget#storyboardClip {{
                background: #f7fafc;
                border: 1px solid {color};
                border-radius: 10px;
            }}
            """
        )

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.setCursor(Qt.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        self.setCursor(Qt.OpenHandCursor)
        super().mouseReleaseEvent(event)


class AudioPaletteCard(QWidget):
    """Large draggable toy card for an imported Timeline palette sound."""

    def __init__(self, owner: "WaveToyWindow", item: AudioPaletteItem) -> None:
        super().__init__()
        self.owner = owner
        self.item = item
        self.drag_start_pos: QPoint | None = None
        self.setObjectName("audioPaletteCard")
        self.setMinimumHeight(108)
        self.setCursor(Qt.OpenHandCursor)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_menu)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(76, 8, 8, 8)
        layout.addStretch(1)
        add_button = QPushButton("➕ Add")
        add_button.setMinimumSize(QSize(86, WaveToySizing.MIN_TOUCH_TARGET))
        add_button.setCursor(Qt.PointingHandCursor)
        add_button.clicked.connect(lambda checked=False: self.owner._timeline_add_palette_item_to_playhead(self.item.item_id))
        layout.addWidget(add_button, 0, Qt.AlignRight | Qt.AlignBottom)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(self.rect()).adjusted(3, 3, -3, -3)
        selected = getattr(self.owner, "timeline_selected_palette_item_id", None) == self.item.item_id
        painter.setPen(QPen(QColor("#ff4fa3" if selected else self.item.color), 4))
        painter.setBrush(QColor("#fff8d9" if selected else "#ffffff"))
        painter.drawRoundedRect(rect, 22, 22)

        painter.setFont(QFont("Arial", 30, QFont.Bold))
        painter.setPen(QColor("#263238"))
        painter.drawText(QRectF(rect.left() + 10, rect.top() + 12, 54, 48), Qt.AlignCenter, "🎧")

        text_left = rect.left() + 72
        painter.setFont(QFont("Arial", 14, QFont.Bold))
        painter.drawText(QRectF(text_left, rect.top() + 12, rect.width() - 160, 24), Qt.AlignLeft | Qt.AlignVCenter, self.item.name)
        painter.setFont(QFont("Arial", 11, QFont.Bold))
        painter.setPen(QColor("#607d8b"))
        painter.drawText(QRectF(text_left, rect.top() + 36, 170, 20), Qt.AlignLeft | Qt.AlignVCenter, f"{self.item.duration_seconds:.2f}s")

        wave_rect = QRectF(text_left, rect.top() + 62, max(80.0, rect.width() - 170), 30)
        painter.setPen(QPen(QColor(self.item.color), 3, Qt.SolidLine, Qt.RoundCap))
        peaks = self.item.waveform_peaks or []
        if peaks:
            step = wave_rect.width() / max(1, len(peaks))
            center = wave_rect.center().y()
            for index, peak in enumerate(peaks):
                x = wave_rect.left() + index * step
                height = max(2.0, float(peak) * wave_rect.height())
                painter.drawLine(QPointF(x, center - height / 2.0), QPointF(x, center + height / 2.0))

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.drag_start_pos = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
            self.owner._timeline_select_palette_item(self.item.item_id)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self.drag_start_pos is None or not (event.buttons() & Qt.LeftButton):
            return super().mouseMoveEvent(event)
        if (event.pos() - self.drag_start_pos).manhattanLength() < QApplication.startDragDistance():
            return
        self.owner._timeline_debug(f"Palette drag started id={self.item.item_id} name={self.item.name}")
        mime = QMimeData()
        mime.setData("application/x-wavetoy-palette-id", str(self.item.item_id).encode("utf-8"))
        mime.setText(self.item.name)
        drag = QDrag(self)
        drag.setMimeData(mime)
        pixmap = QPixmap(self.size())
        pixmap.fill(Qt.transparent)
        self.render(pixmap)
        drag.setPixmap(pixmap.scaledToWidth(220, Qt.SmoothTransformation))
        drag.setHotSpot(QPoint(30, 30))
        drag.exec(Qt.CopyAction)

    def mouseReleaseEvent(self, event) -> None:
        self.setCursor(Qt.OpenHandCursor)
        self.drag_start_pos = None
        super().mouseReleaseEvent(event)

    def _show_menu(self, pos: QPoint) -> None:
        menu = QMenu(self)
        add_action = menu.addAction("➕ Add to Timeline at Playhead")
        action = menu.exec(self.mapToGlobal(pos))
        if action == add_action:
            self.owner._timeline_add_palette_item_to_playhead(self.item.item_id)


class SpeechBinCard(QWidget):
    """Large draggable toy card for created articulation speech units."""

    def __init__(self, owner: "WaveToyWindow", item: SpeechBinItem) -> None:
        super().__init__()
        self.owner = owner
        self.item = item
        self.drag_start_pos: QPoint | None = None
        self.setObjectName("speechBinCard")
        self.setMinimumHeight(82)
        self.setCursor(Qt.OpenHandCursor)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_menu)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(76, 10, 10, 10)
        layout.addStretch(1)
        actions = (
            ("▶", "Preview", self.owner._timeline_preview_speech_item),
            ("✏", "Rename", self.owner._timeline_rename_speech_item),
            ("⧉", "Duplicate", self.owner._timeline_duplicate_speech_item),
            ("Del", "Delete", self.owner._timeline_delete_speech_item),
            ("+", "Add to Timeline", self.owner._timeline_add_speech_item_to_playhead),
        )
        for icon, tip, callback in actions:
            button = QPushButton(icon if tip != "Add to Timeline" else "+ Timeline")
            button.setToolTip(tip)
            button.setMinimumSize(QSize(42 if tip != "Add to Timeline" else 86, WaveToySizing.MIN_TOUCH_TARGET))
            button.setCursor(Qt.PointingHandCursor)
            button.clicked.connect(lambda checked=False, item_id=self.item.id, cb=callback: cb(item_id))
            layout.addWidget(button, 0, Qt.AlignRight | Qt.AlignBottom)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(self.rect()).adjusted(3, 3, -3, -3)
        selected = getattr(self.owner, "timeline_selected_speech_item_id", None) == self.item.id
        painter.setPen(QPen(QColor("#2563eb" if selected else "#64748b"), 2))
        painter.setBrush(QColor("#eaf2ff" if selected else "#ffffff"))
        painter.drawRoundedRect(rect, 10, 10)

        painter.setFont(QFont("Arial", 22, QFont.Bold))
        painter.setPen(QColor("#263238"))
        painter.drawText(QRectF(rect.left() + 10, rect.top() + 12, 54, 46), Qt.AlignCenter, self.item.icon)

        text_left = rect.left() + 72
        painter.setFont(QFont("Arial", 14, QFont.Bold))
        painter.drawText(QRectF(text_left, rect.top() + 12, rect.width() - 330, 24), Qt.AlignLeft | Qt.AlignVCenter, self.item.name)
        painter.setFont(QFont("Arial", 11, QFont.Bold))
        painter.setPen(QColor("#2563eb"))
        asset_type = "Phrase" if self.item.item_type == "chain" else self.item.item_type.title()
        painter.drawText(QRectF(text_left, rect.top() + 34, rect.width() - 330, 18), Qt.AlignLeft | Qt.AlignVCenter, f"{asset_type} • {self.item.duration_seconds:.2f}s • {self.item.source_mode}")
        painter.setPen(QColor("#607d8b"))
        sequence = self.item.display_sequence or self.item.ipa_sequence
        painter.drawText(QRectF(text_left, rect.top() + 56, rect.width() - 330, 20), Qt.AlignLeft | Qt.AlignVCenter, f"Sequence: {sequence}")

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.drag_start_pos = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
            self.owner._timeline_select_speech_item(self.item.id)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self.drag_start_pos is None or not (event.buttons() & Qt.LeftButton):
            return super().mouseMoveEvent(event)
        if (event.pos() - self.drag_start_pos).manhattanLength() < QApplication.startDragDistance():
            return
        mime = QMimeData()
        mime.setData("application/x-wavetoy-speech-id", str(self.item.id).encode("utf-8"))
        mime.setText(self.item.name)
        drag = QDrag(self)
        drag.setMimeData(mime)
        pixmap = QPixmap(self.size())
        pixmap.fill(Qt.transparent)
        self.render(pixmap)
        drag.setPixmap(pixmap.scaledToWidth(220, Qt.SmoothTransformation))
        drag.setHotSpot(QPoint(30, 30))
        drag.exec(Qt.CopyAction)

    def mouseReleaseEvent(self, event) -> None:
        self.setCursor(Qt.OpenHandCursor)
        self.drag_start_pos = None
        super().mouseReleaseEvent(event)

    def _show_menu(self, pos: QPoint) -> None:
        menu = QMenu(self)
        preview_action = menu.addAction("▶ Preview")
        rename_action = menu.addAction("✏ Rename")
        duplicate_action = menu.addAction("⧉ Duplicate")
        add_action = menu.addAction("➕ Add to Timeline at Playhead")
        delete_action = menu.addAction("🗑 Delete from Speech Assets")
        action = menu.exec(self.mapToGlobal(pos))
        if action == preview_action:
            self.owner._timeline_preview_speech_item(self.item.id)
        elif action == rename_action:
            self.owner._timeline_rename_speech_item(self.item.id)
        elif action == duplicate_action:
            self.owner._timeline_duplicate_speech_item(self.item.id)
        elif action == add_action:
            self.owner._timeline_add_speech_item_to_playhead(self.item.id)
        elif action == delete_action:
            self.owner._timeline_delete_speech_item(self.item.id)


class TimelineCanvas(QWidget):
    """Large draggable timeline canvas for arranging sound clips."""

    lane_height = 112
    header_width = 190
    top_pad = 18
    seconds_per_pixel_default = 0.018

    def __init__(self, owner: "WaveToyWindow") -> None:
        super().__init__()
        self.owner = owner
        self.setObjectName("timelineCanvas")
        self.setMouseTracking(True)
        self.setMinimumSize(QSize(980, 520))
        self.setCursor(Qt.ArrowCursor)
        self.seconds_per_pixel = self.seconds_per_pixel_default
        self.selected_clip_id: int | None = None
        self.drag_clip_id: int | None = None
        self.drag_offset_seconds = 0.0
        self.drag_started = False
        self.drag_operation: str | None = None
        self.drag_start_time_seconds = 0.0
        self.drag_start_trim_start_seconds = 0.0
        self.drag_start_trim_end_seconds = 0.0
        self.drag_start_duration_seconds = 0.0
        self.drag_start_playback_rate = 1.0
        self.drop_highlight_lane: int | None = None
        self.setAcceptDrops(True)
        self._clip_rect_debug_cache: set[tuple] = set()

    def _refresh_size(self) -> None:
        arrangement = self.owner.timeline_clips if hasattr(self.owner, "timeline_clips") else []
        lane_count = max(1, getattr(self.owner, "timeline_lane_count", 4))
        end_time = max([clip.end_time_seconds for clip in arrangement] or [8.0])
        width = int(self.header_width + max(8.0, end_time + 2.0) / self.seconds_per_pixel + 80)
        height = int(self.top_pad * 2 + lane_count * self.lane_height + 34)
        self.setMinimumSize(QSize(max(980, width), max(520, height)))
        self.resize(self.minimumSize())

    def set_zoom(self, factor: float) -> None:
        self.seconds_per_pixel = min(0.08, max(0.004, self.seconds_per_pixel * factor))
        self._clip_rect_debug_cache.clear()
        self._refresh_size()
        self.update()

    def _time_to_x(self, seconds: float) -> float:
        return self.header_width + max(0.0, seconds) / self.seconds_per_pixel

    def _x_to_time(self, x: float) -> float:
        return max(0.0, (x - self.header_width) * self.seconds_per_pixel)

    def _lane_top(self, lane: int) -> float:
        return self.top_pad + lane * self.lane_height

    def _lane_from_y(self, y: float) -> int:
        lane_count = max(1, getattr(self.owner, "timeline_lane_count", 4))
        return min(lane_count - 1, max(0, int((y - self.top_pad) // self.lane_height)))

    def _clip_rect(self, clip: TimelineClip) -> QRectF:
        start_x = self._time_to_x(clip.start_time_seconds)
        end_x = self._time_to_x(clip.start_time_seconds + clip.duration_seconds)
        y = self._lane_top(clip.lane) + 10
        width = max(1.0, end_x - start_x)
        height = 92.0
        self._debug_clip_rect(clip, width, False)
        return QRectF(start_x, y, width, height)

    def _clip_hit_rect(self, clip: TimelineClip) -> QRectF:
        rect = self._clip_rect(clip)
        minimum_hit_width = 24.0
        if rect.width() >= minimum_hit_width:
            return rect
        hit_rect = QRectF(rect)
        hit_rect.setWidth(minimum_hit_width)
        hit_rect.moveCenter(QPointF(rect.center().x(), rect.center().y()))
        hit_rect.setLeft(max(self.header_width, hit_rect.left()))
        self._debug_clip_rect(clip, rect.width(), True)
        return hit_rect

    def _debug_clip_rect(self, clip: TimelineClip, width: float, hitbox_applied: bool) -> None:
        cache = getattr(self, "_clip_rect_debug_cache", None)
        if cache is None:
            cache = set()
            self._clip_rect_debug_cache = cache
        key = (clip.clip_id, round(clip.start_time_seconds, 3), round(clip.duration_seconds, 4), round(self.seconds_per_pixel, 5), hitbox_applied)
        if key in cache:
            return
        cache.add(key)
        if hasattr(self.owner, "_timeline_debug"):
            self.owner._timeline_debug(
                f"Clip rect computed id={clip.clip_id} duration={clip.duration_seconds:.3f}s "
                f"samples={len(clip.audio)} sample_rate={clip.sample_rate} visual_width={width:.1f}px "
                f"seconds_per_pixel={self.seconds_per_pixel:.5f} minimum_hitbox_applied={hitbox_applied}"
            )

    def _clip_at(self, pos: QPoint) -> TimelineClip | None:
        for clip in reversed(getattr(self.owner, "timeline_clips", [])):
            if self._clip_hit_rect(clip).contains(QPointF(pos)):
                return clip
        return None

    def _edge_at(self, clip: TimelineClip, pos: QPoint) -> str | None:
        rect = self._clip_hit_rect(clip)
        x = float(pos.x())
        handle = 12.0
        if abs(x - rect.left()) <= handle:
            return "left"
        if abs(x - rect.right()) <= handle:
            return "right"
        return None

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor("#dff8ff"))

        lane_names = getattr(self.owner, "timeline_lane_names", ["🎵 Melody Lane", "🥁 Rhythm Lane", "🌌 Atmosphere Lane", "✨ Effects Lane"])
        lane_count = max(1, getattr(self.owner, "timeline_lane_count", len(lane_names)))
        canvas_right = self.width() - 18
        for lane in range(lane_count):
            top = self._lane_top(lane)
            lane_rect = QRectF(14, top, canvas_right - 14, self.lane_height - 8)
            is_drop_target = self.drop_highlight_lane == lane
            painter.setPen(QPen(QColor("#ff4fa3") if is_drop_target else QColor(0, 0, 0, 40), 5 if is_drop_target else 3))
            painter.setBrush(QColor("#ffe3f3") if is_drop_target else (QColor("#ffffff") if lane % 2 == 0 else QColor("#eefbff")))
            painter.drawRoundedRect(lane_rect, 24, 24)

            header_rect = QRectF(24, top + 10, self.header_width - 38, self.lane_height - 28)
            painter.setPen(QPen(QColor(0, 0, 0, 55), 3))
            painter.setBrush(QColor("#fff8d9"))
            painter.drawRoundedRect(header_rect, 18, 18)
            painter.setPen(QColor("#263238"))
            painter.setFont(QFont("Arial", 20, QFont.Bold))
            name = lane_names[lane] if lane < len(lane_names) else f"🛤️ Lane {lane + 1}"
            painter.drawText(header_rect.adjusted(8, 0, -8, 0), Qt.AlignCenter | Qt.TextWordWrap, name)

        # Time ruler and playhead.
        painter.setPen(QPen(QColor("#78909c"), 2))
        painter.setFont(QFont("Arial", 11, QFont.Bold))
        max_seconds = self._x_to_time(self.width())
        snap = float(getattr(self.owner, "timeline_snap_seconds", 0.05))
        if getattr(self.owner, "timeline_snap_enabled", True) and snap >= 0.005:
            painter.setPen(QPen(QColor(123, 44, 191, 35), 1, Qt.DotLine))
            mark = 0.0
            while mark <= max_seconds + snap:
                x = self._time_to_x(mark)
                painter.drawLine(QPointF(x, 20), QPointF(x, self.height() - 10))
                mark += snap
        for second in range(0, int(max_seconds) + 2):
            x = self._time_to_x(float(second))
            painter.setPen(QPen(QColor("#78909c"), 2))
            painter.drawLine(QPointF(x, 4), QPointF(x, self.height() - 10))
            painter.drawText(QRectF(x + 4, 0, 70, 18), Qt.AlignLeft | Qt.AlignVCenter, f"{second}s")

        playhead_x = self._time_to_x(getattr(self.owner, "timeline_playhead_seconds", 0.0))
        painter.setPen(QPen(QColor("#ff2f91"), 5, Qt.SolidLine, Qt.RoundCap))
        painter.drawLine(QPointF(playhead_x, 0), QPointF(playhead_x, self.height()))

        for clip in getattr(self.owner, "timeline_clips", []):
            rect = self._clip_rect(clip)
            selected = clip.clip_id == self.selected_clip_id
            is_speech = str(getattr(clip, "source_type", "")).startswith("articulation_")
            speech_type = str((clip.speech_metadata or {}).get("item_type", "speech")) if is_speech else ""
            icon = {"phoneme": "🔤", "syllable": "🔡", "word": "🧩", "chain": "🧬"}.get(speech_type, "🌊")
            gradient = QLinearGradient(rect.topLeft(), rect.bottomRight())
            gradient.setColorAt(0.0, QColor("#fff8d9" if not is_speech else "#fff1fb"))
            gradient.setColorAt(1.0, QColor(("#e7c6ff" if is_speech else "#b8f2e6") if not selected else "#ffd166"))
            painter.setPen(QPen(QColor("#ff4fa3" if selected else ("#7b2cbf" if is_speech else "#5c6bc0")), 5 if selected else 4))
            painter.setBrush(gradient)
            painter.drawRoundedRect(rect, min(22.0, max(1.0, rect.width() / 2.0)), 22)
            painter.setBrush(QColor(255, 255, 255, 210))
            painter.setPen(QPen(QColor("#1d3557"), 2))
            painter.drawRect(QRectF(rect.left() - 2, rect.top() + 16, 5, rect.height() - 32))
            painter.drawRect(QRectF(rect.right() - 3, rect.top() + 16, 5, rect.height() - 32))
            if abs(float(clip.playback_rate or 1.0) - 1.0) > 0.005:
                painter.setBrush(QColor("#7b2cbf"))
                painter.setPen(Qt.NoPen)
                rate_rect = QRectF(rect.right() - 104, rect.top() + 8, 98, 20)
                painter.drawRoundedRect(rate_rect, 7, 7)
                painter.setPen(QColor("#ffffff"))
                painter.setFont(QFont("Arial", 9, QFont.Bold))
                painter.drawText(rate_rect, Qt.AlignCenter, clip.stretch_badge)

            narrow = rect.width() < 72.0
            very_narrow = rect.width() < 24.0
            if narrow:
                hit_rect = self._clip_hit_rect(clip)
                painter.setBrush(Qt.NoBrush)
                painter.setPen(QPen(QColor(255, 79, 163, 120), 2, Qt.DashLine))
                painter.drawRoundedRect(hit_rect.adjusted(0, 10, 0, -10), 8, 8)
                handle_x = rect.center().x()
                handle_y = rect.top() + 12
                painter.setBrush(QColor("#ff4fa3" if selected else "#ffffff"))
                painter.setPen(QPen(QColor("#7b2cbf" if is_speech else "#5c6bc0"), 2))
                painter.drawEllipse(QPointF(handle_x, handle_y), 6, 6)
                label_rect = QRectF(rect.right() + 6, rect.top() + 6, 132, 38)
                painter.setBrush(QColor(255, 255, 255, 220))
                painter.setPen(QPen(QColor("#7b2cbf" if is_speech else "#5c6bc0"), 1))
                painter.drawRoundedRect(label_rect, 8, 8)
                painter.setFont(QFont("Arial", 10, QFont.Bold))
                painter.setPen(QColor("#263238"))
                painter.drawText(label_rect.adjusted(6, 0, -6, 0), Qt.AlignLeft | Qt.AlignVCenter, f"{icon} {clip.duration_seconds:.3f}s")
            else:
                painter.save()
                painter.setClipRect(rect.adjusted(0, 0, -1, 0))
                painter.setFont(QFont("Arial", 30, QFont.Bold))
                painter.setPen(QColor("#263238"))
                painter.drawText(QRectF(rect.left() + 12, rect.top() + 10, 48, 42), Qt.AlignCenter, icon)
                painter.setFont(QFont("Arial", 16, QFont.Bold))
                painter.drawText(QRectF(rect.left() + 66, rect.top() + 10, max(0.0, rect.width() - 80), 28), Qt.AlignLeft | Qt.AlignVCenter, clip.name)
                painter.setFont(QFont("Arial", 12, QFont.Bold))
                painter.setPen(QColor("#7b2cbf" if is_speech else "#607d8b"))
                badge = f" • {speech_type}" if is_speech else ""
                warning = " • muted" if clip.muted_warning else ""
                painter.drawText(QRectF(rect.left() + 66, rect.top() + 36, max(0.0, rect.width() - 80), 22), Qt.AlignLeft | Qt.AlignVCenter, f"{clip.duration_seconds:.2f}s • {clip.stretch_badge} • Pitch preserved • Lane {clip.lane + 1}{badge}{warning}")
                painter.restore()

            wave_rect = rect.adjusted(14 if not very_narrow else 1, 62, -14 if not very_narrow else -1, -12)
            painter.setPen(QPen(QColor("#7b2cbf" if is_speech else "#00a8cc"), 3 if not very_narrow else 2, Qt.SolidLine, Qt.RoundCap))
            audio = clip.visible_audio()
            if audio.ndim == 2 and len(audio) > 1 and wave_rect.width() >= 2:
                mono = audio.mean(axis=1)
                steps = max(2, min(90, int(max(2.0, wave_rect.width()) // 4)))
                points = []
                for i in range(steps):
                    sample_index = min(len(mono) - 1, int(i * len(mono) / steps))
                    x = wave_rect.left() + (wave_rect.width() * i / max(1, steps - 1))
                    y = wave_rect.center().y() - float(mono[sample_index]) * wave_rect.height() * 0.42
                    points.append(QPointF(x, y))
                for a, b in zip(points, points[1:]):
                    painter.drawLine(a, b)

    def mousePressEvent(self, event) -> None:
        if event.button() != Qt.LeftButton:
            return super().mousePressEvent(event)
        clip = self._clip_at(event.pos())
        if clip is not None:
            tool = getattr(self.owner, "timeline_edit_tool", "select")
            edge = self._edge_at(clip, event.pos())
            self.selected_clip_id = clip.clip_id
            self.drag_clip_id = clip.clip_id
            self.drag_operation = "move"
            if tool == "trim" and edge is not None:
                self.drag_operation = f"trim_{edge}"
            elif tool == "stretch" and edge is not None:
                self.drag_operation = f"stretch_{edge}"
            self.drag_offset_seconds = self._x_to_time(event.position().x()) - clip.start_time_seconds
            self.drag_start_time_seconds = clip.start_time_seconds
            self.drag_start_trim_start_seconds = clip.trim_start_seconds
            self.drag_start_trim_end_seconds = clip.trim_end_seconds
            self.drag_start_duration_seconds = clip.duration_seconds
            self.drag_start_playback_rate = clip.playback_rate
            self.drag_started = False
            self.setCursor(Qt.SizeHorCursor if self.drag_operation != "move" else Qt.ClosedHandCursor)
            self.owner._timeline_select_clip(clip.clip_id)
        else:
            self.selected_clip_id = None
            self.drag_clip_id = None
            self.drag_operation = None
            self.owner._timeline_clear_selection(move_playhead_to=self.owner._timeline_snap_time(self._x_to_time(event.position().x())))
        self.update()

    def mouseMoveEvent(self, event) -> None:
        if self.drag_clip_id is None:
            hover = self._clip_at(event.pos())
            if hover is not None and self._edge_at(hover, event.pos()) is not None and getattr(self.owner, "timeline_edit_tool", "select") in {"trim", "stretch"}:
                self.setCursor(Qt.SizeHorCursor)
            else:
                self.setCursor(Qt.OpenHandCursor if hover is not None else Qt.ArrowCursor)
            return
        clip = self.owner._timeline_clip_by_id(self.drag_clip_id)
        if clip is None:
            return
        old_start, old_lane = clip.start_time_seconds, clip.lane
        target_time = self.owner._timeline_snap_time(self._x_to_time(event.position().x()))
        minimum = 0.005
        op = self.drag_operation or "move"
        if op == "move":
            clip.start_time_seconds = self.owner._timeline_snap_time(self._x_to_time(event.position().x()) - self.drag_offset_seconds)
            clip.lane = self._lane_from_y(event.position().y())
        elif op == "trim_left":
            right_edge = self.drag_start_time_seconds + self.drag_start_duration_seconds
            new_start = min(max(0.0, target_time), right_edge - minimum)
            delta_visible = max(0.0, (new_start - self.drag_start_time_seconds) * clip.playback_rate)
            max_trim = max(0.0, clip.source_duration_seconds - self.drag_start_trim_end_seconds - minimum * clip.playback_rate)
            clip.trim_start_seconds = min(max_trim, self.drag_start_trim_start_seconds + delta_visible)
            clip.stretched_audio_cache = None
            clip._stretch_cache_key = None
            clip.start_time_seconds = new_start
        elif op == "trim_right":
            new_end = max(clip.start_time_seconds + minimum, target_time)
            wanted_source_visible = max(minimum * clip.playback_rate, (new_end - clip.start_time_seconds) * clip.playback_rate)
            clip.trim_end_seconds = max(0.0, clip.source_duration_seconds - clip.trim_start_seconds - wanted_source_visible)
            clip.stretched_audio_cache = None
            clip._stretch_cache_key = None
        elif op.startswith("stretch"):
            anchor = self.drag_start_time_seconds if op == "stretch_right" else self.drag_start_time_seconds + self.drag_start_duration_seconds
            new_duration = abs(target_time - anchor)
            new_duration = max(minimum, new_duration)
            new_duration = self.owner._timeline_snap_time(new_duration) if getattr(self.owner, "timeline_snap_enabled", True) else new_duration
            visible_source = max(minimum, clip.source_visible_duration_seconds)
            clip.playback_rate = float(np.clip(visible_source / max(minimum, new_duration), 0.25, 4.0))
            clip.stretched_audio_cache = None
            clip._stretch_cache_key = None
            if op == "stretch_left":
                clip.start_time_seconds = max(0.0, anchor - clip.duration_seconds)
        self.drag_started = True
        self.owner._timeline_update_duration()
        self.owner._timeline_update_inspector()
        if abs(old_start - clip.start_time_seconds) > 0.001 or old_lane != clip.lane:
            self.owner._timeline_debug(f"Clip edited id={clip.clip_id} op={op} start={clip.start_time_seconds:.3f}s lane={clip.lane} duration={clip.duration_seconds:.3f}s stretch_ratio={clip.stretch_ratio:.2f}x")
        self._refresh_size()
        self.update()

    def mouseReleaseEvent(self, event) -> None:
        if self.drag_clip_id is not None:
            self.owner._timeline_update_duration()
            self.owner._timeline_mark_mix_dirty()
        self.drag_clip_id = None
        self.drag_operation = None
        self.drag_started = False
        self.setCursor(Qt.OpenHandCursor)
        self.update()

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasFormat("application/x-wavetoy-palette-id") or event.mimeData().hasFormat("application/x-wavetoy-speech-id"):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event) -> None:
        if not (event.mimeData().hasFormat("application/x-wavetoy-palette-id") or event.mimeData().hasFormat("application/x-wavetoy-speech-id")):
            event.ignore()
            return
        self.drop_highlight_lane = self._lane_from_y(event.position().y())
        self.update()
        event.acceptProposedAction()

    def dragLeaveEvent(self, event) -> None:
        self.drop_highlight_lane = None
        self.update()
        event.accept()

    def dropEvent(self, event) -> None:
        start_time = self._x_to_time(event.position().x())
        lane = self._lane_from_y(event.position().y())
        if event.mimeData().hasFormat("application/x-wavetoy-speech-id"):
            try:
                item_id = int(bytes(event.mimeData().data("application/x-wavetoy-speech-id")).decode("utf-8"))
            except ValueError:
                event.ignore()
                return
            self.owner._timeline_debug(f"Speech item dropped on timeline id={item_id} start={start_time:.3f}s lane={lane}")
            self.owner._timeline_add_speech_item_to_timeline(item_id, start_time, lane)
        elif event.mimeData().hasFormat("application/x-wavetoy-palette-id"):
            try:
                item_id = int(bytes(event.mimeData().data("application/x-wavetoy-palette-id")).decode("utf-8"))
            except ValueError:
                event.ignore()
                return
            self.owner._timeline_debug(f"Palette item dropped on timeline id={item_id} start={start_time:.3f}s lane={lane}")
            self.owner._timeline_add_palette_item_to_timeline(item_id, start_time, lane)
        else:
            event.ignore()
            return
        self.drop_highlight_lane = None
        self.update()
        event.acceptProposedAction()



class NoWheelSlider(QSlider):
    """Slider that leaves mouse-wheel scrolling to parent scroll areas."""

    def wheelEvent(self, event) -> None:
        event.ignore()


class NoWheelComboBox(QComboBox):
    """Combo box that cannot be accidentally changed by page scrolling."""

    def wheelEvent(self, event) -> None:
        event.ignore()


class NoWheelSpinBox(QSpinBox):
    """Spin box that cannot be accidentally changed by page scrolling."""

    def wheelEvent(self, event) -> None:
        event.ignore()


class NoWheelDoubleSpinBox(QDoubleSpinBox):
    """Double spin box that cannot be accidentally changed by page scrolling."""

    def wheelEvent(self, event) -> None:
        event.ignore()


class VisualPanelButton(QPushButton):
    """Large dashboard launcher with a cheap cached symbolic preview."""

    COLORS = {
        "sine": QColor("#2ecc71"),
        "triangle": QColor("#f1c40f"),
        "sawtooth": QColor("#3498db"),
        "square": QColor("#e84393"),
    }

    def __init__(self, label: str, kind: str, color: str) -> None:
        super().__init__()
        self.label = label
        self.kind = kind
        self.accent = QColor(color)
        self.status_text = "Ready"
        self.preview_data: Dict[str, object] = {}
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(QSize(200, 118))
        self.setToolTip(f"Open {label} controls.")

    def set_status(self, status_text: str, preview_data: Dict[str, object] | None = None) -> None:
        self.status_text = status_text
        self.preview_data = preview_data or {}
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(self.rect()).adjusted(4, 4, -4, -4)

        gradient = QLinearGradient(rect.topLeft(), rect.bottomRight())
        gradient.setColorAt(0.0, QColor("#ffffff"))
        gradient.setColorAt(0.58, QColor(self.accent.red(), self.accent.green(), self.accent.blue(), 95))
        gradient.setColorAt(1.0, QColor("#fff7c7"))
        border = QColor(0, 0, 0, 95 if self.isDown() else 45)
        painter.setPen(QPen(border, 4 if self.isDown() else 3))
        painter.setBrush(gradient)
        painter.drawRoundedRect(rect, 24, 24)

        title_rect = QRectF(rect.left() + 12, rect.top() + 8, rect.width() - 24, 28)
        painter.setPen(QColor("#263238"))
        painter.setFont(QFont("Arial", 15, QFont.Bold))
        painter.drawText(title_rect, Qt.AlignCenter, self.label)

        symbol_rect = QRectF(rect.left() + 18, rect.top() + 38, rect.width() - 36, 42)
        painter.setPen(QColor("#263238"))
        painter.setFont(QFont("Arial", 30, QFont.Bold))
        painter.drawText(symbol_rect, Qt.AlignCenter, self._simple_symbol())

        status_rect = QRectF(rect.left() + 14, rect.bottom() - 30, rect.width() - 28, 22)
        painter.setPen(QColor("#455a64"))
        painter.setFont(QFont("Arial", 10, QFont.Bold))
        painter.drawText(status_rect, Qt.AlignCenter, self.status_text)

    def _simple_symbol(self) -> str:
        return {
            "shape": "〰️ + 🔺",
            "pitch": "🎡",
            "tuning": "🎼",
            "stereo": "⬅️ 🧍 ➡️",
            "effects": "✨",
            "presets": "🌈",
            "save": "💾",
        }.get(self.kind, "🎛")

    def _draw_preview(self, painter: QPainter, rect: QRectF) -> None:
        painter.setPen(QPen(QColor(255, 255, 255, 190), 2))
        painter.setBrush(QColor(255, 255, 255, 95))
        painter.drawRoundedRect(rect, 16, 16)
        if self.kind == "shape":
            self._draw_shape_mix(painter, rect)
        elif self.kind == "pitch":
            self._draw_pitch_orbit(painter, rect)
        elif self.kind == "tuning":
            self._draw_tuning_ladder(painter, rect)
        elif self.kind == "stereo":
            self._draw_stereo_field(painter, rect)
        elif self.kind == "effects":
            self._draw_effect_blobs(painter, rect)
        elif self.kind == "presets":
            self._draw_preset_cards(painter, rect)
        else:
            self._draw_save_card(painter, rect)

    def _draw_sample_waveform(self, painter: QPainter, rect: QRectF, samples: object, color: QColor, pen_width: int = 3) -> bool:
        values = np.asarray(samples, dtype=np.float32).reshape(-1) if samples is not None else np.zeros(0, dtype=np.float32)
        if values.size < 2:
            return False
        values = np.clip(values, -1.0, 1.0)
        path = QPainterPath()
        for index, value in enumerate(values):
            x = rect.left() + rect.width() * index / max(1, values.size - 1)
            y = rect.center().y() - float(value) * rect.height() * 0.42
            if index == 0:
                path.moveTo(x, y)
            else:
                path.lineTo(x, y)
        painter.setPen(QPen(color, pen_width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.drawPath(path)
        return True

    def _draw_shape_mix(self, painter: QPainter, rect: QRectF) -> None:
        live_samples = self.preview_data.get("samples")
        if self._draw_sample_waveform(painter, rect.adjusted(8, 8, -8, -8), live_samples, QColor("#ff4fa3"), 4):
            return
        amps = self.preview_data.get("amps", {})
        muted = self.preview_data.get("muted", {})
        solo = self.preview_data.get("solo")
        baseline = rect.center().y()
        for index, wave in enumerate(WAVE_ORDER):
            amp = float(amps.get(wave, 0.0))
            dimmed = bool(muted.get(wave, False)) or (solo is not None and solo != wave)
            color = QColor(self.COLORS[wave])
            color.setAlpha(70 if dimmed else 235)
            pen_width = 5 if solo == wave else 3
            painter.setPen(QPen(color, pen_width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            path = QPainterPath()
            y_offset = (index - 1.5) * rect.height() * 0.11
            for step in range(48):
                x = rect.left() + rect.width() * step / 47.0
                phase = step / 8.0
                if wave == "square":
                    value = 1.0 if (step // 6) % 2 == 0 else -1.0
                elif wave == "sawtooth":
                    value = (phase % 1.0) * 2.0 - 1.0
                elif wave == "triangle":
                    value = 1.0 - 4.0 * abs((phase % 1.0) - 0.5)
                else:
                    value = math.sin(phase * 2.0 * math.pi)
                y = baseline + y_offset - value * rect.height() * 0.18 * amp
                if step == 0:
                    path.moveTo(x, y)
                else:
                    path.lineTo(x, y)
            painter.drawPath(path)

    def _draw_pitch_orbit(self, painter: QPainter, rect: QRectF) -> None:
        center = rect.center()
        radius = min(rect.width(), rect.height()) * 0.34
        painter.setPen(QPen(QColor("#7bdff2"), 4))
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(center, radius, radius)
        notes = self.preview_data.get("notes", [])
        if not notes:
            notes = [("Main", "A", QColor("#ff4fa3"))]
        painter.setFont(QFont("Arial", 8, QFont.Bold))
        for index, item in enumerate(notes):
            name, note, color = item
            angle = -math.pi / 2 + index * 2 * math.pi / max(1, len(notes))
            point = QPointF(center.x() + math.cos(angle) * radius, center.y() + math.sin(angle) * radius)
            painter.setPen(QPen(QColor("white"), 2))
            painter.setBrush(color if isinstance(color, QColor) else QColor("#ff4fa3"))
            painter.drawEllipse(point, 12, 12)
            painter.setPen(QColor("#263238"))
            painter.drawText(QRectF(point.x() - 16, point.y() - 9, 32, 18), Qt.AlignCenter, str(note)[:2])

    def _draw_tuning_ladder(self, painter: QPainter, rect: QRectF) -> None:
        root = str(self.preview_data.get("root", "A"))
        method = str(self.preview_data.get("method", "Piano Steps"))
        painter.setPen(QPen(QColor("#9b5de5"), 4, Qt.SolidLine, Qt.RoundCap))
        path = QPainterPath()
        for step in range(12):
            x = rect.left() + rect.width() * (step + 0.5) / 12.0
            y = rect.bottom() - 12 - math.sin(step / 11.0 * math.pi) * (rect.height() - 28)
            if step == 0:
                path.moveTo(x, y)
            else:
                path.lineTo(x, y)
        painter.drawPath(path)
        painter.setFont(QFont("Arial", 13, QFont.Bold))
        painter.setPen(QColor("#263238"))
        painter.drawText(rect.adjusted(8, 0, -8, 0), Qt.AlignCenter, root)

    def _draw_stereo_field(self, painter: QPainter, rect: QRectF) -> None:
        painter.setPen(QPen(QColor("#90a4ae"), 2, Qt.DashLine))
        for frac in (0.2, 0.5, 0.8):
            x = rect.left() + rect.width() * frac
            painter.drawLine(QPointF(x, rect.top() + 8), QPointF(x, rect.bottom() - 8))
        positions = self.preview_data.get("positions", [])
        for index, item in enumerate(positions):
            wave, pan, width, dance = item
            color = QColor(self.COLORS.get(wave, QColor("#ff4fa3")))
            x = rect.center().x() + float(pan) * rect.width() * 0.38
            y = rect.top() + rect.height() * (0.28 + 0.14 * (index % 4))
            radius = 8 + float(width) * 12
            painter.setPen(QPen(color, 3))
            painter.setBrush(QColor(color.red(), color.green(), color.blue(), 70))
            painter.drawEllipse(QPointF(x, y), radius, radius)
            if float(dance) > 0.05:
                painter.setPen(QPen(QColor(color.red(), color.green(), color.blue(), 120), 2, Qt.DashLine))
                painter.setBrush(Qt.NoBrush)
                painter.drawEllipse(QPointF(x, y), radius + 8, radius + 8)

    def _draw_effect_blobs(self, painter: QPainter, rect: QRectF) -> None:
        active = bool(self.preview_data.get("paul_active", False))
        amount = float(self.preview_data.get("amount", 1.0))
        live_rect = rect.adjusted(8, rect.height() * 0.45, -8, -8)
        self._draw_sample_waveform(painter, live_rect, self.preview_data.get("after_samples"), QColor("#9b5de5" if active else "#78909c"), 3)
        blobs = 3 if active else 1
        for index in range(blobs):
            frac = (index + 1) / (blobs + 1)
            radius = 12 + min(18.0, amount * 0.9) * (0.45 + index * 0.18)
            center = QPointF(rect.left() + rect.width() * frac, rect.center().y())
            color = QColor("#9b5de5" if active else "#b0bec5")
            painter.setPen(QPen(QColor("white"), 3))
            painter.setBrush(QColor(color.red(), color.green(), color.blue(), 130))
            painter.drawEllipse(center, radius, radius)
        painter.setFont(QFont("Arial", 18, QFont.Bold))
        painter.setPen(QColor("#263238"))
        painter.drawText(rect.adjusted(0, 0, 0, -rect.height() * 0.25), Qt.AlignCenter, "✨" if active else "😴")

    def _draw_preset_cards(self, painter: QPainter, rect: QRectF) -> None:
        for index, color in enumerate(["#ffd166", "#7bdff2", "#ff99c8"]):
            card = QRectF(rect.left() + 18 + index * 24, rect.top() + 14 + index * 8, rect.width() * 0.48, rect.height() * 0.56)
            painter.setPen(QPen(QColor(0, 0, 0, 55), 2))
            painter.setBrush(QColor(color))
            painter.drawRoundedRect(card, 10, 10)
            painter.setPen(QPen(QColor("#263238"), 2))
            y = card.center().y()
            painter.drawLine(QPointF(card.left() + 10, y), QPointF(card.right() - 10, y - 8 + index * 5))

    def _draw_save_card(self, painter: QPainter, rect: QRectF) -> None:
        disk = QRectF(rect.left() + 20, rect.top() + 10, rect.height() * 0.74, rect.height() * 0.74)
        painter.setPen(QPen(QColor("#263238"), 3))
        painter.setBrush(QColor("#ffd166"))
        painter.drawRoundedRect(disk, 8, 8)
        painter.setBrush(QColor("#ffffff"))
        painter.drawRect(disk.adjusted(10, 8, -10, -disk.height() * 0.58))
        painter.setPen(QPen(QColor("#ff4fa3"), 3, Qt.SolidLine, Qt.RoundCap))
        path = QPainterPath()
        for step in range(28):
            x = rect.left() + rect.width() * (0.48 + 0.46 * step / 27.0)
            y = rect.center().y() - math.sin(step / 3.0) * rect.height() * 0.18
            if step == 0:
                path.moveTo(x, y)
            else:
                path.lineTo(x, y)
        painter.drawPath(path)


class WaveExplorerWindow(QWidget):
    """Large non-modal waveform popup that reuses WaveCanvas rendering."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent, Qt.Window)
        self.setWindowTitle("🌊 Wave Explorer")
        self.resize(760, 520)
        self.setMinimumSize(QSize(620, 420))

        self.playback_start_monotonic: float | None = None
        self.playback_duration_seconds = 0.0
        self.playback_audio_sample_count = 0
        self.playback_sample_rate = SAMPLE_RATE

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        title = QLabel("🌊 Wave Explorer")
        title.setObjectName("waveExplorerTitle")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        self.canvas = WaveCanvas()
        self.canvas.setMinimumSize(QSize(700, 380))
        layout.addWidget(self.canvas, 1)
        controls = QHBoxLayout()
        controls.setSpacing(10)
        for label, callback in (
            ("🔎 Zoom In", lambda checked=False: self.canvas.zoom_by(1.25)),
            ("🔍 Zoom Out", lambda checked=False: self.canvas.zoom_by(0.8)),
            ("⬅ Pan", lambda checked=False: self.canvas.pan_view(-1.0)),
            ("➡ Pan", lambda checked=False: self.canvas.pan_view(1.0)),
            ("↺ Reset", lambda checked=False: self.canvas.reset_zoom()),
        ):
            button = QPushButton(label)
            button.setMinimumHeight(WaveToySizing.BUTTON_HEIGHT)
            button.clicked.connect(callback)
            controls.addWidget(button)
        layout.addLayout(controls)

        self.status_label = QLabel("Mouse wheel zooms; buttons zoom, pan, and reset without hiding the waveform.")
        self.status_label.setObjectName("symbolHint")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        self.follow_timer = QTimer(self)
        self.follow_timer.timeout.connect(self._follow_playback_tick)

    def set_data(
        self,
        audio: np.ndarray,
        freq_env: np.ndarray,
        loud_env: np.ndarray,
        message: str,
        visual_conditions: dict | None = None,
    ) -> None:
        self.canvas.set_data(audio, freq_env, loud_env, message, visual_conditions)
        seconds = len(audio) / SAMPLE_RATE if audio.size else 0.0
        self.status_label.setText(
            f"{message}  •  {seconds:.2f}s sound-picture. Mouse wheel zooms; playback follow is approximate."
        )

    def start_playback_follow(self, audio_samples: int, sample_rate: int = SAMPLE_RATE) -> None:
        self.playback_audio_sample_count = int(max(0, audio_samples))
        self.playback_sample_rate = int(max(1, sample_rate))
        self.playback_duration_seconds = max(0.0, float(self.playback_audio_sample_count) / self.playback_sample_rate)
        if self.playback_duration_seconds <= 0.0:
            self.stop_playback_follow()
            return
        self.playback_start_monotonic = time.monotonic()
        self.follow_timer.start(33)
        print(f"[WaveToy Playback] scrolling enabled for Wave Explorer ({self.playback_duration_seconds:.2f}s)")
        self._follow_playback_tick()

    def stop_playback_follow(self) -> None:
        self.playback_start_monotonic = None
        self.canvas.set_playhead_fraction(None)
        if self.follow_timer.isActive():
            self.follow_timer.stop()

    def _follow_playback_tick(self) -> None:
        if self.playback_start_monotonic is None or self.playback_duration_seconds <= 0.0:
            self.stop_playback_follow()
            return
        elapsed = time.monotonic() - self.playback_start_monotonic
        if elapsed >= self.playback_duration_seconds:
            self.canvas.center_on_playback_fraction(1.0)
            self.stop_playback_follow()
            return
        self.canvas.center_on_playback_fraction(elapsed / self.playback_duration_seconds)


class MiniWavePreview(QWidget):
    """Tiny cached sample-based waveform preview used beside WaveToy sliders."""

    COLORS = {
        "sine": QColor("#2ecc71"),
        "triangle": QColor("#f1c40f"),
        "sawtooth": QColor("#3498db"),
        "square": QColor("#e84393"),
    }

    def __init__(self, wave_type: str = "sine", channel: str = "mono", size: QSize | None = None) -> None:
        super().__init__()
        self.wave_type = wave_type
        self.channel = channel
        self.amplitude = 1.0
        self.left_gain = 1.0
        self.right_gain = 1.0
        self.motion_depth = 0.0
        self.animation_phase = 0.0
        self.motion_active = False
        self.samples: np.ndarray | None = None
        self.setFixedSize(size or QSize(96, 46))
        self.setToolTip("Sample-based waveform preview. It scrolls while sound is playing or live loop is on.")

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)

    def set_wave_type(self, wave_type: str) -> None:
        if self.wave_type != wave_type:
            self.wave_type = wave_type
            self.update()

    def set_amplitude(self, value: float) -> None:
        value = float(np.clip(value, 0.0, 1.0))
        if abs(self.amplitude - value) > 0.001:
            self.amplitude = value
            self.update()

    def set_stereo(self, left_gain: float, right_gain: float) -> None:
        left_gain = float(np.clip(left_gain, 0.0, 1.0))
        right_gain = float(np.clip(right_gain, 0.0, 1.0))
        if abs(self.left_gain - left_gain) > 0.001 or abs(self.right_gain - right_gain) > 0.001:
            self.left_gain = left_gain
            self.right_gain = right_gain
            self.update()

    def set_motion_depth(self, value: float) -> None:
        value = float(np.clip(value, 0.0, 1.0))
        if abs(self.motion_depth - value) > 0.001:
            self.motion_depth = value
            self.update()

    def set_samples(self, samples: np.ndarray) -> None:
        new_samples = np.asarray(samples, dtype=np.float32).reshape(-1)
        if new_samples.size == 0:
            new_samples = np.zeros(24, dtype=np.float32)
        new_samples = np.clip(new_samples, -1.0, 1.0)
        if self.samples is None or self.samples.shape != new_samples.shape or not np.allclose(self.samples, new_samples, atol=0.001):
            self.samples = new_samples
            self.update()

    def set_motion(self, active: bool) -> None:
        self.motion_active = bool(active)
        if self.motion_active and not self.timer.isActive():
            self.timer.start(45)
        elif not self.motion_active and self.timer.isActive():
            self.timer.stop()
        self.update()

    def _tick(self) -> None:
        self.animation_phase = (self.animation_phase + 0.10) % (2.0 * math.pi)
        self.update()

    def _wave_value(self, cycle_position: float) -> float:
        cycle_position = cycle_position % 1.0
        if self.wave_type == "square":
            return 1.0 if cycle_position < 0.5 else -1.0
        if self.wave_type == "sawtooth":
            return 2.0 * cycle_position - 1.0
        if self.wave_type == "triangle":
            return 1.0 - 4.0 * abs(cycle_position - 0.5)
        return math.sin(2.0 * math.pi * cycle_position)

    def _channel_gain(self) -> float:
        dance_offset = 0.12 * self.motion_depth * math.sin(self.animation_phase) if self.motion_active else 0.0
        if self.channel == "left":
            return float(np.clip(self.left_gain + dance_offset, 0.0, 1.0))
        if self.channel == "right":
            return float(np.clip(self.right_gain - dance_offset, 0.0, 1.0))
        return max(self.left_gain, self.right_gain)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = QRectF(self.rect()).adjusted(2, 2, -2, -2)
        gradient = QLinearGradient(rect.topLeft(), rect.bottomRight())
        gradient.setColorAt(0.0, QColor("#ffffff"))
        gradient.setColorAt(1.0, QColor("#d7f3ff"))

        painter.setPen(QPen(QColor(0, 0, 0, 45), 2))
        painter.setBrush(gradient)
        painter.drawRoundedRect(rect, 12, 12)

        inner = rect.adjusted(8, 8, -8, -8)
        center_y = inner.center().y()
        painter.setPen(QPen(QColor("#77c8ff"), 1, Qt.DashLine))
        painter.drawLine(QPointF(inner.left(), center_y), QPointF(inner.right(), center_y))

        channel_gain = self._channel_gain()
        color = QColor(self.COLORS.get(self.wave_type, QColor("#2ecc71")))

        points = max(24, int(inner.width()))
        if self.samples is not None:
            source = self.samples
            scroll = int((self.animation_phase / (2.0 * math.pi)) * len(source)) if self.motion_active else 0
            peak = float(np.max(np.abs(source))) if source.size else 0.0
            color.setAlpha(55 + int(200 * np.clip(max(peak, channel_gain * 0.25), 0.0, 1.0)))
        else:
            source = None
            peak = max(0.05, self.amplitude * channel_gain)
            color.setAlpha(80 + int(175 * np.clip(channel_gain, 0.0, 1.0)))

        path = QPainterPath()
        cycles = 2.35
        phase_cycles = self.animation_phase / (2.0 * math.pi)
        for index in range(points):
            x_fraction = index / max(1, points - 1)
            x = inner.left() + x_fraction * inner.width()
            if source is not None:
                src_index = (int(round(x_fraction * (len(source) - 1))) + scroll) % len(source)
                y_value = float(source[src_index])
            else:
                y_value = self._wave_value(x_fraction * cycles + phase_cycles) * peak
            y = center_y - y_value * inner.height() * 0.44
            if index == 0:
                path.moveTo(QPointF(x, y))
            else:
                path.lineTo(QPointF(x, y))

        painter.setPen(QPen(QColor(0, 0, 0, 45), 5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.drawPath(path)
        painter.setPen(QPen(color, 3, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.drawPath(path)

        if self.channel in {"left", "right"}:
            painter.setPen(QColor("#263238"))
            painter.setFont(QFont("Arial", 8, QFont.Bold))
            painter.drawText(rect.adjusted(5, 2, -5, -2), Qt.AlignTop | Qt.AlignLeft, self.channel[:1].upper())


class EnvelopePreview(QWidget):
    """Cached loudness-envelope preview for one wave-card stage."""

    def __init__(self, size: QSize | None = None) -> None:
        super().__init__()
        self.envelope = np.ones(160, dtype=np.float32)
        self.change_fraction = 1.0
        self.start_gain = 1.0
        self.end_gain = 1.0
        self.setFixedSize(size or QSize(230, 54))
        self.setToolTip("Shows this ingredient's loudness path: start size, end size, and how quickly it changes.")

    def set_envelope(self, envelope: np.ndarray, metadata: Dict[str, float | bool]) -> None:
        new_envelope = np.asarray(envelope, dtype=np.float32).reshape(-1)
        if new_envelope.size == 0:
            new_envelope = np.zeros(160, dtype=np.float32)
        new_envelope = np.clip(new_envelope, 0.0, 1.0)
        changed = self.envelope.shape != new_envelope.shape or not np.allclose(self.envelope, new_envelope, atol=0.001)

        change_fraction = float(np.clip(metadata.get("change_fraction", 1.0), 0.0, 1.0))
        start_gain = float(np.clip(metadata.get("start_gain", new_envelope[0]), 0.0, 1.0))
        end_gain = float(np.clip(metadata.get("end_gain", new_envelope[-1]), 0.0, 1.0))
        changed = changed or any(
            abs(current - new) > 0.001
            for current, new in (
                (self.change_fraction, change_fraction),
                (self.start_gain, start_gain),
                (self.end_gain, end_gain),
            )
        )

        if changed:
            self.envelope = new_envelope
            self.change_fraction = change_fraction
            self.start_gain = start_gain
            self.end_gain = end_gain
            self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = QRectF(self.rect()).adjusted(2, 2, -2, -2)
        painter.setPen(QPen(QColor(0, 0, 0, 45), 2))
        painter.setBrush(QColor("#fff7d6"))
        painter.drawRoundedRect(rect, 12, 12)

        inner = rect.adjusted(10, 8, -10, -12)
        baseline = inner.bottom()
        painter.setPen(QPen(QColor("#ffd166"), 1, Qt.DashLine))
        for fraction in (0.25, 0.5, 0.75):
            y = inner.top() + inner.height() * fraction
            painter.drawLine(QPointF(inner.left(), y), QPointF(inner.right(), y))

        fill_path = QPainterPath()
        line_path = QPainterPath()
        for index, value in enumerate(self.envelope):
            x_fraction = index / max(1, len(self.envelope) - 1)
            x = inner.left() + x_fraction * inner.width()
            y = baseline - float(value) * inner.height()
            if index == 0:
                fill_path.moveTo(QPointF(x, baseline))
                fill_path.lineTo(QPointF(x, y))
                line_path.moveTo(QPointF(x, y))
            else:
                fill_path.lineTo(QPointF(x, y))
                line_path.lineTo(QPointF(x, y))
        fill_path.lineTo(QPointF(inner.right(), baseline))
        fill_path.closeSubpath()

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(255, 209, 102, 100))
        painter.drawPath(fill_path)
        painter.setPen(QPen(QColor("#f39c12"), 3, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.drawPath(line_path)

        change_x = inner.left() + inner.width() * self.change_fraction
        painter.setPen(QPen(QColor("#263238"), 2, Qt.DashLine))
        painter.drawLine(QPointF(change_x, inner.top()), QPointF(change_x, baseline + 4))

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#5cdb95"))
        painter.drawEllipse(QPointF(inner.left(), baseline - self.start_gain * inner.height()), 5, 5)
        painter.setBrush(QColor("#ff4fa3"))
        painter.drawEllipse(QPointF(inner.right(), baseline - self.end_gain * inner.height()), 5, 5)


class StereoFieldPreview(QWidget):
    """Cached per-wave stereo field preview with balance bars and movement."""

    COLORS = MiniWavePreview.COLORS

    def __init__(self, wave_type: str = "sine", size: QSize | None = None) -> None:
        super().__init__()
        self.wave_type = wave_type
        self.left_level = np.zeros(160, dtype=np.float32)
        self.right_level = np.zeros(160, dtype=np.float32)
        self.pan = np.zeros(160, dtype=np.float32)
        self.width = 1.0
        self.dance = 0.0
        self.animation_phase = 0.0
        self.motion_active = False
        self.setFixedSize(size or QSize(230, 54))
        self.setToolTip("Shows where this ingredient sits: left/right balance, spread, and dance movement.")

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)

    def set_wave_type(self, wave_type: str) -> None:
        if self.wave_type != wave_type:
            self.wave_type = wave_type
            self.update()

    def set_stereo_data(self, left_level: np.ndarray, right_level: np.ndarray, pan: np.ndarray, metadata: Dict[str, float | bool]) -> None:
        new_left = np.clip(np.asarray(left_level, dtype=np.float32).reshape(-1), 0.0, 1.0)
        new_right = np.clip(np.asarray(right_level, dtype=np.float32).reshape(-1), 0.0, 1.0)
        new_pan = np.clip(np.asarray(pan, dtype=np.float32).reshape(-1), -1.0, 1.0)
        if new_left.size == 0:
            new_left = np.zeros(160, dtype=np.float32)
        if new_right.size == 0:
            new_right = np.zeros(160, dtype=np.float32)
        if new_pan.size == 0:
            new_pan = np.zeros(160, dtype=np.float32)

        width = float(np.clip(metadata.get("width", 1.0), 0.0, 1.0))
        dance = float(np.clip(metadata.get("dance", 0.0), 0.0, 1.0))
        changed = (
            self.left_level.shape != new_left.shape
            or self.right_level.shape != new_right.shape
            or self.pan.shape != new_pan.shape
            or not np.allclose(self.left_level, new_left, atol=0.001)
            or not np.allclose(self.right_level, new_right, atol=0.001)
            or not np.allclose(self.pan, new_pan, atol=0.001)
            or abs(self.width - width) > 0.001
            or abs(self.dance - dance) > 0.001
        )
        if changed:
            self.left_level = new_left
            self.right_level = new_right
            self.pan = new_pan
            self.width = width
            self.dance = dance
            self.update()

    def set_motion(self, active: bool) -> None:
        self.motion_active = bool(active)
        if self.motion_active and not self.timer.isActive():
            self.timer.start(45)
        elif not self.motion_active and self.timer.isActive():
            self.timer.stop()
        self.update()

    def _tick(self) -> None:
        self.animation_phase = (self.animation_phase + 0.10) % (2.0 * math.pi)
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = QRectF(self.rect()).adjusted(2, 2, -2, -2)
        painter.setPen(QPen(QColor(0, 0, 0, 45), 2))
        painter.setBrush(QColor("#eef7ff"))
        painter.drawRoundedRect(rect, 12, 12)

        inner = rect.adjusted(10, 8, -10, -8)
        center_x = inner.center().x()
        center_y = inner.center().y()
        painter.setPen(QPen(QColor("#77c8ff"), 1, Qt.DashLine))
        painter.drawLine(QPointF(center_x, inner.top()), QPointF(center_x, inner.bottom()))
        painter.drawLine(QPointF(inner.left(), center_y), QPointF(inner.right(), center_y))

        left_peak = float(np.max(self.left_level)) if self.left_level.size else 0.0
        right_peak = float(np.max(self.right_level)) if self.right_level.size else 0.0
        bar_width = inner.width() * 0.38
        bar_height = 8.0
        left_bar = QRectF(center_x - bar_width * left_peak, inner.top() + 2, bar_width * left_peak, bar_height)
        right_bar = QRectF(center_x, inner.top() + 2, bar_width * right_peak, bar_height)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#4aa3ff"))
        painter.drawRoundedRect(left_bar, 4, 4)
        painter.setBrush(QColor("#ff6fb1"))
        painter.drawRoundedRect(right_bar, 4, 4)

        color = QColor(self.COLORS.get(self.wave_type, QColor("#2ecc71")))
        painter.setBrush(QColor(color.red(), color.green(), color.blue(), 70))
        painter.setPen(QPen(color, 3))

        pan_value = float(np.mean(self.pan)) if self.pan.size else 0.0
        if self.motion_active and self.dance > 0.0:
            pan_value += 0.18 * self.dance * math.sin(self.animation_phase)
        pan_value = float(np.clip(pan_value, -1.0, 1.0))
        x = center_x + pan_value * inner.width() * 0.45
        radius_x = 8.0 + self.width * 22.0
        radius_y = 7.0 + max(left_peak, right_peak) * 15.0
        painter.drawEllipse(QPointF(x, center_y + 6), radius_x, radius_y)

        if self.dance > 0.05:
            painter.setBrush(Qt.NoBrush)
            painter.setPen(QPen(QColor(color.red(), color.green(), color.blue(), 140), 2, Qt.DashLine))
            dancer = radius_x + self.dance * (8.0 + 4.0 * math.sin(self.animation_phase))
            painter.drawEllipse(QPointF(x, center_y + 6), dancer, radius_y + self.dance * 6.0)

        painter.setPen(QColor("#263238"))
        painter.setFont(QFont("Arial", 8, QFont.Bold))
        painter.drawText(rect.adjusted(6, 2, -6, -2), Qt.AlignTop | Qt.AlignLeft, "L")
        painter.drawText(rect.adjusted(6, 2, -6, -2), Qt.AlignTop | Qt.AlignRight, "R")


class CircleOfFifthsNotePicker(QWidget):
    """Toy-like circular note selector arranged in circle-of-fifths order."""

    noteSelected = Signal(str)

    FIFTHS_ORDER = ["C", "G", "D", "A", "E", "B", "F#", "C#", "G#", "D#", "A#", "F"]

    def __init__(self, accent_color: QColor | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._selected_note = "A"
        self._main_note = "A"
        self._accent_color = QColor(accent_color or QColor("#ff8cc6"))
        self._note_bubbles: Dict[str, QRectF] = {}
        self.setMinimumSize(QSize(330, 330))
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setToolTip("The wheel picks the note. Each note has a color, mood, and relationship to Home.")

    def sizeHint(self) -> QSize:
        return QSize(330, 330)

    def selected_note(self) -> str:
        return self._selected_note

    def main_note(self) -> str:
        return self._main_note

    def set_main_note(self, note: str) -> None:
        if note not in NOTE_TO_INDEX:
            note = "A"
        if note != self._main_note:
            self._main_note = note
            self.update()

    def set_note(self, note: str) -> None:
        if note not in NOTE_TO_INDEX:
            note = "A"
        if note != self._selected_note:
            self._selected_note = note
            self.update()

    def _bubble_rects(self) -> Dict[str, QRectF]:
        rect = QRectF(self.rect()).adjusted(16, 16, -16, -16)
        center = rect.center()
        radius = min(rect.width(), rect.height()) * 0.36
        bubble_radius = max(20.0, min(rect.width(), rect.height()) * 0.075)
        bubble_rects: Dict[str, QRectF] = {}
        for index, note in enumerate(self.FIFTHS_ORDER):
            angle = -math.pi / 2.0 + index * 2.0 * math.pi / len(self.FIFTHS_ORDER)
            x = center.x() + math.cos(angle) * radius
            y = center.y() + math.sin(angle) * radius
            size = bubble_radius * (2.35 if note == self._selected_note else 2.0)
            bubble_rects[note] = QRectF(x - size / 2.0, y - size / 2.0, size, size)
        return bubble_rects

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = QRectF(self.rect()).adjusted(8, 8, -8, -8)
        gradient = QLinearGradient(rect.topLeft(), rect.bottomRight())
        gradient.setColorAt(0.0, QColor("#fff7c7"))
        gradient.setColorAt(0.45, QColor("#d7f3ff"))
        gradient.setColorAt(1.0, QColor("#ffd6e7"))
        painter.setPen(QPen(QColor(0, 0, 0, 35), 3))
        painter.setBrush(gradient)
        painter.drawRoundedRect(rect, 30, 30)

        center = rect.center()
        wheel_radius = min(rect.width(), rect.height()) * 0.36
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(QColor(self._accent_color.red(), self._accent_color.green(), self._accent_color.blue(), 120), 6))
        painter.drawEllipse(center, wheel_radius, wheel_radius)
        painter.setPen(QPen(QColor(255, 255, 255, 170), 3, Qt.DashLine))
        painter.drawEllipse(center, wheel_radius * 0.72, wheel_radius * 0.72)

        painter.setPen(QColor("#263238"))
        painter.setFont(QFont("Arial", 16, QFont.Bold))
        painter.drawText(rect.adjusted(0, 10, 0, 0), Qt.AlignTop | Qt.AlignHCenter, "🎡 Note Wheel")
        painter.setFont(QFont("Arial", 9, QFont.Bold))
        painter.drawText(rect.adjusted(34, 0, -34, -16), Qt.AlignBottom | Qt.AlignHCenter, "Around the circle: C → G → D → A ...")

        self._note_bubbles = self._bubble_rects()
        for index, note in enumerate(self.FIFTHS_ORDER):
            bubble = self._note_bubbles[note]
            selected = note == self._selected_note
            emotion = note_emotion(note)
            fill = QColor(emotion["color"])
            if selected:
                fill = fill.lighter(118)
                glow = QColor(fill)
                glow.setAlpha(115)
                painter.setPen(QPen(glow, 9))
                painter.setBrush(Qt.NoBrush)
                painter.drawEllipse(bubble.adjusted(-4, -4, 4, 4))
            outline = QColor("#263238") if selected else QColor(255, 255, 255, 235)
            pen_width = 5 if selected else 2

            painter.setPen(QPen(outline, pen_width))
            painter.setBrush(fill)
            painter.drawEllipse(bubble)

            painter.setPen(QColor("#263238"))
            painter.setFont(QFont("Arial", 13 if selected else 11, QFont.Bold))
            painter.drawText(bubble.adjusted(0, 3, 0, -16), Qt.AlignCenter, emotion["emoji"])
            painter.setFont(QFont("Arial", 12 if selected else 10, QFont.Bold))
            painter.drawText(bubble.adjusted(0, 20, 0, -2), Qt.AlignCenter, note)

        selected_emotion = note_emotion(self._selected_note)
        center_text = f"Home: {emotional_note_text(self._main_note)}\n{self._selected_note} • {selected_emotion['label']}"
        painter.setFont(QFont("Arial", 12, QFont.Bold))
        painter.setPen(QColor("#263238"))
        painter.drawText(QRectF(center.x() - 76, center.y() - 42, 152, 84), Qt.AlignCenter, center_text)

    def mousePressEvent(self, event) -> None:
        for note, bubble in self._bubble_rects().items():
            if bubble.contains(event.position()):
                self.set_note(note)
                self.noteSelected.emit(note)
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        for note, bubble in self._bubble_rects().items():
            if bubble.contains(event.position()):
                emotion = note_emotion(note)
                self.setToolTip(f"{note} — {emotion['label']} • {note_relationship(note, self._main_note)}")
                return
        self.setToolTip("The wheel picks the note. Each note has a color, mood, and relationship to Home.")
        super().mouseMoveEvent(event)

    def keyPressEvent(self, event) -> None:
        if event.key() in (Qt.Key_Left, Qt.Key_Up, Qt.Key_Right, Qt.Key_Down):
            notes = self.FIFTHS_ORDER
            index = notes.index(self._selected_note) if self._selected_note in notes else notes.index("A")
            step = -1 if event.key() in (Qt.Key_Left, Qt.Key_Up) else 1
            self.set_note(notes[(index + step) % len(notes)])
            self.noteSelected.emit(self._selected_note)
            event.accept()
            return
        if event.key() in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Space):
            self.noteSelected.emit(self._selected_note)
            event.accept()
            return
        super().keyPressEvent(event)


class NoteWheelDialog(QDialog):
    """Small popup dialog that hosts the circular emotional note picker."""

    def __init__(
        self,
        wave_name: str,
        selected_note: str,
        accent_color: QColor,
        main_note: str = "A",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"🎡 Emotional Note Wheel - {wave_name}")
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        helper = QLabel("Pick a note character. Colors show mood; relationship hints compare each note to Home.")
        helper.setObjectName("subtitle")
        helper.setWordWrap(True)
        layout.addWidget(helper)

        self.center_label = QLabel()
        self.center_label.setObjectName("symbolHint")
        layout.addWidget(self.center_label)

        self.picker = CircleOfFifthsNotePicker(accent_color)
        self.picker.set_main_note(main_note)
        self.picker.set_note(selected_note)
        layout.addWidget(self.picker)

        self.selected_label = QLabel()
        self.selected_label.setObjectName("symbolHint")
        self.selected_label.setWordWrap(True)
        layout.addWidget(self.selected_label)

        self.picker.noteSelected.connect(lambda note: self.refresh_labels(note, self.picker.main_note()))
        self.refresh_labels(selected_note, main_note)

        close_button = QPushButton("Done")
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button, 0, Qt.AlignRight)

    def refresh_labels(self, selected_note: str | None = None, main_note: str | None = None) -> None:
        if selected_note is not None:
            self.picker.set_note(selected_note)
        if main_note is not None:
            self.picker.set_main_note(main_note)
        note = self.picker.selected_note()
        home = self.picker.main_note()
        emotion = note_emotion(note)
        self.center_label.setText(f"Home: {emotional_note_text(home)}")
        self.selected_label.setText(f"Selected Note: {emotional_note_text(note)} • {emotion['label']} • {note_relationship(note, home)}")


class VocalTractCanvas(QWidget):
    """Cartoon vocal tract display driven by articulation values, not DSP knobs."""

    articulationEdited = Signal(str, float)

    def __init__(self) -> None:
        super().__init__()
        self.phoneme = ArticulationPhoneme.from_json_dict(VOWEL_PRESETS["AH"] | {"name": "AH", "voice_pitch": 220.0, "voice_strength": 0.65})
        self.motion_current_name = "AH"
        self.motion_next_name = "—"
        self.motion_transition_progress = 0.0
        self.motion_transition_ms = 0
        self.motion_in_transition = False
        self.motion_playhead_fraction: float | None = None
        self.motion_timeline_blocks: List[Tuple[str, float, float, str]] = []
        self.editable = False
        self._drag_target: str | None = None
        self._last_mouth_rect = QRectF()
        self._last_face_rect = QRectF()
        self._last_nose_rect = QRectF()
        self._last_throat_rect = QRectF()
        self.setMinimumSize(QSize(560, 360))
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setToolTip("Toy vocal tract: mouth openness, tongue position, and lip rounding update as you explore vowels.")

    def set_editable(self, editable: bool) -> None:
        self.editable = bool(editable)
        self.setCursor(Qt.CrossCursor if self.editable else Qt.ArrowCursor)
        self.setToolTip(
            "Direct vocal editor: drag tongue, mouth, lips, airflow, nose, or voice to update Articulation Lab sliders."
            if self.editable
            else "Toy vocal tract: mouth openness, tongue position, and lip rounding update as you explore vowels."
        )

    def set_phoneme(self, phoneme: ArticulationPhoneme) -> None:
        self.phoneme = phoneme.clamped()
        self.update()

    def set_motion_state(
        self,
        phoneme: ArticulationPhoneme,
        current_name: str,
        next_name: str = "—",
        transition_progress: float = 0.0,
        playhead_fraction: float | None = None,
        transition_ms: int = 0,
        in_transition: bool = False,
    ) -> None:
        self.phoneme = phoneme.clamped()
        self.motion_current_name = current_name or self.phoneme.name
        self.motion_next_name = next_name or "—"
        self.motion_transition_progress = float(np.clip(transition_progress, 0.0, 1.0))
        self.motion_transition_ms = int(max(0, transition_ms))
        self.motion_in_transition = bool(in_transition)
        self.motion_playhead_fraction = None if playhead_fraction is None else float(np.clip(playhead_fraction, 0.0, 1.0))
        self.update()

    def set_motion_timeline(self, blocks: List[Tuple[str, float, float, str]]) -> None:
        self.motion_timeline_blocks = list(blocks)
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt override
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor("#fff7e6"))
        rect = QRectF(self.rect()).adjusted(28, 24, -28, -24)

        p = self.phoneme
        mouth_open = float(np.clip(p.mouth_open, 0.0, 1.0))
        tongue_height = float(np.clip(p.tongue_height, 0.0, 1.0))
        tongue_front = float(np.clip(p.tongue_frontness, 0.0, 1.0))
        rounding = float(np.clip(p.lip_rounding, 0.0, 1.0))
        closure = float(np.clip(p.closure, 0.0, 1.0))
        nasal_open = float(np.clip(p.nasal_open, 0.0, 1.0))
        air_pressure = float(np.clip(p.air_pressure, 0.0, 1.0))

        tract_w = min(rect.width() - 48, 680.0)
        tract_h = min(rect.height() - 36, 308.0)
        tract_rect = QRectF(
            rect.center().x() - tract_w / 2,
            rect.center().y() - tract_h / 2,
            tract_w,
            tract_h,
        )
        face_rect = tract_rect.adjusted(18, 8, -18, -8)
        painter.setPen(QPen(QColor("#5f4b32"), 5))
        painter.setBrush(QColor("#ffe0bd"))
        painter.drawRoundedRect(face_rect, 58, 58)

        painter.setPen(QPen(QColor("#3a506b"), 4))
        painter.setBrush(QColor("#ffffff"))
        eye_y = face_rect.top() + face_rect.height() * 0.23
        painter.drawEllipse(QRectF(face_rect.left() + face_rect.width() * 0.30, eye_y, 34, 42))
        painter.drawEllipse(QRectF(face_rect.left() + face_rect.width() * 0.62, eye_y, 34, 42))

        nose_rect = QRectF(face_rect.center().x() - 24, face_rect.top() + face_rect.height() * 0.30, 48, 54)
        painter.setPen(QPen(QColor("#8d6e63"), 3))
        painter.setBrush(QColor("#ffc8a2"))
        painter.drawEllipse(nose_rect)

        mouth_w = face_rect.width() * (0.32 + (1.0 - rounding) * 0.24)
        mouth_h = 56 + mouth_open * 150
        mouth_cx = face_rect.center().x() + face_rect.width() * 0.04
        mouth_cy = face_rect.top() + face_rect.height() * 0.64
        mouth_rect = QRectF(mouth_cx - mouth_w / 2, mouth_cy - mouth_h / 2, mouth_w, mouth_h)
        mouth_rect = mouth_rect.intersected(face_rect.adjusted(48, 86, -48, -28))
        self._last_face_rect = QRectF(face_rect)
        self._last_mouth_rect = QRectF(mouth_rect)
        self._last_nose_rect = QRectF(nose_rect)
        painter.setPen(QPen(QColor("#8c2f39"), 8 + int(rounding * 9)))
        painter.setBrush(QColor("#301018"))
        painter.drawEllipse(mouth_rect)

        lip_pad_x = 12 + rounding * 28
        lip_pad_y = 8 + rounding * 16
        lip_rect = mouth_rect.adjusted(-lip_pad_x, -lip_pad_y, lip_pad_x, lip_pad_y)
        painter.setPen(QPen(QColor("#d1495b"), 5 + int(rounding * 3)))
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(lip_rect)

        tongue_x = mouth_rect.left() + mouth_rect.width() * (0.18 + tongue_front * 0.64)
        tongue_y = mouth_rect.bottom() - 22 - tongue_height * max(34, mouth_rect.height() * 0.58)
        tongue_path = QPainterPath()
        tongue_base_left = QPointF(mouth_rect.left() + mouth_rect.width() * 0.16, mouth_rect.bottom() - 18)
        tongue_base_right = QPointF(mouth_rect.right() - mouth_rect.width() * 0.14, mouth_rect.bottom() - 18)
        tongue_path.moveTo(tongue_base_left)
        tongue_path.cubicTo(tongue_x - 80, tongue_y + 54, tongue_x - 18, tongue_y - 34, tongue_x + 68, tongue_y + 4)
        tongue_path.cubicTo(tongue_x + 48, tongue_y + 58, tongue_base_right.x(), tongue_base_right.y() + 2, tongue_base_left.x(), tongue_base_left.y())
        painter.setPen(QPen(QColor("#b23a48"), 3))
        painter.setBrush(QColor("#ff8fa3"))
        painter.drawPath(tongue_path)

        if closure > 0.08:
            closure_y = mouth_rect.center().y() - (closure * mouth_rect.height() * 0.12)
            painter.setPen(QPen(QColor("#ffb703"), 6 + int(closure * 10), Qt.SolidLine, Qt.RoundCap))
            painter.drawLine(QPointF(mouth_rect.left() + 22, closure_y), QPointF(mouth_rect.right() - 22, closure_y))

        if air_pressure > 0.05:
            painter.setPen(QPen(QColor(78, 205, 196, 55 + int(air_pressure * 130)), 3, Qt.DashLine, Qt.RoundCap))
            for i in range(4):
                y = mouth_rect.center().y() - 30 + i * 20
                painter.drawLine(QPointF(face_rect.left() + 46, y), QPointF(mouth_rect.left() - 12, y + (i - 1.5) * 5))
            painter.setPen(QPen(QColor(78, 205, 196, 60 + int(air_pressure * 100)), 2, Qt.DotLine, Qt.RoundCap))
            painter.drawLine(QPointF(mouth_rect.right() + 8, mouth_rect.center().y()), QPointF(face_rect.right() - 48, mouth_rect.center().y() - 14))

        if nasal_open > 0.05:
            painter.setPen(QPen(QColor("#6a4c93"), 3 + int(nasal_open * 6)))
            painter.drawArc(nose_rect.adjusted(7, 14, -7, 10), 200 * 16, 140 * 16)
            painter.setPen(QPen(QColor("#6a4c93"), 2, Qt.DotLine))
            painter.drawLine(QPointF(nose_rect.center().x(), nose_rect.bottom()), QPointF(nose_rect.center().x(), mouth_rect.top()))

        voice_strength = float(np.clip(p.voice_strength if p.voiced else 0.0, 0.0, 1.0))
        throat = QRectF(face_rect.left() + 42, face_rect.bottom() - 94, 64, 58)
        self._last_throat_rect = QRectF(throat)
        voice_color = QColor(40, 167, 69, 60 + int(voice_strength * 150)) if p.voiced else QColor(108, 117, 125, 80)
        painter.setPen(QPen(QColor("#28a745") if p.voiced else QColor("#6c757d"), 3))
        painter.setBrush(voice_color)
        painter.drawEllipse(throat)
        if p.voiced:
            for offset in (-14, 0, 14):
                painter.drawArc(throat.adjusted(16 + offset, 15, -16 + offset, -15), 35 * 16, 110 * 16)
        painter.setFont(QFont("Arial", 8, QFont.Bold))
        painter.drawText(throat.adjusted(-18, 50, 18, 70), Qt.AlignCenter, f"Voice {voice_strength:.2f}" if p.voiced else "Unvoiced")

        painter.setPen(QPen(QColor("#1d3557"), 2))
        painter.setFont(QFont("Arial", 13, QFont.Bold))
        painter.drawText(rect.left() + 8, rect.top() + 20, f"Current: {self.motion_current_name}   Next: {self.motion_next_name}")
        transition_prefix = "Active" if self.motion_in_transition else "Next"
        progress_label = f"{transition_prefix}: {self.motion_transition_ms} ms • {int(self.motion_transition_progress * 100):02d}%"
        painter.drawText(rect.right() - 260, rect.top() + 20, progress_label)

        timeline_rect = QRectF(rect.left() + 16, rect.bottom() - 34, rect.width() - 32, 22)
        painter.setPen(QPen(QColor("#1d3557"), 2))
        painter.setBrush(QColor("#f8f9fa"))
        painter.drawRoundedRect(timeline_rect, 8, 8)
        for label, start, end, color in self.motion_timeline_blocks:
            block_left = timeline_rect.left() + timeline_rect.width() * float(np.clip(start, 0.0, 1.0))
            block_right = timeline_rect.left() + timeline_rect.width() * float(np.clip(end, 0.0, 1.0))
            block_rect = QRectF(block_left, timeline_rect.top(), max(3.0, block_right - block_left), timeline_rect.height())
            is_transition = label == "→"
            active_transition = bool(is_transition and self.motion_playhead_fraction is not None and start <= self.motion_playhead_fraction <= end)
            painter.setBrush(QColor("#ffd166") if active_transition else (QColor("#ffffff") if is_transition else QColor(color)))
            painter.setPen(QPen(QColor("#e63946") if active_transition else QColor("#6c757d"), 3 if active_transition else 1, Qt.DashLine if is_transition else Qt.SolidLine))
            painter.drawRoundedRect(block_rect.adjusted(1, 2, -1, -2), 5, 5)
            if block_rect.width() > 26 and not is_transition:
                painter.setPen(QPen(QColor("#1d3557"), 1))
                painter.setFont(QFont("Arial", 8, QFont.Bold))
                painter.drawText(block_rect, Qt.AlignCenter, label[:6])
        if self.motion_playhead_fraction is not None:
            x = timeline_rect.left() + timeline_rect.width() * self.motion_playhead_fraction
            painter.setPen(QPen(QColor("#e63946"), 4, Qt.SolidLine, Qt.RoundCap))
            painter.drawLine(QPointF(x, timeline_rect.top() - 7), QPointF(x, timeline_rect.bottom() + 7))

        if self.editable:
            painter.setPen(QPen(QColor("#e63946"), 2, Qt.DashLine))
            painter.setBrush(QColor(255, 255, 255, 120))
            tongue_handle = QPointF(tongue_x, tongue_y)
            painter.drawEllipse(tongue_handle, 12, 12)
            painter.drawText(QRectF(tongue_handle.x() - 58, tongue_handle.y() - 34, 116, 24), Qt.AlignCenter, "drag tongue")
            painter.drawText(QRectF(mouth_rect.right() + 8, mouth_rect.center().y() - 12, 112, 24), Qt.AlignLeft, "mouth / air")
            painter.drawText(QRectF(lip_rect.left(), lip_rect.bottom() + 4, lip_rect.width(), 24), Qt.AlignCenter, "drag lips")
            painter.drawText(QRectF(nose_rect.left() - 38, nose_rect.top() - 24, 124, 24), Qt.AlignCenter, "click nose")
            painter.drawText(QRectF(throat.left() - 22, throat.top() - 24, 116, 24), Qt.AlignCenter, "click voice")

        painter.end()

    def mousePressEvent(self, event) -> None:  # noqa: N802 - Qt override
        if not self.editable:
            return super().mousePressEvent(event)
        pos = event.position() if hasattr(event, "position") else QPointF(event.pos())
        if self._last_nose_rect.adjusted(-12, -12, 12, 12).contains(pos):
            next_value = 0.0 if self.phoneme.nasal_open >= 0.5 else 1.0
            self.articulationEdited.emit("nasal_open", next_value)
            return
        if self._last_throat_rect.adjusted(-14, -14, 14, 14).contains(pos):
            self.articulationEdited.emit("voiced", 0.0 if self.phoneme.voiced else 1.0)
            return
        self._drag_target = "tongue" if self._last_mouth_rect.contains(pos) else "air_pressure"
        self._emit_drag_value(pos)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802 - Qt override
        if not self.editable or not self._drag_target:
            return super().mouseMoveEvent(event)
        pos = event.position() if hasattr(event, "position") else QPointF(event.pos())
        self._emit_drag_value(pos)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802 - Qt override
        self._drag_target = None
        return super().mouseReleaseEvent(event)

    def wheelEvent(self, event) -> None:  # noqa: N802 - Qt override
        if not self.editable:
            return super().wheelEvent(event)
        delta = 0.06 if event.angleDelta().y() > 0 else -0.06
        self.articulationEdited.emit("air_pressure", float(np.clip(self.phoneme.air_pressure + delta, 0.0, 1.0)))
        event.accept()

    def _emit_drag_value(self, pos: QPointF) -> None:
        mouth = self._last_mouth_rect
        face = self._last_face_rect
        if not mouth.isValid() or not face.isValid():
            return
        if self._drag_target == "tongue":
            tongue_frontness = (pos.x() - mouth.left()) / max(1.0, mouth.width())
            tongue_height = (mouth.bottom() - pos.y()) / max(1.0, mouth.height() * 0.72)
            self.articulationEdited.emit("tongue_frontness", float(np.clip(tongue_frontness, 0.0, 1.0)))
            self.articulationEdited.emit("tongue_height", float(np.clip(tongue_height, 0.0, 1.0)))
            mouth_open = (mouth.height() - 56.0) / 150.0
            self.articulationEdited.emit("mouth_open", float(np.clip(mouth_open + (pos.y() - mouth.center().y()) / max(90.0, face.height()), 0.0, 1.0)))
            rounding = 1.0 - ((mouth.width() / max(1.0, face.width())) - 0.32) / 0.24
            self.articulationEdited.emit("lip_rounding", float(np.clip(rounding + (mouth.center().x() - pos.x()) / max(180.0, mouth.width() * 2.0), 0.0, 1.0)))
        else:
            pressure = 1.0 - ((pos.y() - face.top()) / max(1.0, face.height()))
            self.articulationEdited.emit("air_pressure", float(np.clip(pressure, 0.0, 1.0)))


class ArticulationTimelineCanvas(QWidget):
    """Draggable speech timeline for phoneme duration, boundaries, and scrub position."""

    durationEdited = Signal(int, int)
    transitionEdited = Signal(int, int)
    blockSelected = Signal(int)
    scrubbed = Signal(float)

    def __init__(self) -> None:
        super().__init__()
        self.items: List[ArticulationChainItem] = []
        self.total_ms = 1
        self.zoom = 1.0
        self.playhead_ms = 0.0
        self.drag_mode: str | None = None
        self.drag_index: int | None = None
        self.selected_index: int | None = None
        self.setMinimumHeight(190)
        self.setMinimumWidth(900)
        self.setMouseTracking(True)
        self.setToolTip("Drag the red playhead to scrub; drag block edges for duration; drag dashed transition wedges for boundary length.")

    def set_timeline(self, items: List[ArticulationChainItem], total_ms: int, playhead_ms: float) -> None:
        self.items = list(items)
        self.total_ms = max(1, int(total_ms))
        self.playhead_ms = float(np.clip(playhead_ms, 0.0, self.total_ms))
        self.setMinimumWidth(max(900, int(self.total_ms * self.zoom * 1.15)))
        self.updateGeometry()
        self.update()

    def set_items(self, items: List[ArticulationChainItem], selected_index: int | None = None) -> None:
        self.items = list(items)
        if isinstance(selected_index, int) and 0 <= selected_index < len(self.items):
            self.selected_index = selected_index
        else:
            self.selected_index = None
        total_ms = 0
        for index, item in enumerate(self.items):
            total_ms += int(item.duration_ms or item.phoneme.duration_ms)
            if index < len(self.items) - 1:
                total_ms += max(0, int(item.transition_to_next_ms if item.transition_to_next_ms is not None else ARTICULATION_DEFAULT_TRANSITION_MS))
        self.total_ms = max(1, total_ms)
        self.playhead_ms = float(np.clip(self.playhead_ms, 0.0, self.total_ms))
        self.setMinimumWidth(max(900, int(self.total_ms * self.zoom * 1.15)))
        self.updateGeometry()
        self.update()

    def set_zoom(self, zoom: float) -> None:
        self.zoom = float(np.clip(zoom, 0.35, 3.5))
        self.set_timeline(self.items, self.total_ms, self.playhead_ms)

    def _px_per_ms(self) -> float:
        return max(0.25, self.zoom)

    def _lane_rect(self) -> QRectF:
        return QRectF(24, 54, max(1.0, self.total_ms * self._px_per_ms()), 74)

    def _segment_rects(self) -> List[Tuple[str, int, QRectF]]:
        rects: List[Tuple[str, int, QRectF]] = []
        lane = self._lane_rect()
        cursor = lane.left()
        px = self._px_per_ms()
        for index, item in enumerate(self.items):
            width = max(1.0, int(item.duration_ms or item.phoneme.duration_ms) * px)
            rects.append(("block", index, QRectF(cursor, lane.top(), width, lane.height())))
            cursor += width
            if index < len(self.items) - 1:
                transition = max(0, int(item.transition_to_next_ms if item.transition_to_next_ms is not None else ARTICULATION_DEFAULT_TRANSITION_MS))
                trans_width = max(1.0, transition * px)
                rects.append(("transition", index, QRectF(cursor, lane.top() + 10, trans_width, lane.height() - 20)))
                cursor += trans_width
        return rects

    def _ms_from_x(self, x: float) -> float:
        lane = self._lane_rect()
        return float(np.clip((x - lane.left()) / self._px_per_ms(), 0.0, self.total_ms))

    def mousePressEvent(self, event) -> None:  # noqa: N802 - Qt override
        if not self.items:
            return
        pos = event.position() if hasattr(event, "position") else event.pos()
        x = float(pos.x())
        self.drag_mode = "playhead"
        self.drag_index = None
        playhead_x = self._lane_rect().left() + self.playhead_ms * self._px_per_ms()
        for kind, index, rect in self._segment_rects():
            hit_rect = rect.adjusted(-8, -10, 8, 10)
            if hit_rect.contains(pos):
                self.drag_index = index
                if kind == "transition":
                    self.drag_mode = "transition"
                elif abs(x - rect.right()) <= 12.0:
                    self.drag_mode = "duration_right"
                elif abs(x - rect.left()) <= 12.0:
                    self.drag_mode = "duration_left"
                else:
                    self.drag_mode = "playhead"
                    self.blockSelected.emit(index)
                break
        if abs(x - playhead_x) <= 14.0:
            self.drag_mode = "playhead"
        if self.drag_mode == "playhead":
            self.playhead_ms = self._ms_from_x(x)
            self.scrubbed.emit(self.playhead_ms)
            self.update()

    def mouseMoveEvent(self, event) -> None:  # noqa: N802 - Qt override
        if self.drag_mode is None:
            return
        pos = event.position() if hasattr(event, "position") else event.pos()
        x = float(pos.x())
        if self.drag_mode == "playhead":
            self.playhead_ms = self._ms_from_x(x)
            self.scrubbed.emit(self.playhead_ms)
        elif self.drag_index is not None:
            for kind, index, rect in self._segment_rects():
                if index != self.drag_index:
                    continue
                if self.drag_mode.startswith("duration") and kind == "block":
                    raw = (x - rect.left()) / self._px_per_ms() if self.drag_mode == "duration_right" else (rect.right() - x) / self._px_per_ms()
                    self.durationEdited.emit(index, int(np.clip(round(raw / 10.0) * 10, 80, 5000)))
                    break
                if self.drag_mode == "transition" and kind == "transition":
                    raw = (x - rect.left()) / self._px_per_ms()
                    self.transitionEdited.emit(index, int(np.clip(round(raw / 5.0) * 5, 0, 250)))
                    break
        self.update()

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802 - Qt override
        del event
        self.drag_mode = None
        self.drag_index = None

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt override
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor("#fff7e6"))
        lane = self._lane_rect()
        painter.setPen(QPen(QColor("#1d3557"), 2))
        painter.setBrush(QColor("#f8f9fa"))
        painter.drawRoundedRect(lane.adjusted(0, -10, 0, 36), 18, 18)
        painter.setFont(QFont("Arial", 10, QFont.Bold))
        painter.drawText(QRectF(lane.left(), 12, lane.width(), 24), Qt.AlignLeft, f"Visual Articulation Timeline • {self.total_ms} ms • zoom {self.zoom:.2f}x")
        if not self.items:
            painter.setPen(QPen(QColor("#457b9d"), 1))
            painter.setFont(QFont("Arial", 13, QFont.Bold))
            painter.drawText(
                lane.adjusted(18, -2, -18, 24),
                Qt.AlignCenter | Qt.TextWordWrap,
                "No articulation chain yet. Add phonemes from Articulation Lab, then return here to arrange them visually.",
            )
            painter.end()
            return
        for mark in range(0, self.total_ms + 1, 250):
            x = lane.left() + mark * self._px_per_ms()
            painter.setPen(QPen(QColor(29, 53, 87, 70), 1))
            painter.drawLine(QPointF(x, lane.top() - 18), QPointF(x, lane.bottom() + 26))
            painter.drawText(QRectF(x + 3, lane.bottom() + 4, 80, 18), Qt.AlignLeft, f"{mark} ms")
        for kind, index, rect in self._segment_rects():
            item = self.items[index]
            phoneme = item.phoneme_for_render().clamped()
            if kind == "transition":
                curve = item.transition_curve if item.transition_curve in ARTICULATION_TRANSITION_CURVES else ARTICULATION_DEFAULT_TRANSITION_CURVE
                painter.setBrush(QColor("#fff8d9"))
                painter.setPen(QPen(QColor("#7b2cbf"), 2, Qt.DashLine))
                painter.drawRoundedRect(rect, 10, 10)
                painter.setPen(QPen(QColor("#7b2cbf"), 2))
                transition = max(0, int(item.transition_to_next_ms if item.transition_to_next_ms is not None else ARTICULATION_DEFAULT_TRANSITION_MS))
                painter.drawText(rect.adjusted(2, 0, -2, 0), Qt.AlignCenter, f"↔ {transition} ms\n{curve.split()[0]}")
                continue
            painter.setBrush(QColor(phoneme.preview_color))
            selected = index == self.selected_index
            painter.setPen(QPen(QColor("#ff4fa3" if selected else "#1d3557"), 5 if selected else 3))
            painter.drawRoundedRect(rect, min(16.0, max(1.0, rect.width() / 2.0)), 16)
            if rect.width() < 18.0:
                painter.setBrush(Qt.NoBrush)
                painter.setPen(QPen(QColor(255, 79, 163, 120), 2, Qt.DashLine))
                painter.drawRoundedRect(rect.adjusted(-8, 6, 8, -6), 8, 8)
            family_icon = {"vowel": "●", "fricative": "≋", "affricate": "≋!", "stop": "■", "nasal": "∩", "glide": "~", "liquid": "ℓ"}.get(phoneme.phoneme_family, "●")
            badge = articulation_source_badge(phoneme.source_mode, phoneme.source_wave_id, phoneme.source_audio_path)
            label = f"{family_icon} {phoneme.name} /{phoneme.ipa}/\n{int(item.duration_ms or phoneme.duration_ms)} ms • {badge}"
            painter.setPen(QPen(QColor("#1d3557"), 1))
            painter.drawText(rect.adjusted(8, 5, -8, -5), Qt.AlignCenter | Qt.TextWordWrap, label)
            painter.setPen(QPen(QColor("#e63946"), 4))
            painter.drawLine(QPointF(rect.right(), rect.top() + 8), QPointF(rect.right(), rect.bottom() - 8))
        x = lane.left() + self.playhead_ms * self._px_per_ms()
        painter.setPen(QPen(QColor("#e63946"), 4, Qt.SolidLine, Qt.RoundCap))
        painter.drawLine(QPointF(x, 34), QPointF(x, lane.bottom() + 42))
        painter.setBrush(QColor("#e63946"))
        painter.drawEllipse(QRectF(x - 7, 27, 14, 14))
        painter.end()


class ArticulationTrackCanvas(QWidget):
    """Mini automation/formant tracks sharing the articulation timeline scale."""

    def __init__(self, mode: str = "envelopes") -> None:
        super().__init__()
        self.mode = mode
        self.segments: List[Dict[str, object]] = []
        self.total_ms = 1
        self.playhead_ms = 0.0
        self.setMinimumHeight(250 if mode == "envelopes" else 160)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def set_timeline(self, segments: List[Dict[str, object]], total_ms: int, playhead_ms: float) -> None:
        self.segments = list(segments)
        self.total_ms = max(1, int(total_ms))
        self.playhead_ms = float(np.clip(playhead_ms, 0.0, self.total_ms))
        self.update()

    def _sample_phoneme(self, elapsed_ms: float) -> ArticulationPhoneme:
        if not self.segments:
            return ArticulationPhoneme.from_json_dict(VOWEL_PRESETS["AH"] | {"name": "AH"})
        active = self.segments[-1]
        for segment in self.segments:
            if float(segment["start"]) <= elapsed_ms <= float(segment["end"]):
                active = segment
                break
        start = float(active["start"])
        end = max(start + 1.0, float(active["end"]))
        local = float(np.clip((elapsed_ms - start) / (end - start), 0.0, 1.0))
        if active["kind"] == "transition":
            return interpolate_articulation_phoneme(active["from"], active["to"], local, str(active.get("curve", ARTICULATION_DEFAULT_TRANSITION_CURVE)))
        return active["from"].clamped()

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt override
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor("#fff7e6"))
        tracks = list(ARTICULATION_ENVELOPE_TRACKS) if self.mode == "envelopes" else ["F1", "F2", "F3", "F4"]
        margin_l, margin_r, top = 84.0, 18.0, 26.0
        track_h = max(22.0, (self.height() - top - 16) / max(1, len(tracks)))
        width = max(1.0, self.width() - margin_l - margin_r)
        title = "Articulator Automation Curves" if self.mode == "envelopes" else "Formant Explorer"
        painter.setPen(QPen(QColor("#1d3557"), 1))
        painter.setFont(QFont("Arial", 10, QFont.Bold))
        painter.drawText(QRectF(10, 4, self.width() - 20, 20), Qt.AlignLeft, title)
        samples = max(12, min(180, int(width / 6)))
        for row, track in enumerate(tracks):
            y = top + row * track_h
            rect = QRectF(margin_l, y + 3, width, track_h - 6)
            painter.setPen(QPen(QColor("#6c757d"), 1))
            painter.setBrush(QColor("#f8f9fa"))
            painter.drawRoundedRect(rect, 7, 7)
            painter.setPen(QPen(QColor("#1d3557"), 1))
            painter.drawText(QRectF(8, y, margin_l - 12, track_h), Qt.AlignVCenter | Qt.AlignRight, track)
            path = QPainterPath()
            live_value = 0.0
            for i in range(samples):
                ms = (i / max(1, samples - 1)) * self.total_ms
                phoneme = self._sample_phoneme(ms)
                if self.mode == "envelopes":
                    value = float(np.clip(getattr(phoneme, track), 0.0, 1.0))
                else:
                    f1, f2, f3 = formants_from_articulation(phoneme)
                    values = {"F1": f1 / 1000.0, "F2": f2 / 2500.0, "F3": f3 / 3500.0, "F4": (f3 + 850.0) / 4500.0}
                    value = float(np.clip(values[track], 0.0, 1.0))
                if abs(ms - self.playhead_ms) <= self.total_ms / max(1, samples):
                    live_value = value
                x = rect.left() + (i / max(1, samples - 1)) * rect.width()
                py = rect.bottom() - value * rect.height()
                if i == 0:
                    path.moveTo(x, py)
                else:
                    path.lineTo(x, py)
            painter.setPen(QPen(QColor("#4361ee" if self.mode == "envelopes" else "#ff7b00"), 2))
            painter.drawPath(path)
            painter.setPen(QPen(QColor("#e63946"), 1))
            painter.drawText(rect.adjusted(6, 0, -6, 0), Qt.AlignRight | Qt.AlignVCenter, f"{live_value:.2f}" if self.mode == "envelopes" else "active")
        x = margin_l + (self.playhead_ms / self.total_ms) * width
        painter.setPen(QPen(QColor("#e63946"), 3))
        painter.drawLine(QPointF(x, top), QPointF(x, self.height() - 10))
        painter.end()


class GraphicalWaveLayerCanvas(QWidget):
    """Compact direct-manipulation editor for one mix layer's level envelope."""

    levelEdited = Signal(str, float, float)
    waveSelected = Signal(str)

    def __init__(self, wave_id: str) -> None:
        super().__init__()
        self.wave_id = wave_id
        self.label = wave_id
        self.shape_name = "sine"
        self.start_db = -20.0
        self.end_db = -20.0
        self.muted = False
        self.soloed = False
        self._drag_handle: str | None = None
        self.setMinimumHeight(120)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setCursor(Qt.CrossCursor)
        self.setToolTip("Drag the left or right loudness handles to update this Mix Wave Shapes layer.")

    def set_state(self, label: str, shape_name: str, start_db: float, end_db: float, muted: bool, soloed: bool) -> None:
        self.label = label
        self.shape_name = shape_name
        self.start_db = float(np.clip(start_db, -20.0, 0.0))
        self.end_db = float(np.clip(end_db, -20.0, 0.0))
        self.muted = bool(muted)
        self.soloed = bool(soloed)
        self.update()

    def _plot_rect(self) -> QRectF:
        return QRectF(self.rect()).adjusted(18, 28, -18, -20)

    def _y_for_db(self, db: float) -> float:
        plot = self._plot_rect()
        return plot.bottom() - ((float(db) + 20.0) / 20.0) * plot.height()

    def _db_for_y(self, y: float) -> float:
        plot = self._plot_rect()
        ratio = 1.0 - ((float(y) - plot.top()) / max(1.0, plot.height()))
        return float(np.clip(-20.0 + ratio * 20.0, -20.0, 0.0))

    def _handle_pos(self, handle: str) -> QPointF:
        plot = self._plot_rect()
        x = plot.left() if handle == "start" else plot.right()
        y = self._y_for_db(self.start_db if handle == "start" else self.end_db)
        return QPointF(x, y)

    def mousePressEvent(self, event) -> None:  # noqa: N802 - Qt override
        pos = event.position() if hasattr(event, "position") else QPointF(event.pos())
        self.waveSelected.emit(self.wave_id)
        start_dist = (pos - self._handle_pos("start")).manhattanLength()
        end_dist = (pos - self._handle_pos("end")).manhattanLength()
        self._drag_handle = "start" if start_dist <= end_dist else "end"
        self._emit_level(pos)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802 - Qt override
        if not self._drag_handle:
            return
        pos = event.position() if hasattr(event, "position") else QPointF(event.pos())
        self._emit_level(pos)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802 - Qt override
        del event
        self._drag_handle = None

    def _emit_level(self, pos: QPointF) -> None:
        db = self._db_for_y(pos.y())
        if self._drag_handle == "start":
            self.levelEdited.emit(self.wave_id, db, self.end_db)
        elif self._drag_handle == "end":
            self.levelEdited.emit(self.wave_id, self.start_db, db)

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt override
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        bg = QColor("#fff8d9") if self.soloed else QColor("#f8f9fa")
        if self.muted:
            bg = QColor("#eceff1")
        painter.fillRect(self.rect(), bg)
        plot = self._plot_rect()
        painter.setPen(QPen(QColor("#90a4ae"), 1, Qt.DashLine))
        for frac in (0.0, 0.5, 1.0):
            y = plot.top() + plot.height() * frac
            painter.drawLine(QPointF(plot.left(), y), QPointF(plot.right(), y))
        painter.setPen(QPen(QColor("#1d3557"), 2))
        painter.drawRoundedRect(plot, 10, 10)
        path = QPainterPath()
        path.moveTo(self._handle_pos("start"))
        path.cubicTo(QPointF(plot.left() + plot.width() * 0.32, self._y_for_db(self.start_db)), QPointF(plot.left() + plot.width() * 0.68, self._y_for_db(self.end_db)), self._handle_pos("end"))
        painter.setPen(QPen(QColor("#5cdb95") if not self.muted else QColor("#78909c"), 4, Qt.SolidLine, Qt.RoundCap))
        painter.drawPath(path)
        for handle, color in (("start", "#ff6b6b"), ("end", "#4ecdc4")):
            pt = self._handle_pos(handle)
            painter.setBrush(QColor(color))
            painter.setPen(QPen(QColor("#1d3557"), 2))
            painter.drawEllipse(pt, 9, 9)
        painter.setFont(QFont("Arial", 10, QFont.Bold))
        painter.setPen(QPen(QColor("#1d3557"), 1))
        state = " • muted" if self.muted else (" • solo" if self.soloed else "")
        painter.drawText(QRectF(12, 4, self.width() - 24, 22), Qt.AlignLeft, f"{self.label} • {self.shape_name} • {self.start_db:.1f}→{self.end_db:.1f} dB{state}")
        painter.end()


class GraphicalStereoFieldCanvas(QWidget):
    panEdited = Signal(float, float)
    widthEdited = Signal(float)

    def __init__(self) -> None:
        super().__init__()
        self.pan_start = 0.0
        self.pan_end = 0.0
        self.width_value = 0.45
        self.auto_depth = 0.0
        self._drag_target: str | None = None
        self.setMinimumSize(QSize(420, 220))
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setCursor(Qt.CrossCursor)

    def set_state(self, pan_start: float, pan_end: float, width_value: float, auto_depth: float) -> None:
        self.pan_start = float(np.clip(pan_start, -1.0, 1.0))
        self.pan_end = float(np.clip(pan_end, -1.0, 1.0))
        self.width_value = float(np.clip(width_value, 0.0, 1.0))
        self.auto_depth = float(np.clip(auto_depth, 0.0, 1.0))
        self.update()

    def _field_rect(self) -> QRectF:
        return QRectF(self.rect()).adjusted(34, 42, -34, -34)

    def _x_for_pan(self, pan: float) -> float:
        field = self._field_rect()
        return field.left() + ((float(pan) + 1.0) / 2.0) * field.width()

    def _pan_for_x(self, x: float) -> float:
        field = self._field_rect()
        return float(np.clip(((x - field.left()) / max(1.0, field.width())) * 2.0 - 1.0, -1.0, 1.0))

    def mousePressEvent(self, event) -> None:  # noqa: N802 - Qt override
        pos = event.position() if hasattr(event, "position") else QPointF(event.pos())
        center_y = self._field_rect().center().y()
        start_pt = QPointF(self._x_for_pan(self.pan_start), center_y + 28)
        end_pt = QPointF(self._x_for_pan(self.pan_end), center_y - 28)
        self._drag_target = "start" if (pos - start_pt).manhattanLength() <= (pos - end_pt).manhattanLength() else "end"
        self._emit_pan(pos.x())

    def mouseMoveEvent(self, event) -> None:  # noqa: N802 - Qt override
        if not self._drag_target:
            return
        pos = event.position() if hasattr(event, "position") else QPointF(event.pos())
        self._emit_pan(pos.x())

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802 - Qt override
        del event
        self._drag_target = None

    def wheelEvent(self, event) -> None:  # noqa: N802 - Qt override
        delta = 0.05 if event.angleDelta().y() > 0 else -0.05
        self.widthEdited.emit(float(np.clip(self.width_value + delta, 0.0, 1.0)))
        event.accept()

    def _emit_pan(self, x: float) -> None:
        pan = self._pan_for_x(x)
        if self._drag_target == "start":
            self.panEdited.emit(pan, self.pan_end)
        elif self._drag_target == "end":
            self.panEdited.emit(self.pan_start, pan)

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt override
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor("#f0fbff"))
        field = self._field_rect()
        painter.setPen(QPen(QColor("#1d3557"), 3))
        painter.setBrush(QColor("#ffffff"))
        painter.drawRoundedRect(field, 22, 22)
        painter.setFont(QFont("Arial", 13, QFont.Bold))
        painter.drawText(QRectF(field.left() - 24, field.top() - 32, 96, 28), Qt.AlignLeft, "👂 Left")
        painter.drawText(QRectF(field.right() - 78, field.top() - 32, 112, 28), Qt.AlignRight, "Right 👂")
        center_y = field.center().y()
        start = QPointF(self._x_for_pan(self.pan_start), center_y + 28)
        end = QPointF(self._x_for_pan(self.pan_end), center_y - 28)
        painter.setPen(QPen(QColor("#7b2cbf"), 4, Qt.DashLine, Qt.RoundCap))
        painter.drawLine(start, end)
        if self.auto_depth > 0.01:
            painter.setPen(QPen(QColor(255, 193, 7, 120), 3, Qt.DotLine, Qt.RoundCap))
            painter.drawEllipse(QRectF(field.center().x() - field.width() * self.auto_depth / 2, field.center().y() - 44, field.width() * self.auto_depth, 88))
        for pt, label, color in ((start, "Start", "#ff6b6b"), (end, "End", "#4ecdc4")):
            painter.setPen(QPen(QColor("#1d3557"), 2))
            painter.setBrush(QColor(color))
            painter.drawEllipse(pt, 13, 13)
            painter.drawText(QRectF(pt.x() - 42, pt.y() + 14, 84, 24), Qt.AlignCenter, label)
        painter.setPen(QPen(QColor("#1d3557"), 2))
        painter.drawText(QRectF(12, 8, self.width() - 24, 26), Qt.AlignCenter, f"Drag dots to place sound • width {self.width_value:.2f} • auto-pan {self.auto_depth:.2f}")
        painter.end()


class GraphicalPitchCurveCanvas(QWidget):
    pitchEdited = Signal(int, int)

    def __init__(self) -> None:
        super().__init__()
        self.start_value = 69 * MIDI_SLIDER_SCALE
        self.end_value = 69 * MIDI_SLIDER_SCALE
        self.vibrato_depth = 0.0
        self._drag_target: str | None = None
        self.setMinimumSize(QSize(420, 220))
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setCursor(Qt.CrossCursor)

    def set_state(self, start_value: int, end_value: int, vibrato_depth: float) -> None:
        self.start_value = int(np.clip(start_value, 36 * MIDI_SLIDER_SCALE, 84 * MIDI_SLIDER_SCALE))
        self.end_value = int(np.clip(end_value, 36 * MIDI_SLIDER_SCALE, 84 * MIDI_SLIDER_SCALE))
        self.vibrato_depth = float(np.clip(vibrato_depth, 0.0, 1.0))
        self.update()

    def _plot_rect(self) -> QRectF:
        return QRectF(self.rect()).adjusted(36, 34, -28, -38)

    def _y_for_value(self, value: int) -> float:
        plot = self._plot_rect()
        ratio = (float(value) - 36 * MIDI_SLIDER_SCALE) / (48 * MIDI_SLIDER_SCALE)
        return plot.bottom() - ratio * plot.height()

    def _value_for_y(self, y: float) -> int:
        plot = self._plot_rect()
        ratio = 1.0 - ((float(y) - plot.top()) / max(1.0, plot.height()))
        return int(np.clip(round((36 + ratio * 48) * MIDI_SLIDER_SCALE), 36 * MIDI_SLIDER_SCALE, 84 * MIDI_SLIDER_SCALE))

    def mousePressEvent(self, event) -> None:  # noqa: N802 - Qt override
        pos = event.position() if hasattr(event, "position") else QPointF(event.pos())
        plot = self._plot_rect()
        start = QPointF(plot.left(), self._y_for_value(self.start_value))
        end = QPointF(plot.right(), self._y_for_value(self.end_value))
        self._drag_target = "start" if (pos - start).manhattanLength() <= (pos - end).manhattanLength() else "end"
        self._emit_pitch(pos.y())

    def mouseMoveEvent(self, event) -> None:  # noqa: N802 - Qt override
        if not self._drag_target:
            return
        pos = event.position() if hasattr(event, "position") else QPointF(event.pos())
        self._emit_pitch(pos.y())

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802 - Qt override
        del event
        self._drag_target = None

    def _emit_pitch(self, y: float) -> None:
        value = self._value_for_y(y)
        if self._drag_target == "start":
            self.pitchEdited.emit(value, self.end_value)
        elif self._drag_target == "end":
            self.pitchEdited.emit(self.start_value, value)

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt override
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor("#fff7e6"))
        plot = self._plot_rect()
        painter.setPen(QPen(QColor("#90a4ae"), 1, Qt.DashLine))
        for midi in range(36, 85, 12):
            y = self._y_for_value(midi * MIDI_SLIDER_SCALE)
            painter.drawLine(QPointF(plot.left(), y), QPointF(plot.right(), y))
            painter.drawText(QRectF(4, y - 10, 30, 20), Qt.AlignRight, f"{midi}")
        painter.setPen(QPen(QColor("#1d3557"), 2))
        painter.drawRoundedRect(plot, 10, 10)
        start = QPointF(plot.left(), self._y_for_value(self.start_value))
        end = QPointF(plot.right(), self._y_for_value(self.end_value))
        path = QPainterPath(start)
        path.cubicTo(QPointF(plot.left() + plot.width() * 0.33, start.y()), QPointF(plot.left() + plot.width() * 0.66, end.y()), end)
        painter.setPen(QPen(QColor("#7b2cbf"), 4, Qt.SolidLine, Qt.RoundCap))
        painter.drawPath(path)
        if self.vibrato_depth > 0.01:
            painter.setPen(QPen(QColor(255, 193, 7, 130), 2, Qt.DotLine))
            last = None
            for i in range(80):
                t = i / 79.0
                x = plot.left() + plot.width() * t
                base_y = start.y() * (1.0 - t) + end.y() * t
                y = base_y + math.sin(t * math.pi * 16.0) * self.vibrato_depth * 18.0
                if last is not None:
                    painter.drawLine(last, QPointF(x, y))
                last = QPointF(x, y)
        for pt, label, color in ((start, "Start", "#ff6b6b"), (end, "End", "#4ecdc4")):
            painter.setBrush(QColor(color))
            painter.setPen(QPen(QColor("#1d3557"), 2))
            painter.drawEllipse(pt, 11, 11)
            painter.drawText(QRectF(pt.x() - 44, pt.y() + 12, 88, 22), Qt.AlignCenter, label)
        painter.setPen(QPen(QColor("#1d3557"), 2))
        painter.drawText(QRectF(10, 6, self.width() - 20, 24), Qt.AlignCenter, "Drag pitch points • octave grid • wiggle shows pitch motion")
        painter.end()


class GraphicalWaveCard(QWidget):
    """Selectable card surface for graphical wave layers."""

    waveSelected = Signal(str)

    def __init__(self, wave_id: str) -> None:
        super().__init__()
        self.wave_id = wave_id

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.waveSelected.emit(self.wave_id)
        super().mousePressEvent(event)


class WaveToyWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle("WaveToy - Visual Sound and Articulation Lab")
        self.setWindowFlags(Qt.Window)
        self.resize(1280, 820)
        self.setMinimumSize(QSize(960, 680))

        self.current_audio = np.zeros((1, 2), dtype=np.float32)
        self.current_settings = SynthSettings()
        self.live_loop_enabled = False
        self.live_loop_is_refreshing = False
        self.live_loop_timer = QTimer(self)
        self.live_loop_timer.timeout.connect(self._live_loop_tick)
        self.render_dirty = False
        self.last_generate_reason = "startup"
        self._generate_timer = QTimer(self)
        self._generate_timer.setSingleShot(True)
        self._generate_timer.timeout.connect(self._run_scheduled_generate)

        self.user_presets_path = Path.home() / ".wave_toy_sound_experiments.json"
        self.user_preset_buttons: List[QPushButton] = []
        self.user_preset_layout: QVBoxLayout | None = None

        self.wave_start_sliders: Dict[str, QSlider] = {}
        self.wave_end_sliders: Dict[str, QSlider] = {}
        self.wave_time_sliders: Dict[str, QSlider] = {}
        self.wave_start_labels: Dict[str, QLabel] = {}
        self.wave_end_labels: Dict[str, QLabel] = {}
        self.wave_time_labels: Dict[str, QLabel] = {}
        self.wave_pan_sliders: Dict[str, QSlider] = {}
        self.wave_width_sliders: Dict[str, QSlider] = {}
        self.wave_dance_sliders: Dict[str, QSlider] = {}
        self.wave_pan_labels: Dict[str, QLabel] = {}
        self.wave_width_labels: Dict[str, QLabel] = {}
        self.wave_dance_labels: Dict[str, QLabel] = {}
        self.wave_mix_previews: Dict[str, MiniWavePreview] = {}
        self.wave_envelope_previews: Dict[str, EnvelopePreview] = {}
        self.wave_stereo_field_previews: Dict[str, StereoFieldPreview] = {}
        self.wave_stereo_previews: Dict[str, Tuple[MiniWavePreview, MiniWavePreview]] = {}
        self.wave_cards: Dict[str, QWidget] = {}
        self.wave_mute_buttons: Dict[str, QCheckBox] = {}
        self.wave_solo_buttons: Dict[str, QCheckBox] = {}
        self.wave_follow_pitch_buttons: Dict[str, QCheckBox] = {}
        self.wave_note_combos: Dict[str, QComboBox] = {}
        self.wave_note_buttons: Dict[str, QPushButton] = {}
        self.wave_octave_spins: Dict[str, QSpinBox] = {}
        self.wave_cents_sliders: Dict[str, QSlider] = {}
        self.wave_pitch_labels: Dict[str, QLabel] = {}
        self.wave_pitch_panels: Dict[str, QWidget] = {}
        self.wave_shape_combos: Dict[str, QComboBox] = {}
        self.wave_row_order: List[str] = list(DEFAULT_WAVE_ORDER)
        self.user_wave_ids: List[str] = []
        self.next_user_wave_index = len(DEFAULT_WAVE_ORDER) + 1
        self.wave_rows_layout: QVBoxLayout | None = None
        self.add_wave_button: QPushButton | None = None
        self.wave_emotion_labels: Dict[str, QLabel] = {}
        self.visual_panel_buttons: Dict[str, QPushButton] = {}
        self.floating_toy_panels: Dict[str, QWidget] = {}
        self.note_wheel_dialogs: Dict[str, QDialog] = {}
        self.tabs: QTabWidget | None = None
        self.wave_explorer_tab: QWidget | None = None
        self.dashboard_canvas: WaveCanvas | None = None
        self.dashboard_workspace_panel: QWidget | None = None
        self.dashboard_workspace_layout: QGridLayout | None = None
        self.dashboard_workspace_title: QLabel | None = None
        self.dashboard_summary_label: QLabel | None = None
        self.active_dashboard_workspace = "shape"
        self.wave_explorer: WaveExplorerWindow | None = None
        self._preview_stop_timer = QTimer(self)
        self._preview_stop_timer.setSingleShot(True)
        self._preview_stop_timer.timeout.connect(lambda: self._set_preview_motion(False))
        self.playback_start_monotonic: float | None = None
        self.playback_duration_seconds = 0.0
        self.playback_audio_sample_count = 0
        self.playback_sample_rate = SAMPLE_RATE
        self.playback_timer = QTimer(self)
        self.playback_timer.timeout.connect(self._playback_timer_tick)

        self.timeline_clips: List[TimelineClip] = []
        self.timeline_lane_names = ["Melody", "Rhythm", "Atmosphere", "Effects"]
        self.timeline_lane_count = len(self.timeline_lane_names)
        self.timeline_next_clip_id = 1
        self.timeline_selected_clip_id: int | None = None
        self.timeline_audio_palette: List[AudioPaletteItem] = []
        self.timeline_next_palette_item_id = 1
        self.timeline_selected_palette_item_id: int | None = None
        self.timeline_palette_list_widget: QWidget | None = None
        self.timeline_palette_count_label: QLabel | None = None
        self.timeline_speech_bin: List[SpeechBinItem] = []
        self.timeline_next_speech_item_id = 1
        self.timeline_selected_speech_item_id: int | None = None
        self.timeline_speech_bin_widget: QWidget | None = None
        self.speech_asset_list_widgets: List[Tuple[QWidget, str]] = []
        self.timeline_speech_count_label: QLabel | None = None
        self.timeline_speech_cache_dir = Path(".wavetoy_speech_cache")
        self.timeline_playhead_seconds = 0.0
        self.timeline_duration_seconds = 0.0
        self.timeline_last_mix = np.zeros((0, 2), dtype=np.float32)
        self.timeline_last_mix_path: Path | None = None
        self.timeline_mix_dirty = True
        self.timeline_playback_started_at: float | None = None
        self.timeline_play_timer = QTimer(self)
        self.timeline_play_timer.timeout.connect(self._timeline_playback_tick)
        self.timeline_fallback_process: subprocess.Popen | None = None
        self.timeline_fallback_temp_path: Path | None = None
        self.timeline_canvas: TimelineCanvas | None = None
        self.timeline_status_label: QLabel | None = None
        self.timeline_inspector_label: QLabel | None = None
        self.timeline_edit_tool = "select"
        self.timeline_snap_enabled = True
        self.timeline_snap_seconds = 0.05
        self.timeline_tool_buttons: Dict[str, QPushButton] = {}
        self.timeline_snap_checkbox: QCheckBox | None = None
        self.timeline_snap_combo: QComboBox | None = None
        self.timeline_preserve_pitch = True
        self.timeline_stretch_quality = "Balanced"
        self.timeline_stretch_quality_combo: QComboBox | None = None

        self.phonemes_dir = Path("phonemes")
        self.current_phoneme = ArticulationPhoneme.from_json_dict(VOWEL_PRESETS["AH"] | {"name": "AH", "voice_pitch": 220.0, "voice_strength": 0.65})
        self.saved_phonemes: List[ArticulationPhoneme] = []
        self.articulation_canvas: VocalTractCanvas | None = None
        self.articulation_name_label: QLabel | None = None
        self.articulation_ipa_label: QLabel | None = None
        self.articulation_summary_label: QLabel | None = None
        self.articulation_formant_label: QLabel | None = None
        self.articulation_mix_debug_label: QLabel | None = None
        self.articulation_wave_status_label: QLabel | None = None
        self.articulation_source_combo: QComboBox | None = None
        self.articulation_source_badge_label: QLabel | None = None
        self.articulation_chain_items: List[ArticulationChainItem] = []
        self.articulation_selected_chain_index: int | None = None
        self.articulation_chain_widget: QWidget | None = None
        self.articulation_timeline_canvas: ArticulationTimelineCanvas | None = None
        self.articulation_timeline_scroll: QScrollArea | None = None
        self.articulation_timeline_zoom = 1.0
        self.articulation_playhead_ms = 0.0
        self.articulation_scrub_label: QLabel | None = None
        self.articulation_boundary_curve_combo: QComboBox | None = None
        self.articulation_voice_profile_combo: QComboBox | None = None
        self.articulation_boundary_curve_canvas: ArticulationTrackCanvas | None = None
        self.articulation_envelope_canvas: ArticulationTrackCanvas | None = None
        self.articulation_formant_canvas: ArticulationTrackCanvas | None = None
        self.articulation_motion_canvas: VocalTractCanvas | None = None
        self.articulation_motion_status_label: QLabel | None = None
        self.articulation_smooth_transitions_checkbox: QCheckBox | None = None
        self.articulation_word_render_mode_combo: QComboBox | None = None
        self.articulation_motion_timer = QTimer(self)
        self.articulation_motion_timer.timeout.connect(self._articulation_motion_tick)
        self.articulation_motion_started_at: float | None = None
        self.articulation_motion_total_ms = 0
        self.articulation_motion_loop = False
        self.articulation_motion_speed = 1.0
        self.word_motion_start_monotonic: float | None = None
        self.word_motion_duration_seconds = 0.0
        self.word_motion_timeline_total_ms = 1
        self.word_motion_play_audio = False
        self.articulation_word_status_label: QLabel | None = None
        self.articulation_chain_path = Path("articulation_chain.json")
        self.articulation_word_render_audio = np.zeros((0, 2), dtype=np.float32)
        self.articulation_last_word_render_path: Path | None = None
        self.articulation_last_word_render_created_at: float | None = None
        self.articulation_word_render_settings: Dict[str, object] = {
            "gap_after_ms": 0,
            "crossfade_ms": ARTICULATION_DEFAULT_WORD_CROSSFADE_MS,
            "minimum_crossfade_ms": ARTICULATION_MIN_WORD_CROSSFADE_MS,
            "allow_word_gaps": False,
            "boundary_smoothing_ms": 8,
            "smooth_mouth_transitions": True,
            "word_render_mode": ARTICULATION_WORD_RENDER_CONTINUOUS,
            "transition_debug_verbose": False,
            "word_fade_in_ms": 5,
            "word_fade_out_ms": 8,
            "voice_profile": "Neutral",
            "pitch_envelopes": [],
            "note_events": [],
        }
        self.articulation_syllable_markers: List[Dict[str, object]] = []
        self.articulation_phrase_markers: List[Dict[str, object]] = []
        self.phoneme_cards_widget: QWidget | None = None
        self.phoneme_drawer_stack: QStackedWidget | None = None
        self.phoneme_drawer_buttons: Dict[str, QPushButton] = {}
        self.active_phoneme_drawer = "vowels"
        self.articulation_sliders: Dict[str, QSlider] = {}
        self.articulation_value_labels: Dict[str, QLabel] = {}
        self.articulation_voiced_checkbox: QCheckBox | None = None
        self.phoneme_preview_audio = np.zeros((0, 2), dtype=np.float32)
        self.phoneme_loop_enabled = False
        self.phoneme_loop_timer = QTimer(self)
        self.phoneme_loop_timer.timeout.connect(self._articulation_loop_tick)

        self.graphical_wave_canvases: Dict[str, GraphicalWaveLayerCanvas] = {}
        self.graphical_wave_layer_list: QWidget | None = None
        self.graphical_wave_cards: Dict[str, GraphicalWaveCard] = {}
        self.graphical_selected_wave_id: str | None = None
        self.graphical_stereo_canvas: GraphicalStereoFieldCanvas | None = None
        self.graphical_pitch_canvas: GraphicalPitchCurveCanvas | None = None
        self.graphical_vocal_canvas: VocalTractCanvas | None = None
        self.graphical_chain_canvas: ArticulationTimelineCanvas | None = None
        self.graphical_chain_mouth_canvas: VocalTractCanvas | None = None
        self.graphical_status_label: QLabel | None = None

        self._build_actions()
        self._build_ui()
        self._build_shortcuts()
        self._apply_style()
        self._sync_note_to_pitch()
        self._generate_now(reason="startup", update_message=True, force=True)

    def _build_actions(self) -> None:
        about = QAction("About WaveToy", self)
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

    def _build_toy_title_banner(self) -> QWidget:
        """Create the compact in-app WaveToy title banner while leaving native chrome alone."""
        banner = QWidget()
        banner.setObjectName("toyTitleBanner")
        banner.setMinimumHeight(66)
        banner.setMaximumHeight(78)
        layout = QHBoxLayout(banner)
        layout.setContentsMargins(16, 6, 16, 6)
        layout.setSpacing(12)

        left_icons = QLabel("Audio")
        left_icons.setObjectName("toyTitleIconRail")
        left_icons.setAlignment(Qt.AlignCenter)
        left_icons.setMinimumWidth(96)

        text_stack = QVBoxLayout()
        text_stack.setSpacing(0)
        title = QLabel("WaveToy")
        title.setObjectName("toyTitleText")
        title.setAlignment(Qt.AlignCenter)
        subtitle = QLabel("Visual Sound and Articulation Lab")
        subtitle.setObjectName("toyTitleSubtitle")
        subtitle.setAlignment(Qt.AlignCenter)
        text_stack.addWidget(title)
        text_stack.addWidget(subtitle)

        right_icons = QLabel("Speech")
        right_icons.setObjectName("toyTitleIconRail")
        right_icons.setAlignment(Qt.AlignCenter)
        right_icons.setMinimumWidth(96)

        layout.addWidget(left_icons)
        layout.addLayout(text_stack, 1)
        layout.addWidget(right_icons)
        return banner

    def _build_ui(self) -> None:
        app_shell = QWidget()
        app_shell.setObjectName("appShell")
        app_layout = QVBoxLayout(app_shell)
        app_layout.setContentsMargins(12, 8, 12, 12)
        app_layout.setSpacing(2)
        app_layout.addWidget(self._build_toy_title_banner())

        self.tabs = QTabWidget()
        self.tabs.setObjectName("mainTabs")
        app_layout.addWidget(self.tabs, 1)
        self.setCentralWidget(app_shell)

        scroll = WaveToyScrollArea(scroll_speed=1.05)
        self.tabs.addTab(scroll, "Classic Controls")

        root = QWidget()
        root.setMinimumSize(QSize(1060, 720))
        scroll.setWidget(root)

        outer = QVBoxLayout(root)
        outer.setContentsMargins(WaveToySizing.PAGE_MARGIN, 16, WaveToySizing.PAGE_MARGIN, 16)
        outer.setSpacing(WaveToySizing.SECTION_SPACING)

        title = QLabel("WaveToy Synthesis")
        title.setObjectName("title")

        subtitle = QLabel("Design layered waveforms, stereo placement, pitch motion, and texture. Space = play; Shift+Space = live loop.")
        subtitle.setObjectName("subtitle")

        outer.addWidget(title)
        outer.addWidget(subtitle)

        body = QHBoxLayout()
        body.setSpacing(16)
        outer.addLayout(body, 1)

        left = QVBoxLayout()
        right = QVBoxLayout()
        left.setSpacing(10)
        right.setSpacing(10)

        body.addLayout(left, 7)
        body.addLayout(right, 3)

        wave_box = self._toy_group("1. Mix Wave Shapes and Stereo Placement")
        wave_box.setMinimumWidth(620)
        wave_layout = QVBoxLayout(wave_box)
        wave_layout.setContentsMargins(12, 18, 12, 12)
        wave_layout.setSpacing(8)

        def make_slider_cell(label: QLabel, slider: QSlider, caption: str) -> QWidget:
            cell = QWidget()
            cell.setObjectName("sliderCell")
            layout = QVBoxLayout(cell)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(1)
            title = QLabel(caption)
            title.setObjectName("controlCaption")
            title.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            label.setObjectName("controlValue")
            label.setMinimumWidth(72)
            label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            slider.setMinimumWidth(86)
            layout.addWidget(title)
            layout.addWidget(label)
            layout.addWidget(slider)
            return cell

        def make_pitch_cell(
            wave_type: str,
            label: QLabel,
            follow: QCheckBox,
            note_combo: QComboBox,
            note_button: QPushButton,
            octave_spin: QSpinBox,
            cents_slider: QSlider,
        ) -> QWidget:
            cell = QWidget()
            cell.setObjectName("sliderCell")
            layout = QVBoxLayout(cell)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(2)
            title = QLabel("Pitch Toy")
            title.setObjectName("controlCaption")
            label.setObjectName("controlValue")
            label.setMinimumWidth(92)
            label.setToolTip("👯 Main means this wave follows the big pitch controls. 🎯 means this wave has its own note.")

            follow.setMinimumWidth(112)
            layout.addWidget(title)
            layout.addWidget(label)
            layout.addWidget(follow)

            note_panel = QWidget()
            note_panel.setObjectName("pitchNotePanel")
            note_panel_layout = QGridLayout(note_panel)
            note_panel_layout.setContentsMargins(6, 4, 6, 4)
            note_panel_layout.setHorizontalSpacing(4)
            note_panel_layout.setVerticalSpacing(1)

            note_label = QLabel("🎵 Note")
            size_label = QLabel("🧸 Size")
            wiggle_label = QLabel("🎯 Wiggle")
            for tiny_label in (note_label, size_label, wiggle_label):
                tiny_label.setObjectName("tinyPitchLabel")

            note_combo.setVisible(False)
            note_button.setMinimumWidth(76)
            note_button.setToolTip("Energetic")
            octave_spin.setMaximumWidth(48)
            cents_slider.setMinimumWidth(94)
            note_panel_layout.addWidget(note_label, 0, 0)
            note_panel_layout.addWidget(size_label, 0, 1)
            note_panel_layout.addWidget(note_combo, 1, 0)
            note_panel_layout.addWidget(note_button, 1, 0)
            note_panel_layout.addWidget(octave_spin, 1, 1)
            emotion_label = QLabel("Mood: 🔥 Energetic • 🏠 Home")
            emotion_label.setObjectName("tinyPitchLabel")
            emotion_label.setWordWrap(True)
            note_panel_layout.addWidget(wiggle_label, 2, 0, 1, 2)
            note_panel_layout.addWidget(cents_slider, 3, 0, 1, 2)
            note_panel_layout.addWidget(emotion_label, 4, 0, 1, 2)
            self.wave_emotion_labels[wave_type] = emotion_label
            layout.addWidget(note_panel)
            self.wave_pitch_panels[wave_type] = note_panel
            return cell

        def make_stage(title_text: str, visual: QWidget, controls: List[QWidget] | None = None) -> QWidget:
            stage = QWidget()
            stage.setObjectName("signalStage")
            stage_layout = QVBoxLayout(stage)
            stage_layout.setContentsMargins(0, 0, 0, 0)
            stage_layout.setSpacing(3)
            title_label = QLabel(title_text)
            title_label.setObjectName("signalStageTitle")
            title_label.setAlignment(Qt.AlignCenter)
            stage_layout.addWidget(title_label)
            stage_layout.addWidget(visual, 0, Qt.AlignCenter)
            if controls:
                controls_row = QHBoxLayout()
                controls_row.setContentsMargins(0, 0, 0, 0)
                controls_row.setSpacing(4)
                for control in controls:
                    controls_row.addWidget(control)
                stage_layout.addLayout(controls_row)
            return stage

        def make_flow_arrow() -> QLabel:
            arrow = QLabel("➜")
            arrow.setObjectName("signalFlowArrow")
            arrow.setAlignment(Qt.AlignCenter)
            return arrow

        default_start = {
            "sine": 0,
            "triangle": -20,
            "sawtooth": -20,
            "square": -20,
        }
        default_end = dict(default_start)
        default_wave_pan = {
            "sine": -45,
            "triangle": 45,
            "sawtooth": -85,
            "square": 85,
        }

        self.wave_rows_layout = wave_layout

        for wave_type in WAVE_ORDER:
            card = QWidget()
            card.setObjectName("waveCard")
            self.wave_cards[wave_type] = card
            card_layout = QGridLayout(card)
            card_layout.setContentsMargins(10, 8, 10, 8)
            card_layout.setHorizontalSpacing(6)
            card_layout.setVerticalSpacing(4)
            for column, stretch in enumerate([0, 0, 2, 0, 2, 0, 0]):
                card_layout.setColumnStretch(column, stretch)

            name = QLabel(f"{WAVE_LABELS[wave_type]}")
            name.setObjectName("waveCardTitle")
            name.setWordWrap(True)
            name.setAlignment(Qt.AlignCenter)

            mute_button = QCheckBox("🎵 On")
            mute_button.setToolTip("Turn this wave off without changing its sliders.")
            mute_button.stateChanged.connect(lambda state, wt=wave_type: self._set_wave_muted(wt, bool(state)))
            solo_button = QCheckBox("⭐ Only Me")
            solo_button.setToolTip("Hear just this wave.")
            solo_button.stateChanged.connect(lambda state, wt=wave_type: self._set_wave_solo(wt, bool(state)))
            self.wave_mute_buttons[wave_type] = mute_button
            self.wave_solo_buttons[wave_type] = solo_button

            pitch_label = QLabel("👯 Follow Main")
            follow_pitch = QCheckBox("👯 Follow Main")
            follow_pitch.setChecked(True)
            follow_pitch.setToolTip("Click to switch between 👯 Follow Main and 🎯 My Note for this wave.")
            note_combo = NoWheelComboBox()
            note_combo.addItems(NOTE_NAMES)
            note_combo.setCurrentText("A")
            note_combo.setToolTip("🎯 My Note for this wave when Follow Main is off.")
            note_button = QPushButton(f"🎡 {emotional_note_text('A')}")
            octave_spin = NoWheelSpinBox()
            octave_spin.setRange(0, 8)
            octave_spin.setValue(4)
            octave_spin.setToolTip("🧸 Size: octave for this wave's own note.")
            cents_slider = NoWheelSlider(Qt.Horizontal)
            cents_slider.setRange(-50 * 100, 50 * 100)
            cents_slider.setValue(0)
            cents_slider.setToolTip("🎯 Wiggle: fine-tune this wave in cents when My Note is on.")
            follow_pitch.stateChanged.connect(lambda state, wt=wave_type: self._update_wave_pitch_label(wt))
            note_combo.currentTextChanged.connect(lambda value, wt=wave_type: self._update_wave_pitch_label(wt))
            note_button.clicked.connect(lambda checked=False, wt=wave_type: self._open_note_wheel(wt))
            octave_spin.valueChanged.connect(lambda value, wt=wave_type: self._update_wave_pitch_label(wt))
            cents_slider.valueChanged.connect(lambda value, wt=wave_type: self._update_wave_pitch_label(wt))
            self._connect_scheduled_generate(follow_pitch.stateChanged, "wave_follow_pitch")
            self._connect_scheduled_generate(note_combo.currentIndexChanged, "wave_note")
            self._connect_scheduled_generate(octave_spin.valueChanged, "wave_octave")
            self._connect_scheduled_generate(cents_slider.valueChanged, "wave_cents")

            self.wave_follow_pitch_buttons[wave_type] = follow_pitch
            self.wave_note_combos[wave_type] = note_combo
            self.wave_note_buttons[wave_type] = note_button
            self.wave_octave_spins[wave_type] = octave_spin
            self.wave_cents_sliders[wave_type] = cents_slider
            self.wave_pitch_labels[wave_type] = pitch_label

            start_label = QLabel(self._slider_picture_text(default_start[wave_type] * DB_SLIDER_SCALE, "loudness"))
            start_slider = NoWheelSlider(Qt.Horizontal)
            start_slider.setRange(-20 * DB_SLIDER_SCALE, 0)
            start_slider.setValue(default_start[wave_type] * DB_SLIDER_SCALE)
            start_slider.setTickInterval(2 * DB_SLIDER_SCALE)
            start_slider.setToolTip("Starting size of this wave.")
            self._connect_scheduled_generate(start_slider.valueChanged, "wave_start_slider")
            start_slider.valueChanged.connect(lambda value, wt=wave_type: self._update_wave_envelope_labels(wt))

            end_label = QLabel(self._slider_picture_text(default_end[wave_type] * DB_SLIDER_SCALE, "loudness"))
            end_slider = NoWheelSlider(Qt.Horizontal)
            end_slider.setRange(-20 * DB_SLIDER_SCALE, 0)
            end_slider.setValue(default_end[wave_type] * DB_SLIDER_SCALE)
            end_slider.setTickInterval(2 * DB_SLIDER_SCALE)
            end_slider.setToolTip("Ending size of this wave.")
            self._connect_scheduled_generate(end_slider.valueChanged, "wave_end_slider")
            end_slider.valueChanged.connect(lambda value, wt=wave_type: self._update_wave_envelope_labels(wt))

            time_label = QLabel("🐢 Slow")
            time_slider = NoWheelSlider(Qt.Horizontal)
            time_slider.setRange(1, 100 * PERCENT_SLIDER_SCALE)
            time_slider.setValue(100 * PERCENT_SLIDER_SCALE)
            time_slider.setTickInterval(10 * PERCENT_SLIDER_SCALE)
            time_slider.setToolTip("How slowly or quickly this wave changes.")
            self._connect_scheduled_generate(time_slider.valueChanged, "wave_time_slider")
            time_slider.valueChanged.connect(lambda value, wt=wave_type: self._update_wave_envelope_labels(wt))

            pan_label = QLabel(self._pan_picture_text(default_wave_pan[wave_type] * PERCENT_SLIDER_SCALE))
            pan_slider = NoWheelSlider(Qt.Horizontal)
            pan_slider.setRange(-100 * PERCENT_SLIDER_SCALE, 100 * PERCENT_SLIDER_SCALE)
            pan_slider.setValue(default_wave_pan[wave_type] * PERCENT_SLIDER_SCALE)
            pan_slider.setToolTip("Where this ingredient sits between the left and right ear.")
            self._connect_scheduled_generate(pan_slider.valueChanged, "wave_pan_slider")
            pan_slider.valueChanged.connect(lambda value, wt=wave_type: self._update_wave_stereo_labels(wt))

            width_label = QLabel("↔️ Medium")
            width_slider = NoWheelSlider(Qt.Horizontal)
            width_slider.setRange(0, 100 * PERCENT_SLIDER_SCALE)
            width_slider.setValue(65 * PERCENT_SLIDER_SCALE)
            width_slider.setToolTip("How wide this ingredient feels in stereo space.")
            self._connect_scheduled_generate(width_slider.valueChanged, "wave_width_slider")
            width_slider.valueChanged.connect(lambda value, wt=wave_type: self._update_wave_stereo_labels(wt))

            dance_label = QLabel("😴 Still")
            dance_slider = NoWheelSlider(Qt.Horizontal)
            dance_slider.setRange(0, 100 * PERCENT_SLIDER_SCALE)
            dance_slider.setValue(0)
            dance_slider.setToolTip("How much this ingredient dances between ears.")
            self._connect_scheduled_generate(dance_slider.valueChanged, "wave_dance_slider")
            dance_slider.valueChanged.connect(lambda value, wt=wave_type: self._update_wave_stereo_labels(wt))

            self.wave_start_sliders[wave_type] = start_slider
            self.wave_end_sliders[wave_type] = end_slider
            self.wave_time_sliders[wave_type] = time_slider
            self.wave_start_labels[wave_type] = start_label
            self.wave_end_labels[wave_type] = end_label
            self.wave_time_labels[wave_type] = time_label
            self.wave_pan_sliders[wave_type] = pan_slider
            self.wave_width_sliders[wave_type] = width_slider
            self.wave_dance_sliders[wave_type] = dance_slider
            self.wave_pan_labels[wave_type] = pan_label
            self.wave_width_labels[wave_type] = width_label
            self.wave_dance_labels[wave_type] = dance_label

            shape_preview = MiniWavePreview(wave_type, size=QSize(112, 54))
            shape_preview.set_amplitude(db_to_gain(default_start[wave_type]))
            self.wave_mix_previews[wave_type] = shape_preview

            envelope_preview = EnvelopePreview(size=QSize(250, 54))
            self.wave_envelope_previews[wave_type] = envelope_preview

            stereo_field_preview = StereoFieldPreview(wave_type, size=QSize(230, 54))
            self.wave_stereo_field_previews[wave_type] = stereo_field_preview

            left_preview = MiniWavePreview(wave_type, channel="left", size=QSize(62, 34))
            right_preview = MiniWavePreview(wave_type, channel="right", size=QSize(62, 34))
            self.wave_stereo_previews[wave_type] = (left_preview, right_preview)
            ear_preview_row = QHBoxLayout()
            ear_preview_row.setContentsMargins(0, 0, 0, 0)
            ear_preview_row.setSpacing(3)
            ear_preview_row.addWidget(left_preview)
            ear_preview_row.addWidget(right_preview)

            output_visual = QWidget()
            output_visual.setObjectName("earPreviewCell")
            output_layout = QVBoxLayout(output_visual)
            output_layout.setContentsMargins(0, 0, 0, 0)
            output_layout.setSpacing(2)
            output_layout.addWidget(QLabel("L / R"), 0, Qt.AlignCenter)
            output_layout.addLayout(ear_preview_row)

            pitch_cell = make_pitch_cell(wave_type, pitch_label, follow_pitch, note_combo, note_button, octave_spin, cents_slider)
            shape_stage = make_stage("Shape", shape_preview, [mute_button, solo_button, pitch_cell])
            shape_stage.layout().insertWidget(1, name)
            envelope_stage = make_stage(
                "Envelope",
                envelope_preview,
                [
                    make_slider_cell(start_label, start_slider, "Start"),
                    make_slider_cell(end_label, end_slider, "End"),
                    make_slider_cell(time_label, time_slider, "Time"),
                ],
            )
            stereo_stage = make_stage(
                "Stereo",
                stereo_field_preview,
                [
                    make_slider_cell(pan_label, pan_slider, "Place"),
                    make_slider_cell(width_label, width_slider, "Spread"),
                    make_slider_cell(dance_label, dance_slider, "Dance"),
                ],
            )
            output_stage = make_stage("Output", output_visual)

            card_layout.addWidget(shape_stage, 0, 0)
            card_layout.addWidget(make_flow_arrow(), 0, 1)
            card_layout.addWidget(envelope_stage, 0, 2)
            card_layout.addWidget(make_flow_arrow(), 0, 3)
            card_layout.addWidget(stereo_stage, 0, 4)
            card_layout.addWidget(make_flow_arrow(), 0, 5)
            card_layout.addWidget(output_stage, 0, 6)
            wave_layout.addWidget(card)

        for wave_type in list(self.wave_row_order):
            self._update_wave_pitch_label(wave_type)

        self.add_wave_button = QPushButton("➕ Add Wave")
        self.add_wave_button.setToolTip(f"Add another wave row. Soft limit: {MAX_WAVE_ROWS} waves.")
        self.add_wave_button.clicked.connect(self._add_user_wave_row)
        wave_layout.addWidget(self.add_wave_button, 0, Qt.AlignRight)

        self.clear_solo_button = QPushButton("🌈 All Waves")
        self.clear_solo_button.setToolTip("Clear solo so the full mix plays again.")
        self.clear_solo_button.clicked.connect(self._clear_solo)
        wave_layout.addWidget(self.clear_solo_button, 0, Qt.AlignRight)

        left.addWidget(wave_box)

        pitch_box = self._toy_group("2. Choose Pitch")
        pitch_box.setMinimumWidth(300)
        pitch_layout = QGridLayout(pitch_box)
        pitch_layout.setHorizontalSpacing(12)
        pitch_layout.setVerticalSpacing(10)
        pitch_layout.setColumnStretch(0, 1)
        pitch_layout.setColumnStretch(1, 2)

        self.note_combo = NoWheelComboBox()
        self.note_combo.addItems(NOTE_NAMES)
        self.note_combo.setCurrentText("A")

        self.octave_slider = NoWheelSlider(Qt.Horizontal)
        self.octave_slider.setRange(2 * OCTAVE_SLIDER_SCALE, 6 * OCTAVE_SLIDER_SCALE)
        self.octave_slider.setValue(4 * OCTAVE_SLIDER_SCALE)
        self.octave_label = QLabel("🧸 Middle")

        self.cents_slider = NoWheelSlider(Qt.Horizontal)
        self.cents_slider.setRange(-50 * 100, 50 * 100)
        self.cents_slider.setValue(0)
        self.cents_label = QLabel("🎯 Center")

        self.base_pitch_label = QLabel("Pitch: 🎵 ready")
        self.base_pitch_label.setObjectName("symbolHint")
        self.note_emotion_label = QLabel("Selected Note: 🔥 A\nMood: Energetic\nRelationship: 🏠 Home")
        self.note_emotion_label.setObjectName("symbolHint")
        self.note_emotion_label.setWordWrap(True)

        self.tuning_method_combo = NoWheelComboBox()
        for method_id, method in TUNING_METHODS.items():
            self.tuning_method_combo.addItem(str(method["label"]), method_id)
            index = self.tuning_method_combo.count() - 1
            self.tuning_method_combo.setItemData(index, str(method["tooltip"]), Qt.ToolTipRole)
        self.tuning_method_combo.setToolTip("Choose how notes are spaced.")

        self.tuning_root_combo = NoWheelComboBox()
        self.tuning_root_combo.addItems(NOTE_NAMES)
        self.tuning_root_combo.setCurrentText("A")
        self.tuning_root_combo.setToolTip("Pick the home note for tunings that lean around a root.")

        self.tuning_reference_spin = NoWheelDoubleSpinBox()
        self.tuning_reference_spin.setRange(220.0, 880.0)
        self.tuning_reference_spin.setDecimals(1)
        self.tuning_reference_spin.setSingleStep(0.5)
        self.tuning_reference_spin.setValue(440.0)
        self.tuning_reference_spin.setSuffix(" Hz")
        self.tuning_reference_spin.setToolTip("Reference pitch for A4. Default is 440 Hz.")

        pitch_layout.addWidget(QLabel("Note"), 0, 0)
        pitch_layout.addWidget(self.note_combo, 0, 1)
        pitch_layout.addWidget(QLabel("Voice Size"), 1, 0)
        pitch_layout.addWidget(self.octave_label, 1, 1)
        pitch_layout.addWidget(self.octave_slider, 2, 0, 1, 2)
        pitch_layout.addWidget(QLabel("Tiny Wiggle"), 3, 0)
        pitch_layout.addWidget(self.cents_label, 3, 1)
        pitch_layout.addWidget(self.cents_slider, 4, 0, 1, 2)
        tuning_title = QLabel("🎼 Tuning Playground")
        tuning_title.setObjectName("symbolHint")
        pitch_layout.addWidget(tuning_title, 5, 0, 1, 2)
        pitch_layout.addWidget(QLabel("🎼 Tuning Map"), 6, 0)
        pitch_layout.addWidget(self.tuning_method_combo, 6, 1)
        pitch_layout.addWidget(QLabel("Home Note"), 7, 0)
        pitch_layout.addWidget(self.tuning_root_combo, 7, 1)
        pitch_layout.addWidget(QLabel("A4 Sparkle"), 8, 0)
        pitch_layout.addWidget(self.tuning_reference_spin, 8, 1)
        pitch_layout.addWidget(self.base_pitch_label, 9, 0, 1, 2)
        pitch_layout.addWidget(self.note_emotion_label, 10, 0, 1, 2)

        left.addWidget(pitch_box)

        explain_box = self._toy_group("What happened?")
        explain_box.setMinimumHeight(110)
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

        left.addWidget(explain_box)

        self.wave_explorer = WaveExplorerWindow(self)
        self.canvas = self.wave_explorer.canvas

        motion_box = self._toy_group("3. Change Over Time")
        motion_box.setMinimumWidth(280)
        motion_layout = QGridLayout(motion_box)
        motion_layout.setHorizontalSpacing(12)
        motion_layout.setVerticalSpacing(10)
        motion_layout.setColumnStretch(0, 1)
        motion_layout.setColumnStretch(1, 2)

        self.duration_slider = NoWheelSlider(Qt.Horizontal)
        self.duration_slider.setRange(int(TIMELINE_MIN_CLIP_SECONDS * SECONDS_SLIDER_SCALE), int(MAX_PREVIEW_SECONDS * SECONDS_SLIDER_SCALE))
        self.duration_slider.setValue(int(1.5 * SECONDS_SLIDER_SCALE))
        self.duration_label = QLabel("⏱️ Short")
        self.duration_slider.valueChanged.connect(self._sync_duration_slider_to_spin)

        self.pitch_start = NoWheelSlider(Qt.Horizontal)
        self.pitch_start.setRange(36 * MIDI_SLIDER_SCALE, 84 * MIDI_SLIDER_SCALE)
        self.pitch_start.setValue(69 * MIDI_SLIDER_SCALE)
        self.pitch_start_label = QLabel("🎵 Middle")

        self.pitch_end = NoWheelSlider(Qt.Horizontal)
        self.pitch_end.setRange(36 * MIDI_SLIDER_SCALE, 84 * MIDI_SLIDER_SCALE)
        self.pitch_end.setValue(69 * MIDI_SLIDER_SCALE)
        self.pitch_end_label = QLabel("🎵 Middle")

        self.loud_start = NoWheelSlider(Qt.Horizontal)
        self.loud_start.setRange(0, 100 * PERCENT_SLIDER_SCALE)
        self.loud_start.setValue(40 * PERCENT_SLIDER_SCALE)
        self.loud_start_label = QLabel("🌿 Medium")

        self.loud_end = NoWheelSlider(Qt.Horizontal)
        self.loud_end.setRange(0, 100 * PERCENT_SLIDER_SCALE)
        self.loud_end.setValue(40 * PERCENT_SLIDER_SCALE)
        self.loud_end_label = QLabel("🌿 Medium")

        self.curve_combo = NoWheelComboBox()
        for key, label in CURVE_LABELS.items():
            self.curve_combo.addItem(label, key)

        motion_layout.addWidget(QLabel("Clip Time"), 0, 0)
        motion_layout.addWidget(self.duration_label, 0, 1)
        motion_layout.addWidget(self.duration_slider, 1, 0, 1, 2)
        motion_layout.addWidget(QLabel("Start Pitch"), 2, 0)
        motion_layout.addWidget(self.pitch_start_label, 2, 1)
        motion_layout.addWidget(self.pitch_start, 3, 0, 1, 2)
        motion_layout.addWidget(QLabel("End Pitch"), 4, 0)
        motion_layout.addWidget(self.pitch_end_label, 4, 1)
        motion_layout.addWidget(self.pitch_end, 5, 0, 1, 2)
        motion_layout.addWidget(QLabel("Start Wiggle"), 6, 0)
        motion_layout.addWidget(self.loud_start_label, 6, 1)
        motion_layout.addWidget(self.loud_start, 7, 0, 1, 2)
        motion_layout.addWidget(QLabel("End Wiggle"), 8, 0)
        motion_layout.addWidget(self.loud_end_label, 8, 1)
        motion_layout.addWidget(self.loud_end, 9, 0, 1, 2)
        motion_layout.addWidget(QLabel("Change Style"), 10, 0)
        motion_layout.addWidget(self.curve_combo, 10, 1)

        right.addWidget(motion_box)

        paul_box = self._toy_group("4. Sound Modules")
        paul_layout = QGridLayout(paul_box)

        self.modules_label = QLabel(
            "Modules are sound powers that can transform the waveform after it is created."
        )
        self.modules_label.setWordWrap(True)

        self.paulstretch_enabled = QCheckBox("😴 Effect Nap")
        self.paulstretch_enabled.setToolTip("Put this effect to sleep without changing its sliders.")

        self.paul_amount_slider = NoWheelSlider(Qt.Horizontal)
        self.paul_amount_slider.setRange(1 * PAULSTRETCH_SCALE, 30 * PAULSTRETCH_SCALE)
        self.paul_amount_slider.setValue(1 * PAULSTRETCH_SCALE)

        self.paul_evolution_slider = NoWheelSlider(Qt.Horizontal)
        self.paul_evolution_slider.setRange(0, 100 * PERCENT_SLIDER_SCALE)
        self.paul_evolution_slider.setValue(15 * PERCENT_SLIDER_SCALE)

        self.paul_amount_label = QLabel("🙂 Normal")
        self.paul_evolution_label = QLabel("🌌 Gentle")

        paul_layout.addWidget(self.modules_label, 0, 0, 1, 2)
        paul_layout.addWidget(self.paulstretch_enabled, 1, 0, 1, 2)

        paul_layout.addWidget(QLabel("Stretch Amount"), 2, 0)
        paul_layout.addWidget(self.paul_amount_label, 2, 1)
        paul_layout.addWidget(self.paul_amount_slider, 3, 0, 1, 2)

        paul_layout.addWidget(QLabel("Sound Evolution"), 4, 0)
        paul_layout.addWidget(self.paul_evolution_label, 4, 1)
        paul_layout.addWidget(self.paul_evolution_slider, 5, 0, 1, 2)

        right.addWidget(paul_box)

        stereo_box = self._toy_group("5. Whole-Mix Stereo Space")
        stereo_box.setMinimumWidth(280)
        stereo_layout = QGridLayout(stereo_box)
        stereo_layout.setHorizontalSpacing(12)
        stereo_layout.setVerticalSpacing(10)
        stereo_layout.setColumnStretch(0, 1)
        stereo_layout.setColumnStretch(1, 2)

        self.pan_start_slider = self._make_percent_slider(-100, 100, 0)
        self.pan_end_slider = self._make_percent_slider(-100, 100, 0)
        self.width_slider = self._make_percent_slider(0, 100, 45)
        self.auto_pan_depth_slider = self._make_percent_slider(0, 100, 0)
        self.auto_pan_rate = NoWheelSlider(Qt.Horizontal)
        self.auto_pan_rate.setRange(int(0.05 * RATE_SLIDER_SCALE), int(8.0 * RATE_SLIDER_SCALE))
        self.auto_pan_rate.setValue(int(0.5 * RATE_SLIDER_SCALE))

        self.pan_start_label = QLabel("⬅️ 🧍 ➡️")
        self.pan_end_label = QLabel("⬅️ 🧍 ➡️")
        self.width_label = QLabel("↔️ Medium")
        self.auto_pan_depth_label = QLabel("😴 Still")
        self.auto_pan_rate_label = QLabel("🐢 Slow")
        global_stereo_hint = QLabel("Per-wave cards place each ingredient. These controls move the entire mix after ingredients combine.")
        global_stereo_hint.setObjectName("symbolHint")
        global_stereo_hint.setWordWrap(True)

        stereo_layout.addWidget(global_stereo_hint, 0, 0, 1, 2)
        stereo_layout.addWidget(QLabel("Start Place"), 1, 0)
        stereo_layout.addWidget(self.pan_start_label, 1, 1)
        stereo_layout.addWidget(self.pan_start_slider, 2, 0, 1, 2)
        stereo_layout.addWidget(QLabel("End Place"), 3, 0)
        stereo_layout.addWidget(self.pan_end_label, 3, 1)
        stereo_layout.addWidget(self.pan_end_slider, 4, 0, 1, 2)
        stereo_layout.addWidget(QLabel("Ear Spread"), 5, 0)
        stereo_layout.addWidget(self.width_label, 5, 1)
        stereo_layout.addWidget(self.width_slider, 6, 0, 1, 2)
        stereo_layout.addWidget(QLabel("Ear Dance"), 7, 0)
        stereo_layout.addWidget(self.auto_pan_depth_label, 7, 1)
        stereo_layout.addWidget(self.auto_pan_depth_slider, 8, 0, 1, 2)
        stereo_layout.addWidget(QLabel("Dance Speed"), 9, 0)
        stereo_layout.addWidget(self.auto_pan_rate_label, 9, 1)
        stereo_layout.addWidget(self.auto_pan_rate, 10, 0, 1, 2)

        right.addWidget(stereo_box)

        preset_box = self._toy_group("Sound Experiments")
        preset_box.setMinimumWidth(280)
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

        self.make_button = ToyButton("Play", "#5cdb95")
        self.stop_button = ToyButton("Stop", "#ff6b6b")
        self.save_button = ToyButton("Save Audio", "#ffd166")
        self.load_button = ToyButton("Load Audio", "#b8f2e6")
        for button, width in (
            (self.make_button, 160),
            (self.stop_button, 110),
            (self.save_button, 170),
            (self.load_button, 160),
        ):
            button.setMinimumWidth(width)
            button.setMinimumHeight(WaveToySizing.BUTTON_HEIGHT)
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
            self.duration_slider,
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
            self.paulstretch_enabled,
            self.paul_amount_slider,
            self.paul_evolution_slider,
            self.tuning_method_combo,
            self.tuning_root_combo,
            self.tuning_reference_spin,
        ]

        self.note_combo.currentTextChanged.connect(self._sync_note_to_pitch)
        self.octave_slider.valueChanged.connect(self._sync_note_to_pitch)
        self.cents_slider.valueChanged.connect(self._sync_note_to_pitch)
        self.tuning_method_combo.currentIndexChanged.connect(self._sync_note_to_pitch)
        self.tuning_root_combo.currentTextChanged.connect(self._sync_note_to_pitch)
        self.tuning_reference_spin.valueChanged.connect(self._sync_note_to_pitch)
        self.paulstretch_enabled.stateChanged.connect(self._update_module_labels)

        for widget in widgets_to_regenerate:
            if isinstance(widget, QComboBox):
                self._connect_scheduled_generate(widget.currentIndexChanged, "combo_change")
            elif isinstance(widget, QSlider):
                self._connect_scheduled_generate(widget.valueChanged, "slider_change")
            elif isinstance(widget, QCheckBox):
                self._connect_scheduled_generate(widget.stateChanged, "checkbox_change")
            elif hasattr(widget, "valueChanged"):
                self._connect_scheduled_generate(widget.valueChanged, "slider_change")

        for widget in [
            self.duration_slider,
            self.pitch_start,
            self.pitch_end,
            self.curve_combo,
            self.pan_start_slider,
            self.pan_end_slider,
            self.width_slider,
            self.auto_pan_depth_slider,
            self.auto_pan_rate,
        ]:
            if isinstance(widget, QComboBox):
                widget.currentIndexChanged.connect(lambda *args: self._update_all_wave_previews())
            else:
                widget.valueChanged.connect(lambda *args: self._update_all_wave_previews())

        self._build_wave_explorer_tab()
        self._build_play_tab()
        self._build_articulation_tab()
        self._build_graphical_editor_tab()
        self._build_timeline_tab()
        self._build_library_tab()
        if self.tabs is not None:
            self.tabs.setCurrentIndex(0)

    def _build_articulation_tab(self) -> None:
        if self.tabs is None:
            return
        self._load_saved_phonemes()
        tab = WaveToyScrollArea(scroll_speed=0.92, content_drag_scroll=False)
        tab.setObjectName("articulationLabTab")
        tab.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        page = QWidget()
        page.setObjectName("articulationLabPage")
        outer = QVBoxLayout(page)
        outer.setContentsMargins(14, 10, 14, 18)
        outer.setSpacing(8)

        lab_header = QWidget()
        lab_header.setObjectName("articulationLabHeader")
        header_layout = QHBoxLayout(lab_header)
        header_layout.setContentsMargins(14, 8, 14, 8)
        header_layout.setSpacing(12)
        title = QLabel("Articulation Lab")
        title.setObjectName("articulationCompactTitle")
        info = QLabel("Speech workstation: shape the vocal tract, render phonemes, and manage created speech assets.")
        info.setObjectName("articulationInfoBadge")
        info.setWordWrap(True)
        header_layout.addWidget(title)
        header_layout.addWidget(info, 1)
        outer.addWidget(lab_header)

        main = QHBoxLayout()
        main.setSpacing(12)
        outer.addLayout(main, 1)

        left = QVBoxLayout()
        left.setSpacing(10)
        main.addLayout(left, 6)

        explorer = self._toy_group("Vocal Explorer")
        explorer.setMinimumHeight(500)
        explorer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        explorer_layout = QVBoxLayout(explorer)
        explorer_layout.setContentsMargins(14, 18, 14, 12)
        explorer_layout.setSpacing(8)

        top = QHBoxLayout()
        top.setSpacing(8)
        self.articulation_name_label = QLabel("😮 AH")
        self.articulation_name_label.setObjectName("articulationPhonemeTitle")
        self.articulation_ipa_label = QLabel("IPA /a/")
        self.articulation_ipa_label.setObjectName("articulationIpaBadge")
        play_button = self._make_story_button("▶", "Play", "#5cdb95", self._play_phoneme_preview)
        loop_button = self._make_story_button("🔁", "Loop", "#b8f2e6", self._toggle_phoneme_loop)
        stop_button = self._make_story_button("⏹", "Stop", "#ff6b6b", self._stop_phoneme_preview)
        for button in (play_button, loop_button, stop_button):
            button.setMinimumSize(QSize(92, 58))
            button.setMaximumHeight(64)
        top.addWidget(self.articulation_name_label, 2)
        top.addWidget(self.articulation_ipa_label, 1)
        top.addWidget(play_button)
        top.addWidget(loop_button)
        top.addWidget(stop_button)
        explorer_layout.addLayout(top)

        source_panel = QWidget()
        source_panel.setObjectName("articulationStatusStrip")
        source_layout = QHBoxLayout(source_panel)
        source_layout.setContentsMargins(10, 8, 10, 8)
        source_layout.setSpacing(8)
        source_title = QLabel("🌊 Source")
        source_title.setObjectName("articulationToyLabel")
        self.articulation_source_combo = QComboBox()
        self.articulation_source_combo.setObjectName("articulationSourceSelector")
        for mode, label in (
            (ARTICULATION_SOURCE_DEFAULT, "Default Voice"),
            (ARTICULATION_SOURCE_CURRENT, "Current WaveToy Sound"),
            (ARTICULATION_SOURCE_MIX_WAVE, "Selected Mix Wave"),
            (ARTICULATION_SOURCE_IMPORTED, "Imported Audio Asset"),
        ):
            self.articulation_source_combo.addItem(label, mode)
        self.articulation_source_combo.currentIndexChanged.connect(lambda _index: self._articulation_source_mode_changed())
        apply_wave_button = self._make_story_button("🌊", "Apply Current Wave", "#b8f2e6", self._apply_current_wave_to_phoneme)
        reset_wave_button = self._make_story_button("♻", "Reset Voice", "#ffd166", self._reset_current_phoneme_source)
        self.articulation_source_badge_label = QLabel("Default Voice")
        self.articulation_source_badge_label.setObjectName("articulationIpaBadge")
        self.articulation_source_badge_label.setAlignment(Qt.AlignCenter)
        for button in (apply_wave_button, reset_wave_button):
            button.setMinimumSize(QSize(120, 58))
            button.setMaximumHeight(64)
        source_layout.addWidget(source_title)
        source_layout.addWidget(self.articulation_source_combo, 1)
        source_layout.addWidget(apply_wave_button)
        source_layout.addWidget(reset_wave_button)
        source_layout.addWidget(self.articulation_source_badge_label)
        explorer_layout.addWidget(source_panel)

        self.articulation_canvas = VocalTractCanvas()
        self.articulation_canvas.setMinimumHeight(360)
        self.articulation_canvas.setMaximumHeight(460)
        explorer_layout.addWidget(self.articulation_canvas)

        status_strip = QWidget()
        status_strip.setObjectName("articulationStatusStrip")
        status_layout = QVBoxLayout(status_strip)
        status_layout.setContentsMargins(8, 6, 8, 6)
        status_layout.setSpacing(6)
        self.articulation_formant_label = QLabel("Formants: F1 850 Hz • F2 1370 Hz • F3 2500 Hz")
        self.articulation_formant_label.setObjectName("articulationFormantStrip")
        self.articulation_formant_label.setWordWrap(True)
        self.articulation_formant_label.setAlignment(Qt.AlignCenter)
        self.articulation_summary_label = QLabel("😮 AH  |  Open Mouth | Low Tongue")
        self.articulation_summary_label.setObjectName("articulationSummaryStrip")
        self.articulation_summary_label.setWordWrap(True)
        self.articulation_summary_label.setAlignment(Qt.AlignCenter)
        self.articulation_mix_debug_label = QLabel("Mix: voiced_gain 0.65 • noise_gain 0.05 • tonal_gain 0.46 • air_pressure 0.45 • voice_strength 0.65 • source_mode default_voice")
        self.articulation_mix_debug_label.setObjectName("articulationDebugStrip")
        self.articulation_mix_debug_label.setWordWrap(True)
        self.articulation_mix_debug_label.setAlignment(Qt.AlignCenter)
        status_layout.addWidget(self.articulation_formant_label)
        status_layout.addWidget(self.articulation_summary_label)
        status_layout.addWidget(self.articulation_mix_debug_label)
        explorer_layout.addWidget(status_strip)
        left.addWidget(explorer, 3)

        controls_card = self._toy_group("Articulation Controls")
        controls_layout = QVBoxLayout(controls_card)
        controls_layout.setContentsMargins(12, 20, 12, 12)
        controls_layout.setSpacing(8)
        controls_hint = QLabel("Move each toy control from the plain-English left meaning to the right meaning.")
        controls_hint.setObjectName("symbolHint")
        controls_hint.setWordWrap(True)
        controls_layout.addWidget(controls_hint)

        controls_body = QWidget()
        controls_body.setObjectName("articulationControlsBody")
        controls_body_layout = QVBoxLayout(controls_body)
        controls_body_layout.setContentsMargins(2, 2, 2, 2)
        controls_body_layout.setSpacing(8)
        for key, label, low_label, high_label, minimum, maximum, value in (
            ("mouth_open", "👄 Mouth Open", "closed", "open", 0, 100, 95),
            ("tongue_height", "👅 Tongue Height", "low", "high", 0, 100, 20),
            ("tongue_frontness", "👅 Tongue Front", "back", "front", 0, 100, 40),
            ("lip_rounding", "💋 Lip Round", "flat", "round", 0, 100, 0),
            ("voice_pitch", "🎤 Voice Pitch", "low", "high", 60, 880, 220),
            ("voice_strength", "🔊 Voice Strength", "soft", "strong", 0, 100, 65),
            ("air_pressure", "🌬 Air Pressure", "gentle", "strong", 0, 100, 45),
            ("teeth_gap", "🦷 Teeth Gap", "tight", "wide", 0, 100, 50),
            ("closure", "🔒 Closure", "open", "closed", 0, 100, 0),
            ("burst_strength", "💥 Burst", "soft", "sharp", 0, 100, 0),
            ("nasal_open", "👃 Nose Open", "closed", "open", 0, 100, 0),
        ):
            controls_body_layout.addWidget(self._make_articulation_toy_control(key, label, low_label, high_label, minimum, maximum, value))

        voice_card = QWidget()
        voice_card.setObjectName("articulationToyControl")
        voice_card.setMinimumHeight(54)
        voice_layout = QHBoxLayout(voice_card)
        voice_layout.setContentsMargins(12, 6, 12, 6)
        voice_layout.setSpacing(12)
        voice_title = QLabel("🎤 Voice On")
        voice_title.setObjectName("articulationToyLabel")
        voice_detail = QLabel("Toggle vocal-cord buzz for vowels and voiced consonants.")
        voice_detail.setObjectName("articulationToyEndpoint")
        voice_detail.setWordWrap(True)
        self.articulation_voiced_checkbox = QCheckBox("Buzzing")
        self.articulation_voiced_checkbox.setObjectName("articulationVoiceToggle")
        self.articulation_voiced_checkbox.setChecked(True)
        self.articulation_voiced_checkbox.toggled.connect(lambda _checked: self._articulation_slider_changed("voiced"))
        voice_layout.addWidget(voice_title)
        voice_layout.addWidget(voice_detail, 1)
        voice_layout.addWidget(self.articulation_voiced_checkbox)
        controls_body_layout.addWidget(voice_card)
        controls_body_layout.addStretch(1)
        controls_layout.addWidget(controls_body)
        left.addWidget(controls_card)

        chain_card = self._toy_group("Articulation Timeline")
        chain_layout = QVBoxLayout(chain_card)
        chain_layout.setContentsMargins(12, 18, 12, 12)
        chain_layout.setSpacing(8)
        chain_hint = QLabel("Build AH → M → OO → N style chains. Each card can use Default Voice or inherit a WaveToy source.")
        chain_hint.setObjectName("symbolHint")
        chain_hint.setWordWrap(True)
        chain_layout.addWidget(chain_hint)
        primary_label = QLabel("Workflow: Add Current → Create Word → Speech Assets → Add to Timeline")
        primary_label.setObjectName("symbolHint")
        primary_label.setWordWrap(True)
        chain_layout.addWidget(primary_label)

        chain_sections = (
            (
                "Chain Editing",
                (("➕", "Add Current", "#5cdb95", self._add_current_phoneme_to_chain, 76), ("🔡", "Create Syllable", "#caffbf", self._create_articulation_syllable, 58), ("🧹", "Clear Chain", "#ffadad", self._clear_articulation_chain, 58)),
            ),
            (
                "Render Speech",
                (("🧩", "Create Word", "#ffd166", self._create_articulation_word, 76), ("▶", "Play Word", "#b8f2e6", self._play_articulation_word, 58), ("▶", "Play Chain", "#caffbf", self._play_articulation_chain, 58), ("💾", "Export Word", "#fdffb6", self._export_articulation_word, 58)),
            ),
            (
                "Send to Timeline",
                (("➕", "Send Word to Timeline", "#ffc6ff", self._send_articulation_word_to_timeline, 76), ("➕", "Send Phoneme", "#e7c6ff", self._send_current_phoneme_to_timeline, 54), ("➕", "Send Chain", "#e7c6ff", self._send_articulation_chain_to_timeline, 54)),
            ),
            (
                "Save/Load",
                (("💾", "Save Chain", "#ffd166", self._save_articulation_chain, 54), ("📂", "Load Chain", "#d7b9ff", self._load_articulation_chain, 54)),
            ),
            (
                "Wave Source",
                (("🌊", "Apply Wave to Selected", "#b8f2e6", self._apply_current_wave_to_selected_chain_item, 54), ("🌊", "Apply Wave to Whole Chain", "#caffbf", self._apply_current_wave_to_whole_chain, 54), ("♻", "Reset Selected", "#ffd166", self._reset_selected_chain_item_source, 54), ("♻", "Reset Whole Chain", "#ffadad", self._reset_whole_chain_source, 54)),
            ),
        )
        for section_title, actions in chain_sections:
            label = QLabel(section_title)
            label.setObjectName("timelineInspectorText")
            chain_layout.addWidget(label)
            row = QHBoxLayout()
            row.setSpacing(8)
            for icon, button_label, color, callback, height in actions:
                button = self._make_story_button(icon, button_label, color, callback)
                button.setMinimumHeight(height)
                row.addWidget(button)
            chain_layout.addLayout(row)
        self.articulation_word_status_label = QLabel("Create Word saves a named asset to Speech Assets without changing the editable chain.")
        self.articulation_word_status_label.setObjectName("symbolHint")
        self.articulation_word_status_label.setWordWrap(True)
        chain_layout.addWidget(self.articulation_word_status_label)

        self.articulation_smooth_transitions_checkbox = QCheckBox("Smooth Mouth Transitions")
        self.articulation_smooth_transitions_checkbox.setChecked(bool(self.articulation_word_render_settings.get("smooth_mouth_transitions", True)))
        self.articulation_smooth_transitions_checkbox.setToolTip("Create Word uses smoothstep slider motion between phoneme shapes when enabled.")
        self.articulation_smooth_transitions_checkbox.toggled.connect(self._toggle_articulation_smooth_transitions)
        chain_layout.addWidget(self.articulation_smooth_transitions_checkbox)

        mode_row = QHBoxLayout()
        mode_row.setSpacing(8)
        mode_label = QLabel("Word Render Mode")
        mode_label.setObjectName("timelineInspectorText")
        self.articulation_word_render_mode_combo = QComboBox()
        self.articulation_word_render_mode_combo.addItems(list(ARTICULATION_WORD_RENDER_MODES))
        current_mode = str(self.articulation_word_render_settings.get("word_render_mode", ARTICULATION_WORD_RENDER_CONTINUOUS))
        if current_mode not in ARTICULATION_WORD_RENDER_MODES:
            current_mode = ARTICULATION_WORD_RENDER_CONTINUOUS
        self.articulation_word_render_mode_combo.setCurrentText(current_mode)
        self.articulation_word_render_mode_combo.setToolTip("Compare the Task 032 clip-overlap fallback with the prototype continuous articulator-envelope renderer.")
        self.articulation_word_render_mode_combo.currentTextChanged.connect(self._set_articulation_word_render_mode)
        mode_row.addWidget(mode_label)
        mode_row.addWidget(self.articulation_word_render_mode_combo, 1)
        chain_layout.addLayout(mode_row)

        profile_row = QHBoxLayout()
        profile_label = QLabel("Voice Profile")
        profile_label.setObjectName("timelineInspectorText")
        self.articulation_voice_profile_combo = QComboBox()
        self.articulation_voice_profile_combo.addItems(["Neutral", "Child", "Female", "Male", "Robot", "Monster", "Whisper"])
        self.articulation_voice_profile_combo.setToolTip("Non-destructively nudge pitch, formants, voicing, and noise style for every chain phoneme; edit sliders afterward.")
        self.articulation_voice_profile_combo.currentTextChanged.connect(self._apply_voice_profile_to_chain)
        profile_row.addWidget(profile_label)
        profile_row.addWidget(self.articulation_voice_profile_combo, 1)
        chain_layout.addLayout(profile_row)

        timeline_header = QHBoxLayout()
        timeline_title = QLabel("🎞 Visual Speech Timeline")
        timeline_title.setObjectName("timelineInspectorText")
        timeline_header.addWidget(timeline_title)
        for text, callback in (("− Zoom", lambda checked=False: self._zoom_articulation_timeline(-0.25)), ("+ Zoom", lambda checked=False: self._zoom_articulation_timeline(0.25))):
            button = QPushButton(text)
            button.setObjectName("phonemeCardSecondaryAction")
            button.setCursor(Qt.PointingHandCursor)
            button.clicked.connect(callback)
            timeline_header.addWidget(button)
        chain_layout.addLayout(timeline_header)

        self.articulation_timeline_canvas = ArticulationTimelineCanvas()
        self.articulation_timeline_canvas.blockSelected.connect(self._select_articulation_chain_item)
        self.articulation_timeline_canvas.durationEdited.connect(self._set_chain_item_duration_ms)
        self.articulation_timeline_canvas.transitionEdited.connect(self._set_chain_transition_to_next_ms)
        self.articulation_timeline_canvas.scrubbed.connect(self._scrub_articulation_playhead)
        self.articulation_timeline_scroll = QScrollArea()
        self.articulation_timeline_scroll.setWidgetResizable(False)
        self.articulation_timeline_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.articulation_timeline_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.articulation_timeline_scroll.setMinimumHeight(220)
        self.articulation_timeline_scroll.setWidget(self.articulation_timeline_canvas)
        chain_layout.addWidget(self.articulation_timeline_scroll)

        self.articulation_scrub_label = QLabel("Playhead idle • drag the red marker to inspect phoneme, transition progress, articulator values, and formants.")
        self.articulation_scrub_label.setObjectName("symbolHint")
        self.articulation_scrub_label.setWordWrap(True)
        chain_layout.addWidget(self.articulation_scrub_label)

        boundary_row = QHBoxLayout()
        boundary_label = QLabel("Boundary Curve")
        boundary_label.setObjectName("timelineInspectorText")
        self.articulation_boundary_curve_combo = QComboBox()
        self.articulation_boundary_curve_combo.addItems(list(ARTICULATION_TRANSITION_CURVES))
        self.articulation_boundary_curve_combo.currentTextChanged.connect(self._set_selected_boundary_curve)
        boundary_row.addWidget(boundary_label)
        boundary_row.addWidget(self.articulation_boundary_curve_combo, 1)
        chain_layout.addLayout(boundary_row)

        self.articulation_envelope_canvas = ArticulationTrackCanvas("envelopes")
        chain_layout.addWidget(self.articulation_envelope_canvas)
        self.articulation_formant_canvas = ArticulationTrackCanvas("formants")
        chain_layout.addWidget(self.articulation_formant_canvas)

        self.articulation_chain_widget = QWidget()
        chain_layout.addWidget(self.articulation_chain_widget)

        motion_card = self._toy_group("Word Motion Preview")
        motion_layout = QVBoxLayout(motion_card)
        motion_layout.setContentsMargins(12, 18, 12, 12)
        motion_layout.setSpacing(8)
        motion_hint = QLabel("Watch the chain playhead move mouth, tongue, lips, nose, closure, airflow, and voicing indicators through each phoneme.")
        motion_hint.setObjectName("symbolHint")
        motion_hint.setWordWrap(True)
        motion_layout.addWidget(motion_hint)
        motion_buttons = QHBoxLayout()
        motion_buttons.setSpacing(8)
        for icon, label, color, callback in (
            ("▶", "Play Word Motion", "#b8f2e6", self._play_articulation_motion),
            ("🔁", "Loop Motion", "#caffbf", self._loop_articulation_motion),
            ("⏹", "Stop Motion", "#ffadad", self._stop_articulation_motion),
            ("🐢", "Slow Motion Visual Only", "#ffd6a5", self._slow_articulation_motion),
        ):
            button = self._make_story_button(icon, label, color, callback)
            button.setMinimumHeight(54)
            motion_buttons.addWidget(button)
        motion_layout.addLayout(motion_buttons)
        self.articulation_motion_status_label = QLabel("Motion idle • add chain phonemes, then use Play Word Motion or Play Word.")
        self.articulation_motion_status_label.setObjectName("symbolHint")
        self.articulation_motion_status_label.setWordWrap(True)
        motion_layout.addWidget(self.articulation_motion_status_label)
        self.articulation_motion_canvas = VocalTractCanvas()
        self.articulation_motion_canvas.setMinimumSize(QSize(620, 430))
        self.articulation_motion_canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        motion_layout.addWidget(self.articulation_motion_canvas)
        chain_layout.addWidget(motion_card)
        left.addWidget(chain_card)
        self._refresh_articulation_chain_cards()

        drawer_shell = QWidget()
        drawer_shell.setObjectName("phonemeDrawerShell")
        drawer_shell.setMinimumWidth(300)
        drawer_shell.setMaximumWidth(390)
        drawer_shell.resize(340, drawer_shell.height())
        drawer_layout = QHBoxLayout(drawer_shell)
        drawer_layout.setContentsMargins(0, 0, 0, 0)
        drawer_layout.setSpacing(8)

        rail = QWidget()
        rail.setObjectName("phonemeIconRail")
        rail.setFixedWidth(64)
        rail_layout = QVBoxLayout(rail)
        rail_layout.setContentsMargins(6, 8, 6, 8)
        rail_layout.setSpacing(4)
        self.phoneme_drawer_buttons = {}
        self.phoneme_drawer_stack = QStackedWidget()
        self.phoneme_drawer_stack.setObjectName("phonemeDrawerStack")

        drawer_specs = [
            ("vowels", "😀", "Vowels", VOWEL_PRESETS, lambda name, _data: self._select_vowel_preset(name)),
            ("fricatives", "🌬", "Fricatives", dict(CONSONANT_PRESET_SECTIONS[0][1]), lambda name, data: self._select_consonant_preset(name, data)),
            ("stops", "💥", "Stops", dict(CONSONANT_PRESET_SECTIONS[1][1]), lambda name, data: self._select_consonant_preset(name, data)),
            ("nasals", "👃", "Nasals", dict(CONSONANT_PRESET_SECTIONS[2][1]), lambda name, data: self._select_consonant_preset(name, data)),
            ("glides", "〰️", "Glides", dict(CONSONANT_PRESET_SECTIONS[3][1]), lambda name, data: self._select_consonant_preset(name, data)),
            ("liquids", "👅", "Liquids", dict(CONSONANT_PRESET_SECTIONS[4][1]), lambda name, data: self._select_consonant_preset(name, data)),
            ("affricates", "💥", "Affricates", dict(CONSONANT_PRESET_SECTIONS[5][1]), lambda name, data: self._select_consonant_preset(name, data)),
            ("extra_fricatives", "🦷", "Extra Fricatives", dict(CONSONANT_PRESET_SECTIONS[6][1]), lambda name, data: self._select_consonant_preset(name, data)),
            ("saved", "💾", "Saved Phonemes", {}, None),
        ]
        for index, (key, icon, title_text, presets, callback) in enumerate(drawer_specs):
            button = QPushButton(icon)
            button.setObjectName("phonemeRailButton")
            button.setCheckable(True)
            button.setToolTip(title_text)
            button.setAccessibleName(title_text)
            button.setMinimumSize(QSize(52, 44))
            button.setMaximumHeight(48)
            button.setCursor(Qt.PointingHandCursor)
            button.clicked.connect(lambda checked=False, drawer_key=key: self._set_phoneme_drawer(drawer_key))
            self.phoneme_drawer_buttons[key] = button
            rail_layout.addWidget(button)
            self.phoneme_drawer_stack.addWidget(self._build_phoneme_drawer_page(title_text, icon, presets, callback))
        rail_layout.addStretch(1)

        drawer_layout.addWidget(rail)
        drawer_layout.addWidget(self.phoneme_drawer_stack, 1)
        main.addWidget(drawer_shell, 2)
        main.addWidget(self._build_speech_assets_panel("articulation"), 2)

        tab.setWidget(page)
        self.tabs.insertTab(min(2, self.tabs.count()), tab, "Articulation Lab")
        self._refresh_phoneme_cards()
        self._set_phoneme_drawer("vowels")
        self._select_vowel_preset("AH", play=False)

    def _make_articulation_toy_control(self, key: str, label: str, low_label: str, high_label: str, minimum: int, maximum: int, value: int) -> QWidget:
        row = QWidget()
        row.setObjectName("articulationToyControl")
        row.setMinimumHeight(52)
        row.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout = QHBoxLayout(row)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(10)
        name = QLabel(label)
        name.setObjectName("articulationToyLabel")
        name.setMinimumWidth(150)
        low = QLabel(low_label)
        low.setObjectName("articulationToyEndpoint")
        low.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        low.setMinimumWidth(58)
        slider = NoWheelSlider(Qt.Horizontal)
        slider.setRange(minimum, maximum)
        slider.setValue(value)
        slider.setMinimumHeight(44)
        value_label = QLabel("")
        value_label.setObjectName("articulationToyValue")
        value_label.setAlignment(Qt.AlignCenter)
        value_label.setMinimumWidth(72)
        high = QLabel(high_label)
        high.setObjectName("articulationToyEndpoint")
        high.setMinimumWidth(58)
        slider.valueChanged.connect(lambda _value, slider_key=key: self._articulation_slider_changed(slider_key))
        self.articulation_sliders[key] = slider
        self.articulation_value_labels[key] = value_label
        layout.addWidget(name)
        layout.addWidget(low)
        layout.addWidget(slider, 1)
        layout.addWidget(high)
        layout.addWidget(value_label)
        return row

    def _build_phoneme_drawer_page(self, title: str, icon: str, presets: Dict[str, Dict[str, object]], callback) -> QWidget:
        page = QWidget()
        page.setObjectName("phonemeDrawerPage")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        header = QWidget()
        header.setObjectName("phonemeDrawerHeader")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(14, 10, 14, 8)
        header_layout.setSpacing(4)
        title_label = QLabel(f"{icon} {title}")
        title_label.setObjectName("phonemeDrawerTitle")
        help_label = QLabel("One active drawer stays open here. Cards are large enough to read and tap.")
        help_label.setObjectName("symbolHint")
        help_label.setWordWrap(True)
        header_layout.addWidget(title_label)
        header_layout.addWidget(help_label)
        layout.addWidget(header)

        scroll = WaveToyScrollArea(scroll_speed=0.95, content_drag_scroll=False)
        scroll.setObjectName("phonemeDrawerScroll")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        body = QWidget()
        body.setObjectName("phonemeDrawerBody")
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(10, 10, 14, 14)
        body_layout.setSpacing(10)

        if title == "Saved Phonemes":
            save_button = self._make_story_button("💾", "Save Phoneme", "#ffd166", self._save_current_phoneme)
            save_button.setMinimumHeight(72)
            body_layout.addWidget(save_button)
            self.phoneme_cards_widget = QWidget()
            body_layout.addWidget(self.phoneme_cards_widget)
        else:
            for name, data in presets.items():
                button = self._make_phoneme_preset_button(name, data)
                button.clicked.connect(lambda checked=False, preset_name=name, preset_data=data: callback(preset_name, preset_data))
                body_layout.addWidget(button)
        body_layout.addStretch(1)
        scroll.setWidget(body)
        layout.addWidget(scroll, 1)
        return page

    def _set_phoneme_drawer(self, drawer_key: str) -> None:
        order = ["vowels", "fricatives", "stops", "nasals", "glides", "liquids", "affricates", "extra_fricatives", "saved"]
        if self.phoneme_drawer_stack is None or drawer_key not in order:
            return
        self.active_phoneme_drawer = drawer_key
        self.phoneme_drawer_stack.setCurrentIndex(order.index(drawer_key))
        for key, button in self.phoneme_drawer_buttons.items():
            button.blockSignals(True)
            button.setChecked(key == drawer_key)
            button.blockSignals(False)

    def _build_phoneme_preset_grid(self, title: str, presets: Dict[str, Dict[str, object]], callback) -> QGroupBox:
        """Build a roomy two-column preset grid for one sidebar section."""
        box = self._toy_group(title)
        layout = QGridLayout(box)
        layout.setContentsMargins(WaveToySizing.CARD_PADDING, 24, WaveToySizing.CARD_PADDING, WaveToySizing.CARD_PADDING)
        layout.setHorizontalSpacing(12)
        layout.setVerticalSpacing(12)
        for column in range(2):
            layout.setColumnStretch(column, 1)
        for index, (name, data) in enumerate(presets.items()):
            button = self._make_phoneme_preset_button(name, data)
            button.clicked.connect(lambda checked=False, preset_name=name, preset_data=data: callback(preset_name, preset_data))
            layout.addWidget(button, index // 2, index % 2)
        return box

    def _make_phoneme_preset_button(self, name: str, data: Dict[str, object]) -> QPushButton:
        emoji = str(data.get("emoji", "🔊"))
        ipa = str(data.get("ipa", name.lower()))
        button = QPushButton(f"{emoji}  {name}    /{ipa}/")
        button.setObjectName("articulationPresetButton")
        button.setMinimumHeight(56)
        button.setMaximumHeight(64)
        button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        button.setCursor(Qt.PointingHandCursor)
        button.setToolTip(f"Load {name} phoneme preset")
        return button

    def _phoneme_path(self, phoneme: ArticulationPhoneme) -> Path:
        safe = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in phoneme.name.strip()).strip("_")
        return self.phonemes_dir / f"{safe or 'untitled_vowel'}.json"

    def _load_saved_phonemes(self) -> None:
        self.saved_phonemes = []
        if not self.phonemes_dir.exists():
            return
        for path in sorted(self.phonemes_dir.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                self.saved_phonemes.append(ArticulationPhoneme.from_json_dict(data))
            except Exception as exc:
                print(f"[Articulation Lab] Could not load {path}: {exc}")

    def _articulation_slider_value(self, key: str) -> float:
        slider = self.articulation_sliders[key]
        if key == "voice_pitch":
            return float(slider.value())
        return float(slider.value()) / 100.0

    def _phoneme_from_articulation_ui(self) -> ArticulationPhoneme:
        return ArticulationPhoneme(
            name=self.current_phoneme.name,
            ipa=self.current_phoneme.ipa,
            mouth_open=self._articulation_slider_value("mouth_open"),
            tongue_height=self._articulation_slider_value("tongue_height"),
            tongue_frontness=self._articulation_slider_value("tongue_frontness"),
            lip_rounding=self._articulation_slider_value("lip_rounding"),
            voice_pitch=self._articulation_slider_value("voice_pitch"),
            voice_strength=self._articulation_slider_value("voice_strength"),
            duration_ms=self.current_phoneme.duration_ms,
            preview_color=self.current_phoneme.preview_color,
            phoneme_family=self.current_phoneme.phoneme_family,
            air_pressure=self._articulation_slider_value("air_pressure"),
            teeth_gap=self._articulation_slider_value("teeth_gap"),
            closure=self._articulation_slider_value("closure"),
            burst_strength=self._articulation_slider_value("burst_strength"),
            nasal_open=self._articulation_slider_value("nasal_open"),
            voiced=bool(self.articulation_voiced_checkbox.isChecked()) if self.articulation_voiced_checkbox is not None else self.current_phoneme.voiced,
            noise_color=self.current_phoneme.noise_color,
            attack_ms=self.current_phoneme.attack_ms,
            release_ms=self.current_phoneme.release_ms,
            source_mode=self.current_phoneme.source_mode,
            source_wave_id=self.current_phoneme.source_wave_id,
            source_recipe_snapshot=dict(self.current_phoneme.source_recipe_snapshot or {}),
            source_audio_path=self.current_phoneme.source_audio_path,
            source_start_seconds=self.current_phoneme.source_start_seconds,
            source_duration_seconds=self.current_phoneme.source_duration_seconds,
            source_pitch_follow=self.current_phoneme.source_pitch_follow,
            source_loop_to_fit=self.current_phoneme.source_loop_to_fit,
            source_gain=self.current_phoneme.source_gain,
        ).clamped()

    def _set_articulation_ui_from_phoneme(self, phoneme: ArticulationPhoneme) -> None:
        phoneme = phoneme.clamped()
        self.current_phoneme = phoneme
        values = {
            "mouth_open": int(round(phoneme.mouth_open * 100)),
            "tongue_height": int(round(phoneme.tongue_height * 100)),
            "tongue_frontness": int(round(phoneme.tongue_frontness * 100)),
            "lip_rounding": int(round(phoneme.lip_rounding * 100)),
            "voice_pitch": int(round(phoneme.voice_pitch)),
            "voice_strength": int(round(phoneme.voice_strength * 100)),
            "air_pressure": int(round(phoneme.air_pressure * 100)),
            "teeth_gap": int(round(phoneme.teeth_gap * 100)),
            "closure": int(round(phoneme.closure * 100)),
            "burst_strength": int(round(phoneme.burst_strength * 100)),
            "nasal_open": int(round(phoneme.nasal_open * 100)),
        }
        for key, value in values.items():
            slider = self.articulation_sliders.get(key)
            if slider is not None:
                slider.blockSignals(True)
                slider.setValue(value)
                slider.blockSignals(False)
        if self.articulation_voiced_checkbox is not None:
            self.articulation_voiced_checkbox.blockSignals(True)
            self.articulation_voiced_checkbox.setChecked(phoneme.voiced)
            self.articulation_voiced_checkbox.blockSignals(False)
        self._update_articulation_preview(regenerate=True)

    def _articulation_slider_changed(self, key: str) -> None:
        del key
        self.current_phoneme = self._phoneme_from_articulation_ui()
        self._update_articulation_preview(regenerate=True)
        if self.phoneme_loop_enabled:
            self._play_phoneme_preview()

    def _update_articulation_preview(self, regenerate: bool = False) -> None:
        p = self.current_phoneme.clamped()
        if self.articulation_name_label is not None:
            all_preset_data = list(VOWEL_PRESETS.values()) + [data for _title, presets in CONSONANT_PRESET_SECTIONS for data in presets.values()]
            emoji = next((str(data["emoji"]) for data in all_preset_data if data.get("ipa") == p.ipa), "🗣")
            self.articulation_name_label.setText(f"{emoji} {p.name}")
        if self.articulation_ipa_label is not None:
            self.articulation_ipa_label.setText(f"IPA /{p.ipa}/")
        if self.articulation_canvas is not None:
            self.articulation_canvas.set_phoneme(p)
        if self.graphical_vocal_canvas is not None:
            self.graphical_vocal_canvas.set_phoneme(p)
        summary = articulation_summary(p)
        f1, f2, f3 = formants_from_articulation(p)
        if self.articulation_formant_label is not None:
            self.articulation_formant_label.setText(f"Formants: F1 {f1:.0f} Hz • F2 {f2:.0f} Hz • F3 {f3:.0f} Hz")
        if self.articulation_summary_label is not None:
            self.articulation_summary_label.setText(f"{p.name} /{p.ipa}/  |  {summary}")
        if self.articulation_mix_debug_label is not None:
            mix = articulation_synthesis_debug(p)
            stop_debug = ""
            if p.phoneme_family == "stop":
                stop_debug = (
                    f" • burst_gain {float(mix.get('burst_gain', 0.0)):.2f}"
                    f" • burst_brightness {float(mix.get('burst_brightness', 0.0)):.2f}"
                )
            self.articulation_mix_debug_label.setText(
                "Mix: "
                f"voiced_gain {float(mix['voiced_gain']):.2f} • "
                f"noise_gain {float(mix['noise_gain']):.2f} • "
                f"tonal_gain {float(mix['tonal_gain']):.2f} • "
                f"air_pressure {float(mix['air_pressure']):.2f} • "
                f"voice_strength {float(mix['voice_strength']):.2f}"
                f"{stop_debug} • "
                f"source_mode {mix['source_mode']}"
            )
        source_badge = articulation_source_badge(p.source_mode, p.source_wave_id, p.source_audio_path)
        self._sync_articulation_source_widgets(p)
        if self.articulation_wave_status_label is not None:
            self.articulation_wave_status_label.setText(f"🗣 {p.name} /{p.ipa}/  |  {summary}  |  Source: {source_badge}")
        for key, label in self.articulation_value_labels.items():
            value = self._articulation_slider_value(key)
            label.setText(f"{value:.0f} Hz" if key == "voice_pitch" else f"{value:.2f}")
        if regenerate:
            self.phoneme_preview_audio = self._render_articulation_with_source(p)

    def _articulation_source_mode_changed(self) -> None:
        if self.articulation_source_combo is None:
            return
        mode = str(self.articulation_source_combo.currentData() or ARTICULATION_SOURCE_DEFAULT)
        if mode == ARTICULATION_SOURCE_DEFAULT:
            self._reset_current_phoneme_source()
            return
        self.current_phoneme = self._phoneme_from_articulation_ui()
        self.current_phoneme.source_mode = mode
        self.current_phoneme = self.current_phoneme.clamped()
        self._update_articulation_preview(regenerate=True)

    def _sync_articulation_source_widgets(self, phoneme: ArticulationPhoneme) -> None:
        if self.articulation_source_combo is not None:
            index = self.articulation_source_combo.findData(phoneme.source_mode)
            self.articulation_source_combo.blockSignals(True)
            self.articulation_source_combo.setCurrentIndex(max(0, index))
            self.articulation_source_combo.blockSignals(False)
        if self.articulation_source_badge_label is not None:
            self.articulation_source_badge_label.setText(articulation_source_badge(phoneme.source_mode, phoneme.source_wave_id, phoneme.source_audio_path))

    def _selected_articulation_source_mode(self) -> str:
        if self.articulation_source_combo is None:
            return ARTICULATION_SOURCE_CURRENT
        mode = str(self.articulation_source_combo.currentData() or ARTICULATION_SOURCE_CURRENT)
        return mode if mode != ARTICULATION_SOURCE_DEFAULT else ARTICULATION_SOURCE_CURRENT

    def _selected_mix_wave_id(self) -> str:
        solo = self._solo_wave_from_ui() if hasattr(self, "wave_solo_buttons") else None
        if solo:
            return solo
        for wave_id in getattr(self, "wave_row_order", DEFAULT_WAVE_ORDER):
            if wave_id in getattr(self, "wave_start_sliders", {}):
                return wave_id
        return WAVE_ORDER[0]

    def _mix_wave_audio_for_source(self, wave_id: str) -> np.ndarray:
        settings = self._settings_from_ui()
        settings.solo_wave = wave_id
        settings.wave_muted = {wave: False for wave in active_wave_order(settings)}
        audio, _time_axis, _freq_env, _loud_env = generate_audio(settings)
        return audio

    def _source_metadata_for_mode(self, mode: str) -> Dict[str, object]:
        recipe = self._timeline_recipe_snapshot() if hasattr(self, "_timeline_recipe_snapshot") else {}
        metadata: Dict[str, object] = {
            "source_mode": mode,
            "source_recipe_snapshot": recipe,
            "source_start_seconds": 0.0,
            "source_duration_seconds": 0.0,
            "source_pitch_follow": True,
            "source_loop_to_fit": True,
            "source_gain": 1.0,
        }
        if mode == ARTICULATION_SOURCE_MIX_WAVE:
            metadata["source_wave_id"] = self._selected_mix_wave_id()
        elif mode == ARTICULATION_SOURCE_IMPORTED:
            item = self._timeline_palette_item_by_id(self.timeline_selected_palette_item_id)
            if item is not None:
                metadata["source_audio_path"] = item.source_path
                metadata["source_duration_seconds"] = item.duration_seconds
            else:
                QMessageBox.information(self, "Imported Audio Source", "Select an Audio Assets item first. Falling back to Default Voice.")
                metadata["source_mode"] = ARTICULATION_SOURCE_DEFAULT
        return metadata

    def _resolve_articulation_source_audio(self, phoneme: ArticulationPhoneme) -> np.ndarray | None:
        phoneme = phoneme.clamped()
        try:
            if phoneme.source_mode == ARTICULATION_SOURCE_CURRENT:
                return self._timeline_current_audio(force=True)
            if phoneme.source_mode == ARTICULATION_SOURCE_MIX_WAVE:
                return self._mix_wave_audio_for_source(phoneme.source_wave_id or self._selected_mix_wave_id())
            if phoneme.source_mode == ARTICULATION_SOURCE_IMPORTED:
                item = self._timeline_palette_item_by_id(self.timeline_selected_palette_item_id)
                if item is not None and item.source_path == phoneme.source_audio_path:
                    return np.array(item.audio_data, dtype=np.float32, copy=True)
                if phoneme.source_audio_path and Path(phoneme.source_audio_path).exists():
                    audio, _sample_rate = load_audio_file(Path(phoneme.source_audio_path))
                    return audio
                QMessageBox.warning(self, "Missing articulation source", "The saved imported source path is missing, so this phoneme will use Default Voice.")
                return None
        except Exception as exc:
            QMessageBox.warning(self, "Articulation source", f"Waveform source could not be prepared, so Default Voice will play.\n\n{exc}")
        return None

    def _render_articulation_with_source(self, phoneme: ArticulationPhoneme) -> np.ndarray:
        phoneme = phoneme.clamped()
        source_audio = self._resolve_articulation_source_audio(phoneme) if phoneme.source_mode != ARTICULATION_SOURCE_DEFAULT else None
        if source_audio is None:
            fallback = ArticulationPhoneme.from_json_dict({**phoneme.to_json_dict(), "source_mode": ARTICULATION_SOURCE_DEFAULT})
            return render_articulation_phoneme(fallback)
        return render_articulation_phoneme(phoneme, source_audio=source_audio)

    def _apply_current_wave_to_phoneme(self, checked: bool = False) -> None:
        del checked
        mode = self._selected_articulation_source_mode()
        self.current_phoneme = self._phoneme_from_articulation_ui()
        for key, value in self._source_metadata_for_mode(mode).items():
            setattr(self.current_phoneme, key, value)
        self.current_phoneme = self.current_phoneme.clamped()
        self._update_articulation_preview(regenerate=True)

    def _reset_current_phoneme_source(self, checked: bool = False) -> None:
        del checked
        self.current_phoneme = self._phoneme_from_articulation_ui()
        self.current_phoneme.source_mode = ARTICULATION_SOURCE_DEFAULT
        self.current_phoneme.source_wave_id = None
        self.current_phoneme.source_recipe_snapshot = {}
        self.current_phoneme.source_audio_path = None
        self.current_phoneme.source_start_seconds = 0.0
        self.current_phoneme.source_duration_seconds = 0.0
        self.current_phoneme.source_pitch_follow = True
        self.current_phoneme.source_loop_to_fit = True
        self.current_phoneme.source_gain = 1.0
        self.current_phoneme = self.current_phoneme.clamped()
        self._update_articulation_preview(regenerate=True)

    def _refresh_articulation_chain_cards(self) -> None:
        if self.articulation_chain_widget is None:
            return
        layout = self.articulation_chain_widget.layout()
        if layout is None:
            layout = QVBoxLayout(self.articulation_chain_widget)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(8)
        else:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
        if not self.articulation_chain_items:
            empty = QLabel("No chain yet. Add phonemes, then use 🧩 Create Word for a smoothed word render.")
            empty.setObjectName("symbolHint")
            empty.setWordWrap(True)
            layout.addWidget(empty)
            self._update_articulation_word_status()
            self._refresh_articulation_motion_timeline()
            return
        for index, item in enumerate(self.articulation_chain_items):
            layout.addWidget(self._make_articulation_chain_card(index, item))
            if index < len(self.articulation_chain_items) - 1:
                layout.addWidget(self._make_articulation_transition_control(index, item, self.articulation_chain_items[index + 1]))
        self._update_articulation_word_status()
        self._refresh_articulation_motion_timeline()

    def _make_articulation_chain_card(self, index: int, item: ArticulationChainItem) -> QWidget:
        phoneme = item.phoneme_for_render().clamped()
        card = QWidget()
        card.setObjectName("phonemeCard")
        card.setMinimumHeight(118)
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        selected_border = "#1d3557" if index == self.articulation_selected_chain_index else "rgba(0, 0, 0, 0.16)"
        card.setStyleSheet(
            f"QWidget#phonemeCard {{ background: {phoneme.preview_color}; border: 1px solid {selected_border}; border-radius: 10px; }}"
        )
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        header = QHBoxLayout()
        header.setSpacing(10)
        number = QLabel(f"{index + 1}")
        number.setObjectName("articulationIpaBadge")
        number.setAlignment(Qt.AlignCenter)
        number.setMinimumWidth(40)
        title = QLabel(f"{phoneme.name} /{phoneme.ipa}/")
        title.setObjectName("phonemeCardTitle")
        title.setWordWrap(True)
        details = QLabel(
            f"{phoneme.phoneme_family.title()} • {int(item.duration_ms or phoneme.duration_ms)} ms • "
            f"gap {int(item.gap_after_ms)} ms • crossfade {int(item.crossfade_ms)} ms • "
            f"transition {item.transition_ms if item.transition_ms is not None else 'rule'} ms"
        )
        details.setObjectName("phonemeCardSummary")
        details.setWordWrap(True)
        source_badge = QLabel(articulation_source_badge(phoneme.source_mode, phoneme.source_wave_id, phoneme.source_audio_path))
        source_badge.setObjectName("articulationIpaBadge")
        source_badge.setAlignment(Qt.AlignCenter)
        title_stack = QVBoxLayout()
        title_stack.setSpacing(2)
        title_stack.addWidget(title)
        title_stack.addWidget(details)
        title_stack.addWidget(source_badge)
        header.addWidget(number)
        header.addLayout(title_stack, 1)
        layout.addLayout(header)

        actions = QHBoxLayout()
        actions.setSpacing(8)
        for text, callback, danger in (
            ("▶ Play", lambda checked=False, i=index: self._play_chain_item(i), False),
            ("📂 Load/Edit", lambda checked=False, i=index: self._select_articulation_chain_item(i), False),
            ("⬅ Move Earlier", lambda checked=False, i=index: self._move_articulation_chain_item(i, -1), False),
            ("➡ Move Later", lambda checked=False, i=index: self._move_articulation_chain_item(i, 1), False),
            ("🗑 Remove", lambda checked=False, i=index: self._remove_articulation_chain_item(i), True),
        ):
            button = QPushButton(text)
            button.setObjectName("phonemeCardDangerAction" if danger else "phonemeCardSecondaryAction")
            button.setMinimumHeight(WaveToySizing.MIN_TOUCH_TARGET)
            button.setCursor(Qt.PointingHandCursor)
            button.clicked.connect(callback)
            actions.addWidget(button)
        layout.addLayout(actions)
        return card


    def _make_articulation_transition_control(self, index: int, left: ArticulationChainItem, right: ArticulationChainItem) -> QWidget:
        from_name = left.phoneme.name
        to_name = right.phoneme.name
        value = self._chain_transition_duration_ms(left, right)
        explicit = left.transition_to_next_ms is not None
        card = QWidget()
        card.setObjectName("articulationTransitionControl")
        card.setMinimumHeight(64)
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        card.setStyleSheet(
            "QWidget#articulationTransitionControl { background: #f7fafc; border: 1px dashed #7b2cbf; border-radius: 8px; }"
        )
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(4)

        header = QHBoxLayout()
        title = QLabel(f"↔ Transition: {from_name} → {to_name}")
        title.setObjectName("phonemeCardTitle")
        value_label = QLabel(f"{value} ms")
        value_label.setObjectName("articulationIpaBadge")
        value_label.setMinimumWidth(76)
        value_label.setAlignment(Qt.AlignCenter)
        header.addWidget(title, 1)
        header.addWidget(value_label)
        layout.addLayout(header)

        row = QHBoxLayout()
        row.setSpacing(10)
        fast = QLabel("fast")
        fast.setObjectName("articulationToyEndpoint")
        smooth = QLabel("smooth")
        smooth.setObjectName("articulationToyEndpoint")
        slider = QSlider(Qt.Horizontal)
        slider.setMinimum(0)
        slider.setMaximum(250)
        slider.setSingleStep(5)
        slider.setPageStep(25)
        slider.setTickInterval(25)
        slider.setTickPosition(QSlider.TicksBelow)
        slider.setMinimumHeight(34)
        slider.setValue(value)
        slider.setToolTip("0 ms is an immediate cut-style crossfade; higher values make slower, smoother mouth movement without adding silence.")
        slider.valueChanged.connect(lambda raw, i=index, label=value_label: self._set_chain_transition_to_next_ms(i, raw, label))
        row.addWidget(fast)
        row.addWidget(slider, 1)
        row.addWidget(smooth)
        layout.addLayout(row)

        curve_row = QHBoxLayout()
        curve_label = QLabel("Curve")
        curve_label.setObjectName("phonemeCardSummary")
        curve_combo = QComboBox()
        curve_combo.addItems(list(ARTICULATION_TRANSITION_CURVES))
        curve_combo.setCurrentText(left.transition_curve if left.transition_curve in ARTICULATION_TRANSITION_CURVES else ARTICULATION_DEFAULT_TRANSITION_CURVE)
        curve_combo.currentTextChanged.connect(lambda curve, i=index: self._set_chain_transition_curve(i, curve))
        curve_row.addWidget(curve_label)
        curve_row.addWidget(curve_combo, 1)
        layout.addLayout(curve_row)

        note = QLabel(("custom boundary timing" if explicit else "family rule default until you move this slider") + f" • {left.transition_curve} curve")
        note.setObjectName("phonemeCardSummary")
        note.setWordWrap(True)
        layout.addWidget(note)
        return card

    def _set_chain_transition_to_next_ms(self, index: int, raw_value: int, value_label: QLabel | None = None) -> None:
        if index < 0 or index >= len(self.articulation_chain_items) - 1:
            return
        value = int(round(int(raw_value) / 5.0) * 5)
        value = int(np.clip(value, 0, 250))
        sender = self.sender()
        if isinstance(sender, QSlider) and sender.value() != value:
            sender.blockSignals(True)
            sender.setValue(value)
            sender.blockSignals(False)
        self.articulation_chain_items[index].transition_to_next_ms = value
        if value_label is not None:
            value_label.setText(f"{value} ms")
        self._mark_articulation_word_dirty()
        self._refresh_articulation_motion_timeline()

    def _set_chain_item_duration_ms(self, index: int, raw_value: int) -> None:
        if index < 0 or index >= len(self.articulation_chain_items):
            return
        value = int(np.clip(int(raw_value), 80, 5000))
        item = self.articulation_chain_items[index]
        item.duration_ms = value
        item.phoneme.duration_ms = value
        self.articulation_selected_chain_index = index
        self._mark_articulation_word_dirty()
        self._refresh_articulation_chain_cards()
        self._scrub_articulation_playhead(self.articulation_playhead_ms)

    def _set_chain_transition_curve(self, index: int, curve: str) -> None:
        if index < 0 or index >= len(self.articulation_chain_items) - 1:
            return
        if curve not in ARTICULATION_TRANSITION_CURVES:
            curve = ARTICULATION_DEFAULT_TRANSITION_CURVE
        self.articulation_chain_items[index].transition_curve = curve
        self.articulation_selected_chain_index = index
        self._mark_articulation_word_dirty()
        self._refresh_articulation_chain_cards()
        self._scrub_articulation_playhead(self.articulation_playhead_ms)

    def _set_selected_boundary_curve(self, curve: str) -> None:
        if self.articulation_selected_chain_index is None:
            return
        index = min(self.articulation_selected_chain_index, len(self.articulation_chain_items) - 2)
        self._set_chain_transition_curve(index, curve)

    def _zoom_articulation_timeline(self, delta: float) -> None:
        self.articulation_timeline_zoom = float(np.clip(self.articulation_timeline_zoom + delta, 0.35, 3.5))
        if self.articulation_timeline_canvas is not None:
            self.articulation_timeline_canvas.set_zoom(self.articulation_timeline_zoom)
        self._refresh_articulation_motion_timeline()

    def _scrub_articulation_playhead(self, elapsed_ms: float) -> None:
        self.articulation_playhead_ms = float(max(0.0, elapsed_ms))
        self._set_articulation_motion_elapsed(self.articulation_playhead_ms)

    def _select_articulation_chain_item(self, index: int) -> None:
        if index < 0 or index >= len(self.articulation_chain_items):
            return
        self.articulation_selected_chain_index = index
        self._set_articulation_ui_from_phoneme(self.articulation_chain_items[index].phoneme)
        self._refresh_articulation_chain_cards()

    def _add_current_phoneme_to_chain(self, checked: bool = False) -> None:
        del checked
        self.current_phoneme = self._phoneme_from_articulation_ui()
        self.articulation_chain_items.append(ArticulationChainItem(ArticulationPhoneme.from_json_dict(self.current_phoneme.to_json_dict())))
        self.articulation_selected_chain_index = len(self.articulation_chain_items) - 1
        self._mark_articulation_word_dirty()
        self._refresh_articulation_chain_cards()

    def _apply_current_wave_to_selected_chain_item(self, checked: bool = False) -> None:
        del checked
        if self.articulation_selected_chain_index is None or self.articulation_selected_chain_index >= len(self.articulation_chain_items):
            QMessageBox.information(self, "Articulation Chain", "Select a chain phoneme first.")
            return
        phoneme = self.articulation_chain_items[self.articulation_selected_chain_index].phoneme
        for key, value in self._source_metadata_for_mode(self._selected_articulation_source_mode()).items():
            setattr(phoneme, key, value)
        self.articulation_chain_items[self.articulation_selected_chain_index].phoneme = phoneme.clamped()
        self._mark_articulation_word_dirty()
        self._refresh_articulation_chain_cards()

    def _apply_current_wave_to_whole_chain(self, checked: bool = False) -> None:
        del checked
        metadata = self._source_metadata_for_mode(self._selected_articulation_source_mode())
        for item in self.articulation_chain_items:
            for key, value in metadata.items():
                setattr(item.phoneme, key, value)
            item.phoneme = item.phoneme.clamped()
        self._mark_articulation_word_dirty()
        self._refresh_articulation_chain_cards()

    def _reset_selected_chain_item_source(self, checked: bool = False) -> None:
        del checked
        if self.articulation_selected_chain_index is None or self.articulation_selected_chain_index >= len(self.articulation_chain_items):
            return
        item = self.articulation_chain_items[self.articulation_selected_chain_index]
        item.phoneme = ArticulationPhoneme.from_json_dict({**item.phoneme.to_json_dict(), "source_mode": ARTICULATION_SOURCE_DEFAULT, "source_wave_id": None, "source_recipe_snapshot": {}, "source_audio_path": None})
        self._mark_articulation_word_dirty()
        self._refresh_articulation_chain_cards()

    def _reset_whole_chain_source(self, checked: bool = False) -> None:
        del checked
        for item in self.articulation_chain_items:
            item.phoneme = ArticulationPhoneme.from_json_dict({**item.phoneme.to_json_dict(), "source_mode": ARTICULATION_SOURCE_DEFAULT, "source_wave_id": None, "source_recipe_snapshot": {}, "source_audio_path": None})
        self._mark_articulation_word_dirty()
        self._refresh_articulation_chain_cards()

    def _play_chain_item(self, index: int) -> None:
        if index < 0 or index >= len(self.articulation_chain_items):
            return
        self._play_audio_array(self._render_articulation_with_source(self.articulation_chain_items[index].phoneme_for_render()))

    def _move_articulation_chain_item(self, index: int, direction: int) -> None:
        new_index = index + direction
        if index < 0 or index >= len(self.articulation_chain_items) or new_index < 0 or new_index >= len(self.articulation_chain_items):
            return
        self.articulation_chain_items[index], self.articulation_chain_items[new_index] = self.articulation_chain_items[new_index], self.articulation_chain_items[index]
        if self.articulation_selected_chain_index == index:
            self.articulation_selected_chain_index = new_index
        elif self.articulation_selected_chain_index == new_index:
            self.articulation_selected_chain_index = index
        self._mark_articulation_word_dirty()
        self._refresh_articulation_chain_cards()

    def _remove_articulation_chain_item(self, index: int) -> None:
        if index < 0 or index >= len(self.articulation_chain_items):
            return
        del self.articulation_chain_items[index]
        if not self.articulation_chain_items:
            self.articulation_selected_chain_index = None
        elif self.articulation_selected_chain_index is None:
            self.articulation_selected_chain_index = min(index, len(self.articulation_chain_items) - 1)
        elif self.articulation_selected_chain_index == index:
            self.articulation_selected_chain_index = min(index, len(self.articulation_chain_items) - 1)
        elif self.articulation_selected_chain_index > index:
            self.articulation_selected_chain_index -= 1
        self._mark_articulation_word_dirty()
        self._refresh_articulation_chain_cards()

    def _clear_articulation_chain(self, checked: bool = False) -> None:
        del checked
        if not self.articulation_chain_items:
            return
        answer = QMessageBox.question(
            self,
            "Clear Articulation Chain",
            "Clear every editable phoneme card from the Articulation Chain? Saved phonemes are not deleted.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        self.articulation_chain_items = []
        self.articulation_selected_chain_index = None
        self._mark_articulation_word_dirty()
        self._refresh_articulation_chain_cards()

    def _set_articulation_word_render_mode(self, mode: str) -> None:
        if mode not in ARTICULATION_WORD_RENDER_MODES:
            mode = ARTICULATION_WORD_RENDER_CONTINUOUS
        self.articulation_word_render_settings["word_render_mode"] = mode
        self._mark_articulation_word_dirty()
        self._refresh_articulation_motion_timeline()
        self._update_articulation_word_status()

    def _articulation_word_render_mode(self) -> str:
        if self.articulation_word_render_mode_combo is not None:
            mode = str(self.articulation_word_render_mode_combo.currentText())
        else:
            mode = str(self.articulation_word_render_settings.get("word_render_mode", ARTICULATION_WORD_RENDER_CONTINUOUS))
        return mode if mode in ARTICULATION_WORD_RENDER_MODES else ARTICULATION_WORD_RENDER_CONTINUOUS

    def _apply_voice_profile_to_chain(self, profile: str) -> None:
        if profile == "Neutral" or not self.articulation_chain_items:
            self.articulation_word_render_settings["voice_profile"] = profile
            return
        multipliers = {
            "Child": {"pitch": 1.45, "formant": 1.12, "voice": 0.92, "noise": 0.95},
            "Female": {"pitch": 1.22, "formant": 1.06, "voice": 1.00, "noise": 0.95},
            "Male": {"pitch": 0.78, "formant": 0.94, "voice": 1.05, "noise": 0.90},
            "Robot": {"pitch": 1.00, "formant": 1.00, "voice": 0.85, "noise": 0.35},
            "Monster": {"pitch": 0.55, "formant": 0.84, "voice": 1.12, "noise": 1.20},
            "Whisper": {"pitch": 1.00, "formant": 1.02, "voice": 0.25, "noise": 1.55},
        }.get(profile, {"pitch": 1.0, "formant": 1.0, "voice": 1.0, "noise": 1.0})
        for item in self.articulation_chain_items:
            data = item.phoneme.to_json_dict()
            data["voice_pitch"] = float(np.clip(float(data.get("voice_pitch", 220.0)) * multipliers["pitch"], 60.0, 880.0))
            data["tongue_height"] = float(np.clip(0.5 + (float(data.get("tongue_height", 0.5)) - 0.5) * multipliers["formant"], 0.0, 1.0))
            data["tongue_frontness"] = float(np.clip(0.5 + (float(data.get("tongue_frontness", 0.5)) - 0.5) * multipliers["formant"], 0.0, 1.0))
            data["voice_strength"] = float(np.clip(float(data.get("voice_strength", 0.65)) * multipliers["voice"], 0.0, 1.0))
            data["noise_color"] = float(np.clip(float(data.get("noise_color", 0.5)) * multipliers["noise"], 0.0, 1.0))
            if profile == "Whisper":
                data["voiced"] = False
                data["air_pressure"] = float(np.clip(float(data.get("air_pressure", 0.45)) + 0.25, 0.0, 1.0))
            item.phoneme = ArticulationPhoneme.from_json_dict(data)
        self.articulation_word_render_settings["voice_profile"] = profile
        self._mark_articulation_word_dirty()
        self._refresh_articulation_chain_cards()

    def _toggle_articulation_smooth_transitions(self, checked: bool) -> None:
        self.articulation_word_render_settings["smooth_mouth_transitions"] = bool(checked)
        self._mark_articulation_word_dirty()

    def _articulation_smooth_transitions_enabled(self) -> bool:
        if self.articulation_smooth_transitions_checkbox is not None:
            return bool(self.articulation_smooth_transitions_checkbox.isChecked())
        return bool(self.articulation_word_render_settings.get("smooth_mouth_transitions", True))

    def _chain_transition_duration_ms(self, left: ArticulationChainItem, right: ArticulationChainItem) -> int:
        if left.transition_to_next_ms is not None:
            return int(left.transition_to_next_ms)
        left_family = left.phoneme_for_render().phoneme_family
        right_family = right.phoneme_for_render().phoneme_family
        return int(ARTICULATION_TRANSITION_RULE_MS.get((left_family, right_family), ARTICULATION_DEFAULT_TRANSITION_MS))

    def _articulation_motion_timeline(self, include_word_gaps: bool = False) -> Tuple[List[Dict[str, object]], int]:
        del include_word_gaps
        segments, total_ms, _stop_events, _burst_events = self._build_articulation_envelope_timeline()
        return segments, total_ms

    def _refresh_articulation_motion_timeline(self) -> None:
        segments, total_ms = self._articulation_motion_timeline()
        self.articulation_playhead_ms = float(np.clip(self.articulation_playhead_ms, 0.0, total_ms))
        blocks: List[Tuple[str, float, float, str]] = []
        for segment in segments:
            start = float(segment["start"]) / total_ms
            end = float(segment["end"]) / total_ms
            if segment["kind"] == "transition":
                blocks.append(("→", start, end, "#ffffff"))
            elif segment["kind"] == "hold":
                phoneme = segment["from"]
                blocks.append((phoneme.name, start, end, phoneme.preview_color))
        if self.articulation_motion_canvas is not None:
            self.articulation_motion_canvas.set_motion_timeline(blocks)
        if self.articulation_timeline_canvas is not None:
            self.articulation_timeline_canvas.set_zoom(self.articulation_timeline_zoom)
            self.articulation_timeline_canvas.set_timeline(self.articulation_chain_items, total_ms, self.articulation_playhead_ms)
        if self.articulation_envelope_canvas is not None:
            self.articulation_envelope_canvas.set_timeline(segments, total_ms, self.articulation_playhead_ms)
        if self.articulation_formant_canvas is not None:
            self.articulation_formant_canvas.set_timeline(segments, total_ms, self.articulation_playhead_ms)
        if self.articulation_boundary_curve_combo is not None:
            boundary_index = min(self.articulation_selected_chain_index or 0, max(0, len(self.articulation_chain_items) - 2))
            curve = self.articulation_chain_items[boundary_index].transition_curve if boundary_index < len(self.articulation_chain_items) - 1 else ARTICULATION_DEFAULT_TRANSITION_CURVE
            self.articulation_boundary_curve_combo.blockSignals(True)
            self.articulation_boundary_curve_combo.setCurrentText(curve if curve in ARTICULATION_TRANSITION_CURVES else ARTICULATION_DEFAULT_TRANSITION_CURVE)
            self.articulation_boundary_curve_combo.blockSignals(False)
        self._refresh_graphical_chain_editor()

    def _motion_state_at_ms(self, elapsed_ms: float) -> Tuple[ArticulationPhoneme, str, str, float, float, int, bool]:
        segments, total_ms = self._articulation_motion_timeline()
        if not segments:
            phoneme = self.current_phoneme.clamped()
            return phoneme, phoneme.name, "—", 0.0, 0.0, 0, False
        elapsed_ms = float(np.clip(elapsed_ms, 0.0, total_ms))
        active = segments[-1]
        for segment in segments:
            if float(segment["start"]) <= elapsed_ms <= float(segment["end"]):
                active = segment
                break
        start = float(active["start"])
        end = max(start + 1.0, float(active["end"]))
        local = float(np.clip((elapsed_ms - start) / (end - start), 0.0, 1.0))
        left = active["from"]
        right = active["to"]
        transition_duration_ms = self._chain_transition_duration_ms(self.articulation_chain_items[int(active["index"])], self.articulation_chain_items[int(active["index"]) + 1]) if int(active["index"]) < len(self.articulation_chain_items) - 1 else 0
        in_transition = active["kind"] == "transition"
        if in_transition:
            phoneme = interpolate_articulation_phoneme(left, right, local, str(active.get("curve", ARTICULATION_DEFAULT_TRANSITION_CURVE)))
            next_name = right.name
            transition_progress = local
        else:
            phoneme = left.clamped()
            next_index = int(active["index"]) + 1
            next_name = self.articulation_chain_items[next_index].phoneme.name if next_index < len(self.articulation_chain_items) else "—"
            transition_progress = 0.0
        return phoneme, left.name, next_name, transition_progress, elapsed_ms / total_ms, transition_duration_ms, in_transition

    def _set_articulation_motion_elapsed(self, elapsed_ms: float) -> None:
        if self.articulation_motion_canvas is None:
            return
        phoneme, current_name, next_name, transition_progress, playhead, transition_ms, in_transition = self._motion_state_at_ms(elapsed_ms)
        _segments_for_total, total_for_scrub = self._articulation_motion_timeline()
        self.articulation_playhead_ms = float(np.clip(elapsed_ms, 0.0, max(1, total_for_scrub)))
        self.articulation_motion_canvas.set_motion_state(phoneme, current_name, next_name, transition_progress, playhead, transition_ms, in_transition)
        self._refresh_articulation_motion_timeline()
        f1, f2, f3 = formants_from_articulation(phoneme)
        values = ", ".join(f"{name} {getattr(phoneme, name):.2f}" for name in ("mouth_open", "tongue_height", "tongue_frontness", "lip_rounding"))
        status = (
            f"Motion {current_name} → {next_name} • transition {transition_ms} ms • {'active' if in_transition else 'holding'} • "
            f"{int(transition_progress * 100)}% • playhead {int(playhead * 100)}% • {values} • F1/F2/F3 {f1:.0f}/{f2:.0f}/{f3:.0f} Hz"
        )
        if self.articulation_motion_status_label is not None:
            self.articulation_motion_status_label.setText(status)
        if self.articulation_scrub_label is not None:
            self.articulation_scrub_label.setText(status)

    def _start_articulation_motion(self, *, loop: bool = False, speed: float = 1.0, audio: np.ndarray | None = None) -> None:
        if not self.articulation_chain_items:
            QMessageBox.information(self, "Word Motion Preview", "Add at least one phoneme to the Articulation Chain first.")
            return
        self.articulation_motion_loop = bool(loop)
        self.articulation_motion_speed = max(0.05, float(speed))
        self.word_motion_play_audio = audio is not None and audio.size > 0 and abs(self.articulation_motion_speed - 1.0) < 1e-6
        _segments, timeline_total_ms = self._articulation_motion_timeline(include_word_gaps=False)
        self.word_motion_timeline_total_ms = max(1, int(timeline_total_ms))
        if audio is not None and audio.size > 0:
            self.word_motion_duration_seconds = max(0.001, len(audio) / SAMPLE_RATE) / self.articulation_motion_speed
        else:
            self.word_motion_duration_seconds = max(0.001, self.word_motion_timeline_total_ms / 1000.0) / self.articulation_motion_speed
        self.articulation_motion_total_ms = max(1, int(round(self.word_motion_duration_seconds * 1000.0)))
        self.word_motion_start_monotonic = time.monotonic()
        self.articulation_motion_started_at = self.word_motion_start_monotonic
        if self.word_motion_play_audio and audio is not None:
            self._play_audio_array(audio)
        self._refresh_articulation_motion_timeline()
        self.articulation_motion_timer.start(16)
        self._articulation_motion_tick()

    def _current_gapless_word_audio(self) -> np.ndarray:
        if self.articulation_word_render_audio.size == 0:
            return self._render_word_audio_for_current_chain()
        return self.articulation_word_render_audio

    def _play_articulation_motion(self, checked: bool = False) -> None:
        del checked
        audio = self._current_gapless_word_audio()
        if audio.size == 0:
            return
        self._start_articulation_motion(loop=False, speed=1.0, audio=audio)

    def _loop_articulation_motion(self, checked: bool = False) -> None:
        del checked
        audio = self._current_gapless_word_audio()
        if audio.size == 0:
            return
        self._start_articulation_motion(loop=True, speed=1.0, audio=audio)

    def _slow_articulation_motion(self, checked: bool = False) -> None:
        del checked
        self._start_articulation_motion(loop=False, speed=0.35, audio=None)
        if self.articulation_motion_status_label is not None:
            self.articulation_motion_status_label.setText("Slow Motion Visual Only • audio is not time-stretched.")

    def _stop_articulation_motion(self, checked: bool = False) -> None:
        del checked
        self.articulation_motion_started_at = None
        self.word_motion_start_monotonic = None
        self.word_motion_play_audio = False
        self.articulation_motion_timer.stop()
        if sd is not None:
            try:
                sd.stop()
            except Exception:
                pass
        if self.articulation_motion_status_label is not None:
            self.articulation_motion_status_label.setText("Motion stopped • audio stopped.")

    def _articulation_motion_tick(self) -> None:
        if self.articulation_motion_started_at is None or self.articulation_motion_total_ms <= 0:
            self.articulation_motion_timer.stop()
            return
        elapsed_ms = (time.monotonic() - self.articulation_motion_started_at) * 1000.0 * self.articulation_motion_speed
        if elapsed_ms >= self.articulation_motion_total_ms:
            if self.articulation_motion_loop:
                self.articulation_motion_started_at = time.monotonic()
                self.word_motion_start_monotonic = self.articulation_motion_started_at
                elapsed_ms = 0.0
                if self.word_motion_play_audio and self.articulation_word_render_audio.size:
                    self._play_audio_array(self.articulation_word_render_audio)
            else:
                elapsed_ms = float(self.articulation_motion_total_ms)
                self.articulation_motion_timer.stop()
                self.articulation_motion_started_at = None
                self.word_motion_start_monotonic = None
        progress = 0.0 if self.articulation_motion_total_ms <= 0 else float(np.clip(elapsed_ms / self.articulation_motion_total_ms, 0.0, 1.0))
        timeline_elapsed_ms = progress * float(max(1, self.word_motion_timeline_total_ms))
        self._set_articulation_motion_elapsed(timeline_elapsed_ms)

    def _mark_articulation_word_dirty(self) -> None:
        self.articulation_word_render_audio = np.zeros((0, 2), dtype=np.float32)
        self.articulation_last_word_render_path = None
        self.articulation_last_word_render_created_at = None
        self._update_articulation_word_status()

    def _chain_custom_transition_summary(self) -> str:
        custom = [
            f"{item.phoneme.name}→{self.articulation_chain_items[index + 1].phoneme.name} {int(item.transition_to_next_ms)} ms"
            for index, item in enumerate(self.articulation_chain_items[:-1])
            if item.transition_to_next_ms is not None
        ]
        if not custom:
            return "family transition rules"
        preview = ", ".join(custom[:3])
        extra = f", +{len(custom) - 3} more" if len(custom) > 3 else ""
        return f"custom transitions: {preview}{extra}"

    def _update_articulation_word_status(self) -> None:
        if self.articulation_word_status_label is None:
            return
        transition_text = self._chain_custom_transition_summary()
        if self.articulation_word_render_audio.size:
            duration = len(self.articulation_word_render_audio) / SAMPLE_RATE
            path_text = f" • exported: {self.articulation_last_word_render_path}" if self.articulation_last_word_render_path else ""
            mode = self._articulation_word_render_mode()
            self.articulation_word_status_label.setText(
                f"Word ready • {duration:.2f}s • {len(self.articulation_chain_items)} phoneme(s) • render mode: {mode} • {transition_text}{path_text}"
            )
        elif self.articulation_chain_items:
            mode = self._articulation_word_render_mode()
            self.articulation_word_status_label.setText(
                f"{len(self.articulation_chain_items)} phoneme(s) in chain • render mode: {mode} • {transition_text}."
            )
        else:
            self.articulation_word_status_label.setText("Create Word makes a smoothed render without changing the editable chain.")

    def _chain_boundary_crossfade_ms(self, left: ArticulationChainItem, right: ArticulationChainItem) -> int:
        left_family = left.phoneme_for_render().phoneme_family
        right_family = right.phoneme_for_render().phoneme_family
        if left_family == "stop" and right_family == "vowel":
            return 8
        if left_family in {"fricative", "affricate"} and right_family == "vowel":
            return 30
        if left_family == "nasal" and right_family == "vowel":
            return 40
        if left_family in {"glide", "liquid"} and right_family == "vowel":
            return 55
        if left_family == "vowel" and right_family == "vowel":
            return 60
        if left_family == "vowel" and right_family != "vowel":
            return ARTICULATION_DEFAULT_WORD_CROSSFADE_MS
        return int(self.articulation_word_render_settings.get("crossfade_ms", ARTICULATION_DEFAULT_WORD_CROSSFADE_MS))

    def _word_crossfade_ms(self, requested_ms: int, left: ArticulationChainItem | None = None, right: ArticulationChainItem | None = None) -> int:
        rule_ms = self._chain_boundary_crossfade_ms(left, right) if left is not None and right is not None else ARTICULATION_DEFAULT_WORD_CROSSFADE_MS
        requested_ms = int(requested_ms)
        if requested_ms <= 0 or requested_ms in {12, ARTICULATION_DEFAULT_WORD_CROSSFADE_MS}:
            requested_ms = rule_ms
        minimum_ms = int(self.articulation_word_render_settings.get("minimum_crossfade_ms", ARTICULATION_MIN_WORD_CROSSFADE_MS))
        return max(minimum_ms, requested_ms)

    def _word_gap_after_ms(self, item: ArticulationChainItem, index: int) -> int:
        requested = int(item.gap_after_ms) if index < len(self.articulation_chain_items) - 1 else 0
        if requested > 0 and not bool(self.articulation_word_render_settings.get("allow_word_gaps", False)):
            print(f"[WaveToy Word] requested gap ignored after {item.phoneme.name}: {requested} ms")
            return 0
        return max(0, requested)

    def _fade_word_edges(self, audio: np.ndarray) -> np.ndarray:
        if audio.size == 0:
            return audio.astype(np.float32)
        audio = np.array(audio, dtype=np.float32, copy=True)
        fade_in = int(float(self.articulation_word_render_settings.get("word_fade_in_ms", 5)) * SAMPLE_RATE / 1000.0)
        fade_out = int(float(self.articulation_word_render_settings.get("word_fade_out_ms", 8)) * SAMPLE_RATE / 1000.0)
        if fade_in > 0:
            fade_in = min(fade_in, len(audio))
            audio[:fade_in] *= np.linspace(0.0, 1.0, fade_in, dtype=np.float32)[:, None]
        if fade_out > 0:
            fade_out = min(fade_out, len(audio))
            audio[-fade_out:] *= np.linspace(1.0, 0.0, fade_out, dtype=np.float32)[:, None]
        return audio

    def _smooth_word_boundaries(self, audio: np.ndarray, boundaries: List[int]) -> np.ndarray:
        if audio.size == 0:
            return audio.astype(np.float32)
        radius = int(float(self.articulation_word_render_settings.get("boundary_smoothing_ms", 8)) * SAMPLE_RATE / 1000.0)
        if radius <= 1:
            return audio.astype(np.float32)
        smoothed = np.array(audio, dtype=np.float32, copy=True)
        kernel_size = max(3, min(radius, 801))
        if kernel_size % 2 == 0:
            kernel_size += 1
        kernel = np.ones(kernel_size, dtype=np.float32) / float(kernel_size)
        for boundary in boundaries:
            start = max(0, int(boundary) - radius)
            end = min(len(smoothed), int(boundary) + radius)
            if end - start <= kernel_size:
                continue
            window = smoothed[start:end]
            filtered = np.column_stack([np.convolve(window[:, channel], kernel, mode="same") for channel in range(window.shape[1])])
            blend = np.sin(np.linspace(0.0, math.pi, end - start, dtype=np.float32))[:, None] * 0.35
            smoothed[start:end] = window * (1.0 - blend) + filtered * blend
        return smoothed.astype(np.float32)

    def _append_word_clip(self, word: np.ndarray, clip: np.ndarray, crossfade_ms: int, gap_after_ms: int, boundaries: List[int]) -> np.ndarray:
        if clip.size == 0:
            return word.astype(np.float32)
        clip = np.array(clip, dtype=np.float32, copy=True)
        if word.size == 0:
            combined = clip
        else:
            crossfade = int(max(0, crossfade_ms) * SAMPLE_RATE / 1000.0)
            crossfade = min(crossfade, len(word) - 1, len(clip) - 1, int(0.50 * min(len(word), len(clip))))
            if crossfade > 1:
                fade_out = np.cos(np.linspace(0.0, math.pi / 2.0, crossfade, dtype=np.float32))[:, None]
                fade_in = np.sin(np.linspace(0.0, math.pi / 2.0, crossfade, dtype=np.float32))[:, None]
                overlap = word[-crossfade:] * fade_out + clip[:crossfade] * fade_in
                boundary = len(word) - crossfade // 2
                boundaries.append(boundary)
                print(f"[WaveToy Word] boundary crossfade duration {crossfade * 1000.0 / SAMPLE_RATE:.1f} ms at sample {boundary}")
                combined = np.vstack([word[:-crossfade], overlap, clip[crossfade:]])
            else:
                boundaries.append(len(word))
                combined = np.vstack([word, clip])
        gap_samples = int(max(0, gap_after_ms) * SAMPLE_RATE / 1000.0)
        if gap_samples:
            combined = np.vstack([combined, np.zeros((gap_samples, 2), dtype=np.float32)])
        return combined.astype(np.float32)

    def _effective_transition_samples(self, left_clip: np.ndarray, right_clip: np.ndarray, requested_ms: int, left: ArticulationChainItem, right: ArticulationChainItem) -> int:
        requested_samples = int(max(0, requested_ms) * SAMPLE_RATE / 1000.0)
        if requested_samples <= 0 or left_clip.size == 0 or right_clip.size == 0:
            return 0
        shorter = max(1, min(len(left_clip), len(right_clip)))
        left_family = left.phoneme_for_render().phoneme_family
        right_family = right.phoneme_for_render().phoneme_family
        fraction = 0.45
        if left_family == "stop" or right_family == "stop":
            fraction = 0.30
        if left_family == "stop" and right_family == "vowel":
            fraction = 0.22
        maximum_samples = max(1, int(shorter * fraction))
        return int(min(requested_samples, maximum_samples))

    def _overlap_word_clip(self, word: np.ndarray, clip: np.ndarray, overlap_samples: int, boundaries: List[int]) -> np.ndarray:
        if clip.size == 0:
            return word.astype(np.float32)
        clip = np.array(clip, dtype=np.float32, copy=True)
        if word.size == 0:
            return clip.astype(np.float32)
        overlap_samples = int(min(max(0, overlap_samples), len(word) - 1, len(clip) - 1))
        if overlap_samples <= 1:
            boundaries.append(len(word))
            return np.vstack([word, clip]).astype(np.float32)
        fade_out = np.cos(np.linspace(0.0, math.pi / 2.0, overlap_samples, dtype=np.float32))[:, None]
        fade_in = np.sin(np.linspace(0.0, math.pi / 2.0, overlap_samples, dtype=np.float32))[:, None]
        overlap = word[-overlap_samples:] * fade_out + clip[:overlap_samples] * fade_in
        boundary = len(word) - overlap_samples // 2
        boundaries.append(boundary)
        return np.vstack([word[:-overlap_samples], overlap, clip[overlap_samples:]]).astype(np.float32)

    def _transition_gain_snapshot(self, phoneme: ArticulationPhoneme) -> Dict[str, float]:
        debug = articulation_synthesis_debug(phoneme)
        return {
            "voiced_gain": float(debug.get("voiced_gain", 0.0)),
            "noise_gain": float(debug.get("noise_gain", 0.0)),
            "tonal_gain": float(debug.get("tonal_gain", 0.0)),
        }

    def _log_transition_boundary(self, left: ArticulationChainItem, right: ArticulationChainItem, requested_ms: int, effective_samples: int, inserted_silence_samples: int = 0, transition_render_samples: int = 0, interpolated_articulation_used: bool = False) -> None:
        left_phoneme = left.phoneme_for_render()
        right_phoneme = right.phoneme_for_render()
        start_gain = self._transition_gain_snapshot(left_phoneme)
        end_gain = self._transition_gain_snapshot(right_phoneme)
        effective_ms = effective_samples * 1000.0 / SAMPLE_RATE
        print(
            "[WaveToy Transition] "
            f"{left_phoneme.name}->{right_phoneme.name} "
            f"families={left_phoneme.phoneme_family}->{right_phoneme.phoneme_family} "
            f"requested_transition_ms={int(requested_ms)} "
            f"effective_transition_ms={effective_ms:.1f} "
            f"crossfade_samples={int(effective_samples)} "
            f"inserted_silence_samples={int(inserted_silence_samples)} "
            f"transition_render_samples={int(transition_render_samples)} "
            f"interpolated_articulation_used={bool(interpolated_articulation_used)} "
            f"voiced_gain_start={start_gain['voiced_gain']:.3f} "
            f"voiced_gain_end={end_gain['voiced_gain']:.3f} "
            f"noise_gain_start={start_gain['noise_gain']:.3f} "
            f"noise_gain_end={end_gain['noise_gain']:.3f} "
            f"tonal_gain_start={start_gain['tonal_gain']:.3f} "
            f"tonal_gain_end={end_gain['tonal_gain']:.3f}"
        )
        if bool(self.articulation_word_render_settings.get("transition_debug_verbose", False)):
            print(
                "[WaveToy Transition] verbose "
                f"left_duration_ms={left_phoneme.duration_ms} right_duration_ms={right_phoneme.duration_ms} "
                f"left_source={left_phoneme.source_mode} right_source={right_phoneme.source_mode}"
            )

    def _render_articulation_word_simple(self) -> np.ndarray:
        word = np.zeros((0, 2), dtype=np.float32)
        boundaries: List[int] = []
        print(f"[WaveToy Word] word render started • mode simple • phoneme count {len(self.articulation_chain_items)}")
        for index, item in enumerate(self.articulation_chain_items):
            clip = self._render_articulation_with_source(item.phoneme_for_render())
            gap_after_ms = self._word_gap_after_ms(item, index)
            if index < len(self.articulation_chain_items) - 1:
                crossfade_ms = self._word_crossfade_ms(int(item.crossfade_ms), item, self.articulation_chain_items[index + 1])
            else:
                crossfade_ms = 0
            word = self._append_word_clip(word, clip, crossfade_ms, gap_after_ms, boundaries)
        word = self._smooth_word_boundaries(word, boundaries)
        word = self._fade_word_edges(word)
        word = normalize_audio(word).astype(np.float32)
        self._diagnose_word_boundaries(word, boundaries)
        print(f"[WaveToy Word] final word duration {len(word) / SAMPLE_RATE:.3f} s")
        return word

    def _render_interpolated_transition_clip(self, left: ArticulationChainItem, right: ArticulationChainItem, transition_ms: int) -> np.ndarray:
        transition_ms = int(np.clip(transition_ms, 0, 250))
        if transition_ms <= 0:
            return np.zeros((0, 2), dtype=np.float32)
        frame_ms = ARTICULATION_MOTION_FRAME_MS
        frames = max(1, int(math.ceil(transition_ms / frame_ms)))
        frame_samples = max(1, int(frame_ms * SAMPLE_RATE / 1000.0))
        clips: List[np.ndarray] = []
        left_phoneme = left.phoneme_for_render()
        right_phoneme = right.phoneme_for_render()
        for frame in range(frames):
            progress = (frame + 0.5) / frames
            phoneme = interpolate_articulation_phoneme(left_phoneme, right_phoneme, progress)
            phoneme.duration_ms = max(80, frame_ms)
            rendered = self._render_articulation_with_source(phoneme)
            if rendered.size:
                start = min(max(0, len(rendered) // 3), max(0, len(rendered) - frame_samples))
                clips.append(rendered[start:start + frame_samples])
        if not clips:
            return np.zeros((0, 2), dtype=np.float32)
        transition = np.vstack(clips).astype(np.float32)
        target_samples = max(1, int(transition_ms * SAMPLE_RATE / 1000.0))
        transition = transition[:target_samples]
        return transition.astype(np.float32)

    def _build_articulation_envelope_timeline(self) -> Tuple[List[Dict[str, object]], int, List[Dict[str, object]], List[Dict[str, object]]]:
        """Create the shared hold/transition timeline used by motion and continuous audio."""
        segments: List[Dict[str, object]] = []
        stop_events: List[Dict[str, object]] = []
        burst_events: List[Dict[str, object]] = []
        cursor = 0
        for index, item in enumerate(self.articulation_chain_items):
            phoneme = item.phoneme_for_render().clamped()
            hold_ms = max(1, int(item.duration_ms or phoneme.duration_ms))
            hold_start = cursor
            hold_end = cursor + hold_ms
            segments.append({"kind": "hold", "index": index, "start": hold_start, "end": hold_end, "from": phoneme, "to": phoneme})
            if phoneme.phoneme_family == "stop" or phoneme.closure > 0.75:
                stop_params = _stop_burst_parameters(phoneme)
                closure_ms = int(np.clip(hold_ms * (0.18 + phoneme.closure * 0.54), 8, max(9, hold_ms - 1)))
                closure_end = max(hold_start + 1, min(hold_end - 1, hold_start + closure_ms))
                stop_events.append({"index": index, "phoneme": phoneme.name, "start": hold_start, "end": closure_end, "closure": phoneme.closure})
                if stop_params["burst_gain"] > 0.0:
                    burst_ms = int(np.clip(stop_params["burst_ms"], 8, 60))
                    burst_start = max(closure_end, min(hold_end - 1, closure_end))
                    burst_end = min(hold_end, burst_start + burst_ms)
                    burst_events.append({
                        "index": index,
                        "phoneme": phoneme.name,
                        "start": burst_start,
                        "end": burst_end,
                        "strength": phoneme.burst_strength,
                        "gain": stop_params["burst_gain"],
                        "brightness": stop_params["burst_brightness"],
                        "voiced_onset_gain": stop_params["voiced_onset_gain"],
                    })
            cursor = hold_end
            if index < len(self.articulation_chain_items) - 1:
                transition_ms = max(0, int(self._chain_transition_duration_ms(item, self.articulation_chain_items[index + 1])))
                if transition_ms > 0:
                    next_phoneme = self.articulation_chain_items[index + 1].phoneme_for_render().clamped()
                    segments.append({"kind": "transition", "index": index, "start": cursor, "end": cursor + transition_ms, "from": phoneme, "to": next_phoneme, "curve": item.transition_curve})
                    cursor += transition_ms
        return segments, max(cursor, 1), stop_events, burst_events

    def _envelope_state_at_ms(self, elapsed_ms: float, segments: List[Dict[str, object]]) -> Tuple[ArticulationPhoneme, float, float, float, Dict[str, object]]:
        active = segments[-1]
        for segment in segments:
            if float(segment["start"]) <= elapsed_ms <= float(segment["end"]):
                active = segment
                break
        start = float(active["start"])
        end = max(start + 1.0, float(active["end"]))
        local = float(np.clip((elapsed_ms - start) / (end - start), 0.0, 1.0))
        left = active["from"]
        right = active["to"]
        if active["kind"] == "transition":
            curve = str(active.get("curve", ARTICULATION_DEFAULT_TRANSITION_CURVE))
            phoneme = interpolate_articulation_phoneme(left, right, local, curve)
            t = articulation_curve_progress(local, curve)
            left_voiced = _articulation_voiced_gain(left)
            right_voiced = _articulation_voiced_gain(right)
            voiced_gain = float(left_voiced + (right_voiced - left_voiced) * t)
            left_noise = float(articulation_synthesis_debug(left).get("noise_gain", 0.0))
            right_noise = float(articulation_synthesis_debug(right).get("noise_gain", 0.0))
            noise_gain = float(left_noise + (right_noise - left_noise) * t)
        else:
            phoneme = left.clamped()
            voiced_gain = _articulation_voiced_gain(phoneme)
            noise_gain = float(articulation_synthesis_debug(phoneme).get("noise_gain", 0.0))
        closure = float(np.clip(phoneme.closure, 0.0, 1.0))
        return phoneme, float(np.clip(voiced_gain, 0.0, 1.0)), float(np.clip(noise_gain, 0.0, 1.8)), closure, active

    def _shape_continuous_frame(self, mono: np.ndarray, phoneme: ArticulationPhoneme) -> np.ndarray:
        if mono.size <= 4:
            return mono
        spectrum = np.fft.rfft(mono)
        freqs = np.fft.rfftfreq(mono.size, 1.0 / SAMPLE_RATE)
        f1, f2, f3 = formants_from_articulation(phoneme)
        envelope = np.full_like(freqs, 0.30, dtype=np.float64)
        for center, width, gain in ((f1, 135.0, 1.25), (f2, 240.0, 0.88), (f3, 380.0, 0.55)):
            envelope += gain * np.exp(-0.5 * ((freqs - center) / width) ** 2)
        if phoneme.nasal_open > 0.0:
            nasal = float(np.clip(phoneme.nasal_open, 0.0, 1.0))
            nasal_center = 260.0 + (1.0 - phoneme.tongue_frontness) * 180.0
            envelope += nasal * 1.20 * np.exp(-0.5 * ((freqs - nasal_center) / 120.0) ** 2)
            envelope *= 1.0 / (1.0 + nasal * (freqs / 2400.0) ** 2)
        envelope *= 1.0 - 0.22 * phoneme.lip_rounding * np.clip((freqs - 1800.0) / 5000.0, 0.0, 1.0)
        return np.fft.irfft(spectrum * envelope, n=mono.size)

    def _render_articulation_word_continuous(self) -> np.ndarray:
        segments, total_ms, stop_events, burst_events = self._build_articulation_envelope_timeline()
        frame_ms = ARTICULATION_MOTION_FRAME_MS
        frame_samples = max(1, int(round(frame_ms * SAMPLE_RATE / 1000.0)))
        total_samples = max(1, int(round(total_ms * SAMPLE_RATE / 1000.0)))
        frame_count = max(1, int(math.ceil(total_samples / frame_samples)))
        print(f"[WaveToy Envelope] render mode={ARTICULATION_WORD_RENDER_CONTINUOUS} phoneme_count={len(self.articulation_chain_items)} total_envelope_ms={total_ms} frame_count={frame_count}")
        for segment in segments:
            if segment["kind"] == "transition":
                print(f"[WaveToy Envelope] transition {segment['from'].name}->{segment['to'].name} start_ms={segment['start']} end_ms={segment['end']} duration_ms={int(segment['end']) - int(segment['start'])}")
        for event in stop_events:
            print(f"[WaveToy Envelope] stop event phoneme={event['phoneme']} start_ms={event['start']} end_ms={event['end']} closure={event['closure']:.2f}")
        for event in burst_events:
            print(
                f"[WaveToy Envelope] burst event phoneme={event['phoneme']} start_ms={event['start']} "
                f"end_ms={event['end']} strength={event['strength']:.2f} "
                f"gain={float(event.get('gain', 0.0)):.3f} brightness={float(event.get('brightness', 0.0)):.3f}"
            )

        rng = np.random.default_rng(33033)
        mono = np.zeros(total_samples, dtype=np.float64)
        voiced_trace = np.zeros(total_samples, dtype=np.float32)
        noise_trace = np.zeros(total_samples, dtype=np.float32)
        closure_trace = np.zeros(total_samples, dtype=np.float32)
        phase = 0.0
        previous_tail = 0.0
        for frame_index in range(frame_count):
            start_sample = frame_index * frame_samples
            end_sample = min(total_samples, start_sample + frame_samples)
            count = end_sample - start_sample
            if count <= 0:
                continue
            center_ms = ((start_sample + end_sample) * 0.5) * 1000.0 / SAMPLE_RATE
            phoneme, voiced_gain, noise_gain, closure, _active = self._envelope_state_at_ms(center_ms, segments)
            t = np.arange(count, dtype=np.float64) / SAMPLE_RATE
            pitch = float(np.clip(phoneme.voice_pitch, 60.0, 880.0))
            phase_step = 2.0 * math.pi * pitch / SAMPLE_RATE
            phases = phase + phase_step * np.arange(count, dtype=np.float64)
            phase = float((phases[-1] + phase_step) % (2.0 * math.pi))
            tone = (np.sin(phases) + 0.28 * np.sin(phases * 2.0) + 0.12 * np.sin(phases * 3.0)) * voiced_gain
            raw_noise = rng.normal(0.0, 1.0, count)
            brightness = float(np.clip((phoneme.noise_color + phoneme.tongue_frontness + (1.0 - phoneme.lip_rounding)) / 3.0, 0.0, 1.0))
            diff_noise = np.concatenate([[previous_tail], raw_noise[:-1]])
            previous_tail = float(raw_noise[-1])
            noise = raw_noise * (0.55 - 0.35 * brightness) + (raw_noise - diff_noise) * (0.25 + 0.45 * brightness)
            if phoneme.phoneme_family == "stop":
                stop_params = _stop_burst_parameters(phoneme)
                noise *= noise_gain * (0.04 + 0.18 * stop_params["air_pressure"]) * (0.25 + 0.75 * (1.0 - stop_params["teeth_gap"]))
                closure_gate = float(np.clip(1.0 - closure * 0.97, 0.02, 1.0))
                voice_gate = float(np.clip(1.0 - closure * 0.70, 0.10, 1.0)) if phoneme.voiced else closure_gate
                frame = self._shape_continuous_frame(tone * 0.62 * voice_gate + noise * 0.16 * closure_gate, phoneme)
            else:
                noise *= noise_gain * (0.18 + 0.82 * phoneme.air_pressure) * (0.35 + 0.65 * phoneme.teeth_gap)
                closure_gate = float(np.clip(1.0 - closure * 0.94, 0.04, 1.0))
                frame = self._shape_continuous_frame((tone * 0.62 + noise * 0.28) * closure_gate, phoneme)
            mono[start_sample:end_sample] += frame
            voiced_trace[start_sample:end_sample] = voiced_gain
            noise_trace[start_sample:end_sample] = noise_gain
            closure_trace[start_sample:end_sample] = closure

        for event in burst_events:
            start_sample = int(round(float(event["start"]) * SAMPLE_RATE / 1000.0))
            end_sample = min(total_samples, int(round(float(event["end"]) * SAMPLE_RATE / 1000.0)))
            if end_sample <= start_sample:
                continue
            phoneme = self.articulation_chain_items[int(event["index"])].phoneme_for_render().clamped()
            count = end_sample - start_sample
            params = _stop_burst_parameters(phoneme)
            burst = _stop_burst_noise(count, phoneme)
            env = np.exp(-np.linspace(0.0, 5.5, count, dtype=np.float64))
            env *= np.linspace(1.0, 0.18, count, dtype=np.float64)
            gain = float(event.get("gain", params["burst_gain"]))
            _log_stop_render(phoneme, {**params, "burst_samples": float(count), "burst_gain": gain}, count)
            mono[start_sample:end_sample] += burst * env * gain * 0.82

        smooth_samples = max(3, int(0.004 * SAMPLE_RATE))
        if smooth_samples % 2 == 0:
            smooth_samples += 1
        if len(mono) > smooth_samples:
            kernel = np.hanning(smooth_samples)
            kernel = kernel / max(1.0e-9, float(np.sum(kernel)))
            mono = np.convolve(mono, kernel, mode="same")
        peak = float(np.max(np.abs(mono))) if mono.size else 0.0
        if peak <= 1.0e-8:
            print("[WaveToy Envelope] warning continuous renderer produced empty audio; falling back to clip crossfade")
            return np.zeros((0, 2), dtype=np.float32)
        mono = mono / peak * 0.82
        audio = np.column_stack([mono, mono]).astype(np.float32)
        audio = self._fade_word_edges(audio)
        print(
            f"[WaveToy Envelope] max_voiced_gain={float(np.max(voiced_trace)):.3f} "
            f"max_noise_gain={float(np.max(noise_trace)):.3f} max_closure={float(np.max(closure_trace)):.3f} "
            f"final_rendered_duration={len(audio) / SAMPLE_RATE:.3f}s"
        )
        return audio.astype(np.float32)

    def _diagnose_word_boundaries(self, audio: np.ndarray, boundaries: List[int]) -> None:
        if audio.size == 0 or not boundaries:
            return
        threshold = 1.0e-4
        minimum_silent = max(1, int(0.005 * SAMPLE_RATE))
        radius = max(minimum_silent, int(0.012 * SAMPLE_RATE))
        envelope = np.max(np.abs(audio), axis=1)
        for boundary in boundaries:
            start = max(0, int(boundary) - radius)
            end = min(len(envelope), int(boundary) + radius)
            if end <= start:
                continue
            silent = envelope[start:end] <= threshold
            longest = current = 0
            for value in silent:
                if bool(value):
                    current += 1
                    longest = max(longest, current)
                else:
                    current = 0
            if longest > minimum_silent:
                print(f"[WaveToy Word] detected silent boundary region {longest * 1000.0 / SAMPLE_RATE:.1f} ms near sample {boundary}")

    def _render_articulation_word_coarticulated(self) -> np.ndarray:
        word = np.zeros((0, 2), dtype=np.float32)
        boundaries: List[int] = []
        print(f"[WaveToy Word] word render started • mode coarticulated overlap • phoneme count {len(self.articulation_chain_items)}")
        clips = [self._render_articulation_with_source(item.phoneme_for_render()) for item in self.articulation_chain_items]
        for index, (item, clip) in enumerate(zip(self.articulation_chain_items, clips)):
            if index == 0:
                word = self._overlap_word_clip(word, clip, 0, boundaries)
                continue
            previous_item = self.articulation_chain_items[index - 1]
            requested_transition_ms = self._chain_transition_duration_ms(previous_item, item)
            effective_samples = self._effective_transition_samples(clips[index - 1], clip, requested_transition_ms, previous_item, item)
            self._log_transition_boundary(
                previous_item,
                item,
                requested_transition_ms,
                effective_samples,
                inserted_silence_samples=0,
                transition_render_samples=0,
                interpolated_articulation_used=False,
            )
            word = self._overlap_word_clip(word, clip, effective_samples, boundaries)
        word = self._smooth_word_boundaries(word, boundaries)
        word = self._fade_word_edges(word)
        word = normalize_audio(word).astype(np.float32)
        self._diagnose_word_boundaries(word, boundaries)
        print(f"[WaveToy Word] final word duration {len(word) / SAMPLE_RATE:.3f} s")
        return word

    def _render_articulation_word_clip_crossfade(self) -> np.ndarray:
        print(f"[WaveToy Envelope] render mode={ARTICULATION_WORD_RENDER_CLIP_CROSSFADE} phoneme_count={len(self.articulation_chain_items)}")
        if self._articulation_smooth_transitions_enabled():
            return self._render_articulation_word_coarticulated()
        return self._render_articulation_word_simple()

    def _render_articulation_word(self) -> np.ndarray:
        mode = self._articulation_word_render_mode()
        if mode == ARTICULATION_WORD_RENDER_CONTINUOUS:
            try:
                audio = self._render_articulation_word_continuous()
                if audio.size > 0:
                    return audio
            except Exception as exc:
                print(f"[WaveToy Envelope] warning continuous renderer failed: {exc}; falling back to {ARTICULATION_WORD_RENDER_CLIP_CROSSFADE}")
            QMessageBox.warning(self, "Create Word", "Continuous Mouth Motion could not render audio, so WaveToy used Clip Crossfade instead.")
            return self._render_articulation_word_clip_crossfade()
        return self._render_articulation_word_clip_crossfade()

    def _render_word_audio_for_current_chain(self) -> np.ndarray:
        if not self.articulation_chain_items:
            QMessageBox.information(self, "Create Word", "Add at least one phoneme to the Articulation Chain first.")
            return np.zeros((0, 2), dtype=np.float32)
        self.articulation_word_render_audio = self._render_articulation_word()
        self.articulation_last_word_render_created_at = time.time()
        self.articulation_last_word_render_path = None
        self._update_articulation_word_status()
        return self.articulation_word_render_audio

    def _create_articulation_word(self, checked: bool = False) -> np.ndarray:
        del checked
        audio = self._render_word_audio_for_current_chain()
        if audio.size == 0:
            return audio
        default_name = (self._speech_display_sequence_for_chain().replace(" + ", "").lower() or "word")
        name, ok = QInputDialog.getText(self, "Create Word", "Name this Speech Assets word:", text=default_name)
        if not ok:
            name = default_name
        name = name.strip() or default_name
        word_item = self._create_rendered_speech_bin_item("word", name=name)
        if word_item is not None:
            self.timeline_selected_speech_item_id = word_item.id
            self._timeline_refresh_speech_bin_cards()
            message = f"Word ready: {word_item.name} • {word_item.duration_seconds:.2f}s • {self._chain_custom_transition_summary()} • saved to Speech Assets."
            self.articulation_word_status_label.setText(message)
            self._timeline_debug(message)
        return audio

    def _play_articulation_word(self, checked: bool = False) -> None:
        del checked
        if self.articulation_word_render_audio.size == 0:
            audio = self._render_word_audio_for_current_chain()
            if audio.size == 0:
                return
        self._start_articulation_motion(loop=False, speed=1.0, audio=self.articulation_word_render_audio)

    def _export_articulation_word(self, checked: bool = False) -> None:
        del checked
        if self.articulation_word_render_audio.size == 0:
            audio = self._create_articulation_word(checked=False)
            if audio.size == 0:
                return
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        chain_name = "_".join(item.phoneme.name.lower() for item in self.articulation_chain_items[:6]) or "word"
        safe_name = "".join(ch if ch.isalnum() or ch in {"_", "-"} else "_" for ch in chain_name)
        filename, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Export Created Word",
            f"wave_toy_word_{safe_name}_{timestamp}.wav",
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
            save_audio_file(path, self.articulation_word_render_audio)
            sidecar = path.with_suffix(path.suffix + ".wave-toy-word.json")
            data = ArticulationChain(
                items=self.articulation_chain_items,
                last_word_render_path=str(path),
                last_word_render_created_at=self.articulation_last_word_render_created_at,
                word_render_settings=dict(self.articulation_word_render_settings),
            ).to_json_dict()
            data.update(
                {
                    "version": 1,
                    "sample_rate": SAMPLE_RATE,
                    "duration_seconds": len(self.articulation_word_render_audio) / SAMPLE_RATE,
                    "notes": "Created Word metadata stores articulation snapshots and source paths only; raw audio is not embedded.",
                }
            )
            sidecar.write_text(json.dumps(data, indent=2), encoding="utf-8")
            self.articulation_last_word_render_path = path
            self._update_articulation_word_status()
            QMessageBox.information(self, "Word Exported", f"Saved created word:\n{path}\n\nSaved word metadata:\n{sidecar}")
        except Exception as exc:
            QMessageBox.warning(self, "Could not export word", str(exc))

    def _play_articulation_chain(self, checked: bool = False) -> None:
        del checked
        if not self.articulation_chain_items:
            QMessageBox.information(self, "Articulation Chain", "Add at least one phoneme to the chain first.")
            return
        rendered = [self._render_articulation_with_source(item.phoneme_for_render()) for item in self.articulation_chain_items]
        audio = np.vstack([clip for clip in rendered if clip.size]) if rendered else np.zeros((0, 2), dtype=np.float32)
        self._play_audio_array(audio)
        self._start_articulation_motion(loop=False, speed=1.0)

    def _save_articulation_chain(self, checked: bool = False) -> None:
        del checked
        data = ArticulationChain(
            items=self.articulation_chain_items,
            last_word_render_path=str(self.articulation_last_word_render_path) if self.articulation_last_word_render_path else None,
            last_word_render_created_at=self.articulation_last_word_render_created_at,
            word_render_settings=dict(self.articulation_word_render_settings),
            syllable_markers=list(self.articulation_syllable_markers),
            phrase_markers=list(self.articulation_phrase_markers),
        ).to_json_dict()
        self.articulation_chain_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        QMessageBox.information(self, "Articulation Chain", f"Saved {len(self.articulation_chain_items)} chain phoneme(s) to {self.articulation_chain_path}.")

    def _load_articulation_chain(self, checked: bool = False) -> None:
        del checked
        if not self.articulation_chain_path.exists():
            QMessageBox.information(self, "Articulation Chain", "No saved articulation_chain.json file was found yet.")
            return
        data = json.loads(self.articulation_chain_path.read_text(encoding="utf-8"))
        self.articulation_chain_items = [ArticulationChainItem.from_json_dict(item) for item in data.get("items", []) if isinstance(item, dict)]
        self.articulation_selected_chain_index = 0 if self.articulation_chain_items else None
        self.articulation_last_word_render_path = Path(data["last_word_render_path"]) if data.get("last_word_render_path") else None
        self.articulation_last_word_render_created_at = data.get("last_word_render_created_at") if isinstance(data.get("last_word_render_created_at"), (int, float)) else None
        if isinstance(data.get("word_render_settings"), dict):
            self.articulation_word_render_settings.update(data["word_render_settings"])
        self.articulation_syllable_markers = list(data.get("syllable_markers", [])) if isinstance(data.get("syllable_markers", []), list) else []
        self.articulation_phrase_markers = list(data.get("phrase_markers", [])) if isinstance(data.get("phrase_markers", []), list) else []
        if self.articulation_smooth_transitions_checkbox is not None:
            self.articulation_smooth_transitions_checkbox.setChecked(bool(self.articulation_word_render_settings.get("smooth_mouth_transitions", True)))
        if self.articulation_word_render_mode_combo is not None:
            mode = str(self.articulation_word_render_settings.get("word_render_mode", ARTICULATION_WORD_RENDER_CONTINUOUS))
            self.articulation_word_render_mode_combo.setCurrentText(mode if mode in ARTICULATION_WORD_RENDER_MODES else ARTICULATION_WORD_RENDER_CONTINUOUS)
        self.articulation_word_render_audio = np.zeros((0, 2), dtype=np.float32)
        self._refresh_articulation_chain_cards()
        self._refresh_articulation_motion_timeline()

    def _select_vowel_preset(self, preset_name: str, play: bool = False) -> None:
        data = VOWEL_PRESETS[preset_name]
        pitch = self._settings_from_ui().pitch_start_hz if hasattr(self, "pitch_start") else 220.0
        phoneme = ArticulationPhoneme.from_json_dict({**data, "name": preset_name, "phoneme_family": "vowel", "voiced": True, "voice_pitch": pitch, "voice_strength": 0.65, "duration_ms": 500})
        self._set_articulation_ui_from_phoneme(phoneme)
        if play:
            self._play_phoneme_preview()

    def _select_consonant_preset(self, preset_name: str, preset_data: Dict[str, object], play: bool = False) -> None:
        pitch = self._settings_from_ui().pitch_start_hz if hasattr(self, "pitch_start") else 220.0
        data = {**preset_data, "name": preset_name, "voice_pitch": pitch, "voice_strength": 0.62}
        phoneme = ArticulationPhoneme.from_json_dict(data)
        self._set_articulation_ui_from_phoneme(phoneme)
        if play:
            self._play_phoneme_preview()

    def _play_audio_array(self, audio: np.ndarray) -> None:
        if sd is not None:
            try:
                sd.stop()
                sd.play(audio, SAMPLE_RATE, blocking=False)
                return
            except Exception:
                pass
        old_audio = self.current_audio
        try:
            self.current_audio = audio
            ok, message = self._play_with_system_player()
        finally:
            self.current_audio = old_audio
        if not ok:
            self._show_playback_warning(message)

    def _play_phoneme_preview(self, checked: bool = False) -> None:
        del checked
        self.current_phoneme = self._phoneme_from_articulation_ui()
        self.phoneme_preview_audio = self._render_articulation_with_source(self.current_phoneme)
        self._play_audio_array(self.phoneme_preview_audio)
        if self.phoneme_loop_enabled:
            duration_ms = max(100, int((len(self.phoneme_preview_audio) / SAMPLE_RATE) * 1000))
            self.phoneme_loop_timer.start(duration_ms)

    def _toggle_phoneme_loop(self, checked: bool = False) -> None:
        del checked
        self.phoneme_loop_enabled = not self.phoneme_loop_enabled
        if self.phoneme_loop_enabled:
            self._play_phoneme_preview()
        else:
            self._stop_phoneme_preview()

    def _articulation_loop_tick(self) -> None:
        if self.phoneme_loop_enabled:
            self._play_phoneme_preview()

    def _stop_phoneme_preview(self, checked: bool = False) -> None:
        del checked
        self.phoneme_loop_enabled = False
        self.phoneme_loop_timer.stop()
        if sd is not None:
            try:
                sd.stop()
            except Exception:
                pass

    def _save_current_phoneme(self, checked: bool = False) -> None:
        del checked
        phoneme = self._phoneme_from_articulation_ui()
        name, ok = QInputDialog.getText(self, "Save Phoneme", "Friendly phoneme name:", text=phoneme.name.lower())
        if not ok or not name.strip():
            return
        phoneme.name = name.strip()
        self.current_phoneme = phoneme.clamped()
        self.phonemes_dir.mkdir(parents=True, exist_ok=True)
        path = self._phoneme_path(self.current_phoneme)
        path.write_text(json.dumps(self.current_phoneme.to_json_dict(), indent=2), encoding="utf-8")
        self._load_saved_phonemes()
        self._refresh_phoneme_cards()
        self._update_articulation_preview(regenerate=True)

    def _refresh_phoneme_cards(self) -> None:
        if self.phoneme_cards_widget is None:
            return
        layout = self.phoneme_cards_widget.layout()
        if layout is None:
            layout = QVBoxLayout(self.phoneme_cards_widget)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(10)
        else:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
        if not self.saved_phonemes:
            empty = QLabel("Save a vowel or consonant to make a reusable phoneme card.")
            empty.setWordWrap(True)
            empty.setObjectName("symbolHint")
            layout.addWidget(empty)
            layout.addStretch(1)
            return
        for phoneme in self.saved_phonemes:
            layout.addWidget(self._make_phoneme_card(phoneme))
        layout.addStretch(1)

    def _make_phoneme_card(self, phoneme: ArticulationPhoneme) -> QWidget:
        card = QWidget()
        card.setObjectName("phonemeCard")
        card.setMinimumHeight(72)
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        card.setStyleSheet(f"QWidget#phonemeCard {{ background: {phoneme.preview_color}; border-radius: 10px; }}")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        header = QHBoxLayout()
        header.setSpacing(10)
        ipa = QLabel(f"/{phoneme.ipa}/")
        ipa.setObjectName("phonemeCardIpa")
        ipa.setAlignment(Qt.AlignCenter)
        ipa.setMinimumWidth(66)
        title = QLabel(phoneme.name)
        title.setObjectName("phonemeCardTitle")
        title.setWordWrap(True)
        summary = QLabel(articulation_summary(phoneme))
        summary.setObjectName("phonemeCardSummary")
        summary.setWordWrap(True)
        source_badge = QLabel(articulation_source_badge(phoneme.source_mode, phoneme.source_wave_id, phoneme.source_audio_path))
        source_badge.setObjectName("articulationIpaBadge")
        source_badge.setAlignment(Qt.AlignCenter)
        title_stack = QVBoxLayout()
        title_stack.setSpacing(2)
        title_stack.addWidget(title)
        title_stack.addWidget(summary)
        title_stack.addWidget(source_badge)

        play_button = QPushButton("▶ Play")
        play_button.setObjectName("phonemeCardPrimaryAction")
        play_button.setMinimumHeight(WaveToySizing.MIN_TOUCH_TARGET)
        play_button.clicked.connect(lambda checked=False, p=phoneme: self._play_saved_phoneme(p))
        delete_button = QPushButton("🗑 Delete")
        delete_button.setObjectName("phonemeCardDangerAction")
        delete_button.setMinimumHeight(WaveToySizing.MIN_TOUCH_TARGET)
        delete_button.clicked.connect(lambda checked=False, p=phoneme: self._delete_saved_phoneme(p))

        header.addWidget(ipa)
        header.addLayout(title_stack, 1)
        header.addWidget(play_button)
        header.addWidget(delete_button)
        layout.addLayout(header)

        tools = QHBoxLayout()
        tools.setSpacing(8)
        secondary_actions = (
            ("Load", lambda checked=False, p=phoneme: self._load_saved_phoneme(p)),
            ("Rename", lambda checked=False, p=phoneme: self._rename_saved_phoneme(p)),
            ("Duplicate", lambda checked=False, p=phoneme: self._duplicate_saved_phoneme(p)),
        )
        for text, callback in secondary_actions:
            button = QPushButton(text)
            button.setObjectName("phonemeCardSecondaryAction")
            button.setMinimumHeight(WaveToySizing.MIN_TOUCH_TARGET)
            button.clicked.connect(callback)
            tools.addWidget(button)
        layout.addLayout(tools)
        return card

    def _play_saved_phoneme(self, phoneme: ArticulationPhoneme) -> None:
        self._play_audio_array(self._render_articulation_with_source(phoneme))

    def _load_saved_phoneme(self, phoneme: ArticulationPhoneme) -> None:
        self._set_articulation_ui_from_phoneme(phoneme)

    def _rename_saved_phoneme(self, phoneme: ArticulationPhoneme) -> None:
        new_name, ok = QInputDialog.getText(self, "Rename Phoneme", "New friendly name:", text=phoneme.name)
        if not ok or not new_name.strip():
            return
        old_path = self._phoneme_path(phoneme)
        phoneme.name = new_name.strip()
        new_path = self._phoneme_path(phoneme)
        self.phonemes_dir.mkdir(parents=True, exist_ok=True)
        new_path.write_text(json.dumps(phoneme.to_json_dict(), indent=2), encoding="utf-8")
        if old_path.exists() and old_path != new_path:
            old_path.unlink()
        self._load_saved_phonemes()
        self._refresh_phoneme_cards()

    def _duplicate_saved_phoneme(self, phoneme: ArticulationPhoneme) -> None:
        duplicate = ArticulationPhoneme.from_json_dict(phoneme.to_json_dict())
        duplicate.name = f"{phoneme.name}_copy"
        self.phonemes_dir.mkdir(parents=True, exist_ok=True)
        self._phoneme_path(duplicate).write_text(json.dumps(duplicate.to_json_dict(), indent=2), encoding="utf-8")
        self._load_saved_phonemes()
        self._refresh_phoneme_cards()

    def _delete_saved_phoneme(self, phoneme: ArticulationPhoneme) -> None:
        path = self._phoneme_path(phoneme)
        if path.exists():
            path.unlink()
        self._load_saved_phonemes()
        self._refresh_phoneme_cards()

    def _make_story_button(self, icon: str, label: str, color: str, callback) -> QPushButton:
        button = QPushButton(f"{icon}\n{label}")
        button.setObjectName("storyTransportButton")
        button.setMinimumSize(QSize(150, 76))
        button.setCursor(Qt.PointingHandCursor)
        button.setToolTip(label)
        button.setStyleSheet(
            f"""
            QPushButton#storyTransportButton {{
                background: {color};
                color: #1d1d1d;
                border: 1px solid rgba(0, 0, 0, 0.18);
                border-radius: 10px;
                font-size: 15px;
                font-weight: 900;
                min-height: 76px;
                padding: 8px 14px;
            }}
            QPushButton#storyTransportButton:pressed {{
                padding-top: 12px;
            }}
            """
        )
        button.clicked.connect(callback)
        return button

    def _timeline_debug(self, message: str) -> None:
        print(f"[WaveToy Timeline] {message}")
        if getattr(self, "timeline_status_label", None) is not None:
            self.timeline_status_label.setText(message)

    def _timeline_stretch_debug(self, message: str) -> None:
        print(f"[WaveToy Stretch] {message}")
        if getattr(self, "timeline_status_label", None) is not None:
            self.timeline_status_label.setText(message)


    def _build_graphical_editor_tab(self) -> None:
        if self.tabs is None:
            return
        tab = WaveToyScrollArea(scroll_speed=0.92, content_drag_scroll=False)
        tab.setObjectName("graphicalEditorTab")
        tab.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        page = QWidget()
        page.setObjectName("graphicalEditorPage")
        outer = QVBoxLayout(page)
        outer.setContentsMargins(16, 12, 16, 18)
        outer.setSpacing(12)

        title = QLabel("Graphical Editor")
        title.setObjectName("title")
        subtitle = QLabel("Visual-first sound building: drag wave layers, stereo dots, pitch points, and the mouth model. Sliders stay available as advanced fallback controls.")
        subtitle.setObjectName("subtitle")
        subtitle.setWordWrap(True)
        self.graphical_status_label = QLabel("Graphical Editor shares the same controls as Classic Controls, Wave Explorer, and Articulation Lab — no duplicate recipe state.")
        self.graphical_status_label.setObjectName("dashboardSummary")
        self.graphical_status_label.setWordWrap(True)
        self.graphical_status_label.setAlignment(Qt.AlignCenter)
        outer.addWidget(title)
        outer.addWidget(subtitle)
        outer.addWidget(self.graphical_status_label)

        outer.addWidget(self._graphical_workflow_section(
            "1. Source Wave",
            "Drag loudness handles on each layer card. Add, duplicate, mute, solo, and remove waves here; Classic Controls mix sliders update immediately.",
            self._build_graphical_wave_section(),
            "Advanced: Classic Controls",
            lambda checked=False: self._show_named_tab("Classic Controls"),
            expanded=True,
        ))
        outer.addWidget(self._graphical_workflow_section(
            "2. Stereo Field",
            "Drag start/end dots across the ears to update whole-mix Stereo Placement. Use the mouse wheel over the field for stereo width.",
            self._build_graphical_stereo_section(),
            "Advanced: Wave Explorer",
            lambda checked=False: self._show_named_tab("Wave Explorer"),
            expanded=True,
        ))
        outer.addWidget(self._graphical_workflow_section(
            "3. Pitch Motion",
            "Drag pitch start/end points on an octave grid. The curve writes to the same pitch sliders used by Classic Controls and the tuning map.",
            self._build_graphical_pitch_section(),
            "Advanced: Pitch Tools",
            lambda checked=False: self._show_named_tab("Classic Controls"),
            expanded=True,
        ))
        outer.addWidget(self._graphical_workflow_section(
            "4. Texture / Effects",
            "Preview-only blocks show the signal order for this phase. Toggle and intensity controls still use existing Sound Modules sliders.",
            self._build_graphical_sound_magic_section(),
            "Advanced: Texture / Effects",
            lambda checked=False: self._show_named_tab("Classic Controls"),
            expanded=False,
        ))
        outer.addWidget(self._graphical_workflow_section(
            "5. Vocal Tract",
            "Drag tongue, mouth/lips, airflow, click the nose, or click the voice bubble. Articulation Lab sliders and phoneme preview stay synchronized.",
            self._build_graphical_vocal_section(),
            "Advanced: Articulation Lab",
            lambda checked=False: self._show_named_tab("Articulation Lab"),
            expanded=True,
        ))
        outer.addWidget(self._graphical_workflow_section(
            "6. Articulation Timeline",
            "Drag phoneme block edges and transition zones, scrub the playhead, and preview the mouth motion. Create Word uses these edited chain values.",
            self._build_graphical_chain_section(),
            "Advanced: Articulation Timeline",
            lambda checked=False: self._show_named_tab("Articulation Lab"),
            expanded=True,
        ))
        outer.addWidget(self._graphical_workflow_section(
            "7. Send to Timeline",
            "Preview-only handoff panel: use existing Speech Assets, Audio Assets, and Timeline buttons to place rendered sounds without changing those workflows.",
            self._build_graphical_timeline_section(),
            "Open Timeline",
            lambda checked=False: self._show_named_tab("Timeline"),
            expanded=False,
        ))
        outer.addStretch(1)
        tab.setWidget(page)
        self.tabs.insertTab(max(0, self.tabs.count() - 1), tab, "Graphical Editor")
        self._refresh_graphical_editor()

    def _graphical_workflow_section(self, title: str, body: str, content: QWidget, button_text: str, callback, *, expanded: bool) -> QWidget:
        wrapper = QWidget()
        wrapper.setObjectName("graphicalWorkflowCard")
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(12, 10, 12, 12)
        layout.setSpacing(8)
        header = QLabel(title)
        header.setObjectName("dashboardExplorerTitle")
        header.setWordWrap(True)
        hint = QLabel(body)
        hint.setObjectName("symbolHint")
        hint.setWordWrap(True)
        shortcut = QPushButton(button_text)
        shortcut.setObjectName("workspaceToolbarButton")
        shortcut.setMinimumHeight(38)
        shortcut.clicked.connect(callback)
        top = QHBoxLayout()
        top.addWidget(header, 1)
        top.addWidget(shortcut, 0)
        box = QWidget()
        box_layout = QVBoxLayout(box)
        box_layout.setContentsMargins(0, 0, 0, 0)
        box_layout.setSpacing(8)
        box_layout.addWidget(hint)
        box_layout.addWidget(content)
        layout.addLayout(top)
        layout.addWidget(CollapsibleSection("Show / hide direct controls", box, expanded=expanded))
        return wrapper

    def _build_graphical_wave_section(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        toolbar = QWidget()
        toolbar.setObjectName("graphicalWaveToolbar")
        toolbar_layout = FlowLayout(toolbar, margin=0, spacing=8)
        add_button = QPushButton("➕ Add Wave Layer")
        duplicate_button = QPushButton("⧉ Duplicate Loudest Layer")
        all_button = QPushButton("🌈 Clear Solo")
        for button in (add_button, duplicate_button, all_button):
            button.setObjectName("workspaceToolbarButton")
            button.setMinimumHeight(52)
            button.setMinimumWidth(156)
            button.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
            toolbar_layout.addWidget(button)
        add_button.clicked.connect(self._graphical_add_wave_layer)
        duplicate_button.clicked.connect(self._graphical_duplicate_loudest_wave)
        all_button.clicked.connect(self._clear_solo)
        layout.addWidget(toolbar)
        self.graphical_wave_layer_list = QWidget()
        self.graphical_wave_layer_list.setObjectName("graphicalLayerList")
        self.graphical_wave_layer_list.setLayout(QVBoxLayout())
        self.graphical_wave_layer_list.layout().setContentsMargins(0, 0, 0, 0)
        self.graphical_wave_layer_list.layout().setSpacing(8)
        layout.addWidget(self.graphical_wave_layer_list)
        return panel

    def _build_graphical_stereo_section(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        self.graphical_stereo_canvas = GraphicalStereoFieldCanvas()
        self.graphical_stereo_canvas.panEdited.connect(self._graphical_set_stereo_pan)
        self.graphical_stereo_canvas.widthEdited.connect(self._graphical_set_stereo_width)
        layout.addWidget(self.graphical_stereo_canvas)
        return panel

    def _build_graphical_pitch_section(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        self.graphical_pitch_canvas = GraphicalPitchCurveCanvas()
        self.graphical_pitch_canvas.pitchEdited.connect(self._graphical_set_pitch_values)
        layout.addWidget(self.graphical_pitch_canvas)
        return panel

    def _build_graphical_sound_magic_section(self) -> QWidget:
        panel = QWidget()
        layout = QGridLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        blocks = [
            ("🌫 Noise Texture", "preview-only: articulation/noise sources"),
            ("✨ Shimmer", "preview-only roadmap block"),
            ("😴 Stretch", "editable via existing Effect Nap sliders"),
            ("Filter / Modulation", "preview-only roadmap block"),
        ]
        for index, (name, note) in enumerate(blocks):
            block = QLabel(f"{name}\n{note}")
            block.setObjectName("graphicalEffectBlock")
            block.setWordWrap(True)
            block.setAlignment(Qt.AlignCenter)
            block.setMinimumHeight(86)
            layout.addWidget(block, 0, index)
        return panel

    def _build_graphical_vocal_section(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        self.graphical_vocal_canvas = VocalTractCanvas()
        self.graphical_vocal_canvas.setMinimumHeight(430)
        self.graphical_vocal_canvas.set_editable(True)
        self.graphical_vocal_canvas.articulationEdited.connect(self._graphical_set_articulation_value)
        layout.addWidget(self.graphical_vocal_canvas)
        return panel

    def _build_graphical_chain_section(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        self.graphical_chain_canvas = ArticulationTimelineCanvas()
        self.graphical_chain_canvas.durationEdited.connect(self._graphical_set_chain_duration)
        self.graphical_chain_canvas.transitionEdited.connect(self._graphical_set_chain_transition)
        self.graphical_chain_canvas.scrubbed.connect(self._graphical_scrub_chain)
        self.graphical_chain_canvas.blockSelected.connect(self._select_articulation_chain_item)
        layout.addWidget(self.graphical_chain_canvas)
        curve_row = QHBoxLayout()
        curve_row.addWidget(QLabel("Transition curve:"))
        for curve in ARTICULATION_TRANSITION_CURVES:
            button = QPushButton(curve)
            button.setMinimumHeight(36)
            button.clicked.connect(lambda checked=False, curve_name=curve: self._graphical_set_selected_chain_curve(curve_name))
            curve_row.addWidget(button)
        layout.addLayout(curve_row)
        self.graphical_chain_mouth_canvas = VocalTractCanvas()
        self.graphical_chain_mouth_canvas.setMinimumHeight(310)
        layout.addWidget(self.graphical_chain_mouth_canvas)
        return panel

    def _build_graphical_timeline_section(self) -> QWidget:
        panel = QWidget()
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        for text, callback in (
            ("Open Timeline", lambda checked=False: self._show_named_tab("Timeline")),
            ("Send Current Phoneme", self._send_current_phoneme_to_timeline),
            ("Send Chain", self._send_articulation_chain_to_timeline),
        ):
            button = QPushButton(text)
            button.setMinimumHeight(46)
            button.clicked.connect(callback)
            layout.addWidget(button)
        return panel

    def _show_named_tab(self, tab_text: str) -> None:
        if self.tabs is None:
            return
        for index in range(self.tabs.count()):
            if self.tabs.tabText(index) == tab_text:
                self.tabs.setCurrentIndex(index)
                return

    def _refresh_graphical_editor(self) -> None:
        self._refresh_graphical_wave_layers()
        if self.graphical_stereo_canvas is not None and hasattr(self, "pan_start_slider"):
            self.graphical_stereo_canvas.set_state(
                self.pan_start_slider.value() / (100.0 * PERCENT_SLIDER_SCALE),
                self.pan_end_slider.value() / (100.0 * PERCENT_SLIDER_SCALE),
                self.width_slider.value() / (100.0 * PERCENT_SLIDER_SCALE),
                self.auto_pan_depth_slider.value() / (100.0 * PERCENT_SLIDER_SCALE),
            )
        if self.graphical_pitch_canvas is not None and hasattr(self, "pitch_start"):
            self.graphical_pitch_canvas.set_state(self.pitch_start.value(), self.pitch_end.value(), abs(self.pitch_end.value() - self.pitch_start.value()) / float(48 * MIDI_SLIDER_SCALE))
        if self.graphical_vocal_canvas is not None and hasattr(self, "current_phoneme"):
            self.graphical_vocal_canvas.set_phoneme(self.current_phoneme)
        self._refresh_graphical_chain_editor()
        if self.graphical_status_label is not None:
            self.graphical_status_label.setText("Two-way sync active: graphical edits write sliders/model; slider, preset, recipe, and chain refreshes repaint this tab.")

    def _refresh_graphical_wave_layers(self) -> None:
        if self.graphical_wave_layer_list is None or self.graphical_wave_layer_list.layout() is None:
            return
        layout = self.graphical_wave_layer_list.layout()
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self.graphical_wave_canvases.clear()
        self.graphical_wave_cards.clear()
        if self.graphical_selected_wave_id not in self.wave_row_order:
            self.graphical_selected_wave_id = self.wave_row_order[0] if self.wave_row_order else None
        solo_wave = self._solo_wave_from_ui() if hasattr(self, "wave_solo_buttons") else None
        for wave_id in list(self.wave_row_order):
            row = GraphicalWaveCard(wave_id)
            row.waveSelected.connect(self._graphical_select_wave)
            muted = self.wave_mute_buttons.get(wave_id).isChecked() if wave_id in self.wave_mute_buttons else False
            soloed = solo_wave == wave_id
            self._set_graphical_wave_card_visuals(row, wave_id, muted, soloed)
            row_layout = QVBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(0)

            actions = GraphicalWaveCard(wave_id)
            actions.setObjectName("graphicalWaveCardHeader")
            actions.waveSelected.connect(self._graphical_select_wave)
            actions_layout = FlowLayout(actions, margin=10, spacing=8)
            mute = QPushButton("🎵 Mute")
            solo = QPushButton("⭐ Solo")
            duplicate = QPushButton("📄 Copy")
            remove = QPushButton("🗑 Remove")
            for button in (mute, solo, duplicate, remove):
                button.setObjectName("workspaceToolbarButton")
                button.setMinimumSize(QSize(96, 48))
                button.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
                actions_layout.addWidget(button)
            mute.setCheckable(True)
            mute.setChecked(muted)
            solo.setCheckable(True)
            solo.setChecked(soloed)
            mute.clicked.connect(lambda checked=False, wt=wave_id: self._graphical_toggle_wave_mute(wt))
            solo.clicked.connect(lambda checked=False, wt=wave_id: self._set_wave_solo(wt, True))
            duplicate.clicked.connect(lambda checked=False, wt=wave_id: self._graphical_duplicate_wave(wt))
            remove.clicked.connect(lambda checked=False, wt=wave_id: self._graphical_remove_wave(wt))
            row_layout.addWidget(actions)

            body = GraphicalWaveCard(wave_id)
            body.setObjectName("graphicalWaveCardBody")
            body.waveSelected.connect(self._graphical_select_wave)
            body_layout = QVBoxLayout(body)
            body_layout.setContentsMargins(10, 10, 10, 10)
            body_layout.setSpacing(0)
            canvas = GraphicalWaveLayerCanvas(wave_id)
            canvas.levelEdited.connect(self._graphical_set_wave_levels)
            canvas.waveSelected.connect(self._graphical_select_wave)
            label = wave_label_for(self._settings_from_ui(), wave_id) if hasattr(self, "note_combo") else wave_id
            shape = wave_shape_for(self._settings_from_ui(), wave_id) if hasattr(self, "note_combo") else wave_id
            start_db = self.wave_start_sliders[wave_id].value() / DB_SLIDER_SCALE
            end_db = self.wave_end_sliders[wave_id].value() / DB_SLIDER_SCALE
            canvas.set_state(label, shape, start_db, end_db, muted, soloed)
            self.graphical_wave_canvases[wave_id] = canvas
            self.graphical_wave_cards[wave_id] = row
            body_layout.addWidget(canvas, 1)
            row_layout.addWidget(body, 1)
            layout.addWidget(row)

    def _refresh_graphical_chain_editor(self) -> None:
        selected_index = self.articulation_selected_chain_index
        if isinstance(selected_index, int) and 0 <= selected_index < len(self.articulation_chain_items):
            selected = selected_index
        else:
            selected = None
        if self.graphical_chain_canvas is not None:
            self.graphical_chain_canvas.set_items(self.articulation_chain_items, selected)
        if self.graphical_chain_mouth_canvas is not None:
            if selected is not None:
                p = self.articulation_chain_items[selected].phoneme_for_render()
                name = p.name
            else:
                p = self.current_phoneme
                name = p.name
            self.graphical_chain_mouth_canvas.set_motion_state(p, name, playhead_fraction=0.0)

    def _graphical_set_wave_levels(self, wave_id: str, start_db: float, end_db: float) -> None:
        if wave_id not in self.wave_start_sliders or wave_id not in self.wave_end_sliders:
            return
        self.wave_start_sliders[wave_id].setValue(int(round(float(start_db) * DB_SLIDER_SCALE)))
        self.wave_end_sliders[wave_id].setValue(int(round(float(end_db) * DB_SLIDER_SCALE)))
        self._update_wave_envelope_labels(wave_id)
        self._schedule_generate("graphical_wave_level")
        self._refresh_graphical_editor()

    def _graphical_add_wave_layer(self, checked: bool = False) -> None:
        del checked
        self._add_user_wave_row()
        self._refresh_graphical_editor()

    def _graphical_duplicate_loudest_wave(self, checked: bool = False) -> None:
        del checked
        if not self.wave_row_order:
            return
        loudest = max(self.wave_row_order, key=lambda wt: max(self.wave_start_sliders[wt].value(), self.wave_end_sliders[wt].value()))
        self._graphical_duplicate_wave(loudest)

    def _graphical_duplicate_wave(self, wave_id: str) -> None:
        if len(self.wave_row_order) >= MAX_WAVE_ROWS or wave_id not in self.wave_start_sliders:
            return
        before = set(self.wave_row_order)
        self._add_user_wave_row()
        new_ids = [wt for wt in self.wave_row_order if wt not in before]
        if not new_ids:
            return
        new_id = new_ids[-1]
        for src, dst in ((self.wave_start_sliders, self.wave_start_sliders), (self.wave_end_sliders, self.wave_end_sliders), (self.wave_time_sliders, self.wave_time_sliders), (self.wave_pan_sliders, self.wave_pan_sliders), (self.wave_width_sliders, self.wave_width_sliders), (self.wave_dance_sliders, self.wave_dance_sliders)):
            dst[new_id].setValue(src[wave_id].value())
        if wave_id in self.wave_shape_combos and new_id in self.wave_shape_combos:
            shape_index = self.wave_shape_combos[new_id].findData(wave_shape_for(self._settings_from_ui(), wave_id))
            self.wave_shape_combos[new_id].setCurrentIndex(max(0, shape_index))
        self._schedule_generate("graphical_duplicate_wave")
        self._refresh_graphical_editor()

    def _graphical_wave_card_object_name(self, wave_id: str, muted: bool, soloed: bool) -> str:
        if wave_id == self.graphical_selected_wave_id:
            return "waveCardSelected"
        if soloed:
            return "waveCardSolo"
        if muted:
            return "waveCardMuted"
        return "waveCard"

    def _set_graphical_wave_card_visuals(self, card: QWidget, wave_id: str, muted: bool, soloed: bool) -> None:
        selected = wave_id == self.graphical_selected_wave_id
        card.setObjectName(self._graphical_wave_card_object_name(wave_id, muted, soloed))
        if selected:
            glow = QGraphicsDropShadowEffect(card)
            glow.setBlurRadius(24)
            glow.setColor(QColor(92, 219, 149, 150))
            glow.setOffset(0, 0)
            card.setGraphicsEffect(glow)
        else:
            card.setGraphicsEffect(None)
        card.style().unpolish(card)
        card.style().polish(card)
        card.update()

    def _refresh_graphical_wave_card_styles(self) -> None:
        solo_wave = self._solo_wave_from_ui() if hasattr(self, "wave_solo_buttons") else None
        for wave_id, card in self.graphical_wave_cards.items():
            muted = self.wave_mute_buttons.get(wave_id).isChecked() if wave_id in self.wave_mute_buttons else False
            self._set_graphical_wave_card_visuals(card, wave_id, muted, solo_wave == wave_id)

    def _graphical_select_wave(self, wave_id: str) -> None:
        if wave_id not in self.wave_row_order:
            return
        self.graphical_selected_wave_id = wave_id
        self._refresh_graphical_wave_card_styles()
        if self.graphical_status_label is not None:
            self.graphical_status_label.setText(f"Selected wave layer: {wave_label_for(self._settings_from_ui(), wave_id)}")

    def _graphical_toggle_wave_mute(self, wave_id: str) -> None:
        button = self.wave_mute_buttons.get(wave_id)
        if button is None:
            return
        self._set_wave_muted(wave_id, not button.isChecked())
        self._refresh_graphical_editor()

    def _graphical_remove_wave(self, wave_id: str) -> None:
        if wave_id in self.user_wave_ids:
            self._remove_user_wave_row(wave_id)
            self._refresh_graphical_editor()
        elif self.graphical_status_label is not None:
            self.graphical_status_label.setText("Default wave layers are kept for compatibility; mute them instead of removing them.")

    def _graphical_set_stereo_pan(self, pan_start: float, pan_end: float) -> None:
        self.pan_start_slider.setValue(int(round(float(pan_start) * 100 * PERCENT_SLIDER_SCALE)))
        self.pan_end_slider.setValue(int(round(float(pan_end) * 100 * PERCENT_SLIDER_SCALE)))
        self._schedule_generate("graphical_stereo_pan")
        self._refresh_graphical_editor()

    def _graphical_set_stereo_width(self, width_value: float) -> None:
        self.width_slider.setValue(int(round(float(width_value) * 100 * PERCENT_SLIDER_SCALE)))
        self._schedule_generate("graphical_stereo_width")
        self._refresh_graphical_editor()

    def _graphical_set_pitch_values(self, start_value: int, end_value: int) -> None:
        self.pitch_start.setValue(int(start_value))
        self.pitch_end.setValue(int(end_value))
        self._schedule_generate("graphical_pitch_curve")
        self._refresh_graphical_editor()

    def _graphical_set_articulation_value(self, key: str, value: float) -> None:
        if key == "voiced":
            if self.articulation_voiced_checkbox is not None:
                self.articulation_voiced_checkbox.setChecked(bool(value >= 0.5))
            self._articulation_slider_changed(key)
            self._refresh_graphical_editor()
            return
        slider = self.articulation_sliders.get(key)
        if slider is None:
            return
        raw = int(round(float(value))) if key == "voice_pitch" else int(round(float(value) * 100.0))
        slider.setValue(max(slider.minimum(), min(slider.maximum(), raw)))
        self._articulation_slider_changed(key)
        self._refresh_graphical_editor()

    def _graphical_set_chain_duration(self, index: int, duration_ms: int) -> None:
        if 0 <= index < len(self.articulation_chain_items):
            self.articulation_chain_items[index].duration_ms = int(np.clip(duration_ms, 80, 5000))
            self._refresh_articulation_chain_cards()
            self._refresh_graphical_editor()

    def _graphical_set_chain_transition(self, index: int, transition_ms: int) -> None:
        if 0 <= index < len(self.articulation_chain_items):
            self.articulation_chain_items[index].transition_ms = int(np.clip(transition_ms, 0, 250))
            self._refresh_articulation_chain_cards()
            self._refresh_graphical_editor()

    def _graphical_set_selected_chain_curve(self, curve: str) -> None:
        if curve not in ARTICULATION_TRANSITION_CURVES:
            return
        selected_index = self.articulation_selected_chain_index
        if isinstance(selected_index, int) and 0 <= selected_index < len(self.articulation_chain_items):
            self.articulation_chain_items[selected_index].transition_curve = curve
            self._refresh_articulation_chain_cards()
            self._refresh_graphical_editor()

    def _graphical_scrub_chain(self, playhead_ms: float) -> None:
        if self.graphical_chain_mouth_canvas is None:
            return
        self.articulation_playhead_ms = float(max(0.0, playhead_ms))
        phoneme, current_name, next_name, transition_progress, playhead, transition_ms, in_transition = self._motion_state_at_ms(self.articulation_playhead_ms)
        self.graphical_chain_mouth_canvas.set_motion_state(phoneme, current_name, next_name, transition_progress, playhead, transition_ms, in_transition)


    def _build_speech_assets_panel(self, context: str = "timeline") -> QWidget:
        """Create a visible Speech Assets panel backed by the existing Speech Bin data model."""
        panel = QWidget()
        panel.setObjectName("speechAssetsPanel")
        panel.setMinimumWidth(300)
        if context in {"timeline", "library"}:
            panel.setMaximumWidth(380)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        title = QLabel("Speech Assets")
        title.setObjectName("timelineInspectorTitle")
        subtitle = QLabel("Created phonemes, syllables, words, and phrases. Create Word saves here; select an asset to preview or add it to the Timeline.")
        subtitle.setObjectName("timelineInspectorText")
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)

        filters = QTabWidget()
        filters.setObjectName("speechAssetFilterTabs")
        for label, item_filter in (
            ("All", "all"),
            ("Phonemes", "phoneme"),
            ("Syllables", "syllable"),
            ("Words", "word"),
            ("Phrases", "phrase"),
        ):
            page = QWidget()
            page_layout = QVBoxLayout(page)
            page_layout.setContentsMargins(4, 6, 4, 4)
            page_layout.setSpacing(8)
            if item_filter == "word":
                actions = QHBoxLayout()
                add_word = QPushButton("Add Latest Word")
                add_word.clicked.connect(lambda checked=False: self._timeline_add_first_speech_type_to_playhead("word"))
                clear = QPushButton("Clear Assets")
                clear.clicked.connect(self._timeline_clear_speech_bin)
                actions.addWidget(add_word)
                actions.addWidget(clear)
                page_layout.addLayout(actions)
            count_label = QLabel("No created speech yet.")
            count_label.setObjectName("timelineInspectorText")
            count_label.setWordWrap(True)
            if context == "timeline" and item_filter == "all":
                self.timeline_speech_count_label = count_label
            page_layout.addWidget(count_label)
            scroll = WaveToyScrollArea(scroll_speed=0.9)
            list_widget = QWidget()
            list_widget.setObjectName("timelineSpeechBinList")
            if context == "timeline" and item_filter == "all":
                self.timeline_speech_bin_widget = list_widget
            scroll.setWidget(list_widget)
            page_layout.addWidget(scroll, 1)
            self.speech_asset_list_widgets.append((list_widget, item_filter))
            filters.addTab(page, label)
        layout.addWidget(filters, 1)
        return panel

    def _build_library_tab(self) -> None:
        if self.tabs is None:
            return
        tab = QWidget()
        tab.setObjectName("libraryTab")
        layout = QHBoxLayout(tab)
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(12)
        intro = QWidget()
        intro.setObjectName("timelineInspector")
        intro_layout = QVBoxLayout(intro)
        intro_layout.setContentsMargins(12, 12, 12, 12)
        intro_layout.setSpacing(8)
        title = QLabel("Library")
        title.setObjectName("timelineInspectorTitle")
        body = QLabel("Central asset management for imported Audio Assets and created Speech Assets. Speech Assets uses the existing Speech Bin data model so saved chains and Timeline integration remain compatible.")
        body.setObjectName("timelineInspectorText")
        body.setWordWrap(True)
        intro_layout.addWidget(title)
        intro_layout.addWidget(body)
        intro_layout.addStretch(1)
        layout.addWidget(intro, 1)
        layout.addWidget(self._build_speech_assets_panel("library"), 2)
        self.tabs.insertTab(max(0, self.tabs.count() - 1), tab, "Library")
        self._timeline_refresh_speech_bin_cards()

    def _build_timeline_tab(self) -> None:
        if self.tabs is None:
            return
        tab = QWidget()
        tab.setObjectName("timelineStoryboardTab")
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(14)

        title = QLabel("Timeline")
        title.setObjectName("timelineStoryboardTitle")
        title.setAlignment(Qt.AlignCenter)
        subtitle = QLabel("Arrange Audio Assets and Speech Assets on measured lanes, edit timing, then render and export the mix.")
        subtitle.setObjectName("timelineStoryboardSubtitle")
        subtitle.setWordWrap(True)
        subtitle.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        layout.addWidget(subtitle)

        transport = QWidget()
        transport.setObjectName("storyTransportBar")
        transport.setMinimumHeight(88)
        transport_layout = QHBoxLayout(transport)
        transport_layout.setContentsMargins(12, 10, 12, 10)
        transport_layout.setSpacing(12)
        buttons = [
            self._make_story_button("▶", "Play", "#5cdb95", self._timeline_play_story),
            self._make_story_button("■", "Stop", "#ff6b6b", self._timeline_stop_story),
            self._make_story_button("Mix", "Render Mix", "#ffd166", self._timeline_render_mix),
            self._make_story_button("+", "Add Sound", "#b8f2e6", self._drop_story_sound),
            self._make_story_button("Lane", "Add Lane", "#d7b9ff", self._add_story_lane),
            self._make_story_button("Voice", "Add Voice Lane", "#ffc6ff", self._add_voice_lane),
            self._make_story_button("+", "Zoom In", "#caffbf", lambda checked=False: self._timeline_zoom(0.72)),
            self._make_story_button("-", "Zoom Out", "#ffc6ff", lambda checked=False: self._timeline_zoom(1.28)),
        ]
        for button in buttons:
            button.setMinimumHeight(44)
            transport_layout.addWidget(button)
        layout.addWidget(transport)

        edit_bar = QWidget()
        edit_layout = QHBoxLayout(edit_bar)
        edit_layout.setContentsMargins(0, 0, 0, 0)
        edit_layout.setSpacing(10)
        self.timeline_tool_buttons = {}
        for tool, icon, label, color, shortcut in (
            ("select", "➤", "Select/Move", "#b8f2e6", "V"),
            ("trim", "↔", "Trim Tool", "#caffbf", "T"),
            ("stretch", "⤢", "Time Stretch", "#ffd166", "S"),
            ("split", "✂", "Split", "#f1c0e8", "Ctrl+B"),
            ("delete", "⌫", "Delete", "#ffadad", "Delete"),
        ):
            button = self._make_story_button(icon, f"{label} ({shortcut})", color, (self._timeline_split_selected if tool == "split" else self._timeline_delete_selected if tool == "delete" else lambda checked=False, name=tool: self._timeline_set_tool(name)))
            button.setCheckable(tool in {"select", "trim", "stretch"})
            button.setChecked(tool == self.timeline_edit_tool)
            button.setMinimumHeight(40)
            edit_layout.addWidget(button)
            if tool in {"select", "trim", "stretch"}:
                self.timeline_tool_buttons[tool] = button
        for icon, label, color, callback in (
            ("⧉", "Duplicate Clip (Ctrl+D)", "#f1c0e8", self._timeline_duplicate_selected),
            ("💾", "Export Last Mix", "#fdffb6", self._timeline_export_last_mix),
        ):
            button = self._make_story_button(icon, label, color, callback)
            button.setMinimumHeight(40)
            edit_layout.addWidget(button)
        self.timeline_snap_checkbox = QCheckBox("Snap")
        self.timeline_snap_checkbox.setChecked(self.timeline_snap_enabled)
        self.timeline_snap_checkbox.stateChanged.connect(self._timeline_snap_changed)
        edit_layout.addWidget(self.timeline_snap_checkbox)
        self.timeline_snap_combo = QComboBox()
        for value in (0.005, 0.01, 0.02, 0.05, 0.10, 0.25, 0.50, 1.00):
            self.timeline_snap_combo.addItem(f"{value:.3f}s" if value < 0.1 else f"{value:.2f}s", value)
        self.timeline_snap_combo.setCurrentIndex(3)
        self.timeline_snap_combo.currentIndexChanged.connect(self._timeline_snap_changed)
        edit_layout.addWidget(self.timeline_snap_combo)
        quality_label = QLabel("Stretch Quality")
        quality_label.setObjectName("timelineInspectorText")
        edit_layout.addWidget(quality_label)
        self.timeline_stretch_quality_combo = QComboBox()
        self.timeline_stretch_quality_combo.addItems(["Fast", "Balanced", "Best available"])
        self.timeline_stretch_quality_combo.setCurrentText(self.timeline_stretch_quality)
        self.timeline_stretch_quality_combo.currentTextChanged.connect(self._timeline_stretch_quality_changed)
        edit_layout.addWidget(self.timeline_stretch_quality_combo)
        layout.addWidget(edit_bar)
        QShortcut(QKeySequence("V"), self, activated=lambda: self._timeline_set_tool("select"))
        QShortcut(QKeySequence("T"), self, activated=lambda: self._timeline_set_tool("trim"))
        QShortcut(QKeySequence("S"), self, activated=lambda: self._timeline_set_tool("stretch"))
        QShortcut(QKeySequence("Ctrl+B"), self, activated=self._timeline_split_selected)
        QShortcut(QKeySequence("Delete"), self, activated=self._timeline_delete_selected)
        QShortcut(QKeySequence("Ctrl+D"), self, activated=self._timeline_duplicate_selected)

        split = QHBoxLayout()
        split.setSpacing(12)

        palette = QWidget()
        palette.setObjectName("timelineAudioPalette")
        palette.setMinimumWidth(300)
        palette.setMaximumWidth(370)
        palette_layout = QVBoxLayout(palette)
        palette_layout.setContentsMargins(12, 12, 12, 12)
        palette_layout.setSpacing(10)
        palette_title = QLabel("Audio Assets")
        palette_title.setObjectName("timelineInspectorTitle")
        palette_subtitle = QLabel("Import sounds, then drag cards into lanes or use Add.")
        palette_subtitle.setObjectName("timelineInspectorText")
        palette_subtitle.setWordWrap(True)
        import_button = self._make_story_button("Import", "Import Sounds", "#b8f2e6", self._timeline_import_sounds)
        import_button.setMinimumHeight(42)
        self.timeline_palette_count_label = QLabel("No imported sounds yet.")
        self.timeline_palette_count_label.setObjectName("timelineInspectorText")
        self.timeline_palette_count_label.setWordWrap(True)
        palette_scroll = WaveToyScrollArea(scroll_speed=0.9)
        self.timeline_palette_list_widget = QWidget()
        self.timeline_palette_list_widget.setObjectName("timelinePaletteList")
        palette_scroll.setWidget(self.timeline_palette_list_widget)
        drawer_tabs = QTabWidget()
        drawer_tabs.setObjectName("timelineDrawerTabs")

        audio_page = QWidget()
        audio_layout = QVBoxLayout(audio_page)
        audio_layout.setContentsMargins(4, 4, 4, 4)
        audio_layout.setSpacing(10)
        audio_layout.addWidget(palette_title)
        audio_layout.addWidget(palette_subtitle)
        audio_layout.addWidget(import_button)
        audio_layout.addWidget(self.timeline_palette_count_label)
        audio_layout.addWidget(palette_scroll, 1)
        drawer_tabs.addTab(audio_page, "Audio Assets")

        speech_page = self._build_speech_assets_panel("timeline")
        drawer_tabs.addTab(speech_page, "Speech Assets")
        palette_layout.addWidget(drawer_tabs, 1)
        split.addWidget(palette)
        self._timeline_refresh_palette_cards()
        self._timeline_refresh_speech_bin_cards()

        scroll = WaveToyScrollArea(scroll_speed=1.0, content_drag_scroll=False)
        scroll.setWidgetResizable(False)
        scroll.setObjectName("storyboardScroll")
        self.timeline_canvas = TimelineCanvas(self)
        self.timeline_canvas._refresh_size()
        scroll.setWidget(self.timeline_canvas)
        split.addWidget(scroll, 1)

        inspector = QWidget()
        inspector.setObjectName("timelineInspector")
        inspector.setMinimumWidth(260)
        inspector_layout = QVBoxLayout(inspector)
        inspector_layout.setContentsMargins(12, 12, 12, 12)
        inspector_layout.setSpacing(10)
        inspector_title = QLabel("Selected Clip Inspector")
        inspector_title.setObjectName("timelineInspectorTitle")
        self.timeline_inspector_label = QLabel("No clip selected. Click a clip, or click empty time to move the playhead.")
        self.timeline_inspector_label.setObjectName("timelineInspectorText")
        self.timeline_inspector_label.setWordWrap(True)
        self.timeline_status_label = QLabel("Timeline ready.")
        self.timeline_status_label.setObjectName("timelineInspectorText")
        self.timeline_status_label.setWordWrap(True)
        inspector_layout.addWidget(inspector_title)
        inspector_layout.addWidget(self.timeline_inspector_label)
        inspector_layout.addStretch(1)
        inspector_layout.addWidget(QLabel("Status"))
        inspector_layout.addWidget(self.timeline_status_label)
        split.addWidget(inspector)
        layout.addLayout(split, 1)

        self._timeline_update_inspector()
        self.tabs.insertTab(max(0, self.tabs.count() - 1), tab, "Timeline")
        self._timeline_debug("Timeline tab constructed")

    def _speech_display_sequence_for_chain(self) -> str:
        return " + ".join(item.phoneme.name for item in self.articulation_chain_items) or "Empty Chain"

    def _speech_ipa_sequence_for_chain(self) -> str:
        return " ".join(f"/{item.phoneme.ipa}/" for item in self.articulation_chain_items)

    def _speech_chain_metadata_snapshot(self) -> Dict[str, object]:
        return ArticulationChain(
            items=self.articulation_chain_items,
            last_word_render_path=str(self.articulation_last_word_render_path) if self.articulation_last_word_render_path else None,
            last_word_render_created_at=self.articulation_last_word_render_created_at,
            word_render_settings=dict(self.articulation_word_render_settings),
            syllable_markers=list(self.articulation_syllable_markers),
            phrase_markers=list(self.articulation_phrase_markers),
        ).to_json_dict()

    def _speech_cache_audio(self, audio: np.ndarray, prefix: str, item_id: int) -> str | None:
        if audio.size == 0:
            return None
        try:
            self.timeline_speech_cache_dir.mkdir(parents=True, exist_ok=True)
            path = self.timeline_speech_cache_dir / f"{prefix}_{item_id}_{int(time.time())}.wav"
            save_wav(path, audio, SAMPLE_RATE)
            return str(path)
        except Exception as exc:
            self._timeline_debug(f"Speech cache write failed prefix={prefix} error={exc}")
            return None

    def _add_speech_bin_item(
        self,
        name: str,
        item_type: str,
        audio: np.ndarray,
        ipa_sequence: str,
        display_sequence: str,
        articulation_metadata: Dict[str, object],
        source_mode: str,
    ) -> SpeechBinItem | None:
        audio = np.asarray(audio, dtype=np.float32)
        if audio.ndim == 1:
            audio = np.column_stack([audio, audio]).astype(np.float32)
        if audio.ndim != 2 or audio.size == 0:
            QMessageBox.warning(self, "Speech Assets", "That speech item did not render any audio, so it was not added to Speech Assets.")
            return None
        if audio.shape[1] == 1:
            audio = np.repeat(audio, 2, axis=1)
        if audio.shape[1] > 2:
            audio = audio[:, :2]
        item_id = self.timeline_next_speech_item_id
        self.timeline_next_speech_item_id += 1
        item = SpeechBinItem(
            id=item_id,
            name=name,
            item_type=item_type,
            ipa_sequence=ipa_sequence,
            display_sequence=display_sequence,
            duration_seconds=len(audio) / SAMPLE_RATE,
            audio_cache_path=self._speech_cache_audio(audio, item_type, item_id),
            articulation_metadata=articulation_metadata,
            source_mode=source_mode,
            created_at=time.time(),
            audio_data=np.array(audio, dtype=np.float32, copy=True),
        )
        self.timeline_speech_bin.append(item)
        self.timeline_selected_speech_item_id = item.id
        self._timeline_refresh_speech_bin_cards()
        self._timeline_debug(f"Speech Assets item added id={item.id} type={item.item_type} name={item.name} duration={item.duration_seconds:.3f}s cache={item.audio_cache_path}")
        return item

    def _current_phoneme_speech_name(self, phoneme: ArticulationPhoneme) -> str:
        return f"{phoneme.name} /{phoneme.ipa}/"

    def _create_phoneme_speech_bin_item(self) -> SpeechBinItem | None:
        self.current_phoneme = self._phoneme_from_articulation_ui().clamped()
        audio = self._render_articulation_with_source(self.current_phoneme)
        metadata = {"phoneme": self.current_phoneme.to_json_dict()}
        return self._add_speech_bin_item(
            name=self._current_phoneme_speech_name(self.current_phoneme),
            item_type="phoneme",
            audio=audio,
            ipa_sequence=f"/{self.current_phoneme.ipa}/",
            display_sequence=self.current_phoneme.name,
            articulation_metadata=metadata,
            source_mode=self.current_phoneme.source_mode,
        )

    def _create_chain_speech_bin_item(self) -> SpeechBinItem | None:
        if not self.articulation_chain_items:
            QMessageBox.information(self, "Speech Assets", "Add at least one phoneme to the Articulation Chain first.")
            return None
        rendered = [self._render_articulation_with_source(item.phoneme_for_render()) for item in self.articulation_chain_items]
        audio = np.vstack([clip for clip in rendered if clip.size]) if rendered else np.zeros((0, 2), dtype=np.float32)
        return self._add_speech_bin_item(
            name=self._speech_display_sequence_for_chain(),
            item_type="chain",
            audio=audio,
            ipa_sequence=self._speech_ipa_sequence_for_chain(),
            display_sequence=self._speech_display_sequence_for_chain(),
            articulation_metadata=self._speech_chain_metadata_snapshot(),
            source_mode="articulation_chain_raw",
        )

    def _create_rendered_speech_bin_item(self, item_type: str, name: str | None = None) -> SpeechBinItem | None:
        if not self.articulation_chain_items:
            QMessageBox.information(self, "Speech Assets", "Add at least one phoneme to the Articulation Chain first.")
            return None
        if self.articulation_word_render_audio.size == 0:
            audio = self._render_word_audio_for_current_chain()
            if audio.size == 0:
                return None
        display = self._speech_display_sequence_for_chain()
        if not name:
            default = display.replace(" + ", "").lower() if item_type == "word" else display.replace(" + ", "")
            name = default or item_type.title()
        return self._add_speech_bin_item(
            name=name,
            item_type=item_type,
            audio=self.articulation_word_render_audio,
            ipa_sequence=self._speech_ipa_sequence_for_chain(),
            display_sequence=display,
            articulation_metadata=self._speech_chain_metadata_snapshot(),
            source_mode=f"articulation_{item_type}_render",
        )

    def _send_current_phoneme_to_timeline(self, checked: bool = False) -> None:
        del checked
        item = self._create_phoneme_speech_bin_item()
        if item is not None:
            self._timeline_add_speech_item_to_playhead(item.id)

    def _send_articulation_chain_to_timeline(self, checked: bool = False) -> None:
        del checked
        item = self._create_chain_speech_bin_item()
        if item is not None:
            self._timeline_add_speech_item_to_playhead(item.id)

    def _create_articulation_syllable(self, checked: bool = False) -> np.ndarray:
        del checked
        if self.articulation_word_render_audio.size == 0:
            audio = self._render_word_audio_for_current_chain()
            if audio.size == 0:
                return audio
        item = self._create_rendered_speech_bin_item("syllable")
        if item is not None:
            QMessageBox.information(self, "Create Syllable", f"Syllable saved to Speech Assets: {item.name} ({item.duration_seconds:.2f}s).")
        return self.articulation_word_render_audio

    def _send_articulation_word_to_timeline(self, checked: bool = False) -> None:
        del checked
        word_item = next((item for item in reversed(self.timeline_speech_bin) if item.item_type == "word"), None)
        if self.articulation_word_render_audio.size == 0 or word_item is None:
            if self._create_articulation_word(checked=False).size == 0:
                return
            word_item = next((item for item in reversed(self.timeline_speech_bin) if item.item_type == "word"), None)
        if word_item is not None:
            self._timeline_add_speech_item_to_playhead(word_item.id)

    def _timeline_refresh_palette_cards(self) -> None:
        if self.timeline_palette_list_widget is None:
            return
        layout = self.timeline_palette_list_widget.layout()
        if layout is None:
            layout = QVBoxLayout(self.timeline_palette_list_widget)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(10)
        else:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
        if not self.timeline_audio_palette:
            empty = QLabel("📥 Import WAV files to build Audio Assets.")
            empty.setObjectName("timelineInspectorText")
            empty.setWordWrap(True)
            empty.setMinimumHeight(92)
            layout.addWidget(empty)
        else:
            for item in self.timeline_audio_palette:
                layout.addWidget(AudioPaletteCard(self, item))
        layout.addStretch(1)
        if self.timeline_palette_count_label is not None:
            count = len(self.timeline_audio_palette)
            self.timeline_palette_count_label.setText(f"{count} palette sound{'s' if count != 1 else ''} ready." if count else "No imported sounds yet.")

    def _timeline_select_palette_item(self, item_id: int) -> None:
        item = self._timeline_palette_item_by_id(item_id)
        if item is None:
            return
        self.timeline_selected_palette_item_id = item_id
        self._timeline_refresh_palette_cards()
        self._timeline_debug(f"Palette item selected id={item.item_id} name={item.name}")

    def _timeline_palette_item_by_id(self, item_id: int | None) -> AudioPaletteItem | None:
        for item in self.timeline_audio_palette:
            if item.item_id == item_id:
                return item
        return None

    def _timeline_refresh_speech_bin_cards(self) -> None:
        if not self.speech_asset_list_widgets and self.timeline_speech_bin_widget is None:
            return
        targets = list(self.speech_asset_list_widgets)
        if not targets and self.timeline_speech_bin_widget is not None:
            targets = [(self.timeline_speech_bin_widget, "all")]
        for list_widget, item_filter in targets:
            layout = list_widget.layout()
            if layout is None:
                layout = QVBoxLayout(list_widget)
                layout.setContentsMargins(0, 0, 0, 0)
                layout.setSpacing(8)
            else:
                while layout.count():
                    item = layout.takeAt(0)
                    widget = item.widget()
                    if widget is not None:
                        widget.deleteLater()
            visible_items = [item for item in self.timeline_speech_bin if item_filter == "all" or item.item_type == item_filter or (item_filter == "phrase" and item.item_type == "chain")]
            if not visible_items:
                label = "Create a word, syllable, phrase, or phoneme in Articulation Lab to populate Speech Assets."
                if item_filter != "all":
                    label = f"No {item_filter} assets yet. Create one in Articulation Lab; it will appear here immediately."
                empty = QLabel(label)
                empty.setObjectName("timelineInspectorText")
                empty.setWordWrap(True)
                empty.setMinimumHeight(72)
                layout.addWidget(empty)
            else:
                for item in visible_items:
                    layout.addWidget(SpeechBinCard(self, item))
            layout.addStretch(1)
        if self.timeline_speech_count_label is not None:
            count = len(self.timeline_speech_bin)
            self.timeline_speech_count_label.setText(f"{count} Speech Asset{'s' if count != 1 else ''} ready." if count else "No created speech yet.")

    def _timeline_select_speech_item(self, item_id: int) -> None:
        item = self._timeline_speech_item_by_id(item_id)
        if item is None:
            return
        self.timeline_selected_speech_item_id = item_id
        self._timeline_refresh_speech_bin_cards()
        self._timeline_debug(f"Speech item selected id={item.id} type={item.item_type} name={item.name}")

    def _timeline_speech_item_by_id(self, item_id: int | None) -> SpeechBinItem | None:
        for item in self.timeline_speech_bin:
            if item.id == item_id:
                return item
        return None

    def _timeline_preview_speech_item(self, item_id: int | None = None) -> None:
        item = self._timeline_speech_item_by_id(item_id if item_id is not None else self.timeline_selected_speech_item_id)
        if item is None:
            QMessageBox.information(self, "Speech Assets", "Select a speech card to preview.")
            return
        audio, warning = self._speech_audio_for_item(item)
        if audio.size == 0:
            QMessageBox.warning(self, "Speech Assets Preview", warning or "That speech card could not render audio.")
            return
        self.timeline_selected_speech_item_id = item.id
        self._timeline_refresh_speech_bin_cards()
        self._play_audio_array(audio)
        self._timeline_debug(f"Speech preview id={item.id} type={item.item_type} name={item.name} warning={warning}")

    def _timeline_rename_speech_item(self, item_id: int | None = None) -> None:
        item = self._timeline_speech_item_by_id(item_id if item_id is not None else self.timeline_selected_speech_item_id)
        if item is None:
            QMessageBox.information(self, "Speech Assets", "Select a speech card to rename.")
            return
        name, ok = QInputDialog.getText(self, "Rename Speech Card", "Speech card name:", text=item.name)
        if not ok:
            return
        name = name.strip()
        if not name:
            QMessageBox.information(self, "Speech Assets", "Speech card names cannot be blank.")
            return
        item.name = name
        self.timeline_selected_speech_item_id = item.id
        self._timeline_refresh_speech_bin_cards()
        self._timeline_debug(f"Speech item renamed id={item.id} name={item.name}")

    def _timeline_duplicate_speech_item(self, item_id: int | None = None) -> None:
        item = self._timeline_speech_item_by_id(item_id if item_id is not None else self.timeline_selected_speech_item_id)
        if item is None:
            QMessageBox.information(self, "Speech Assets", "Select a speech card to duplicate.")
            return
        audio, warning = self._speech_audio_for_item(item)
        if audio.size == 0:
            QMessageBox.warning(self, "Speech Assets", warning or "That speech card could not be duplicated because it has no audio.")
            return
        duplicate = self._add_speech_bin_item(
            name=f"{item.name} Copy",
            item_type=item.item_type,
            audio=audio,
            ipa_sequence=item.ipa_sequence,
            display_sequence=item.display_sequence,
            articulation_metadata=json.loads(json.dumps(item.articulation_metadata)),
            source_mode=item.source_mode,
        )
        if duplicate is not None:
            self._timeline_debug(f"Speech item duplicated source_id={item.id} duplicate_id={duplicate.id}")

    def _timeline_delete_speech_item(self, item_id: int | None = None) -> None:
        item = self._timeline_speech_item_by_id(item_id if item_id is not None else self.timeline_selected_speech_item_id)
        if item is None:
            QMessageBox.information(self, "Speech Assets", "Select a speech card to delete.")
            return
        response = QMessageBox.question(
            self,
            "Delete Speech Card",
            f"Delete '{item.name}' from Speech Assets? Existing Timeline clips stay in the arrangement.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if response != QMessageBox.Yes:
            return
        self.timeline_speech_bin = [existing for existing in self.timeline_speech_bin if existing.id != item.id]
        if self.timeline_selected_speech_item_id == item.id:
            self.timeline_selected_speech_item_id = None
        self._timeline_refresh_speech_bin_cards()
        self._timeline_debug(f"Speech item deleted id={item.id}; timeline clips preserved")

    def _timeline_clear_speech_bin(self, checked: bool = False) -> None:
        del checked
        if not self.timeline_speech_bin:
            QMessageBox.information(self, "Speech Assets", "Speech Assets is already empty.")
            return
        response = QMessageBox.question(
            self,
            "Clear Speech Assets",
            "Clear all Speech Assets source cards? Existing Timeline clips stay in the arrangement.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if response != QMessageBox.Yes:
            return
        count = len(self.timeline_speech_bin)
        self.timeline_speech_bin.clear()
        self.timeline_selected_speech_item_id = None
        self._timeline_refresh_speech_bin_cards()
        self._timeline_debug(f"Speech Assets cleared count={count}; timeline clips preserved")

    def _rerender_speech_item_from_metadata(self, item: SpeechBinItem) -> np.ndarray:
        metadata = item.articulation_metadata or {}
        try:
            if item.item_type == "phoneme" and isinstance(metadata.get("phoneme"), dict):
                phoneme = ArticulationPhoneme.from_json_dict(metadata["phoneme"])
                return self._render_articulation_with_source(phoneme)
            chain_items = [ArticulationChainItem.from_json_dict(data) for data in metadata.get("items", []) if isinstance(data, dict)]
            if not chain_items:
                return np.zeros((0, 2), dtype=np.float32)
            previous_items = self.articulation_chain_items
            previous_settings = dict(self.articulation_word_render_settings)
            try:
                self.articulation_chain_items = chain_items
                if isinstance(metadata.get("word_render_settings"), dict):
                    self.articulation_word_render_settings.update(metadata["word_render_settings"])
                if item.item_type == "chain":
                    clips = [self._render_articulation_with_source(chain_item.phoneme_for_render()) for chain_item in chain_items]
                    return np.vstack([clip for clip in clips if clip.size]) if clips else np.zeros((0, 2), dtype=np.float32)
                return self._render_articulation_word()
            finally:
                self.articulation_chain_items = previous_items
                self.articulation_word_render_settings = previous_settings
        except Exception as exc:
            self._timeline_debug(f"Speech rerender failed id={item.id} error={exc}")
            return np.zeros((0, 2), dtype=np.float32)

    def _speech_audio_for_item(self, item: SpeechBinItem) -> Tuple[np.ndarray, str | None]:
        cache_missing = not item.audio_cache_path or not Path(item.audio_cache_path).exists()
        if item.audio_data.size and cache_missing:
            item.audio_cache_path = self._speech_cache_audio(item.audio_data, item.item_type, item.id)
            self._timeline_debug(f"Speech cache restored from in-memory audio id={item.id} cache={item.audio_cache_path}")
        if item.audio_data.size:
            item.duration_seconds = len(item.audio_data) / float(SAMPLE_RATE)
            return np.array(item.audio_data, dtype=np.float32, copy=True), None
        if item.audio_cache_path:
            try:
                path = Path(item.audio_cache_path)
                if path.exists():
                    audio, _sample_rate = load_audio_file(path)
                    item.audio_data = np.array(audio, dtype=np.float32, copy=True)
                    item.duration_seconds = len(item.audio_data) / float(SAMPLE_RATE)
                    return item.audio_data, None
            except Exception as exc:
                self._timeline_debug(f"Speech cache load failed id={item.id} path={item.audio_cache_path} error={exc}")
        self._timeline_debug(f"Speech cache missing; attempting metadata re-render id={item.id} type={item.item_type}")
        rerendered = self._rerender_speech_item_from_metadata(item)
        if rerendered.size:
            item.audio_data = np.array(rerendered, dtype=np.float32, copy=True)
            item.duration_seconds = len(item.audio_data) / float(SAMPLE_RATE)
            if not item.audio_cache_path or not Path(item.audio_cache_path).exists():
                item.audio_cache_path = self._speech_cache_audio(item.audio_data, item.item_type, item.id)
            return item.audio_data, None
        return np.zeros((0, 2), dtype=np.float32), "Missing speech audio cache and articulation metadata could not be re-rendered; clip is visible but muted."

    def _timeline_add_first_speech_type_to_playhead(self, item_type: str) -> None:
        item = next((candidate for candidate in reversed(self.timeline_speech_bin) if candidate.item_type == item_type), None)
        if item is None:
            QMessageBox.information(self, "Speech Assets", f"No created {item_type} cards are in Speech Assets yet.")
            return
        self._timeline_add_speech_item_to_playhead(item.id)

    def _timeline_add_speech_item_to_playhead(self, item_id: int | None = None) -> None:
        target_id = item_id if item_id is not None else self.timeline_selected_speech_item_id
        item = self._timeline_speech_item_by_id(target_id)
        if item is None:
            QMessageBox.information(self, "Speech Assets", "Select or create a speech card first.")
            return
        self._timeline_add_speech_item_to_timeline(item.id, self.timeline_playhead_seconds, self._first_voice_lane_index())

    def _timeline_add_speech_item_to_timeline(self, item_id: int, start_time_seconds: float, lane: int) -> None:
        item = self._timeline_speech_item_by_id(item_id)
        if item is None:
            QMessageBox.warning(self, "Speech Assets", "That speech card is no longer available.")
            return
        audio, warning = self._speech_audio_for_item(item)
        if audio.size == 0:
            QMessageBox.warning(self, "Speech Assets", warning or "That speech card could not render audio.")
        clip_id = self.timeline_next_clip_id
        self.timeline_next_clip_id += 1
        clip = TimelineClip(
            clip_id=clip_id,
            name=f"{item.icon} {item.name}",
            audio=np.array(audio, dtype=np.float32, copy=True),
            start_time_seconds=self._timeline_snap_time(start_time_seconds),
            lane=max(0, min(self.timeline_lane_count - 1, lane)),
            sample_rate=SAMPLE_RATE,
            recipe=None,
            source_path=item.audio_cache_path,
            source_type=item.source_type,
            speech_metadata=item.metadata(),
            muted_warning=warning,
        )
        self.timeline_clips.append(clip)
        self.timeline_selected_clip_id = clip.clip_id
        self.timeline_selected_speech_item_id = item.id
        self._timeline_update_duration()
        self._timeline_mark_mix_dirty()
        if self.timeline_canvas is not None:
            self.timeline_canvas.selected_clip_id = clip.clip_id
            self.timeline_canvas._refresh_size()
            self.timeline_canvas.update()
        self._timeline_update_inspector()
        self._timeline_refresh_speech_bin_cards()
        self._timeline_debug(f"Clip created from speech clip_id={clip.clip_id} speech_id={item.id} type={item.item_type} start={clip.start_time_seconds:.3f}s lane={clip.lane} duration={clip.duration_seconds:.3f}s warning={warning}")

    def _timeline_import_sounds(self, checked: bool = False) -> None:
        self._timeline_debug("Audio import requested")
        filenames, _selected_filter = QFileDialog.getOpenFileNames(
            self,
            "Import Sounds to Palette",
            "",
            "Audio Files (*.wav *.ogg *.flac *.mp3);;WAV Audio (*.wav);;All Files (*)",
        )
        if not filenames:
            self._timeline_debug("Audio import cancelled")
            return
        imported = 0
        failures: List[str] = []
        colors = ["#5cdb95", "#ffd166", "#b8f2e6", "#d7b9ff", "#ffadad", "#caffbf", "#ffc6ff"]
        for filename in filenames:
            path = Path(filename)
            try:
                audio, sample_rate = load_audio_file(path)
                if audio.size == 0 or len(audio) < 2:
                    raise ValueError("Imported audio is empty")
                item_id = self.timeline_next_palette_item_id
                self.timeline_next_palette_item_id += 1
                item = AudioPaletteItem(
                    id=item_id,
                    name=path.stem,
                    source_path=str(path),
                    audio_data=audio,
                    sample_rate=sample_rate,
                    duration_seconds=len(audio) / float(sample_rate),
                    waveform_peaks=compute_waveform_peaks(audio),
                    color=colors[(item_id - 1) % len(colors)],
                )
                self.timeline_audio_palette.append(item)
                imported += 1
                self._timeline_debug(f"File import success id={item.item_id} path={path} duration={item.duration_seconds:.3f}s")
            except Exception as exc:
                failures.append(f"{path.name}: {exc}")
                self._timeline_debug(f"File import failure path={path} error={exc}")
        self._timeline_refresh_palette_cards()
        if imported:
            self.timeline_selected_palette_item_id = self.timeline_audio_palette[-1].item_id
        message = f"Imported {imported} sound{'s' if imported != 1 else ''} into the Audio Assets."
        if failures:
            message += "\n\nSome files could not be imported:\n" + "\n".join(failures[:6])
        if imported and not failures:
            QMessageBox.information(self, "Import Sounds", message)
        else:
            QMessageBox.warning(self, "Import Sounds", message)

    def _timeline_add_palette_item_to_playhead(self, item_id: int | None = None) -> None:
        target_id = item_id if item_id is not None else self.timeline_selected_palette_item_id
        item = self._timeline_palette_item_by_id(target_id)
        if item is None:
            QMessageBox.information(self, "Audio Assets", "Select or import a palette sound first.")
            return
        self._timeline_add_palette_item_to_timeline(item.item_id, self.timeline_playhead_seconds, 0)

    def _timeline_add_palette_item_to_timeline(self, item_id: int, start_time_seconds: float, lane: int) -> None:
        item = self._timeline_palette_item_by_id(item_id)
        if item is None:
            QMessageBox.warning(self, "Audio Assets", "That palette sound is no longer available.")
            return
        clip_id = self.timeline_next_clip_id
        self.timeline_next_clip_id += 1
        clip = TimelineClip(
            clip_id=clip_id,
            name=item.name,
            audio=np.array(item.audio_data, dtype=np.float32, copy=True),
            start_time_seconds=self._timeline_snap_time(start_time_seconds),
            lane=max(0, min(self.timeline_lane_count - 1, lane)),
            sample_rate=item.sample_rate,
            recipe=None,
            source_path=item.source_path,
            import_metadata={
                "palette_item_id": item.item_id,
                "palette_name": item.name,
                "source_path": item.source_path,
                "duration_seconds": item.duration_seconds,
            },
            source_type="imported_audio",
        )
        self.timeline_clips.append(clip)
        self.timeline_selected_clip_id = clip.clip_id
        self.timeline_selected_palette_item_id = item.item_id
        self._timeline_update_duration()
        self._timeline_mark_mix_dirty()
        if self.timeline_canvas is not None:
            self.timeline_canvas.selected_clip_id = clip.clip_id
            self.timeline_canvas._refresh_size()
            self.timeline_canvas.update()
        self._timeline_update_inspector()
        self._timeline_refresh_palette_cards()
        self._timeline_debug(f"Clip created from palette clip_id={clip.clip_id} palette_id={item.item_id} start={clip.start_time_seconds:.3f}s lane={clip.lane} duration={clip.duration_seconds:.3f}s")

    def _add_story_lane(self, checked: bool = False, icon: str | None = None, label: str | None = None, clips: list | None = None) -> None:
        if icon is not None and label is not None:
            name = f"{icon} {label}"
        else:
            defaults = ["🎵 Melody Lane", "🥁 Rhythm Lane", "🌌 Atmosphere Lane", "✨ Effects Lane"]
            name = defaults[self.timeline_lane_count % len(defaults)] if self.timeline_lane_count < len(defaults) else f"🛤️ Lane {self.timeline_lane_count + 1}"
        self.timeline_lane_names.append(name)
        self.timeline_lane_count = len(self.timeline_lane_names)
        if self.timeline_canvas is not None:
            self.timeline_canvas._refresh_size()
            self.timeline_canvas.update()
        self._timeline_debug(f"Lane added index={self.timeline_lane_count - 1} name={name}")

    def _add_voice_lane(self, checked: bool = False) -> None:
        del checked
        if not any(name == "🗣 Voice Lane" for name in self.timeline_lane_names):
            self._add_story_lane(icon="🗣", label="Voice Lane")
            return
        self._timeline_debug("Voice Lane already exists")

    def _first_voice_lane_index(self) -> int:
        for index, name in enumerate(self.timeline_lane_names):
            if name == "🗣 Voice Lane" or "Voice Lane" in name:
                return index
        return 0

    def _add_story_clip(self, lane_layout: QHBoxLayout, icon: str, name: str, duration: str, wave_type: str, color: str) -> None:
        # Kept for compatibility with older storyboard code paths; the active timeline uses TimelineClip objects.
        pass

    def _timeline_current_audio(self, force: bool = True) -> np.ndarray:
        if force or self.current_audio.size <= 2 or len(self.current_audio) < 8:
            self._timeline_debug("Rendering current sound for timeline drop")
            self._generate_now(reason="timeline_drop", update_message=True, force=True)
        audio = np.asarray(self.current_audio, dtype=np.float32)
        if audio.ndim == 1:
            audio = np.column_stack([audio, audio]).astype(np.float32)
        if audio.ndim != 2 or audio.shape[0] == 0:
            return np.zeros((0, 2), dtype=np.float32)
        if audio.shape[1] == 1:
            audio = np.repeat(audio, 2, axis=1)
        if audio.shape[1] > 2:
            audio = audio[:, :2]
        duration = len(audio) / SAMPLE_RATE
        peak = float(np.max(np.abs(audio))) if audio.size else 0.0
        self._timeline_debug(f"Current audio shape={audio.shape} duration={duration:.3f}s peak={peak:.4f}")
        return np.array(audio, dtype=np.float32, copy=True)

    def _timeline_recipe_snapshot(self) -> Dict[str, object]:
        try:
            return self._settings_to_recipe("Timeline Clip")
        except Exception as exc:
            self._timeline_debug(f"Recipe snapshot failed: {exc}")
            return {"name": "Timeline Clip", "error": str(exc)}

    def _timeline_snap_time(self, seconds: float) -> float:
        seconds = max(0.0, float(seconds))
        if not getattr(self, "timeline_snap_enabled", True):
            return seconds
        grid = max(0.001, float(getattr(self, "timeline_snap_seconds", 0.05)))
        return max(0.0, round(seconds / grid) * grid)

    def _timeline_render_clip_audio(self, clip: TimelineClip) -> np.ndarray:
        audio = clip.visible_audio()
        if audio.ndim == 1 and audio.size:
            audio = np.column_stack([audio, audio]).astype(np.float32)
        if audio.ndim != 2 or audio.size == 0:
            return np.zeros((0, 2), dtype=np.float32)
        audio = _ensure_stereo_float(audio)
        source_rate = int(clip.sample_rate or SAMPLE_RATE)
        if source_rate != SAMPLE_RATE:
            audio = _resample_audio(audio, source_rate, SAMPLE_RATE)
        trim_duration = len(audio) / float(SAMPLE_RATE) if audio.size else 0.0
        target_duration = max(0.0, float(clip.duration_seconds))
        target_len = max(1, int(round(target_duration * SAMPLE_RATE))) if target_duration > 0 else 0
        stretch_ratio = target_duration / max(1e-9, trim_duration)
        pitch_preserve = bool(getattr(self, "timeline_preserve_pitch", True) and clip.pitch_preserve_enabled)
        algorithm = clip.stretch_algorithm or "numpy_phase_vocoder"
        if audio.size and target_len > 0 and abs(target_len - len(audio)) > 1:
            cache_key = (
                len(audio),
                target_len,
                round(float(clip.trim_start_seconds), 6),
                round(float(clip.trim_end_seconds), 6),
                round(float(clip.playback_rate), 6),
                self.timeline_stretch_quality,
                pitch_preserve,
                algorithm,
            )
            if pitch_preserve:
                if clip.stretched_audio_cache is not None and clip._stretch_cache_key == cache_key:
                    audio = np.array(clip.stretched_audio_cache, dtype=np.float32, copy=True)
                else:
                    audio = time_stretch_preserve_pitch(audio, SAMPLE_RATE, target_duration, self.timeline_stretch_quality)
                    clip.stretched_audio_cache = np.array(audio, dtype=np.float32, copy=True)
                    clip._stretch_cache_key = cache_key
            else:
                # Compatibility escape hatch only: default Timeline stretch never uses this pitch-shifting path.
                target_rate = max(1, int(round(SAMPLE_RATE / max(0.25, float(clip.playback_rate or 1.0)))))
                audio = _resample_audio(audio, SAMPLE_RATE, target_rate)
                audio = _fit_audio_length(audio, target_len)
                algorithm = "legacy_speed_resample"
        else:
            audio = _fit_audio_length(audio, target_len) if target_len > 0 else np.zeros((0, 2), dtype=np.float32)
        clip.rendered_duration_seconds = len(audio) / SAMPLE_RATE if audio.size else 0.0
        self._timeline_stretch_debug(
            f"clip_id={clip.clip_id} source_duration={clip.source_duration_seconds:.3f}s "
            f"trim_duration={trim_duration:.3f}s target_duration={target_duration:.3f}s "
            f"stretch_ratio={stretch_ratio:.3f} algorithm={algorithm} "
            f"output_duration={clip.rendered_duration_seconds:.3f}s pitch_preserve_enabled={pitch_preserve}"
        )
        return np.asarray(audio, dtype=np.float32)

    def _timeline_tool_display_name(self, tool: str) -> str:
        return {"select": "Select", "trim": "Trim", "stretch": "Time Stretch", "split": "Split", "delete": "Delete"}.get(tool, str(tool).title())

    def _timeline_set_tool(self, tool: str) -> None:
        self.timeline_edit_tool = tool
        for name, button in getattr(self, "timeline_tool_buttons", {}).items():
            button.setChecked(name == tool)
        if self.timeline_status_label is not None:
            self.timeline_status_label.setText(
                f"Tool: {self._timeline_tool_display_name(tool)} • Snap {'on' if self.timeline_snap_enabled else 'off'} "
                f"{self.timeline_snap_seconds:.3f}s • Pitch-preserving stretch {self.timeline_stretch_quality}"
            )
        if self.timeline_canvas is not None:
            self.timeline_canvas.update()

    def _timeline_snap_changed(self, *args) -> None:
        del args
        if self.timeline_snap_checkbox is not None:
            self.timeline_snap_enabled = self.timeline_snap_checkbox.isChecked()
        if self.timeline_snap_combo is not None:
            self.timeline_snap_seconds = float(self.timeline_snap_combo.currentData() or 0.05)
        self._timeline_set_tool(self.timeline_edit_tool)

    def _timeline_stretch_quality_changed(self, text: str) -> None:
        self.timeline_stretch_quality = str(text or "Balanced")
        for clip in self.timeline_clips:
            clip.stretched_audio_cache = None
            clip._stretch_cache_key = None
        self._timeline_mark_mix_dirty()
        self._timeline_set_tool(self.timeline_edit_tool)


    def _drop_story_sound(self, checked: bool = False) -> None:
        self._timeline_debug("Drop Current Sound clicked")
        audio = self._timeline_current_audio(force=True)
        if audio.size == 0 or len(audio) < 8:
            self._timeline_debug("Drop rejected: empty audio")
            QMessageBox.warning(self, "Timeline drop failed", "WaveToy could not find a rendered sound to drop. Try Make Sound, then Drop Sound again.")
            return
        peak = float(np.max(np.abs(audio))) if audio.size else 0.0
        if peak <= 1e-6:
            self._timeline_debug("Drop rejected: nearly silent audio")
            QMessageBox.warning(self, "Timeline drop failed", "The current sound is silent. Turn up a wave or loudness, then drop it again.")
            return
        clip_id = self.timeline_next_clip_id
        self.timeline_next_clip_id += 1
        clip = TimelineClip(
            clip_id=clip_id,
            name=f"Sound {clip_id}",
            audio=audio,
            start_time_seconds=self._timeline_snap_time(self.timeline_playhead_seconds),
            lane=0,
            recipe=self._timeline_recipe_snapshot(),
        )
        self.timeline_clips.append(clip)
        self.timeline_selected_clip_id = clip.clip_id
        self._timeline_update_duration()
        self._timeline_mark_mix_dirty()
        if self.timeline_canvas is not None:
            self.timeline_canvas.selected_clip_id = clip.clip_id
            self.timeline_canvas._refresh_size()
            self.timeline_canvas.update()
        self._timeline_update_inspector()
        self._timeline_debug(f"Clip created id={clip.clip_id} start={clip.start_time_seconds:.3f}s lane={clip.lane} duration={clip.duration_seconds:.3f}s")

    def _timeline_clip_by_id(self, clip_id: int | None) -> TimelineClip | None:
        for clip in self.timeline_clips:
            if clip.clip_id == clip_id:
                return clip
        return None

    def _timeline_select_clip(self, clip_id: int) -> None:
        clip = self._timeline_clip_by_id(clip_id)
        if clip is None:
            return
        self.timeline_selected_clip_id = clip_id
        if self.timeline_canvas is not None:
            self.timeline_canvas.selected_clip_id = clip_id
        self._timeline_update_inspector()
        self._timeline_debug(f"Clip selected id={clip.clip_id} start={clip.start_time_seconds:.3f}s lane={clip.lane}")

    def _timeline_clear_selection(self, move_playhead_to: float | None = None) -> None:
        self.timeline_selected_clip_id = None
        if move_playhead_to is not None:
            self.timeline_playhead_seconds = max(0.0, move_playhead_to)
        if self.timeline_canvas is not None:
            self.timeline_canvas.selected_clip_id = None
            self.timeline_canvas.update()
        self._timeline_update_inspector()

    def _timeline_update_inspector(self) -> None:
        if self.timeline_inspector_label is None:
            return
        clip = self._timeline_clip_by_id(self.timeline_selected_clip_id)
        if clip is None:
            self.timeline_inspector_label.setText(f"No clip selected. Playhead: {self.timeline_playhead_seconds:.2f}s")
            return
        visual_width = None
        if self.timeline_canvas is not None:
            visual_width = clip.duration_seconds / self.timeline_canvas.seconds_per_pixel
        trimmed_duration = clip.source_visible_duration_seconds
        rendered_duration = clip.rendered_duration_seconds or clip.duration_seconds
        source_text = (
            f"\nSource type: {clip.source_type}"
            f"\nStart time: {clip.start_time_seconds:.3f}s"
            f"\nEnd time: {clip.end_time_seconds:.3f}s"
            f"\nSource duration: {clip.source_duration_seconds:.3f}s"
            f"\nTrimmed duration: {trimmed_duration:.3f}s"
            f"\nStretched duration: {clip.duration_seconds:.3f}s"
            f"\nRendered duration: {rendered_duration:.3f}s"
            f"\nTrim start: {clip.trim_start_seconds:.3f}s"
            f"\nTrim end: {clip.trim_end_seconds:.3f}s"
            f"\nStretch ratio: {clip.stretch_ratio:.2f}x duration"
            f"\nTime-stretched: {'yes' if abs(clip.stretch_ratio - 1.0) > 0.005 else 'no'}"
            f"\nPitch preserved: {'yes' if clip.pitch_preserve_enabled else 'no'}"
            f"\nStretch algorithm: {clip.stretch_algorithm}"
            f"\nSample count: {len(clip.audio)}"
            f"\nSample rate: {clip.sample_rate} Hz"
        )
        if visual_width is not None:
            source_text += f"\nVisual width: {visual_width:.1f}px"
        if clip.speech_metadata:
            cache_path = str(clip.speech_metadata.get("audio_cache_path") or "")
            cache_status = "cached" if cache_path and Path(cache_path).exists() else "missing / will re-render if needed"
            source_text += (
                f"\nSpeech type: {clip.speech_metadata.get('item_type', 'speech')}"
                f"\nPhoneme sequence: {clip.speech_metadata.get('display_sequence', '')}"
                f"\nIPA: {clip.speech_metadata.get('ipa_sequence', '')}"
                f"\nSpeech asset visible duration: {clip.duration_seconds:.3f}s"
                f"\nCache path: {cache_path or 'none'}"
                f"\nCache status: {cache_status}"
                f"\nArticulation source mode: {clip.speech_metadata.get('source_mode', 'unknown')}"
            )
        if clip.muted_warning:
            source_text += f"\nWarning: {clip.muted_warning}"
        self.timeline_inspector_label.setText(
            f"{clip.name}\nID: {clip.clip_id}\nLane: {clip.lane + 1}\nTool: {self._timeline_tool_display_name(self.timeline_edit_tool)}\nDuration: {clip.duration_seconds:.3f}s{source_text}"
        )

    def _timeline_update_duration(self) -> None:
        previous_duration = getattr(self, "timeline_duration_seconds", 0.0)
        self.timeline_duration_seconds = max([clip.start_time_seconds + clip.duration_seconds for clip in self.timeline_clips] or [0.0])
        if abs(previous_duration - self.timeline_duration_seconds) > 0.0005:
            self._timeline_debug(f"Timeline duration recalculated duration={self.timeline_duration_seconds:.3f}s clip_count={len(self.timeline_clips)}")

    def _timeline_mark_mix_dirty(self) -> None:
        self.timeline_mix_dirty = True

    def _timeline_zoom(self, factor: float) -> None:
        if self.timeline_canvas is not None:
            self.timeline_canvas.set_zoom(factor)
            self._timeline_debug(f"Timeline zoom changed seconds_per_pixel={self.timeline_canvas.seconds_per_pixel:.4f}")

    def _timeline_duplicate_selected(self, checked: bool = False) -> None:
        source = self._timeline_clip_by_id(self.timeline_selected_clip_id)
        if source is None:
            QMessageBox.information(self, "Duplicate Clip", "Select a timeline clip first.")
            return
        clip_id = self.timeline_next_clip_id
        self.timeline_next_clip_id += 1
        duplicate = TimelineClip(
            clip_id=clip_id,
            name=f"{source.name} Copy",
            audio=np.array(source.audio, dtype=np.float32, copy=True),
            start_time_seconds=source.start_time_seconds + 0.25,
            lane=source.lane,
            recipe=source.recipe,
            source_path=source.source_path,
            import_metadata=source.import_metadata,
            source_type=source.source_type,
            speech_metadata=source.speech_metadata,
            muted_warning=source.muted_warning,
            source_audio_full_length_samples=source.source_audio_full_length_samples,
            trim_start_seconds=source.trim_start_seconds,
            trim_end_seconds=source.trim_end_seconds,
            playback_rate=source.playback_rate,
            rendered_duration_seconds=source.rendered_duration_seconds,
            stretch_mode=source.stretch_mode,
            stretch_algorithm=source.stretch_algorithm,
        )
        self.timeline_clips.append(duplicate)
        self.timeline_selected_clip_id = duplicate.clip_id
        self._timeline_update_duration()
        self._timeline_mark_mix_dirty()
        if self.timeline_canvas is not None:
            self.timeline_canvas.selected_clip_id = duplicate.clip_id
            self.timeline_canvas._refresh_size()
            self.timeline_canvas.update()
        self._timeline_update_inspector()
        self._timeline_debug(f"Clip created id={duplicate.clip_id} start={duplicate.start_time_seconds:.3f}s lane={duplicate.lane} duration={duplicate.duration_seconds:.3f}s duplicate_of={source.clip_id}")

    def _timeline_split_selected(self, checked: bool = False) -> None:
        del checked
        source = self._timeline_clip_by_id(self.timeline_selected_clip_id)
        if source is None:
            QMessageBox.information(self, "Split Clip", "Select a timeline clip first.")
            return
        split_time = float(self.timeline_playhead_seconds)
        if not (source.start_time_seconds + 0.005 < split_time < source.end_time_seconds - 0.005):
            QMessageBox.information(self, "Split Clip", "Move the playhead inside the selected clip before splitting.")
            return
        left_duration = split_time - source.start_time_seconds
        source_delta = left_duration * source.playback_rate
        original_trim_end = source.trim_end_seconds
        right_trim_start = source.trim_start_seconds + source_delta
        source.trim_end_seconds = max(0.0, source.source_duration_seconds - source.trim_start_seconds - source_delta)
        source.stretched_audio_cache = None
        source._stretch_cache_key = None
        clip_id = self.timeline_next_clip_id
        self.timeline_next_clip_id += 1
        right = TimelineClip(
            clip_id=clip_id,
            name=f"{source.name} Split",
            audio=np.array(source.audio, dtype=np.float32, copy=True),
            start_time_seconds=split_time,
            lane=source.lane,
            sample_rate=source.sample_rate,
            recipe=source.recipe,
            source_path=source.source_path,
            import_metadata=source.import_metadata,
            source_type=source.source_type,
            speech_metadata=source.speech_metadata,
            muted_warning=source.muted_warning,
            source_audio_full_length_samples=source.source_audio_full_length_samples,
            trim_start_seconds=right_trim_start,
            trim_end_seconds=original_trim_end,
            playback_rate=source.playback_rate,
            stretch_mode=source.stretch_mode,
            stretch_algorithm=source.stretch_algorithm,
        )
        self.timeline_clips.append(right)
        self.timeline_selected_clip_id = right.clip_id
        self._timeline_update_duration()
        self._timeline_mark_mix_dirty()
        if self.timeline_canvas is not None:
            self.timeline_canvas.selected_clip_id = right.clip_id
            self.timeline_canvas._refresh_size()
            self.timeline_canvas.update()
        self._timeline_update_inspector()
        self._timeline_debug(f"Clip split id={source.clip_id} right_id={right.clip_id} at={split_time:.3f}s")


    def _timeline_delete_selected(self, checked: bool = False) -> None:
        clip = self._timeline_clip_by_id(self.timeline_selected_clip_id)
        if clip is None:
            QMessageBox.information(self, "Delete Clip", "Select a timeline clip first.")
            return
        self.timeline_clips = [existing for existing in self.timeline_clips if existing.clip_id != clip.clip_id]
        self.timeline_selected_clip_id = None
        self._timeline_update_duration()
        self._timeline_mark_mix_dirty()
        if self.timeline_canvas is not None:
            self.timeline_canvas.selected_clip_id = None
            self.timeline_canvas._refresh_size()
            self.timeline_canvas.update()
        self._timeline_update_inspector()
        self._timeline_debug(f"Clip deleted id={clip.clip_id}")

    def _timeline_render_mix(self, checked: bool = False) -> np.ndarray:
        self._timeline_update_duration()
        if not self.timeline_clips:
            self._timeline_debug("Arrangement mixdown clip_count=0 duration=0.000s peak=0.0000")
            QMessageBox.warning(self, "Timeline mix", "Drop at least one sound before rendering the mix.")
            self.timeline_last_mix = np.zeros((0, 2), dtype=np.float32)
            return self.timeline_last_mix
        total_samples = max(1, int(math.ceil(self.timeline_duration_seconds * SAMPLE_RATE)))
        mix = np.zeros((total_samples, 2), dtype=np.float32)
        for clip in self.timeline_clips:
            start = max(0, int(round(clip.start_time_seconds * SAMPLE_RATE)))
            clip_audio = self._timeline_render_clip_audio(clip)
            if clip_audio.size == 0:
                continue
            end = min(total_samples, start + len(clip_audio))
            if end <= start:
                continue
            mix[start:end, :2] += np.asarray(clip_audio[: end - start, :2], dtype=np.float32)
        peak = float(np.max(np.abs(mix))) if mix.size else 0.0
        if peak > 1.0:
            mix = mix / peak
        final_peak = float(np.max(np.abs(mix))) if mix.size else 0.0
        self.timeline_last_mix = mix.astype(np.float32, copy=False)
        self.timeline_mix_dirty = False
        self._timeline_debug(f"Arrangement mixdown clip_count={len(self.timeline_clips)} duration={len(mix) / SAMPLE_RATE:.3f}s peak={final_peak:.4f}")
        return self.timeline_last_mix

    def _timeline_play_story(self, checked: bool = False) -> None:
        self._timeline_debug("Timeline play clicked")
        mix = self._timeline_render_mix(checked=False)
        if mix.size == 0:
            return
        self.timeline_playhead_seconds = 0.0
        self.timeline_playback_started_at = time.monotonic()
        self.timeline_play_timer.start(33)
        if self.timeline_canvas is not None:
            self.timeline_canvas.update()
        if sd is None:
            self._timeline_debug("Playback fallback selected: sounddevice is not installed")
            ok, message = self._timeline_play_with_system_player(mix)
            if ok:
                QMessageBox.information(self, "Timeline playback fallback", message)
            else:
                QMessageBox.warning(self, "Timeline playback fallback", message)
            return
        try:
            sd.stop()
            sd.play(mix, SAMPLE_RATE, blocking=False)
        except Exception as exc:
            self._timeline_debug(f"Playback failed: {exc}")
            QMessageBox.warning(self, "Playback is not available", f"Timeline mix was rendered, but playback failed. Export still works.\n\nDetails: {exc}")

    def _timeline_play_with_system_player(self, mix: np.ndarray) -> Tuple[bool, str]:
        players = [
            ("xdg-open", ["xdg-open"]),
            ("paplay", ["paplay"]),
            ("aplay", ["aplay", "-q"]),
            ("ffplay", ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet"]),
            ("play", ["play", "-q"]),
        ]
        found = [(name, command) for name, command in players if shutil.which(name)]
        try:
            temp = tempfile.NamedTemporaryFile(prefix="wave_toy_timeline_", suffix=".wav", delete=False)
            temp_path = Path(temp.name)
            temp.close()
            save_wav(temp_path, mix, SAMPLE_RATE)
            self.timeline_fallback_temp_path = temp_path
            self._timeline_debug(f"Temporary playback file path={temp_path}")
        except Exception as exc:
            return False, f"Timeline mix was rendered, but WaveToy could not save a temporary WAV for fallback playback. Export Last Mix still works.\n\nDetails: {exc}"

        if not found:
            self._timeline_debug("Playback fallback failed: no system audio command found")
            return False, (
                "sounddevice is not installed, and WaveToy could not find a system audio player command. "
                "Export Last Mix still works.\n\n"
                f"Temporary WAV saved at:\n{temp_path}"
            )

        name, command = found[0]
        try:
            self.timeline_fallback_process = subprocess.Popen(
                [*command, str(temp_path)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            self._timeline_debug(f"Fallback subprocess started command={name} path={temp_path}")
            note = " Stop can terminate WaveToy's fallback subprocess when the player keeps running." if name != "xdg-open" else " The system player may continue separately if it takes over from xdg-open."
            return True, (
                "sounddevice is not installed, so WaveToy opened a temporary WAV with your system player. "
                "Export still works.\n\n"
                f"Player: {name}\nTemporary WAV: {temp_path}\n{note}"
            )
        except Exception as exc:
            self._timeline_debug(f"Fallback subprocess failed command={name} error={exc}")
            return False, (
                "sounddevice is not installed, and WaveToy could not open the temporary WAV with a system player. "
                "Export Last Mix still works.\n\n"
                f"Temporary WAV saved at:\n{temp_path}\n\nDetails: {exc}"
            )

    def _timeline_stop_story(self, checked: bool = False) -> None:
        self._timeline_debug("Stop clicked")
        self.timeline_play_timer.stop()
        self.timeline_playback_started_at = None
        if sd is not None:
            try:
                sd.stop()
            except Exception as exc:
                self._timeline_debug(f"sounddevice stop failed: {exc}")
        if self.timeline_fallback_process is not None and self.timeline_fallback_process.poll() is None:
            try:
                self.timeline_fallback_process.terminate()
                self._timeline_debug("Fallback subprocess stopped")
            except Exception as exc:
                self._timeline_debug(f"Fallback subprocess stop failed: {exc}")
        self.timeline_fallback_process = None
        if self.timeline_canvas is not None:
            self.timeline_canvas.update()

    def _timeline_playback_tick(self) -> None:
        if self.timeline_playback_started_at is None:
            self.timeline_play_timer.stop()
            return
        elapsed = time.monotonic() - self.timeline_playback_started_at
        duration = len(self.timeline_last_mix) / SAMPLE_RATE if self.timeline_last_mix.size else self.timeline_duration_seconds
        self.timeline_playhead_seconds = min(max(0.0, elapsed), max(0.0, duration))
        self._timeline_update_inspector()
        if self.timeline_canvas is not None:
            self.timeline_canvas.update()
        if duration > 0 and elapsed >= duration:
            self.timeline_play_timer.stop()
            self.timeline_playback_started_at = None

    def _timeline_export_last_mix(self, checked: bool = False) -> None:
        self._timeline_debug("Export attempted")
        mix = self._timeline_render_mix(checked=False)
        if mix.size == 0:
            self._timeline_debug("Export failed: empty mix")
            return
        filename, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Export Timeline Mix",
            "wave_toy_timeline_mix.wav",
            "WAV Audio (*.wav);;Ogg Vorbis (*.ogg);;MP3 Audio (*.mp3);;FLAC Audio (*.flac)",
        )
        if not filename:
            self._timeline_debug("Export failed: user cancelled")
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
            save_audio_file(path, mix)
            sidecar = path.with_suffix(path.suffix + ".wave-toy-arrangement.json")
            data = {
                "name": path.stem,
                "version": 1,
                "sample_rate": SAMPLE_RATE,
                "duration_seconds": len(mix) / SAMPLE_RATE,
                "clip_count": len(self.timeline_clips),
                "time_scale_model": "TimelineCanvas.seconds_per_pixel is the shared timeline scale; clip widths are visible_duration_seconds / seconds_per_pixel.",
                "snap_enabled": self.timeline_snap_enabled,
                "snap_seconds": self.timeline_snap_seconds,
                "edit_model": "Non-destructive trim_start_seconds, trim_end_seconds, and playback_rate duration-scaling metadata are applied during mixdown/export; pitch-preserving time stretch is rendered after trim and source audio arrays/source paths remain unchanged.",
                "palette_sources": [item.metadata() for item in self.timeline_audio_palette],
                "speech_bin_sources": [item.metadata() for item in self.timeline_speech_bin],
                "clip_source_types": [
                    "generated_wavetoy_sound",
                    "imported_audio",
                    "articulation_phoneme",
                    "articulation_chain_raw",
                    "articulation_word_render",
                    "articulation_syllable_render",
                ],
                "clips": [clip.metadata() for clip in self.timeline_clips],
                "notes": "Timeline metadata stores imported and speech source paths plus articulation snapshots only; raw audio arrays are not embedded. Missing speech cache audio should be re-rendered from speech_metadata.articulation_metadata when possible, otherwise the clip stays visible as muted with a warning.",
            }
            sidecar.write_text(json.dumps(data, indent=2), encoding="utf-8")
            self.timeline_last_mix_path = path
            self._timeline_debug(f"Export succeeded audio={path} sidecar={sidecar}")
            QMessageBox.information(self, "Timeline Exported", f"Saved timeline mix:\n{path}\n\nSaved arrangement metadata:\n{sidecar}")
        except Exception as exc:
            self._timeline_debug(f"Export failed: {exc}")
            QMessageBox.warning(self, "Could not export timeline", str(exc))

    def _build_play_tab(self) -> None:
        if self.tabs is None:
            return
        play = QWidget()
        play.setObjectName("playTab")
        layout = QVBoxLayout(play)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)

        title = QLabel("Synthesis")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignCenter)
        subtitle = QLabel("Fast performance controls. Use Wave Explorer for focused panels or Classic Controls for every fallback control.")
        subtitle.setObjectName("subtitle")
        subtitle.setWordWrap(True)
        subtitle.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        layout.addWidget(subtitle)

        if self.dashboard_canvas is not None:
            play_canvas = WaveCanvas()
            play_canvas.setMinimumSize(QSize(720, 340))
            play_canvas.setToolTip("Performance waveform view. Mouse wheel zooms only this waveform view.")
            self.play_canvas = play_canvas
            layout.addWidget(play_canvas, 1)

        controls = QHBoxLayout()
        controls.setSpacing(12)
        for label, color, callback in (
            ("Play", "#5cdb95", self._play),
            ("Stop", "#ff6b6b", self._stop),
            ("Save Audio", "#ffd166", self._save),
            ("Load Audio", "#b8f2e6", self._load_sound),
        ):
            button = ToyButton(label, color)
            button.setMinimumHeight(42)
            button.clicked.connect(callback)
            controls.addWidget(button)
        layout.addLayout(controls)
        layout.addStretch(1)
        self.tabs.insertTab(0, play, "Synthesis")

    def _build_wave_explorer_tab(self) -> None:
        if self.tabs is None:
            return
        tab = QWidget()
        tab.setObjectName("waveExplorerTab")
        self.wave_explorer_tab = tab
        tab_layout = QVBoxLayout(tab)
        tab_layout.setContentsMargins(12, 8, 12, 12)
        tab_layout.setSpacing(8)

        specs = {
            "shape": ("🎚 Shape Mix", "#5cdb95"),
            "stereo": ("👂 Stereo Space", "#7bdff2"),
            "tuning": ("🎼 Tuning Map", "#b8f2e6"),
            "pitch": ("Pitch Tools", "#ffd166"),
            "effects": ("Texture / Effects", "#d7b9ff"),
            "presets": ("🌈 Sound Experiment", "#ff99c8"),
        }
        toolbar = QWidget()
        toolbar.setObjectName("workspaceToolbar")
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(8, 6, 8, 6)
        toolbar_layout.setSpacing(8)
        self.visual_panel_buttons.clear()
        for key, (label, color) in specs.items():
            button = QPushButton(label)
            button.setObjectName("workspaceToolbarButton")
            button.setProperty("accentColor", color)
            button.setCursor(Qt.PointingHandCursor)
            button.setCheckable(True)
            button.setMinimumHeight(44)
            button.setMaximumHeight(52)
            button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            button.clicked.connect(lambda checked=False, panel_key=key: self._open_toy_panel(panel_key))
            self.visual_panel_buttons[key] = button
            toolbar_layout.addWidget(button)
        tab_layout.addWidget(toolbar, 0)

        dashboard_layout = QGridLayout()
        dashboard_layout.setContentsMargins(0, 0, 0, 0)
        dashboard_layout.setHorizontalSpacing(0)
        dashboard_layout.setVerticalSpacing(0)
        dashboard_layout.setColumnStretch(0, 1)
        dashboard_layout.setRowStretch(0, 1)

        explorer_panel = QWidget()
        explorer_panel.setObjectName("explorerDashboardPanel")
        explorer_layout = QVBoxLayout(explorer_panel)
        explorer_layout.setContentsMargins(12, 10, 12, 10)
        explorer_layout.setSpacing(6)
        explorer_title = QLabel("🌊 Wave Explorer")
        explorer_title.setObjectName("dashboardExplorerTitle")
        explorer_title.setAlignment(Qt.AlignCenter)
        explorer_hint = QLabel("Use the compact toolbar above for focused panels; the center stays reserved for the waveform.")
        explorer_hint.setObjectName("symbolHint")
        explorer_hint.setWordWrap(True)
        explorer_hint.setAlignment(Qt.AlignCenter)
        self.dashboard_summary_label = QLabel("Custom Wave • A4 Main • Piano Steps • No bends • All waves")
        self.dashboard_summary_label.setObjectName("dashboardSummary")
        self.dashboard_summary_label.setWordWrap(True)
        self.dashboard_summary_label.setAlignment(Qt.AlignCenter)
        self.articulation_wave_status_label = QLabel("🗣 No phoneme selected yet. Open Articulation Lab to design vowels.")
        self.articulation_wave_status_label.setObjectName("dashboardSummary")
        self.articulation_wave_status_label.setWordWrap(True)
        self.articulation_wave_status_label.setAlignment(Qt.AlignCenter)
        self.dashboard_canvas = WaveCanvas()
        self.dashboard_canvas.setMinimumSize(QSize(720, 500))
        self.dashboard_canvas.setToolTip("Central Wave Explorer. Mouse wheel zooms only this waveform view.")
        wave_controls = QHBoxLayout()
        wave_controls.setSpacing(8)
        for label, callback in (
            ("🔎 Zoom In", lambda checked=False: self.dashboard_canvas.zoom_by(1.25)),
            ("🔍 Zoom Out", lambda checked=False: self.dashboard_canvas.zoom_by(0.8)),
            ("⬅ Pan", lambda checked=False: self.dashboard_canvas.pan_view(-1.0)),
            ("➡ Pan", lambda checked=False: self.dashboard_canvas.pan_view(1.0)),
            ("↺ Reset", lambda checked=False: self.dashboard_canvas.reset_zoom()),
        ):
            button = QPushButton(label)
            button.setObjectName("waveExplorerControlButton")
            button.setMinimumHeight(WaveToySizing.BUTTON_HEIGHT)
            button.clicked.connect(callback)
            wave_controls.addWidget(button)

        explorer_layout.addWidget(explorer_title)
        explorer_layout.addWidget(explorer_hint)
        explorer_layout.addWidget(self.dashboard_canvas, 1)
        explorer_layout.addLayout(wave_controls)
        explorer_layout.addWidget(self.dashboard_summary_label)
        explorer_layout.addWidget(self.articulation_wave_status_label)
        dashboard_layout.addWidget(explorer_panel, 0, 0)
        tab_layout.addLayout(dashboard_layout, 1)

        self.tabs.insertTab(1, tab, "Wave Explorer")

    def _open_toy_panel(self, panel_key: str) -> None:
        self.active_dashboard_workspace = panel_key
        for key, button in self.visual_panel_buttons.items():
            is_active = key == panel_key
            button.setChecked(is_active)
            button.setDown(is_active)
            button.setProperty("active", is_active)
            button.style().unpolish(button)
            button.style().polish(button)
            button.update()
        panel = self.floating_toy_panels.get(panel_key)
        if panel is None:
            panel = QWidget(self, Qt.Tool)
            panel.setObjectName("toyFloatingPanel")
            panel.setWindowTitle(self._toy_panel_title(panel_key))
            panel.setMinimumSize(QSize(360, 220))
            panel.resize(self._toy_panel_size(panel_key))
            outer = QVBoxLayout(panel)
            outer.setContentsMargins(12, 10, 12, 12)
            outer.setSpacing(8)
            title = QLabel(self._toy_panel_title(panel_key))
            title.setObjectName("workspaceTitle")
            title.setWordWrap(True)
            grid = QGridLayout()
            grid.setHorizontalSpacing(8)
            grid.setVerticalSpacing(6)
            outer.addWidget(title)
            outer.addLayout(grid)
            old_title = self.dashboard_workspace_title
            old_layout = self.dashboard_workspace_layout
            self.dashboard_workspace_title = title
            self.dashboard_workspace_layout = grid
            builders = {
                "shape": self._build_shape_workspace,
                "pitch": self._build_pitch_workspace,
                "tuning": self._build_tuning_workspace,
                "stereo": self._build_stereo_workspace,
                "effects": self._build_effects_workspace,
                "presets": self._build_presets_workspace,
            }
            builders.get(panel_key, self._build_shape_workspace)()
            self.dashboard_workspace_title = old_title
            self.dashboard_workspace_layout = old_layout
            self.floating_toy_panels[panel_key] = panel
        panel.move(self._toy_panel_position(panel_key, panel.size()))
        panel.show()
        panel.raise_()
        panel.activateWindow()

    def _toy_panel_title(self, panel_key: str) -> str:
        return {
            "shape": "🎚 Shape Mix Toy Panel",
            "pitch": "Pitch Tools Panel",
            "tuning": "🎼 Tuning Map Panel",
            "stereo": "👂 Stereo Space Panel",
            "effects": "Texture / Effects Panel",
            "presets": "🌈 Sound Experiments Panel",
        }.get(panel_key, "🎛 Toy Panel")

    def _toy_panel_size(self, panel_key: str) -> QSize:
        return {
            "shape": QSize(520, 360),
            "pitch": QSize(560, 420),
            "tuning": QSize(430, 250),
            "stereo": QSize(540, 390),
            "effects": QSize(420, 260),
            "presets": QSize(420, 300),
        }.get(panel_key, QSize(420, 280))

    def _toy_panel_position(self, panel_key: str, panel_size: QSize) -> QPoint:
        anchor = self.wave_explorer_tab or self
        top_left = anchor.mapToGlobal(anchor.rect().topLeft())
        rect = anchor.rect()
        margin = 18
        positions = {
            "shape": (margin, margin),
            "pitch": (rect.width() - panel_size.width() - margin, margin),
            "stereo": (margin, rect.height() - panel_size.height() - margin),
            "effects": (rect.width() - panel_size.width() - margin, rect.height() - panel_size.height() - margin),
            "tuning": (margin, max(margin, rect.height() // 2 - panel_size.height() // 2)),
            "presets": (rect.width() - panel_size.width() - margin, max(margin, rect.height() // 2 - panel_size.height() // 2)),
        }
        x_offset, y_offset = positions.get(panel_key, (margin, margin))
        return QPoint(top_left.x() + max(margin, x_offset), top_left.y() + max(margin, y_offset))

    def _build_visual_dashboard(self, outer: QVBoxLayout) -> None:
        dashboard = self._toy_group("🐙 Wave Explorer Dashboard")
        dashboard.setObjectName("dashboardGroup")
        dashboard_layout = QGridLayout(dashboard)
        dashboard_layout.setContentsMargins(12, 18, 12, 12)
        dashboard_layout.setHorizontalSpacing(14)
        dashboard_layout.setVerticalSpacing(12)
        dashboard_layout.setColumnMinimumWidth(0, 220)
        dashboard_layout.setColumnMinimumWidth(1, 650)
        dashboard_layout.setColumnMinimumWidth(2, 220)
        dashboard_layout.setColumnStretch(0, 0)
        dashboard_layout.setColumnStretch(1, 1)
        dashboard_layout.setColumnStretch(2, 0)
        dashboard_layout.setRowMinimumHeight(0, 140)
        dashboard_layout.setRowMinimumHeight(1, 140)
        dashboard_layout.setRowMinimumHeight(2, 140)
        dashboard_layout.setRowStretch(0, 0)
        dashboard_layout.setRowStretch(1, 1)
        dashboard_layout.setRowStretch(2, 0)

        explorer_panel = QWidget()
        explorer_panel.setObjectName("explorerDashboardPanel")
        explorer_layout = QVBoxLayout(explorer_panel)
        explorer_layout.setContentsMargins(10, 10, 10, 10)
        explorer_layout.setSpacing(8)
        explorer_title = QLabel("🌊 Wave Explorer")
        explorer_title.setObjectName("dashboardExplorerTitle")
        explorer_title.setAlignment(Qt.AlignCenter)
        explorer_hint = QLabel("The waveform is the instrument. Every limb changes this center sound picture.")
        explorer_hint.setObjectName("symbolHint")
        explorer_hint.setWordWrap(True)
        explorer_hint.setAlignment(Qt.AlignCenter)
        self.dashboard_summary_label = QLabel("Custom Wave • A4 Main • Piano Steps • No bends • All waves")
        self.dashboard_summary_label.setObjectName("dashboardSummary")
        self.dashboard_summary_label.setWordWrap(True)
        self.dashboard_summary_label.setAlignment(Qt.AlignCenter)
        self.articulation_wave_status_label = QLabel("🗣 No phoneme selected yet. Open Articulation Lab to design vowels.")
        self.articulation_wave_status_label.setObjectName("dashboardSummary")
        self.articulation_wave_status_label.setWordWrap(True)
        self.articulation_wave_status_label.setAlignment(Qt.AlignCenter)
        self.dashboard_canvas = WaveCanvas()
        self.dashboard_canvas.setMinimumSize(QSize(640, 330))
        self.dashboard_canvas.setToolTip("Central Wave Explorer. Mouse wheel zooms only this waveform view.")
        explorer_open = ToyButton("🔍 Big View", "#7bdff2")
        explorer_open.setMinimumHeight(44)
        explorer_open.setMaximumWidth(150)
        explorer_open.clicked.connect(self._open_wave_explorer)

        explorer_layout.addWidget(explorer_title)
        explorer_layout.addWidget(explorer_hint)
        explorer_layout.addWidget(self.dashboard_canvas, 1)
        explorer_layout.addWidget(self.dashboard_summary_label)
        explorer_layout.addWidget(self.articulation_wave_status_label)
        explorer_layout.addWidget(explorer_open, 0, Qt.AlignRight)
        dashboard_layout.addWidget(explorer_panel, 1, 1)

        specs = {
            "shape": ("🎚 Shape Mix", "#5cdb95"),
            "pitch": ("Pitch Tools", "#ffd166"),
            "tuning": ("🎼 Tuning Map", "#b8f2e6"),
            "stereo": ("👂 Stereo Space", "#7bdff2"),
            "effects": ("Texture / Effects", "#d7b9ff"),
            "presets": ("🌈 Experiments", "#ff99c8"),
            "save": ("💾 Save Sound", "#ffd166"),
        }
        positions = {
            "shape": (0, 0, Qt.AlignRight | Qt.AlignBottom),
            "pitch": (0, 1, Qt.AlignHCenter | Qt.AlignBottom),
            "tuning": (0, 2, Qt.AlignLeft | Qt.AlignBottom),
            "stereo": (1, 0, Qt.AlignRight | Qt.AlignVCenter),
            "effects": (1, 2, Qt.AlignLeft | Qt.AlignVCenter),
            "presets": (2, 0, Qt.AlignRight | Qt.AlignTop),
            "save": (2, 2, Qt.AlignLeft | Qt.AlignTop),
        }
        for key, (label, color) in specs.items():
            button = VisualPanelButton(label, key, color)
            if key == "save":
                button.clicked.connect(self._save)
            else:
                button.clicked.connect(lambda checked=False, workspace=key: self._activate_dashboard_workspace(workspace))
            self.visual_panel_buttons[key] = button
            row, column, alignment = positions[key]
            dashboard_layout.addWidget(button, row, column, alignment)

        self.dashboard_workspace_panel = QWidget()
        self.dashboard_workspace_panel.setObjectName("workspacePanel")
        workspace_outer = QVBoxLayout(self.dashboard_workspace_panel)
        workspace_outer.setContentsMargins(10, 8, 10, 8)
        workspace_outer.setSpacing(6)
        self.dashboard_workspace_title = QLabel("Workspace")
        self.dashboard_workspace_title.setObjectName("workspaceTitle")
        self.dashboard_workspace_title.setWordWrap(True)
        self.dashboard_workspace_layout = QGridLayout()
        self.dashboard_workspace_layout.setHorizontalSpacing(8)
        self.dashboard_workspace_layout.setVerticalSpacing(6)
        workspace_outer.addWidget(self.dashboard_workspace_title)
        workspace_outer.addLayout(self.dashboard_workspace_layout)
        dashboard_layout.addWidget(self.dashboard_workspace_panel, 2, 1)

        outer.addWidget(dashboard)

    def _clear_dashboard_workspace(self) -> None:
        if self.dashboard_workspace_layout is None:
            return
        while self.dashboard_workspace_layout.count():
            item = self.dashboard_workspace_layout.takeAt(0)
            widget = item.widget()
            child_layout = item.layout()
            if widget is not None:
                widget.deleteLater()
            elif child_layout is not None:
                while child_layout.count():
                    child = child_layout.takeAt(0)
                    child_widget = child.widget()
                    if child_widget is not None:
                        child_widget.deleteLater()

    def _activate_dashboard_workspace(self, workspace: str) -> None:
        if self.dashboard_workspace_layout is None or self.dashboard_workspace_title is None:
            return
        self.active_dashboard_workspace = workspace
        for key, button in self.visual_panel_buttons.items():
            button.setDown(key == workspace)
        self._clear_dashboard_workspace()
        builders = {
            "shape": self._build_shape_workspace,
            "pitch": self._build_pitch_workspace,
            "tuning": self._build_tuning_workspace,
            "stereo": self._build_stereo_workspace,
            "effects": self._build_effects_workspace,
            "presets": self._build_presets_workspace,
        }
        builders.get(workspace, self._build_shape_workspace)()

    def _make_synced_slider(self, source: QSlider) -> NoWheelSlider:
        slider = NoWheelSlider(Qt.Horizontal)
        slider.setRange(source.minimum(), source.maximum())
        slider.setValue(source.value())
        slider.setTickInterval(source.tickInterval())
        slider.valueChanged.connect(source.setValue)
        source.valueChanged.connect(slider.setValue)
        return slider

    def _make_synced_combo(self, source: QComboBox) -> NoWheelComboBox:
        combo = NoWheelComboBox()
        for index in range(source.count()):
            combo.addItem(source.itemText(index), source.itemData(index))
        combo.setCurrentIndex(source.currentIndex())
        combo.currentIndexChanged.connect(source.setCurrentIndex)
        source.currentIndexChanged.connect(combo.setCurrentIndex)
        return combo

    def _make_synced_spin(self, source: QSpinBox) -> NoWheelSpinBox:
        spin = NoWheelSpinBox()
        spin.setRange(source.minimum(), source.maximum())
        spin.setValue(source.value())
        spin.valueChanged.connect(source.setValue)
        source.valueChanged.connect(spin.setValue)
        return spin

    def _make_synced_double_spin(self, source: QDoubleSpinBox) -> NoWheelDoubleSpinBox:
        spin = NoWheelDoubleSpinBox()
        spin.setRange(source.minimum(), source.maximum())
        spin.setDecimals(source.decimals())
        spin.setSingleStep(source.singleStep())
        spin.setSuffix(source.suffix())
        spin.setValue(source.value())
        spin.valueChanged.connect(source.setValue)
        source.valueChanged.connect(spin.setValue)
        return spin

    def _add_workspace_slider_row(self, row: int, label: str, source: QSlider) -> None:
        if self.dashboard_workspace_layout is None:
            return
        self.dashboard_workspace_layout.addWidget(QLabel(label), row, 0)
        self.dashboard_workspace_layout.addWidget(self._make_synced_slider(source), row, 1, 1, 2)

    def _build_shape_workspace(self) -> None:
        if self.dashboard_workspace_layout is None or self.dashboard_workspace_title is None:
            return
        self.dashboard_workspace_title.setText("🎚 Shape Mix — mute, solo, loudness, and envelope time without hiding the waveform.")
        headers = ["Wave", "Mute", "Solo", "Start", "End", "Time"]
        for column, header in enumerate(headers):
            self.dashboard_workspace_layout.addWidget(QLabel(header), 0, column)
        for row, wave_type in enumerate(self.wave_row_order, start=1):
            self.dashboard_workspace_layout.addWidget(QLabel(f"{self._wave_icon(wave_type)} {wave_label_for(self._settings_from_ui(), wave_type)}"), row, 0)
            mute = QCheckBox()
            mute.setChecked(self.wave_mute_buttons[wave_type].isChecked())
            mute.stateChanged.connect(lambda state, wt=wave_type: self.wave_mute_buttons[wt].setChecked(bool(state)))
            self.wave_mute_buttons[wave_type].stateChanged.connect(mute.setChecked)
            solo = QCheckBox()
            solo.setChecked(self.wave_solo_buttons[wave_type].isChecked())
            solo.stateChanged.connect(lambda state, wt=wave_type: self.wave_solo_buttons[wt].setChecked(bool(state)))
            self.wave_solo_buttons[wave_type].stateChanged.connect(solo.setChecked)
            self.dashboard_workspace_layout.addWidget(mute, row, 1)
            self.dashboard_workspace_layout.addWidget(solo, row, 2)
            self.dashboard_workspace_layout.addWidget(self._make_synced_slider(self.wave_start_sliders[wave_type]), row, 3)
            self.dashboard_workspace_layout.addWidget(self._make_synced_slider(self.wave_end_sliders[wave_type]), row, 4)
            self.dashboard_workspace_layout.addWidget(self._make_synced_slider(self.wave_time_sliders[wave_type]), row, 5)

    def _build_pitch_workspace(self) -> None:
        if self.dashboard_workspace_layout is None or self.dashboard_workspace_title is None:
            return
        self.dashboard_workspace_title.setText("🎯 Pitch Workspace — Note Wheel ideas without hiding the waveform.")
        self.dashboard_workspace_layout.addWidget(QLabel("🎵 Main Note"), 0, 0)
        self.dashboard_workspace_layout.addWidget(self._make_synced_combo(self.note_combo), 0, 1)
        self._add_workspace_slider_row(1, "🧸 Size", self.octave_slider)
        self._add_workspace_slider_row(2, "🎯 Wiggle", self.cents_slider)
        self._add_workspace_slider_row(3, "Start Pitch", self.pitch_start)
        self._add_workspace_slider_row(4, "End Pitch", self.pitch_end)
        for index, wave_type in enumerate(self.wave_row_order, start=5):
            follow = QCheckBox("👯 Follow Main")
            follow.setChecked(self.wave_follow_pitch_buttons[wave_type].isChecked())
            follow.stateChanged.connect(lambda state, wt=wave_type: self.wave_follow_pitch_buttons[wt].setChecked(bool(state)))
            self.wave_follow_pitch_buttons[wave_type].stateChanged.connect(follow.setChecked)
            note = self._make_synced_combo(self.wave_note_combos[wave_type])
            octave = self._make_synced_spin(self.wave_octave_spins[wave_type])
            cents = self._make_synced_slider(self.wave_cents_sliders[wave_type])
            wheel = QPushButton("🎡 Note Wheel")
            wheel.clicked.connect(lambda checked=False, wt=wave_type: self._open_note_wheel(wt))
            self.dashboard_workspace_layout.addWidget(QLabel(f"{self._wave_icon(wave_type)}"), index, 0)
            self.dashboard_workspace_layout.addWidget(follow, index, 1)
            self.dashboard_workspace_layout.addWidget(note, index, 2)
            self.dashboard_workspace_layout.addWidget(octave, index, 3)
            self.dashboard_workspace_layout.addWidget(cents, index, 4)
            self.dashboard_workspace_layout.addWidget(wheel, index, 5)

    def _build_tuning_workspace(self) -> None:
        if self.dashboard_workspace_layout is None or self.dashboard_workspace_title is None:
            return
        self.dashboard_workspace_title.setText("🎼 Tuning Workspace — map notes while the waveform remains in view.")
        self.dashboard_workspace_layout.addWidget(QLabel("🎼 Tuning Map"), 0, 0)
        self.dashboard_workspace_layout.addWidget(self._make_synced_combo(self.tuning_method_combo), 0, 1, 1, 2)
        self.dashboard_workspace_layout.addWidget(QLabel("Home Note"), 1, 0)
        self.dashboard_workspace_layout.addWidget(self._make_synced_combo(self.tuning_root_combo), 1, 1, 1, 2)
        self.dashboard_workspace_layout.addWidget(QLabel("A4 Sparkle"), 2, 0)
        self.dashboard_workspace_layout.addWidget(self._make_synced_double_spin(self.tuning_reference_spin), 2, 1, 1, 2)
        explanation = QLabel("Tuning changes how notes are spaced. Root chooses the home note; A4 Sparkle is the reference pitch in Hz.")
        explanation.setWordWrap(True)
        explanation.setObjectName("symbolHint")
        self.dashboard_workspace_layout.addWidget(explanation, 3, 0, 1, 3)

    def _build_stereo_workspace(self) -> None:
        if self.dashboard_workspace_layout is None or self.dashboard_workspace_title is None:
            return
        self.dashboard_workspace_title.setText("👂 Stereo Space — whole mix plus per-wave left, center, right, width, and dance.")
        self._add_workspace_slider_row(0, "Mix Start L↔R", self.pan_start_slider)
        self._add_workspace_slider_row(1, "Mix End L↔R", self.pan_end_slider)
        self._add_workspace_slider_row(2, "Mix Width", self.width_slider)
        self._add_workspace_slider_row(3, "Mix Dance", self.auto_pan_depth_slider)
        self._add_workspace_slider_row(4, "Dance Speed", self.auto_pan_rate)
        for row, wave_type in enumerate(self.wave_row_order, start=5):
            self.dashboard_workspace_layout.addWidget(QLabel(f"{self._wave_icon(wave_type)}"), row, 0)
            self.dashboard_workspace_layout.addWidget(self._make_synced_slider(self.wave_pan_sliders[wave_type]), row, 1)
            self.dashboard_workspace_layout.addWidget(self._make_synced_slider(self.wave_width_sliders[wave_type]), row, 2)
            self.dashboard_workspace_layout.addWidget(self._make_synced_slider(self.wave_dance_sliders[wave_type]), row, 3)

    def _build_effects_workspace(self) -> None:
        if self.dashboard_workspace_layout is None or self.dashboard_workspace_title is None:
            return
        self.dashboard_workspace_title.setText("Texture / Effects Workspace — signal processors around the waveform.")
        nap = QCheckBox("😴 Paulstretch Nap")
        nap.setChecked(self.paulstretch_enabled.isChecked())
        nap.stateChanged.connect(lambda state: self.paulstretch_enabled.setChecked(bool(state)))
        self.paulstretch_enabled.stateChanged.connect(nap.setChecked)
        self.dashboard_workspace_layout.addWidget(nap, 0, 0, 1, 3)
        self._add_workspace_slider_row(1, "Dream Amount", self.paul_amount_slider)
        self._add_workspace_slider_row(2, "Evolution", self.paul_evolution_slider)

    def _build_presets_workspace(self) -> None:
        if self.dashboard_workspace_layout is None or self.dashboard_workspace_title is None:
            return
        self.dashboard_workspace_title.setText("🌈 Experiments Workspace — jump between sounds without leaving the Explorer.")
        presets = [
            ("Pure A4", self._preset_pure_a4),
            ("Rocket Pitch 🚀", self._preset_rocket_pitch),
            ("Robot Beep 🤖", self._preset_robot_beep),
            ("Falling Star ⭐", self._preset_falling_star),
            ("Fade-In Mountain 🏔️", self._preset_fade_in_triangle),
        ]
        for index, (label, callback) in enumerate(presets):
            button = QPushButton(label)
            button.clicked.connect(callback)
            self.dashboard_workspace_layout.addWidget(button, index // 2, index % 2)
        save = QPushButton("💾 Save")
        save.clicked.connect(self._save)
        load = QPushButton("📂 Load")
        load.clicked.connect(self._load_sound)
        self.dashboard_workspace_layout.addWidget(save, 3, 0)
        self.dashboard_workspace_layout.addWidget(load, 3, 1)

    def _dashboard_audio_thumbnail(self, points: int = 72) -> np.ndarray:
        if self.current_audio.size == 0:
            return np.zeros(0, dtype=np.float32)
        mono = np.asarray(self.current_audio, dtype=np.float32)
        if mono.ndim == 2:
            mono = mono.mean(axis=1)
        mono = mono.reshape(-1)
        if mono.size == 0:
            return np.zeros(0, dtype=np.float32)
        indices = np.linspace(0, mono.size - 1, min(points, mono.size)).astype(np.int64)
        return np.clip(mono[indices], -1.0, 1.0)

    def _update_visual_panel_buttons(self) -> None:
        if not self.visual_panel_buttons:
            return
        status_buttons = {key: button for key, button in self.visual_panel_buttons.items() if hasattr(button, "set_status")}
        s = self.current_settings
        live_samples = self._dashboard_audio_thumbnail()
        muted = s.wave_muted or {}
        wave_order = active_wave_order(s)
        solo = s.solo_wave if s.solo_wave in wave_order else None
        amps = {
            wave: max(db_to_gain((s.wave_start_db or {}).get(wave, -20.0)), db_to_gain((s.wave_end_db or {}).get(wave, -20.0)))
            for wave in wave_order
        }
        active = [wave for wave in wave_order if not muted.get(wave, False) and (solo is None or solo == wave) and amps[wave] > 0.01]
        shape_status = f"Solo {wave_label_for(s, solo).split()[0]}" if solo else f"{len(active)} Waves"
        if "shape" in status_buttons:
            status_buttons["shape"].set_status(shape_status, {"amps": amps, "muted": muted, "solo": solo, "samples": live_samples})

        follow = s.wave_follow_main_pitch or {wave: True for wave in wave_order}
        notes = s.wave_note or {wave: s.note for wave in wave_order}
        pitch_items = []
        custom = []
        for wave in wave_order:
            color = VisualPanelButton.COLORS.get(wave_shape_for(s, wave), QColor("#ff4fa3"))
            note_text = s.note if follow.get(wave, True) else str(notes.get(wave, s.note))
            pitch_items.append((wave, note_text, color))
            if not follow.get(wave, True):
                custom.append(f"{wave.title()} {note_text}")
        pitch_status = f"{s.note}{int(round(s.octave))} Main" if not custom else "Custom Notes"
        if "pitch" in status_buttons:
            status_buttons["pitch"].set_status(pitch_status, {"notes": pitch_items})

        tuning_label = TUNING_METHODS.get(s.tuning_method, TUNING_METHODS["equal_temperament_12"])["label"]
        if "tuning" in status_buttons:
            status_buttons["tuning"].set_status(str(tuning_label), {"method": tuning_label, "root": s.tuning_root_note})

        positions = []
        wave_pan = s.wave_pan or {}
        wave_width = s.wave_width or {}
        wave_dance = s.wave_dance or {}
        for wave in wave_order:
            positions.append((wave, wave_pan.get(wave, 0.0), wave_width.get(wave, 0.65), wave_dance.get(wave, 0.0)))
        stereo_status = "Dancing" if s.auto_pan_depth > 0.05 or any(float(item[3]) > 0.05 for item in positions) else "Wide" if s.stereo_width > 0.55 else "Centered"
        if "stereo" in status_buttons:
            status_buttons["stereo"].set_status(stereo_status, {"positions": positions})

        paul_active = not (s.muted_modules or {}).get("paulstretch", True)
        effect_status = "Paulstretch On" if paul_active else "Paulstretch Off"
        if "effects" in status_buttons:
            status_buttons["effects"].set_status(effect_status, {"paul_active": paul_active, "amount": s.paulstretch_amount, "after_samples": live_samples})

        recipe_count = len(self._read_user_recipes())
        preset_status = f"{recipe_count} Saved" if recipe_count else "Try Presets"
        if "presets" in status_buttons:
            status_buttons["presets"].set_status(preset_status, {"count": recipe_count})
        if "save" in self.visual_panel_buttons:
            self.visual_panel_buttons["save"].set_status("WAV + Recipe", {"samples": live_samples})
        self._update_dashboard_summary(s, tuning_label, solo, active)

    def _update_dashboard_summary(self, s: SynthSettings, tuning_label: str, solo: str | None, active: List[str]) -> None:
        if self.dashboard_summary_label is None:
            return
        sound_name = "Custom Wave"
        main_pitch = f"{s.note}{int(round(s.octave))} Main"
        bend_hz = abs(float(s.pitch_start_hz) - float(s.pitch_end_hz))
        bend_text = "Pitch bend on" if bend_hz > 0.5 else "No bends"
        if solo:
            mute_text = f"Solo {wave_label_for(s, solo).split()[0]}"
        else:
            muted_count = sum(1 for muted_value in (s.wave_muted or {}).values() if muted_value)
            mute_text = "All waves" if muted_count == 0 else f"{muted_count} muted • {len(active)} active"
        self.dashboard_summary_label.setText(
            f"{sound_name} • {main_pitch} • {tuning_label} • {bend_text} • {mute_text}"
        )

    def _toy_group(self, title: str) -> QGroupBox:
        box = QGroupBox(title)
        box.setObjectName("toyGroup")
        box.setMinimumHeight(90)
        return box

    def _make_percent_slider(self, minimum: int, maximum: int, value: int) -> QSlider:
        slider = NoWheelSlider(Qt.Horizontal)
        slider.setRange(minimum * PERCENT_SLIDER_SCALE, maximum * PERCENT_SLIDER_SCALE)
        slider.setValue(value * PERCENT_SLIDER_SCALE)
        slider.setTickInterval(10 * PERCENT_SLIDER_SCALE)
        return slider

    def _wave_icon(self, wave_type: str) -> str:
        shape = self._wave_shapes_from_ui().get(wave_type, wave_type) if hasattr(self, "wave_shape_combos") else wave_type
        return {
            "sine": "〰️",
            "triangle": "🔺",
            "sawtooth": "📐",
            "square": "🧱",
        }.get(shape, "〰️")

    def _slider_style_sheet(self) -> str:
        """Return centralized slider styling for larger, rounder controls."""
        return f"""
            QSlider {{
                min-height: {SLIDER_MIN_HEIGHT}px;
            }}
            QWidget#sliderCell QSlider {{
                min-height: 38px;
            }}
            QSlider::groove:horizontal {{
                height: {SLIDER_GROOVE_HEIGHT}px;
                background: #d7f3ff;
                border-radius: {SLIDER_GROOVE_RADIUS}px;
            }}
            QSlider::sub-page:horizontal {{
                background: #eef3f8;
                border-radius: {SLIDER_GROOVE_RADIUS}px;
            }}
            QSlider::handle:horizontal {{
                background: #ff4fa3;
                border: 1px solid white;
                width: {SLIDER_HANDLE_SIZE}px;
                height: {SLIDER_HANDLE_SIZE}px;
                margin: {SLIDER_HANDLE_MARGIN}px 0;
                border-radius: {SLIDER_HANDLE_RADIUS}px;
            }}
            QSlider::handle:horizontal:hover {{
                background: #ff2f91;
            }}
        """

    def _apply_style(self) -> None:
        base_style = """
            QMainWindow {
                background: #eef3f8;
            }
            QScrollArea {
                background: #eef3f8;
            }
            QTabWidget#mainTabs::pane {
                border: 0;
                background: #eef3f8;
            }
            QTabBar::tab {
                background: #e9fbff;
                border: 1px solid rgba(0, 0, 0, 0.12);
                border-bottom: 0;
                border-top-left-radius: 14px;
                border-top-right-radius: 14px;
                color: #263238;
                font-size: 14px;
                font-weight: 900;
                min-height: 42px;
                padding: 8px 22px;
            }
            QTabBar::tab:selected {
                background: #ffffff;
            }
            QWidget#waveExplorerTab, QWidget#playTab, QWidget#timelineStoryboardTab, QWidget#libraryTab, QScrollArea#graphicalEditorTab, QWidget#graphicalEditorPage {
                background: #eef3f8;
            }
            QWidget#graphicalWorkflowCard {
                background: rgba(255, 255, 255, 0.86);
                border: 1px solid rgba(255, 153, 200, 0.72);
                border-radius: 12px;
            }
            QWidget#graphicalLayerList {
                background: transparent;
            }
            QWidget#graphicalWaveToolbar {
                background: transparent;
            }
            QWidget#graphicalWaveCardHeader {
                background: rgba(255, 255, 255, 0.54);
                border-top-left-radius: 16px;
                border-top-right-radius: 16px;
                border-bottom: 2px solid rgba(38, 50, 56, 0.10);
            }
            QWidget#graphicalWaveCardBody {
                background: transparent;
                border-bottom-left-radius: 16px;
                border-bottom-right-radius: 16px;
            }
            QLabel#graphicalEffectBlock {
                background: #f7fafc;
                border: 4px dashed rgba(123, 44, 191, 0.72);
                border-radius: 10px;
                color: #263238;
                font-size: 13px;
                font-weight: 900;
                padding: 8px;
            }
            QLabel#timelineStoryboardTitle {
                font-size: 28px;
                font-weight: 900;
                color: #263238;
            }
            QLabel#timelineStoryboardSubtitle {
                font-size: 15px;
                font-weight: 900;
                color: #37474f;
            }
            QWidget#storyTransportBar {
                background: rgba(255, 255, 255, 0.72);
                border: 1px solid rgba(255, 153, 200, 0.58);
                border-radius: 12px;
            }
            QPushButton#storyTransportButton {
                min-height: 44px;
                font-size: 15px;
                font-weight: 900;
                border-radius: 10px;
                padding: 8px 14px;
            }
            QScrollArea#storyboardScroll, QWidget#storyboardLaneRoot {
                background: transparent;
            }
            QWidget#timelineCanvas {
                background: #e6f0fb;
                border: 1px solid rgba(0, 0, 0, 0.12);
                border-radius: 10px;
            }
            QWidget#timelineInspector, QWidget#timelineAudioPalette, QWidget#speechAssetsPanel {
                background: #f7fafc;
                border: 1px solid rgba(255, 153, 200, 0.72);
                border-radius: 10px;
            }
            QWidget#timelinePaletteList {
                background: transparent;
            }
            QLabel#timelineInspectorTitle {
                font-size: 14px;
                font-weight: 900;
                color: #263238;
            }
            QLabel#timelineInspectorText {
                font-size: 13px;
                font-weight: 800;
                color: #37474f;
            }
            QWidget#storyboardLane {
                background: #eefbff;
                border: 1px solid rgba(123, 223, 242, 0.78);
                border-radius: 12px;
            }
            QLabel#storyboardLaneHeader {
                background: #ffffff;
                border: 1px solid rgba(0, 0, 0, 0.14);
                border-radius: 10px;
                color: #263238;
                font-size: 15px;
                font-weight: 900;
                padding: 8px;
            }
            QWidget#storyboardClipStrip {
                background: rgba(255, 255, 255, 0.62);
                border: 1px dashed rgba(0, 0, 0, 0.12);
                border-radius: 10px;
            }
            QWidget#storyboardClip {
                background: #f7fafc;
                border: 1px solid rgba(255, 153, 200, 0.82);
                border-radius: 10px;
            }
            QLabel#storyboardClipIcon {
                font-size: 28px;
                background: #ffffff;
                border: 1px solid rgba(0, 0, 0, 0.10);
                border-radius: 18px;
            }
            QLabel#storyboardClipName {
                font-size: 15px;
                font-weight: 900;
                color: #263238;
            }
            QLabel#storyboardClipDuration {
                font-size: 13px;
                font-weight: 900;
                color: #607d8b;
            }
            QPushButton#storyboardTinyAction {
                min-width: 48px;
                min-height: 36px;
                border-radius: 16px;
                font-size: 15px;
                padding: 0;
            }
            QWidget#toyFloatingPanel {
                background: #f7fafc;
                border: 1px solid rgba(255, 153, 200, 0.75);
                border-radius: 10px;
            }
            QWidget#appShell {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #7bdff2, stop:0.55 #fff1d6, stop:1 #ff99c8);
            }
            QWidget#toyTitleBanner {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ffffff, stop:0.48 #fff8d9, stop:1 #ffd6e8);
                border: 1px solid rgba(255, 79, 163, 0.72);
                border-radius: 12px;
            }
            QLabel#toyTitleText {
                font-size: 26px;
                font-weight: 900;
                color: #263238;
                letter-spacing: 1px;
            }
            QLabel#toyTitleSubtitle {
                font-size: 15px;
                font-weight: 900;
                color: #4361ee;
            }
            QLabel#toyTitleIconRail {
                background: rgba(255, 255, 255, 0.76);
                border: 1px solid rgba(0, 0, 0, 0.10);
                border-radius: 10px;
                font-size: 14px;
                font-weight: 900;
                padding: 4px;
            }
            QLabel#title {
                font-size: 28px;
                font-weight: 900;
                color: #263238;
            }
            QLabel#subtitle {
                font-size: 14px;
                font-weight: 700;
                color: #37474f;
            }
            QGroupBox#toyGroup {
                background: #ffffff;
                border: 1px solid rgba(0, 0, 0, 0.16);
                border-radius: 8px;
                margin-top: 16px;
                padding: 10px;
                font-size: 14px;
                font-weight: 900;
                color: #263238;
            }
            QGroupBox#toyGroup::title {
                subcontrol-origin: margin;
                left: 16px;
                padding: 1px 8px;
                background: #ffffff;
                border-radius: 8px;
            }
            QGroupBox#dashboardGroup {
                background: #ffffff;
                border: 1px solid rgba(0, 0, 0, 0.18);
                border-radius: 10px;
                margin-top: 16px;
                padding: 10px;
                font-size: 14px;
                font-weight: 900;
                color: #263238;
            }
            QGroupBox#dashboardGroup::title {
                subcontrol-origin: margin;
                left: 16px;
                padding: 1px 8px;
                background: #ffffff;
                border-radius: 8px;
            }
            QWidget#explorerDashboardPanel {
                background: #eefbff;
                border: 1px solid rgba(123, 223, 242, 0.78);
                border-radius: 12px;
                padding: 8px;
            }
            QLabel#dashboardExplorerTitle {
                font-size: 26px;
                font-weight: 900;
                color: #263238;
            }
            QLabel#dashboardSummary {
                background: rgba(255, 255, 255, 0.82);
                border: 2px solid rgba(0, 0, 0, 0.10);
                border-radius: 14px;
                color: #263238;
                font-size: 14px;
                font-weight: 900;
                padding: 6px;
            }
            QWidget#workspacePanel {
                background: rgba(255, 255, 255, 0.78);
                border: 2px solid rgba(0, 0, 0, 0.10);
                border-radius: 16px;
            }
            QWidget#workspaceToolbar {
                background: rgba(255, 255, 255, 0.84);
                border: 2px solid rgba(0, 0, 0, 0.10);
                border-radius: 16px;
            }
            QPushButton#workspaceToolbarButton {
                background: rgba(255, 255, 255, 0.90);
                border: 2px solid rgba(38, 50, 56, 0.16);
                border-radius: 14px;
                color: #263238;
                font-size: 14px;
                font-weight: 900;
                padding: 6px 10px;
            }
            QPushButton#workspaceToolbarButton:checked,
            QPushButton#workspaceToolbarButton[active="true"] {
                background: #fff7c7;
                border: 1px solid rgba(92, 219, 149, 0.86);
                padding: 4px 8px;
            }
            QLabel#workspaceTitle {
                font-size: 14px;
                font-weight: 900;
                color: #263238;
            }
            QWidget#waveCard {
                background: #f9fbff;
                border: 1px solid rgba(0, 0, 0, 0.10);
                border-radius: 16px;
            }
            QWidget#waveCardMuted {
                background: #eef1f4;
                border: 1px dashed rgba(69, 90, 100, 0.25);
                border-radius: 16px;
            }
            QWidget#waveCardSolo {
                background: #f7fafc;
                border: 1px solid #ffd166;
                border-radius: 16px;
            }
            QWidget#waveCardSelected {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #f0fff7, stop:1 #fff7d6);
                border: 1px solid #5cdb95;
                border-radius: 18px;
            }
            QWidget#sliderCell, QWidget#earPreviewCell, QWidget#signalStage {
                background: transparent;
            }
            QWidget#pitchNotePanel {
                background: #fff3c4;
                border: 2px solid rgba(255, 209, 102, 0.85);
                border-radius: 10px;
            }
            QLabel#tinyPitchLabel {
                font-size: 10px;
                font-weight: 900;
                color: #6d4c41;
            }
            QLabel#waveCardTitle {
                font-size: 13px;
                font-weight: 900;
            }
            QLabel#signalStageTitle {
                font-size: 12px;
                font-weight: 900;
                color: #455a64;
            }
            QLabel#signalFlowArrow {
                font-size: 15px;
                font-weight: 900;
                color: #90a4ae;
            }
            QLabel#controlCaption {
                font-size: 11px;
                font-weight: 900;
                color: #607d8b;
            }
            QLabel#controlValue {
                font-size: 12px;
                font-weight: 900;
                color: #263238;
            }
            QLabel#articulationPhonemeTitle {
                font-size: 26px;
                font-weight: 900;
                color: #263238;
            }
            QLabel#articulationIpaBadge {
                background: #ffffff;
                border: 1px solid rgba(0, 0, 0, 0.14);
                border-radius: 8px;
                font-size: 14px;
                font-weight: 900;
                padding: 7px;
            }
            QLabel#articulationControlLabel {
                font-size: 15px;
                font-weight: 900;
                color: #263238;
            }
            QLabel#phonemeCardIpa {
                background: rgba(255, 255, 255, 0.82);
                border: 1px solid rgba(0, 0, 0, 0.12);
                border-radius: 18px;
                font-size: 14px;
                font-weight: 900;
                color: #1d1d1d;
                padding: 8px;
            }
            QLabel#phonemeCardTitle {
                font-size: 15px;
                font-weight: 900;
                color: #1d1d1d;
            }
            QLabel#phonemeCardSummary {
                font-size: 13px;
                font-weight: 900;
                color: #263238;
            }
            QPushButton#phonemeCardPrimaryAction, QPushButton#phonemeCardDangerAction, QPushButton#phonemeCardSecondaryAction {
                border-radius: 16px;
                font-size: 14px;
                font-weight: 900;
                padding: 8px 10px;
                min-height: 36px;
            }
            QPushButton#phonemeCardPrimaryAction {
                background: #5cdb95;
            }
            QPushButton#phonemeCardDangerAction {
                background: #ffadad;
            }
            QPushButton#phonemeCardSecondaryAction {
                background: #eefbff;
            }
            QPushButton#articulationPresetButton {
                border-radius: 18px;
                border: 1px solid rgba(0, 0, 0, 0.16);
                background: #fff7e6;
                font-size: 14px;
                font-weight: 900;
                min-height: 40px;
                max-height: 64px;
                padding: 6px 10px;
                text-align: left;
            }
            QPushButton#articulationPresetButton:hover {
                background: #fff0bd;
                border-color: rgba(255, 79, 163, 0.62);
            }
            QPushButton#articulationPresetButton:pressed {
                background: #ffd166;
                padding-top: 13px;
            }
            QWidget#articulationLabTab {
                background: #fff1d6;
            }
            QWidget#articulationLabHeader {
                background: rgba(255, 255, 255, 0.72);
                border: 1px solid rgba(0, 0, 0, 0.10);
                border-radius: 18px;
            }
            QLabel#articulationCompactTitle {
                font-size: 14px;
                font-weight: 900;
                color: #263238;
            }
            QLabel#articulationInfoBadge {
                background: #eefbff;
                border: 2px solid rgba(123, 223, 242, 0.88);
                border-radius: 14px;
                color: #37474f;
                font-size: 13px;
                font-weight: 900;
                padding: 6px 10px;
            }
            QWidget#articulationControlsCard {
                background: #ffffff;
            }
            QScrollArea#articulationLabTab, QScrollArea#phonemeDrawerScroll {
                background: transparent;
                border: 0;
            }
            QWidget#articulationToyControl {
                background: #fff7e6;
                border: 1px solid rgba(0, 0, 0, 0.10);
                border-radius: 18px;
            }
            QLabel#articulationToyLabel {
                font-size: 14px;
                font-weight: 900;
                color: #263238;
            }
            QLabel#articulationToyEndpoint {
                font-size: 12px;
                font-weight: 900;
                color: #607d8b;
            }
            QLabel#articulationToyValue {
                background: #ffffff;
                border: 2px solid rgba(0, 0, 0, 0.12);
                border-radius: 12px;
                color: #263238;
                font-size: 14px;
                font-weight: 900;
                padding: 5px 7px;
            }
            QCheckBox#articulationVoiceToggle {
                background: #ffffff;
                border: 2px solid rgba(0, 0, 0, 0.12);
                border-radius: 14px;
                padding: 8px 12px;
                font-size: 15px;
            }
            QWidget#phonemeDrawerShell {
                background: rgba(255, 255, 255, 0.60);
                border: 1px solid rgba(0, 0, 0, 0.12);
                border-radius: 10px;
            }
            QWidget#phonemeIconRail {
                background: #eefbff;
                border-radius: 8px;
            }
            QWidget#articulationStatusStrip {
                background: transparent;
                border: 0;
            }
            QLabel#articulationFormantStrip, QLabel#articulationSummaryStrip {
                background: rgba(255, 255, 255, 0.80);
                border: 1px solid rgba(0, 0, 0, 0.10);
                border-radius: 16px;
                color: #263238;
                font-size: 13px;
                font-weight: 900;
                padding: 7px 10px;
            }
            QLabel#articulationSummaryStrip {
                background: rgba(255, 247, 230, 0.92);
            }
            QLabel#articulationDebugStrip {
                background: rgba(238, 246, 255, 0.94);
                border: 2px dashed rgba(58, 80, 107, 0.42);
                border-radius: 14px;
                color: #263238;
                font-family: monospace;
                font-size: 12px;
                font-weight: 900;
                padding: 6px 9px;
            }
            QPushButton#phonemeRailButton {
                background: #ffffff;
                border: 1px solid rgba(0, 0, 0, 0.12);
                border-radius: 18px;
                color: #263238;
                font-size: 14px;
                font-weight: 900;
                padding: 4px;
            }
            QPushButton#phonemeRailButton:checked {
                background: #ffd166;
                border: 1px solid #ff4fa3;
            }
            QWidget#phonemeDrawerPage, QWidget#phonemeDrawerBody {
                background: transparent;
            }
            QWidget#phonemeDrawerHeader {
                background: #ffffff;
                border-top-right-radius: 20px;
                border-bottom: 3px solid rgba(0, 0, 0, 0.08);
            }
            QLabel#phonemeDrawerTitle {
                font-size: 14px;
                font-weight: 900;
                color: #263238;
            }

            QLabel {
                font-size: 14px;
                font-weight: 700;
                color: #263238;
            }
            QLabel#explain {
                font-size: 14px;
                font-weight: 700;
                color: #263238;
                padding: 10px;
            }
            QLabel#loopStatus {
                font-size: 13px;
                font-weight: 900;
                color: #263238;
                background: #ffffff;
                border: 1px solid rgba(0, 0, 0, 0.14);
                border-radius: 16px;
                padding: 10px;
            }
            QCheckBox {
                font-size: 13px;
                font-weight: 800;
                color: #263238;
            }
            QComboBox, QSpinBox, QDoubleSpinBox {
                min-height: 38px;
                border: 1px solid rgba(0, 0, 0, 0.18);
                border-radius: 12px;
                padding: 4px 8px;
                font-size: 14px;
                background: #f9fbff;
            }
            QPushButton {
                min-height: 34px;
                border-radius: 14px;
                border: 1px solid rgba(0, 0, 0, 0.12);
                background: #f1f7ff;
                font-size: 14px;
                font-weight: 800;
                padding: 6px 10px;
            }
            QPushButton:hover {
                background: #e2f2ff;
            }
            QWidget#collapsibleSection {
                background: transparent;
                margin: 0;
            }
            QToolButton#collapsibleHeader {
                background: #ffffff;
                border: 1px solid rgba(255, 153, 200, 0.62);
                border-radius: 8px;
                color: #263238;
                font-size: 15px;
                font-weight: 900;
                min-height: 40px;
                padding: 10px 14px;
                text-align: left;
            }
            QToolButton#collapsibleHeader:hover {
                background: #f7fafc;
            }
            """
        self.setStyleSheet(base_style + self._slider_style_sheet() + WaveToyTheme.global_control_style() + WaveToyTheme.scroll_area_style())

    def _db_text(self, value: int) -> str:
        db_value = value / DB_SLIDER_SCALE
        return "Off" if db_value <= -20 else f"{db_value:.2f} dB"

    def _slider_picture_text(self, value: int, kind: str) -> str:
        """Child-facing slider labels. No numerical values here."""
        if kind == "time":
            if value <= 25:
                return "🐇 Fast"
            if value <= 65:
                return "🚶 Medium"
            return "🐢 Slow"

        db_value = value / DB_SLIDER_SCALE
        if db_value <= -20:
            return "🤫 Silent"
        if db_value <= -14:
            return "🌱 Tiny"
        if db_value <= -8:
            return "🌿 Medium"
        return "🌳 Big"

    def _octave_picture_text(self, value: int) -> str:
        voice_value = value / OCTAVE_SLIDER_SCALE
        if voice_value <= 2.6:
            return "🐻 Big Low"
        if voice_value <= 4.4:
            return "🧸 Middle"
        return "🐭 Tiny High"

    def _cents_picture_text(self, value: int) -> str:
        cents_value = value / 100.0
        if cents_value < -12:
            return "⬅️ Soft Lean"
        if cents_value > 12:
            return "➡️ Sharp Lean"
        return "🎯 Center"

    def _pitch_picture_text(self, midi_value: int) -> str:
        scaled_midi = midi_value / MIDI_SLIDER_SCALE
        if scaled_midi < 52:
            return "🐻 Low"
        if scaled_midi > 76:
            return "🐭 High"
        return "🧸 Middle"

    def _plain_loudness_text(self, value: int) -> str:
        percent = value / PERCENT_SLIDER_SCALE
        if percent <= 20:
            return "🤫 Tiny"
        if percent <= 65:
            return "🌿 Medium"
        return "🌳 Big"

    def _duration_picture_text(self, duration_steps: int) -> str:
        seconds = duration_steps / SECONDS_SLIDER_SCALE
        if seconds <= 1.2:
            return "⚡ Quick"
        if seconds <= 3.5:
            return "⏱️ Short"
        if seconds <= 6.0:
            return "🚶 Long"
        return "🐢 Very Long"

    def _pan_picture_text(self, value: int) -> str:
        percent = value / PERCENT_SLIDER_SCALE
        if percent < -35:
            return "⬅️ Left"
        if percent > 35:
            return "Right ➡️"
        return "⬅️ 🧍 ➡️"

    def _width_picture_text(self, value: int) -> str:
        percent = value / PERCENT_SLIDER_SCALE
        if percent <= 20:
            return "🤏 Close"
        if percent <= 65:
            return "↔️ Medium"
        return "👐 Wide"

    def _dance_picture_text(self, value: int) -> str:
        percent = value / PERCENT_SLIDER_SCALE
        if percent <= 10:
            return "😴 Still"
        if percent <= 55:
            return "🙂 Sway"
        return "💃 Dance"


    def _stretch_picture_text(self, value: int) -> str:
        amount = value / PAULSTRETCH_SCALE
        if amount <= 1.2:
            return "🙂 Normal"
        if amount <= 4.0:
            return "🌠 Dreamy"
        if amount <= 12.0:
            return "🚀 Space Drift"
        return "🌀 Time Melt"

    def _evolution_picture_text(self, value: int) -> str:
        percent = value / PERCENT_SLIDER_SCALE
        if percent <= 15:
            return "🌌 Gentle"
        if percent <= 45:
            return "✨ Shimmer"
        if percent <= 75:
            return "🛸 Alien"
        return "⚡ Chaotic"

    def _rate_picture_text(self, value: int) -> str:
        hz = value / RATE_SLIDER_SCALE
        if hz <= 1.5:
            return "🐢 Slow"
        if hz <= 4.5:
            return "🚶 Medium"
        return "🐇 Fast"

    def _update_symbolic_labels(self) -> None:
        self.duration_label.setText(self._duration_picture_text(self.duration_slider.value()))
        self.pitch_start_label.setText(self._pitch_picture_text(self.pitch_start.value()))
        self.pitch_end_label.setText(self._pitch_picture_text(self.pitch_end.value()))
        self.loud_start_label.setText(self._plain_loudness_text(self.loud_start.value()))
        self.loud_end_label.setText(self._plain_loudness_text(self.loud_end.value()))
        self.pan_start_label.setText(self._pan_picture_text(self.pan_start_slider.value()))
        self.pan_end_label.setText(self._pan_picture_text(self.pan_end_slider.value()))
        self.width_label.setText(self._width_picture_text(self.width_slider.value()))
        self.auto_pan_depth_label.setText(self._dance_picture_text(self.auto_pan_depth_slider.value()))
        self.auto_pan_rate_label.setText(self._rate_picture_text(self.auto_pan_rate.value()))
        if hasattr(self, "paul_amount_label"):
            self.paul_amount_label.setText(self._stretch_picture_text(self.paul_amount_slider.value()))
            self.paul_evolution_label.setText(self._evolution_picture_text(self.paul_evolution_slider.value()))
            self._update_module_labels()
        for wave_type in self.wave_row_order:
            if wave_type in self.wave_pan_sliders:
                self._update_wave_stereo_labels(wave_type)

    def _wave_muted_from_ui(self) -> Dict[str, bool]:
        return {
            wave_type: button.isChecked()
            for wave_type, button in self.wave_mute_buttons.items()
        }

    def _solo_wave_from_ui(self) -> str | None:
        for wave_type, button in self.wave_solo_buttons.items():
            if button.isChecked():
                return wave_type
        return None

    def _set_wave_muted(self, wave_type: str, muted: bool) -> None:
        button = self.wave_mute_buttons.get(wave_type)
        if button is not None:
            button.setText("🤫 Quiet" if muted else "🎵 On")
        self._update_wave_card_state(wave_type)
        self._update_wave_previews(wave_type)
        self._schedule_generate("wave_mute_toggle")

    def _set_wave_solo(self, wave_type: str, soloed: bool) -> None:
        if soloed:
            for other_wave, button in self.wave_solo_buttons.items():
                if other_wave != wave_type and button.isChecked():
                    button.blockSignals(True)
                    button.setChecked(False)
                    button.setText("⭐ Only Me")
                    button.blockSignals(False)
        button = self.wave_solo_buttons.get(wave_type)
        if button is not None:
            button.setText("👑 Star Sound" if soloed else "⭐ Only Me")
        self._refresh_all_wave_card_states()
        self._update_all_wave_previews()
        self._schedule_generate("wave_solo_toggle")

    def _clear_solo(self) -> None:
        for button in self.wave_solo_buttons.values():
            button.blockSignals(True)
            button.setChecked(False)
            button.setText("⭐ Only Me")
            button.blockSignals(False)
        self._refresh_all_wave_card_states()
        self._update_all_wave_previews()
        self._schedule_generate("clear_solo")

    def _update_wave_card_state(self, wave_type: str) -> None:
        card = self.wave_cards.get(wave_type)
        if card is None:
            return
        muted = self.wave_mute_buttons.get(wave_type).isChecked() if wave_type in self.wave_mute_buttons else False
        soloed = self.wave_solo_buttons.get(wave_type).isChecked() if wave_type in self.wave_solo_buttons else False
        card.setObjectName("waveCardSolo" if soloed else "waveCardMuted" if muted else "waveCard")
        card.style().unpolish(card)
        card.style().polish(card)
        card.update()

    def _refresh_all_wave_card_states(self) -> None:
        for wave_type in list(self.wave_row_order):
            self._update_wave_card_state(wave_type)

    def _update_module_labels(self) -> None:
        if hasattr(self, "paulstretch_enabled"):
            self.paulstretch_enabled.setText("✨ Effect On" if self.paulstretch_enabled.isChecked() else "😴 Effect Nap")

    def _tuning_ratio_from_ui(self) -> float:
        note = self.note_combo.currentText()
        octave = int(round(self.octave_slider.value() / OCTAVE_SLIDER_SCALE))
        cents = float(self.cents_slider.value()) / 100.0
        root_note = self.tuning_root_combo.currentText() if hasattr(self, "tuning_root_combo") else "A"
        method = self.tuning_method_combo.currentData() if hasattr(self, "tuning_method_combo") else "equal_temperament_12"
        reference = self.tuning_reference_spin.value() if hasattr(self, "tuning_reference_spin") else 440.0
        equal_base = frequency_for_note(note, octave, 0.0, "equal_temperament_12", "A", reference)
        tuned_base = frequency_for_note(note, octave, cents, str(method), root_note, reference)
        return tuned_base / max(1.0, equal_base)

    def _tuned_slider_midi_to_hz(self, midi_value: int) -> float:
        return self._slider_midi_to_hz(midi_value) * self._tuning_ratio_from_ui()

    def _set_tuning_method(self, method_id: str) -> None:
        if not hasattr(self, "tuning_method_combo"):
            return
        index = self.tuning_method_combo.findData(method_id)
        self.tuning_method_combo.setCurrentIndex(index if index >= 0 else 0)

    def _wave_start_db_from_ui(self) -> Dict[str, float]:
        return {
            wave_type: float(slider.value()) / DB_SLIDER_SCALE
            for wave_type, slider in self.wave_start_sliders.items()
        }

    def _wave_end_db_from_ui(self) -> Dict[str, float]:
        return {
            wave_type: float(slider.value()) / DB_SLIDER_SCALE
            for wave_type, slider in self.wave_end_sliders.items()
        }

    def _clip_duration_seconds(self) -> float:
        return max(TIMELINE_MIN_CLIP_SECONDS, self.duration_slider.value() / SECONDS_SLIDER_SCALE)

    def _slider_midi_to_hz(self, midi_value: int) -> float:
        scaled_midi = midi_value / MIDI_SLIDER_SCALE
        return 440.0 * (2.0 ** ((scaled_midi - 69) / 12.0))

    def _wave_delta_time_from_ui(self) -> Dict[str, float]:
        duration = self._clip_duration_seconds()
        return {
            wave_type: duration * float(slider.value()) / (100.0 * PERCENT_SLIDER_SCALE)
            for wave_type, slider in self.wave_time_sliders.items()
        }

    def _wave_pan_from_ui(self) -> Dict[str, float]:
        return {
            wave_type: slider.value() / (100.0 * PERCENT_SLIDER_SCALE)
            for wave_type, slider in self.wave_pan_sliders.items()
        }

    def _wave_width_from_ui(self) -> Dict[str, float]:
        return {
            wave_type: slider.value() / (100.0 * PERCENT_SLIDER_SCALE)
            for wave_type, slider in self.wave_width_sliders.items()
        }

    def _wave_dance_from_ui(self) -> Dict[str, float]:
        return {
            wave_type: slider.value() / (100.0 * PERCENT_SLIDER_SCALE)
            for wave_type, slider in self.wave_dance_sliders.items()
        }


    def _wave_note_from_ui(self) -> Dict[str, str]:
        return {
            wave_type: combo.currentText()
            for wave_type, combo in self.wave_note_combos.items()
        }

    def _wave_octave_from_ui(self) -> Dict[str, int]:
        return {
            wave_type: int(spin.value())
            for wave_type, spin in self.wave_octave_spins.items()
        }

    def _wave_cents_from_ui(self) -> Dict[str, float]:
        return {
            wave_type: float(slider.value()) / 100.0
            for wave_type, slider in self.wave_cents_sliders.items()
        }

    def _wave_follow_main_pitch_from_ui(self) -> Dict[str, bool]:
        return {
            wave_type: button.isChecked()
            for wave_type, button in self.wave_follow_pitch_buttons.items()
        }

    def _wave_shapes_from_ui(self) -> Dict[str, str]:
        shapes = {wave_type: wave_type for wave_type in DEFAULT_WAVE_ORDER}
        for wave_type, combo in self.wave_shape_combos.items():
            shape = str(combo.currentData() or combo.currentText()).lower()
            shapes[wave_type] = shape if shape in DEFAULT_WAVE_ORDER else "sine"
        return shapes

    def _open_note_wheel(self, wave_type: str) -> None:
        combo = self.wave_note_combos.get(wave_type)
        if combo is None:
            return

        dialog = self.note_wheel_dialogs.get(wave_type)
        if dialog is None:
            accent = QColor(MiniWavePreview.COLORS.get(wave_type, QColor("#ff8cc6")))
            dialog = NoteWheelDialog(
                WAVE_LABELS.get(wave_type, wave_type.title()),
                combo.currentText(),
                accent,
                self.note_combo.currentText(),
                self,
            )
            dialog.setModal(False)
            dialog.setWindowFlag(Qt.Tool, True)

            def choose_note(note: str, wt: str = wave_type, picker_dialog: QDialog = dialog) -> None:
                target_combo = self.wave_note_combos.get(wt)
                if target_combo is not None and note in NOTE_TO_INDEX:
                    target_combo.setCurrentText(note)
                    picker_dialog.hide()

            dialog.picker.noteSelected.connect(choose_note)
            self.note_wheel_dialogs[wave_type] = dialog
        else:
            dialog.refresh_labels(combo.currentText(), self.note_combo.currentText())
            dialog.picker.update()

        parent = self.floating_toy_panels.get("pitch") or self
        top_left = parent.mapToGlobal(parent.rect().topRight())
        dialog.move(top_left.x() + 12, top_left.y() + 12)
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()

    def _update_wave_pitch_label(self, wave_type: str) -> None:
        if wave_type not in self.wave_pitch_labels:
            return
        follows = self.wave_follow_pitch_buttons.get(wave_type).isChecked() if wave_type in self.wave_follow_pitch_buttons else True
        note = self.wave_note_combos.get(wave_type).currentText() if wave_type in self.wave_note_combos else "A"
        octave = self.wave_octave_spins.get(wave_type).value() if wave_type in self.wave_octave_spins else 4
        cents = self.wave_cents_sliders.get(wave_type).value() / 100.0 if wave_type in self.wave_cents_sliders else 0.0
        if follows:
            text = "👯 Main"
        else:
            sign = "+" if cents > 0 else ""
            cents_text = f" {sign}{cents:.0f}¢" if abs(cents) >= 0.5 else ""
            text = f"🎯 {note}{octave}{cents_text}"
        self.wave_pitch_labels[wave_type].setText(text)
        button = self.wave_follow_pitch_buttons.get(wave_type)
        if button is not None:
            button.setText("👯 Follow Main" if follows else "🎯 My Note")
        note_button = self.wave_note_buttons.get(wave_type)
        if note_button is not None:
            emotion = note_emotion(note)
            relationship = note_relationship(note, self.note_combo.currentText() if hasattr(self, "note_combo") else note)
            note_button.setText(f"🎡 {emotion['emoji']} {note}")
            note_button.setToolTip(emotion["label"])
            note_button.setStyleSheet(f"background-color: {emotion['color']}; color: #263238; font-weight: bold;")
        emotion_label = self.wave_emotion_labels.get(wave_type)
        if emotion_label is not None:
            emotion = note_emotion(note)
            relationship = note_relationship(note, self.note_combo.currentText() if hasattr(self, "note_combo") else note)
            emotion_label.setText(f"Selected Note: {emotion['emoji']} {note}\nMood: {emotion['label']}\nRelationship: {relationship}")
        panel = self.wave_pitch_panels.get(wave_type)
        if panel is not None:
            panel.setVisible(not follows)
        for widget in (
            self.wave_note_combos.get(wave_type),
            self.wave_note_buttons.get(wave_type),
            self.wave_octave_spins.get(wave_type),
            self.wave_cents_sliders.get(wave_type),
        ):
            if widget is not None:
                widget.setEnabled(not follows)
        if hasattr(self, "duration_slider"):
            self._update_all_wave_previews()

    def _open_wave_explorer(self) -> None:
        if self.wave_explorer is None:
            self.wave_explorer = WaveExplorerWindow(self)
        self.wave_explorer.show()
        self.wave_explorer.raise_()
        self.wave_explorer.activateWindow()

    def _settings_from_ui(self) -> SynthSettings:
        return SynthSettings(
            wave_start_db=self._wave_start_db_from_ui(),
            wave_end_db=self._wave_end_db_from_ui(),
            wave_delta_time=self._wave_delta_time_from_ui(),
            note=self.note_combo.currentText(),
            octave=int(round(self.octave_slider.value() / OCTAVE_SLIDER_SCALE)),
            cents=float(self.cents_slider.value()) / 100.0,
            pitch_start_hz=self._tuned_slider_midi_to_hz(self.pitch_start.value()),
            pitch_end_hz=self._tuned_slider_midi_to_hz(self.pitch_end.value()),
            loudness_start=self.loud_start.value() / (100.0 * PERCENT_SLIDER_SCALE),
            loudness_end=self.loud_end.value() / (100.0 * PERCENT_SLIDER_SCALE),
            duration_seconds=self._clip_duration_seconds(),
            curve_type=self.curve_combo.currentData(),
            pan_start=self.pan_start_slider.value() / (100.0 * PERCENT_SLIDER_SCALE),
            pan_end=self.pan_end_slider.value() / (100.0 * PERCENT_SLIDER_SCALE),
            stereo_width=self.width_slider.value() / (100.0 * PERCENT_SLIDER_SCALE),
            auto_pan_depth=self.auto_pan_depth_slider.value() / (100.0 * PERCENT_SLIDER_SCALE),
            auto_pan_rate=self.auto_pan_rate.value() / RATE_SLIDER_SCALE,
            wave_pan=self._wave_pan_from_ui(),
            wave_width=self._wave_width_from_ui(),
            wave_dance=self._wave_dance_from_ui(),
            wave_muted=self._wave_muted_from_ui(),
            solo_wave=self._solo_wave_from_ui(),
            muted_modules={"paulstretch": not self.paulstretch_enabled.isChecked()},
            tuning_method=str(self.tuning_method_combo.currentData()),
            tuning_root_note=self.tuning_root_combo.currentText(),
            tuning_reference_hz=float(self.tuning_reference_spin.value()),
            wave_note=self._wave_note_from_ui(),
            wave_octave=self._wave_octave_from_ui(),
            wave_cents=self._wave_cents_from_ui(),
            wave_follow_main_pitch=self._wave_follow_main_pitch_from_ui(),
            wave_shapes=self._wave_shapes_from_ui(),
            wave_order=list(self.wave_row_order),
            paulstretch_enabled=self.paulstretch_enabled.isChecked(),
            paulstretch_amount=self.paul_amount_slider.value() / PAULSTRETCH_SCALE,
            paulstretch_evolution=self.paul_evolution_slider.value() / (100.0 * PERCENT_SLIDER_SCALE),
            enabled_modules={
                "paulstretch": self.paulstretch_enabled.isChecked(),
            },
        )

    def _sync_note_to_pitch(self) -> None:
        octave_float = self.octave_slider.value() / OCTAVE_SLIDER_SCALE
        octave = int(round(octave_float))
        cents = self.cents_slider.value()
        midi_value = midi_note(self.note_combo.currentText(), octave)
        tuning_name = "Piano Steps"
        base_frequency = frequency_from_note(self.note_combo.currentText(), octave, cents / 100.0)
        if hasattr(self, "tuning_method_combo"):
            tuning_name = self.tuning_method_combo.currentText()
            base_frequency = frequency_for_note(
                self.note_combo.currentText(),
                octave,
                cents / 100.0,
                str(self.tuning_method_combo.currentData()),
                self.tuning_root_combo.currentText(),
                float(self.tuning_reference_spin.value()),
            )

        self.octave_label.setText(self._octave_picture_text(octave))
        self.cents_label.setText(self._cents_picture_text(cents))
        note = self.note_combo.currentText()
        emotion = note_emotion(note)
        self.note_combo.setToolTip(f"{emotion['label']} • {note_relationship(note, note)}")
        self.note_emotion_label.setText(
            f"Selected Note: {emotional_note_text(note)}\nMood: {emotion['label']}\nRelationship: {note_relationship(note, note)}"
        )
        self.note_emotion_label.setStyleSheet(
            f"background-color: {emotion['color']}; color: #263238; border-radius: 10px; padding: 6px; font-weight: bold;"
        )
        self.base_pitch_label.setText(
            f"Pitch: {self._pitch_picture_text(midi_value)} • {emotional_note_text(note)} {emotion['label']} • {tuning_name} • {base_frequency:.1f} Hz"
        )
        for wave_type in list(self.wave_pitch_labels):
            self._update_wave_pitch_label(wave_type)

        self.pitch_start.blockSignals(True)
        self.pitch_end.blockSignals(True)
        self.pitch_start.setValue(midi_value * MIDI_SLIDER_SCALE)
        self.pitch_end.setValue(midi_value * MIDI_SLIDER_SCALE)
        self.pitch_start.blockSignals(False)
        self.pitch_end.blockSignals(False)

        self._update_symbolic_labels()
        self._schedule_generate("pitch_controls")

    def _visual_conditions_from_ui(self) -> Dict[str, Dict[str, float | bool]]:
        conditions: Dict[str, Dict[str, float | bool]] = {}

        for wave_type in self.wave_row_order:
            start_db = self.wave_start_sliders[wave_type].value() / DB_SLIDER_SCALE
            end_db = self.wave_end_sliders[wave_type].value() / DB_SLIDER_SCALE
            change_fraction = self.wave_time_sliders[wave_type].value() / (100.0 * PERCENT_SLIDER_SCALE)
            pan = self.wave_pan_sliders.get(wave_type).value() / (100.0 * PERCENT_SLIDER_SCALE) if wave_type in self.wave_pan_sliders else 0.0
            spread = self.wave_width_sliders.get(wave_type).value() / (100.0 * PERCENT_SLIDER_SCALE) if wave_type in self.wave_width_sliders else 0.0
            dance = self.wave_dance_sliders.get(wave_type).value() / (100.0 * PERCENT_SLIDER_SCALE) if wave_type in self.wave_dance_sliders else 0.0

            muted = self.wave_mute_buttons.get(wave_type).isChecked() if wave_type in self.wave_mute_buttons else False
            solo_wave = self._solo_wave_from_ui()
            audible = not muted and (solo_wave is None or solo_wave == wave_type)

            conditions[wave_type] = {
                "active": audible and (start_db > -20.0 or end_db > -20.0),
                "muted": muted,
                "soloed": solo_wave == wave_type,
                "start_db": start_db,
                "end_db": end_db,
                "change_fraction": change_fraction,
                "pan": pan,
                "spread": spread,
                "dance": dance,
            }

        return conditions

    def _connect_scheduled_generate(self, signal, reason: str) -> None:
        signal.connect(lambda *args, reason=reason: self._schedule_generate(reason))

    def _add_user_wave_row(self, checked: bool = False) -> None:
        del checked
        if len(self.wave_row_order) >= MAX_WAVE_ROWS:
            QMessageBox.warning(self, "Add Wave", f"WaveToy keeps mixes to {MAX_WAVE_ROWS} wave rows so preview and export stay responsive.")
            return
        while True:
            wave_id = f"wave_{self.next_user_wave_index}"
            self.next_user_wave_index += 1
            if wave_id not in self.wave_row_order:
                break
        self._create_user_wave_row(wave_id)
        self._schedule_generate("add_wave")

    def _create_user_wave_row(self, wave_id: str, shape: str = "sine", values: Dict[str, object] | None = None) -> None:
        if self.wave_rows_layout is None or wave_id in self.wave_row_order or len(self.wave_row_order) >= MAX_WAVE_ROWS:
            return
        values = values or {}
        self.wave_row_order.append(wave_id)
        self.user_wave_ids.append(wave_id)

        card = QWidget()
        card.setObjectName("waveCard")
        self.wave_cards[wave_id] = card
        layout = QGridLayout(card)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setHorizontalSpacing(8)
        layout.setVerticalSpacing(5)

        title = QLabel(f"Extra Wave {len(self.wave_row_order)}")
        title.setObjectName("waveCardTitle")
        shape_combo = NoWheelComboBox()
        for shape_id in DEFAULT_WAVE_ORDER:
            shape_combo.addItem(WAVE_LABELS[shape_id], shape_id)
        shape_combo.setCurrentIndex(max(0, shape_combo.findData(shape if shape in DEFAULT_WAVE_ORDER else "sine")))
        shape_combo.currentIndexChanged.connect(lambda _index, wt=wave_id: self._user_wave_shape_changed(wt))
        self._connect_scheduled_generate(shape_combo.currentIndexChanged, "wave_shape")
        self.wave_shape_combos[wave_id] = shape_combo

        mute_button = QCheckBox("🎵 On")
        mute_button.stateChanged.connect(lambda state, wt=wave_id: self._set_wave_muted(wt, bool(state)))
        solo_button = QCheckBox("⭐ Only Me")
        solo_button.stateChanged.connect(lambda state, wt=wave_id: self._set_wave_solo(wt, bool(state)))
        remove_button = QPushButton("➖ Remove")
        remove_button.clicked.connect(lambda checked=False, wt=wave_id: self._remove_user_wave_row(wt))
        self.wave_mute_buttons[wave_id] = mute_button
        self.wave_solo_buttons[wave_id] = solo_button

        follow_pitch = QCheckBox("👯 Follow Main")
        follow_pitch.setChecked(bool(values.get("follow_main_pitch", True)))
        pitch_label = QLabel("👯 Main")
        note_combo = NoWheelComboBox(); note_combo.addItems(NOTE_NAMES); note_combo.setCurrentText(str(values.get("note", "A")) if str(values.get("note", "A")) in NOTE_TO_INDEX else "A")
        note_button = QPushButton(f"🎡 {emotional_note_text(note_combo.currentText())}")
        octave_spin = NoWheelSpinBox(); octave_spin.setRange(0, 8); octave_spin.setValue(int(values.get("octave", 4)))
        cents_slider = NoWheelSlider(Qt.Horizontal); cents_slider.setRange(-50 * 100, 50 * 100); cents_slider.setValue(int(float(values.get("cents", 0.0)) * 100))
        follow_pitch.stateChanged.connect(lambda _state, wt=wave_id: self._update_wave_pitch_label(wt))
        note_combo.currentTextChanged.connect(lambda _value, wt=wave_id: self._update_wave_pitch_label(wt))
        note_button.clicked.connect(lambda checked=False, wt=wave_id: self._open_note_wheel(wt))
        octave_spin.valueChanged.connect(lambda _value, wt=wave_id: self._update_wave_pitch_label(wt))
        cents_slider.valueChanged.connect(lambda _value, wt=wave_id: self._update_wave_pitch_label(wt))
        self._connect_scheduled_generate(follow_pitch.stateChanged, "wave_follow_pitch")
        self._connect_scheduled_generate(note_combo.currentIndexChanged, "wave_note")
        self._connect_scheduled_generate(octave_spin.valueChanged, "wave_octave")
        self._connect_scheduled_generate(cents_slider.valueChanged, "wave_cents")
        self.wave_follow_pitch_buttons[wave_id] = follow_pitch
        self.wave_note_combos[wave_id] = note_combo
        self.wave_note_buttons[wave_id] = note_button
        self.wave_octave_spins[wave_id] = octave_spin
        self.wave_cents_sliders[wave_id] = cents_slider
        self.wave_pitch_labels[wave_id] = pitch_label

        def slider(minimum: int, maximum: int, value: int, reason: str) -> NoWheelSlider:
            control = NoWheelSlider(Qt.Horizontal)
            control.setRange(minimum, maximum)
            control.setValue(value)
            self._connect_scheduled_generate(control.valueChanged, reason)
            return control

        start_slider = slider(-20 * DB_SLIDER_SCALE, 0, int(values.get("start_db", -12 * DB_SLIDER_SCALE)), "wave_start_slider")
        end_slider = slider(-20 * DB_SLIDER_SCALE, 0, int(values.get("end_db", -12 * DB_SLIDER_SCALE)), "wave_end_slider")
        time_slider = slider(1, 100 * PERCENT_SLIDER_SCALE, int(values.get("change_time_percent", 100 * PERCENT_SLIDER_SCALE)), "wave_time_slider")
        pan_slider = slider(-100 * PERCENT_SLIDER_SCALE, 100 * PERCENT_SLIDER_SCALE, int(values.get("pan", round(default_wave_pan_for(wave_id, len(self.wave_row_order)) * 100 * PERCENT_SLIDER_SCALE))), "wave_pan_slider")
        width_slider = slider(0, 100 * PERCENT_SLIDER_SCALE, int(values.get("spread", 65 * PERCENT_SLIDER_SCALE)), "wave_width_slider")
        dance_slider = slider(0, 100 * PERCENT_SLIDER_SCALE, int(values.get("dance", 0)), "wave_dance_slider")
        self.wave_start_sliders[wave_id] = start_slider; self.wave_end_sliders[wave_id] = end_slider; self.wave_time_sliders[wave_id] = time_slider
        self.wave_pan_sliders[wave_id] = pan_slider; self.wave_width_sliders[wave_id] = width_slider; self.wave_dance_sliders[wave_id] = dance_slider
        self.wave_start_labels[wave_id] = QLabel(); self.wave_end_labels[wave_id] = QLabel(); self.wave_time_labels[wave_id] = QLabel()
        self.wave_pan_labels[wave_id] = QLabel(); self.wave_width_labels[wave_id] = QLabel(); self.wave_dance_labels[wave_id] = QLabel()
        for control, updater in ((start_slider, self._update_wave_envelope_labels), (end_slider, self._update_wave_envelope_labels), (time_slider, self._update_wave_envelope_labels), (pan_slider, self._update_wave_stereo_labels), (width_slider, self._update_wave_stereo_labels), (dance_slider, self._update_wave_stereo_labels)):
            control.valueChanged.connect(lambda _value, wt=wave_id, fn=updater: fn(wt))

        shape_preview = MiniWavePreview(shape if shape in DEFAULT_WAVE_ORDER else "sine", size=QSize(112, 54))
        self.wave_mix_previews[wave_id] = shape_preview
        self.wave_envelope_previews[wave_id] = EnvelopePreview(size=QSize(220, 54))
        self.wave_stereo_field_previews[wave_id] = StereoFieldPreview(shape if shape in DEFAULT_WAVE_ORDER else "sine", size=QSize(220, 54))
        self.wave_stereo_previews[wave_id] = (MiniWavePreview(shape, channel="left", size=QSize(62, 34)), MiniWavePreview(shape, channel="right", size=QSize(62, 34)))

        layout.addWidget(title, 0, 0)
        layout.addWidget(QLabel("Shape"), 0, 1); layout.addWidget(shape_combo, 0, 2)
        layout.addWidget(mute_button, 0, 3); layout.addWidget(solo_button, 0, 4); layout.addWidget(remove_button, 0, 5)
        layout.addWidget(shape_preview, 1, 0)
        for col, (caption, label, control) in enumerate((("Start", self.wave_start_labels[wave_id], start_slider), ("End", self.wave_end_labels[wave_id], end_slider), ("Time", self.wave_time_labels[wave_id], time_slider)), start=1):
            box = QWidget(); box_layout = QVBoxLayout(box); box_layout.setContentsMargins(0, 0, 0, 0); box_layout.addWidget(QLabel(caption)); box_layout.addWidget(label); box_layout.addWidget(control); layout.addWidget(box, 1, col)
        pitch_box = QWidget(); pitch_layout = QVBoxLayout(pitch_box); pitch_layout.setContentsMargins(0, 0, 0, 0); pitch_layout.addWidget(pitch_label); pitch_layout.addWidget(follow_pitch); pitch_layout.addWidget(note_button); pitch_layout.addWidget(octave_spin); pitch_layout.addWidget(cents_slider); layout.addWidget(pitch_box, 1, 4)
        stereo_box = QWidget(); stereo_layout = QGridLayout(stereo_box); stereo_layout.setContentsMargins(0, 0, 0, 0)
        for row, (caption, label, control) in enumerate((("Pan", self.wave_pan_labels[wave_id], pan_slider), ("Width", self.wave_width_labels[wave_id], width_slider), ("Auto-pan", self.wave_dance_labels[wave_id], dance_slider))):
            stereo_layout.addWidget(QLabel(caption), row, 0); stereo_layout.addWidget(label, row, 1); stereo_layout.addWidget(control, row, 2)
        layout.addWidget(stereo_box, 1, 5)
        row_index = max(0, self.wave_rows_layout.count() - 2)
        self.wave_rows_layout.insertWidget(row_index, card)
        self._update_wave_pitch_label(wave_id)
        self._update_wave_envelope_labels(wave_id)
        self._update_wave_stereo_labels(wave_id)
        self._user_wave_shape_changed(wave_id)

    def _user_wave_shape_changed(self, wave_id: str) -> None:
        shape = self._wave_shapes_from_ui().get(wave_id, "sine")
        for preview in (self.wave_mix_previews.get(wave_id), self.wave_stereo_field_previews.get(wave_id)):
            if preview is not None and hasattr(preview, "wave_type"):
                preview.wave_type = shape
                preview.update()
        for preview in self.wave_stereo_previews.get(wave_id, ()):
            preview.wave_type = shape
            preview.update()
        self._update_all_wave_previews()

    def _remove_user_wave_row(self, wave_id: str) -> None:
        if wave_id not in self.user_wave_ids:
            return
        widget = self.wave_cards.pop(wave_id, None)
        if widget is not None:
            widget.setParent(None)
            widget.deleteLater()
        for mapping in (self.wave_start_sliders, self.wave_end_sliders, self.wave_time_sliders, self.wave_start_labels, self.wave_end_labels, self.wave_time_labels, self.wave_pan_sliders, self.wave_width_sliders, self.wave_dance_sliders, self.wave_pan_labels, self.wave_width_labels, self.wave_dance_labels, self.wave_mix_previews, self.wave_envelope_previews, self.wave_stereo_field_previews, self.wave_stereo_previews, self.wave_mute_buttons, self.wave_solo_buttons, self.wave_follow_pitch_buttons, self.wave_note_combos, self.wave_note_buttons, self.wave_octave_spins, self.wave_cents_sliders, self.wave_pitch_labels, self.wave_pitch_panels, self.wave_emotion_labels, self.wave_shape_combos):
            mapping.pop(wave_id, None)
        if wave_id in self.wave_row_order:
            self.wave_row_order.remove(wave_id)
        if wave_id in self.user_wave_ids:
            self.user_wave_ids.remove(wave_id)
        if self.current_settings.solo_wave == wave_id:
            self._clear_solo()
        self._schedule_generate("remove_wave")

    def _schedule_generate(self, reason: str = "ui_change") -> None:
        was_pending = self._generate_timer.isActive()
        self.render_dirty = True
        self.last_generate_reason = str(reason)
        if not was_pending:
            print(
                f"[WaveToy] Scheduled debounced generation in {GENERATION_DEBOUNCE_MS} ms "
                f"(reason={self.last_generate_reason})."
            )
        self._generate_timer.start(GENERATION_DEBOUNCE_MS)

    def _run_scheduled_generate(self) -> None:
        if not self.render_dirty:
            return
        self._generate_now(reason=f"debounced:{self.last_generate_reason}", force=True)

    def _generate_now(self, reason: str = "direct", update_message: bool = False, force: bool = False) -> None:
        if self._generate_timer.isActive():
            self._generate_timer.stop()

        if not self.render_dirty and not force:
            return

        generation_type = "debounced" if str(reason).startswith("debounced") else "direct"
        start_time = time.perf_counter()
        print(f"[WaveToy] Starting {generation_type} generation (reason={reason}).")
        self._render_current_sound(update_message=update_message)
        self.render_dirty = False
        self.last_generate_reason = str(reason)
        duration_ms = (time.perf_counter() - start_time) * 1000.0
        print(f"[WaveToy] Completed {generation_type} generation in {duration_ms:.1f} ms (reason={reason}).")

    def _generate(self, update_message: bool = False) -> None:
        self._generate_now(reason="direct", update_message=update_message, force=True)

    def _render_current_sound(self, update_message: bool = False) -> None:
        self._update_symbolic_labels()
        self.current_settings = self._settings_from_ui()
        self._update_all_wave_previews()
        self._refresh_graphical_editor()
        audio, time_axis, freq_env, loud_env = generate_audio(self.current_settings)

        self.current_audio = audio

        wave_muted = self.current_settings.wave_muted or {}
        solo_wave = self.current_settings.solo_wave if self.current_settings.solo_wave in active_wave_order(self.current_settings) else None
        active_count = sum(
            1
            for wave_type, db in (self.current_settings.wave_start_db or {}).items()
            if not wave_muted.get(wave_type, False)
            and (solo_wave is None or solo_wave == wave_type)
            and (db > -20 or (self.current_settings.wave_end_db or {}).get(wave_type, -20) > -20)
        )

        if self.current_settings.auto_pan_depth > 0:
            msg = "The sound wiggles between your left and right ears!"
        elif abs(self.current_settings.pitch_start_hz - self.current_settings.pitch_end_hz) > 0.5:
            msg = "The waves squeeze or stretch, so the pitch changes!"
        else:
            msg = f"You are mixing {active_count} wave shape(s). Move the sliders!"

        visual_conditions = self._visual_conditions_from_ui()
        if self.dashboard_canvas is not None:
            self.dashboard_canvas.set_data(audio, freq_env, loud_env, msg, visual_conditions)
        if hasattr(self, "play_canvas"):
            self.play_canvas.set_data(audio, freq_env, loud_env, msg, visual_conditions)
        if self.wave_explorer is not None:
            self.wave_explorer.set_data(audio, freq_env, loud_env, msg, visual_conditions)
        self._update_visual_panel_buttons()
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

            if start_db > -20 or end_db > -20:
                active.append(
                    f"{wave_label_for(s, wave_type)} {start_db:.1f}→{end_db:.1f} dB over {change_time:.1f}s"
                )

        active_text = ", ".join(active) if active else "no waves yet"

        if self.beginner_mode.isChecked():
            simple_wave_words = []

            for wave_type, start_db in (s.wave_start_db or {}).items():
                end_db = (s.wave_end_db or {}).get(wave_type, start_db)

                if start_db > -20 or end_db > -20:
                    simple_wave_words.append(wave_label_for(s, wave_type).lower())

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
                + "Blue is left. Yellow is the shared middle. Pink is right."
            )
        else:
            self.explain_label.setText(
                f"You are mixing: {active_text}. Pitch moves from {s.pitch_start_hz:.1f} Hz to "
                f"{s.pitch_end_hz:.1f} Hz using {curve_name.lower()}. Global loudness moves from "
                f"{s.loudness_start:.2f} to {s.loudness_end:.2f}. Stereo pan moves from "
                f"{s.pan_start:.2f} to {s.pan_end:.2f}, width is {s.stereo_width:.2f}, and "
                f"auto-pan depth/rate are {s.auto_pan_depth:.2f}/{s.auto_pan_rate:.2f} Hz. "
                f"Per-wave stereo pan values are {s.wave_pan}; spreads are {s.wave_width}; dances are {s.wave_dance}. "
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
        self._start_playback_tracking(len(self.current_audio), SAMPLE_RATE)
        if not self.live_loop_enabled:
            self._start_preview_motion_for_current_duration()

    def _start_playback_tracking(self, audio_samples: int, sample_rate: int = SAMPLE_RATE) -> None:
        self.playback_audio_sample_count = int(max(0, audio_samples))
        self.playback_sample_rate = int(max(1, sample_rate))
        self.playback_duration_seconds = max(0.0, self.playback_audio_sample_count / self.playback_sample_rate)
        if self.playback_duration_seconds <= 0.0:
            self._stop_playback_tracking(clear_playheads=True)
            return
        self.playback_start_monotonic = time.monotonic()
        print(f"[WaveToy Playback] play started samples={self.playback_audio_sample_count} rate={self.playback_sample_rate}")
        print(f"[WaveToy Playback] audio duration {self.playback_duration_seconds:.2f}s")
        self.playback_timer.start(33)
        print("[WaveToy Playback] playback timer started")
        if self.wave_explorer is not None:
            self.wave_explorer.start_playback_follow(self.playback_audio_sample_count, self.playback_sample_rate)
        self._playback_timer_tick()

    def _stop_playback_tracking(self, clear_playheads: bool = False) -> None:
        self.playback_start_monotonic = None
        if self.playback_timer.isActive():
            self.playback_timer.stop()
        if self.wave_explorer is not None:
            self.wave_explorer.stop_playback_follow()
        if clear_playheads:
            for canvas in (getattr(self, "play_canvas", None), self.dashboard_canvas):
                if canvas is not None:
                    canvas.set_playhead_fraction(None)

    def _playback_timer_tick(self) -> None:
        if self.playback_start_monotonic is None or self.playback_duration_seconds <= 0.0:
            self._stop_playback_tracking()
            return
        elapsed = time.monotonic() - self.playback_start_monotonic
        if elapsed >= self.playback_duration_seconds:
            fraction = 1.0
            ended = True
        else:
            fraction = elapsed / self.playback_duration_seconds
            ended = False
        for canvas in (getattr(self, "play_canvas", None), self.dashboard_canvas):
            if canvas is not None:
                canvas.center_on_playback_fraction(fraction)
        if ended:
            print("[WaveToy Playback] playback ended")
            self._stop_playback_tracking(clear_playheads=True)

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
            "WaveToy could generate the sound, but could not find an audio player.\n\n"
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
        self._preview_stop_timer.stop()
        self._set_preview_motion(True)
        self._start_playback_tracking(len(self.current_audio), SAMPLE_RATE)
        self._restart_live_loop(regenerate=True)

    def _disable_live_loop(self) -> None:
        self.live_loop_enabled = False
        self.live_loop_timer.stop()
        self.live_loop_is_refreshing = False
        self._preview_stop_timer.stop()
        self._set_preview_motion(False)
        self._stop_playback_tracking(clear_playheads=True)
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
            self._start_playback_tracking(len(self.current_audio), SAMPLE_RATE)

            duration_ms = max(100, int((len(self.current_audio) / SAMPLE_RATE) * 1000))
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
        self._stop_playback_tracking(clear_playheads=True)
        self._stop_articulation_motion()
        print("[WaveToy Playback] playback stopped")

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
                "octave": self.octave_slider.value(),
                "cents": self.cents_slider.value(),
                "pitch_start_slider": self.pitch_start.value(),
                "pitch_end_slider": self.pitch_end.value(),
                "loudness_start_slider": self.loud_start.value(),
                "loudness_end_slider": self.loud_end.value(),
                "duration_slider": self.duration_slider.value(),
                "pan_start_slider": self.pan_start_slider.value(),
                "pan_end_slider": self.pan_end_slider.value(),
                "width_slider": self.width_slider.value(),
                "auto_pan_depth_slider": self.auto_pan_depth_slider.value(),
                "auto_pan_rate": self.auto_pan_rate.value(),
                "curve_type": self.curve_combo.currentData(),
                "tuning_method": self.tuning_method_combo.currentData(),
                "tuning_root_note": self.tuning_root_combo.currentText(),
                "tuning_reference_hz": self.tuning_reference_spin.value(),
                "muted_modules": {"paulstretch": not self.paulstretch_enabled.isChecked()},
                "paulstretch_enabled": self.paulstretch_enabled.isChecked(),
                "paulstretch_amount": self.paul_amount_slider.value(),
                "paulstretch_evolution": self.paul_evolution_slider.value(),
                "solo_wave": self._solo_wave_from_ui(),
                "waves": {
                    wave_type: {
                        "start_db": self.wave_start_sliders[wave_type].value(),
                        "end_db": self.wave_end_sliders[wave_type].value(),
                        "change_time_percent": self.wave_time_sliders[wave_type].value(),
                        "pan": self.wave_pan_sliders[wave_type].value(),
                        "spread": self.wave_width_sliders[wave_type].value(),
                        "dance": self.wave_dance_sliders[wave_type].value(),
                        "muted": self.wave_mute_buttons[wave_type].isChecked(),
                        "follow_main_pitch": self.wave_follow_pitch_buttons[wave_type].isChecked(),
                        "note": self.wave_note_combos[wave_type].currentText(),
                        "octave": self.wave_octave_spins[wave_type].value(),
                        "cents": self.wave_cents_sliders[wave_type].value() / 100.0,
                    }
                    for wave_type in self.wave_row_order
                },
                "dynamic_wave_entries": [
                    {
                        "id": wave_type,
                        "shape": self._wave_shapes_from_ui().get(wave_type, wave_type),
                        "user_added": wave_type in self.user_wave_ids,
                        "start_db": self.wave_start_sliders[wave_type].value(),
                        "end_db": self.wave_end_sliders[wave_type].value(),
                        "change_time_percent": self.wave_time_sliders[wave_type].value(),
                        "pan": self.wave_pan_sliders[wave_type].value(),
                        "spread": self.wave_width_sliders[wave_type].value(),
                        "dance": self.wave_dance_sliders[wave_type].value(),
                        "muted": self.wave_mute_buttons[wave_type].isChecked(),
                        "follow_main_pitch": self.wave_follow_pitch_buttons[wave_type].isChecked(),
                        "note": self.wave_note_combos[wave_type].currentText(),
                        "octave": self.wave_octave_spins[wave_type].value(),
                        "cents": self.wave_cents_sliders[wave_type].value() / 100.0,
                    }
                    for wave_type in self.wave_row_order
                ],
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

    def _load_scaled_value(self, value: object, scale: float, minimum: float, maximum: float) -> int:
        """Load old coarse recipe values or new high-resolution raw slider values."""
        try:
            numeric = float(value)
        except Exception:
            numeric = minimum

        # If the stored number is in human units, scale it. If already raw slider units, keep it.
        if minimum <= numeric <= maximum:
            numeric *= scale

        return int(round(numeric))

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
        dynamic_entries = ui.get("dynamic_wave_entries", settings.get("dynamic_wave_entries", []))
        if not isinstance(dynamic_entries, list):
            dynamic_entries = []
        for old_wave_id in list(self.user_wave_ids):
            self._remove_user_wave_row(old_wave_id)

        self.note_combo.setCurrentText(str(ui.get("note", settings.get("note", "A"))))
        loaded_octave = float(ui.get("octave", settings.get("octave", 4)))
        if loaded_octave > 8:
            self.octave_slider.setValue(int(loaded_octave))
        else:
            self.octave_slider.setValue(int(loaded_octave * OCTAVE_SLIDER_SCALE))
        loaded_cents = float(ui.get("cents", settings.get("cents", 0.0)))
        if abs(loaded_cents) > 50:
            self.cents_slider.setValue(int(loaded_cents))
        else:
            self.cents_slider.setValue(int(loaded_cents * 100))
        self._set_tuning_method(str(ui.get("tuning_method", settings.get("tuning_method", "equal_temperament_12"))))
        self.tuning_root_combo.setCurrentText(str(ui.get("tuning_root_note", settings.get("tuning_root_note", "A"))))
        self.tuning_reference_spin.setValue(float(ui.get("tuning_reference_hz", settings.get("tuning_reference_hz", 440.0))))
        self.pitch_start.setValue(int(ui.get("pitch_start_slider", round((69 + 12 * math.log2(max(1.0, float(settings.get("pitch_start_hz", 440.0))) / 440.0)) * MIDI_SLIDER_SCALE))))
        self.pitch_end.setValue(int(ui.get("pitch_end_slider", round((69 + 12 * math.log2(max(1.0, float(settings.get("pitch_end_hz", 440.0))) / 440.0)) * MIDI_SLIDER_SCALE))))
        self.duration_slider.setValue(max(int(TIMELINE_MIN_CLIP_SECONDS * SECONDS_SLIDER_SCALE), int(round(float(settings.get("duration_seconds", 1.5)) * SECONDS_SLIDER_SCALE))))
        self.loud_start.setValue(self._load_scaled_value(ui.get("loudness_start_slider", 40), PERCENT_SLIDER_SCALE, 0, 100))
        self.loud_end.setValue(self._load_scaled_value(ui.get("loudness_end_slider", 40), PERCENT_SLIDER_SCALE, 0, 100))
        self.pan_start_slider.setValue(self._load_scaled_value(ui.get("pan_start_slider", 0), PERCENT_SLIDER_SCALE, -100, 100))
        self.pan_end_slider.setValue(self._load_scaled_value(ui.get("pan_end_slider", 0), PERCENT_SLIDER_SCALE, -100, 100))
        self.width_slider.setValue(self._load_scaled_value(ui.get("width_slider", 45), PERCENT_SLIDER_SCALE, 0, 100))
        self.auto_pan_depth_slider.setValue(self._load_scaled_value(ui.get("auto_pan_depth_slider", 0), PERCENT_SLIDER_SCALE, 0, 100))
        self.auto_pan_rate.setValue(self._load_scaled_value(ui.get("auto_pan_rate", 5), RATE_SLIDER_SCALE / 10, 0.05, 8.0))
        muted_modules = ui.get("muted_modules", settings.get("muted_modules", {}))
        if not isinstance(muted_modules, dict):
            muted_modules = {}
        paul_enabled_default = bool(settings.get("paulstretch_enabled", False))
        self.paulstretch_enabled.setChecked(bool(ui.get("paulstretch_enabled", paul_enabled_default)) and not bool(muted_modules.get("paulstretch", False)))
        self._update_module_labels()
        self.paul_amount_slider.setValue(self._load_scaled_value(ui.get("paulstretch_amount", 10), PAULSTRETCH_SCALE / 10, 1, 30))
        self.paul_evolution_slider.setValue(self._load_scaled_value(ui.get("paulstretch_evolution", 15), PERCENT_SLIDER_SCALE, 0, 100))

        self._set_curve(str(ui.get("curve_type", settings.get("curve_type", "linear"))))

        start_levels: Dict[str, int] = {}
        end_levels: Dict[str, int] = {}
        times: Dict[str, int] = {}
        wave_pan: Dict[str, int] = {}
        wave_width: Dict[str, int] = {}
        wave_dance: Dict[str, int] = {}
        wave_muted: Dict[str, bool] = {}
        wave_follow_pitch: Dict[str, bool] = {}
        wave_note: Dict[str, str] = {}
        wave_octave: Dict[str, int] = {}
        wave_cents: Dict[str, float] = {}
        settings_wave_follow = settings.get("wave_follow_main_pitch", {}) if isinstance(settings.get("wave_follow_main_pitch", {}), dict) else {}
        settings_wave_note = settings.get("wave_note", {}) if isinstance(settings.get("wave_note", {}), dict) else {}
        settings_wave_octave = settings.get("wave_octave", {}) if isinstance(settings.get("wave_octave", {}), dict) else {}
        settings_wave_cents = settings.get("wave_cents", {}) if isinstance(settings.get("wave_cents", {}), dict) else {}
        settings_wave_shapes = settings.get("wave_shapes", {}) if isinstance(settings.get("wave_shapes", {}), dict) else {}

        for entry in dynamic_entries[:MAX_WAVE_ROWS]:
            if not isinstance(entry, dict):
                continue
            wave_id = str(entry.get("id", "")).strip()
            if not wave_id or wave_id in DEFAULT_WAVE_ORDER or wave_id in self.wave_row_order:
                continue
            shape = str(entry.get("shape", settings_wave_shapes.get(wave_id, "sine")))
            self._create_user_wave_row(wave_id, shape if shape in DEFAULT_WAVE_ORDER else "sine", entry)

        for entry in dynamic_entries:
            if isinstance(entry, dict) and entry.get("id"):
                waves.setdefault(str(entry.get("id")), entry)

        for wave_type in list(self.wave_row_order):
            wave_data = waves.get(wave_type, {})
            if isinstance(wave_data, dict):
                start_levels[wave_type] = int(wave_data.get("start_db", -20))
                end_levels[wave_type] = int(wave_data.get("end_db", -20))
                times[wave_type] = int(wave_data.get("change_time_percent", 100))
                wave_pan[wave_type] = int(wave_data.get("pan", self.wave_pan_sliders[wave_type].value()))
                wave_width[wave_type] = int(wave_data.get("spread", self.wave_width_sliders[wave_type].value()))
                wave_dance[wave_type] = int(wave_data.get("dance", self.wave_dance_sliders[wave_type].value()))
                wave_muted[wave_type] = bool(wave_data.get("muted", (settings.get("wave_muted", {}) if isinstance(settings.get("wave_muted", {}), dict) else {}).get(wave_type, False)))
                wave_follow_pitch[wave_type] = bool(wave_data.get("follow_main_pitch", settings_wave_follow.get(wave_type, True)))
                wave_note[wave_type] = str(wave_data.get("note", settings_wave_note.get(wave_type, "A")))
                try:
                    wave_octave[wave_type] = int(wave_data.get("octave", settings_wave_octave.get(wave_type, 4)))
                except Exception:
                    wave_octave[wave_type] = 4
                try:
                    wave_cents[wave_type] = float(wave_data.get("cents", settings_wave_cents.get(wave_type, 0.0)))
                except Exception:
                    wave_cents[wave_type] = 0.0

        self._set_wave_levels(start_levels, end_levels, times)
        self._set_wave_stereo(wave_pan, wave_width, wave_dance)
        for wave_type in list(self.wave_row_order):
            button = self.wave_mute_buttons.get(wave_type)
            if button is not None:
                button.blockSignals(True)
                button.setChecked(bool(wave_muted.get(wave_type, False)))
                button.setText("🤫 Quiet" if button.isChecked() else "🎵 On")
                button.blockSignals(False)
        for wave_type in list(self.wave_row_order):
            follow = self.wave_follow_pitch_buttons.get(wave_type)
            note = self.wave_note_combos.get(wave_type)
            octave = self.wave_octave_spins.get(wave_type)
            cents = self.wave_cents_sliders.get(wave_type)
            if follow is not None:
                follow.blockSignals(True)
                follow.setChecked(bool(wave_follow_pitch.get(wave_type, True)))
                follow.blockSignals(False)
            if note is not None:
                note.blockSignals(True)
                note.setCurrentText(wave_note.get(wave_type, "A") if wave_note.get(wave_type, "A") in NOTE_TO_INDEX else "A")
                note.blockSignals(False)
            if octave is not None:
                octave.blockSignals(True)
                octave.setValue(max(0, min(8, int(wave_octave.get(wave_type, 4)))))
                octave.blockSignals(False)
            if cents is not None:
                cents.blockSignals(True)
                cents.setValue(max(-5000, min(5000, int(round(wave_cents.get(wave_type, 0.0) * 100)))))
                cents.blockSignals(False)
            shape_combo = self.wave_shape_combos.get(wave_type)
            if shape_combo is not None:
                shape_value = str((waves.get(wave_type, {}) if isinstance(waves.get(wave_type, {}), dict) else {}).get("shape", settings_wave_shapes.get(wave_type, "sine")))
                shape_combo.blockSignals(True)
                shape_combo.setCurrentIndex(max(0, shape_combo.findData(shape_value if shape_value in DEFAULT_WAVE_ORDER else "sine")))
                shape_combo.blockSignals(False)
                self._user_wave_shape_changed(wave_type)
            self._update_wave_pitch_label(wave_type)

        solo_wave = ui.get("solo_wave", settings.get("solo_wave"))
        for wave_type, button in self.wave_solo_buttons.items():
            button.blockSignals(True)
            button.setChecked(solo_wave == wave_type)
            button.setText("👑 Star Sound" if button.isChecked() else "⭐ Only Me")
            button.blockSignals(False)
        self._refresh_all_wave_card_states()
        self._generate()


    def _load_sound(self) -> None:
        """Load a WaveToy recipe or audio file."""
        filename, selected_filter = QFileDialog.getOpenFileName(
            self,
            "Load Sound or Recipe",
            "",
            (
                "WaveToy Recipe (*.json *.wave-toy.json);;"
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
                    f"Loaded WaveToy recipe:\n{path.name}"
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
            "About WaveToy",
            "WaveToy is a visual sound and articulation lab for waveform synthesis, stereo visualization, and speech assets.\n\n"
            "Kid words: pitch, loudness, wave shape, left ear, right ear.\n"
            "Grown-up words: frequency, amplitude, waveform, envelope, stereo field.",
        )

    def _reset_wave_pitch_to_follow_main(self) -> None:
        """Return all wave cards to the backward-compatible main-pitch mode."""
        for wave_type, button in self.wave_follow_pitch_buttons.items():
            button.blockSignals(True)
            button.setChecked(True)
            button.blockSignals(False)
            self._update_wave_pitch_label(wave_type)

    def _preset_pure_a4(self) -> None:
        self._reset_wave_pitch_to_follow_main()
        self._set_wave_levels(
            {"sine": 0, "triangle": -20, "sawtooth": -20, "square": -20},
        )
        self.note_combo.setCurrentText("A")
        self.octave_slider.setValue(4 * OCTAVE_SLIDER_SCALE)
        self.cents_slider.setValue(0)
        self.pitch_start.setValue(69 * MIDI_SLIDER_SCALE)
        self.pitch_end.setValue(69 * MIDI_SLIDER_SCALE)
        self.loud_start.setValue(35 * PERCENT_SLIDER_SCALE)
        self.loud_end.setValue(35 * PERCENT_SLIDER_SCALE)
        self.duration_slider.setValue(int(1.5 * SECONDS_SLIDER_SCALE))
        self.pan_start_slider.setValue(0)
        self.pan_end_slider.setValue(0)
        self.width_slider.setValue(20 * PERCENT_SLIDER_SCALE)
        self.auto_pan_depth_slider.setValue(0)
        self._set_curve("linear")
        self._generate()

    def _preset_rocket_pitch(self) -> None:
        self._reset_wave_pitch_to_follow_main()
        self._set_wave_levels(
            {"sine": -18, "triangle": -20, "sawtooth": -18, "square": -24},
            {"sine": -30, "triangle": -20, "sawtooth": 0, "square": -36},
            {"sine": 100, "triangle": 100, "sawtooth": 55, "square": 80},
        )
        self.pitch_start.setValue(57 * MIDI_SLIDER_SCALE)
        self.pitch_end.setValue(81 * MIDI_SLIDER_SCALE)
        self.loud_start.setValue(30 * PERCENT_SLIDER_SCALE)
        self.loud_end.setValue(45 * PERCENT_SLIDER_SCALE)
        self.duration_slider.setValue(int(2.2 * SECONDS_SLIDER_SCALE))
        self.pan_start_slider.setValue(-40 * PERCENT_SLIDER_SCALE)
        self.pan_end_slider.setValue(40 * PERCENT_SLIDER_SCALE)
        self.width_slider.setValue(70 * PERCENT_SLIDER_SCALE)
        self.auto_pan_depth_slider.setValue(15 * PERCENT_SLIDER_SCALE)
        self._set_curve("exponential")
        self._generate()

    def _preset_robot_beep(self) -> None:
        self._reset_wave_pitch_to_follow_main()
        self._set_wave_levels(
            {"sine": -30, "triangle": -20, "sawtooth": -24, "square": 0},
            {"sine": -20, "triangle": -20, "sawtooth": -18, "square": -12},
            {"sine": 35, "triangle": 100, "sawtooth": 70, "square": 20},
        )
        self.pitch_start.setValue(64 * MIDI_SLIDER_SCALE)
        self.pitch_end.setValue(76 * MIDI_SLIDER_SCALE)
        self.loud_start.setValue(35 * PERCENT_SLIDER_SCALE)
        self.loud_end.setValue(35 * PERCENT_SLIDER_SCALE)
        self.duration_slider.setValue(int(0.8 * SECONDS_SLIDER_SCALE))
        self.width_slider.setValue(80 * PERCENT_SLIDER_SCALE)
        self.auto_pan_depth_slider.setValue(30 * PERCENT_SLIDER_SCALE)
        self.auto_pan_rate.setValue(int(2.0 * RATE_SLIDER_SCALE))
        self._set_curve("linear")
        self._generate()

    def _preset_falling_star(self) -> None:
        self._reset_wave_pitch_to_follow_main()
        self._set_wave_levels(
            {"sine": 0, "triangle": -18, "sawtooth": -20, "square": -20},
            {"sine": -24, "triangle": -36, "sawtooth": -20, "square": -20},
            {"sine": 100, "triangle": 75, "sawtooth": 100, "square": 100},
        )
        self.pitch_start.setValue(83 * MIDI_SLIDER_SCALE)
        self.pitch_end.setValue(53 * MIDI_SLIDER_SCALE)
        self.loud_start.setValue(45 * PERCENT_SLIDER_SCALE)
        self.loud_end.setValue(10 * PERCENT_SLIDER_SCALE)
        self.duration_slider.setValue(int(2.5 * SECONDS_SLIDER_SCALE))
        self.pan_start_slider.setValue(45 * PERCENT_SLIDER_SCALE)
        self.pan_end_slider.setValue(-45 * PERCENT_SLIDER_SCALE)
        self.width_slider.setValue(60 * PERCENT_SLIDER_SCALE)
        self._set_curve("logarithmic")
        self._generate()

    def _preset_fade_in_triangle(self) -> None:
        self._reset_wave_pitch_to_follow_main()
        self._set_wave_levels(
            {"sine": -20, "triangle": -20, "sawtooth": -20, "square": -20},
            {"sine": -24, "triangle": 0, "sawtooth": -20, "square": -20},
            {"sine": 100, "triangle": 100, "sawtooth": 100, "square": 100},
        )
        self.pitch_start.setValue(60 * MIDI_SLIDER_SCALE)
        self.pitch_end.setValue(60 * MIDI_SLIDER_SCALE)
        self.loud_start.setValue(0)
        self.loud_end.setValue(50 * PERCENT_SLIDER_SCALE)
        self.duration_slider.setValue(int(2.0 * SECONDS_SLIDER_SCALE))
        self.width_slider.setValue(40 * PERCENT_SLIDER_SCALE)
        self._set_curve("linear")
        self._generate()

    def _set_wave_stereo(
        self,
        pan_values: Dict[str, int],
        width_values: Dict[str, int],
        dance_values: Dict[str, int],
    ) -> None:
        for wave_type in list(self.wave_row_order):
            for slider_dict, value_dict, default_value in [
                (self.wave_pan_sliders, pan_values, self.wave_pan_sliders[wave_type].value()),
                (self.wave_width_sliders, width_values, self.wave_width_sliders[wave_type].value()),
                (self.wave_dance_sliders, dance_values, self.wave_dance_sliders[wave_type].value()),
            ]:
                slider = slider_dict[wave_type]
                slider.blockSignals(True)
                raw_value = int(value_dict.get(wave_type, default_value))
                if slider_dict in (self.wave_start_sliders, self.wave_end_sliders):
                    # Backward compatible: old recipes/presets use whole dB values or tenths.
                    if -20 <= raw_value <= 0:
                        raw_value *= DB_SLIDER_SCALE
                    elif -200 <= raw_value <= 0:
                        raw_value *= DB_SLIDER_SCALE // 10
                elif slider_dict is self.wave_time_sliders:
                    if 0 <= raw_value <= 100:
                        raw_value *= PERCENT_SLIDER_SCALE
                slider.setValue(raw_value)
                slider.blockSignals(False)

            self._update_wave_stereo_labels(wave_type)

        self._generate()

    def _set_wave_levels(
        self,
        levels: Dict[str, int],
        end_levels: Dict[str, int] | None = None,
        times: Dict[str, int] | None = None,
    ) -> None:
        end_levels = end_levels or levels
        times = times or {wave_type: 100 for wave_type in self.wave_row_order}

        for wave_type in list(self.wave_row_order):
            for slider_dict, value_dict, default_value in [
                (self.wave_start_sliders, levels, -20),
                (self.wave_end_sliders, end_levels, -20),
                (self.wave_time_sliders, times, 100),
            ]:
                slider = slider_dict[wave_type]
                slider.blockSignals(True)
                raw_value = int(value_dict.get(wave_type, default_value))
                if slider_dict in (self.wave_start_sliders, self.wave_end_sliders):
                    # Backward compatible: old recipes/presets use whole dB values or tenths.
                    if -20 <= raw_value <= 0:
                        raw_value *= DB_SLIDER_SCALE
                    elif -200 <= raw_value <= 0:
                        raw_value *= DB_SLIDER_SCALE // 10
                elif slider_dict is self.wave_time_sliders:
                    if 0 <= raw_value <= 100:
                        raw_value *= PERCENT_SLIDER_SCALE
                slider.setValue(raw_value)
                slider.blockSignals(False)

            self._update_wave_envelope_labels(wave_type)

        self._generate()


    def _set_preview_motion(self, active: bool) -> None:
        for preview in self.wave_mix_previews.values():
            preview.set_motion(active)
        for preview in self.wave_stereo_field_previews.values():
            preview.set_motion(active)
        for left_preview, right_preview in self.wave_stereo_previews.values():
            left_preview.set_motion(active)
            right_preview.set_motion(active)

    def _start_preview_motion_for_current_duration(self) -> None:
        self._preview_stop_timer.stop()
        self._set_preview_motion(True)
        duration_ms = max(250, int((len(self.current_audio) / SAMPLE_RATE) * 1000))
        self._preview_stop_timer.start(duration_ms)

    def _preview_samples_for_wave(self, wave_type: str) -> Dict[str, np.ndarray | Dict[str, float | bool]]:
        return build_wave_preview_samples(self._settings_from_ui(), wave_type)

    def _update_all_wave_previews(self) -> None:
        for wave_type in list(self.wave_row_order):
            self._update_wave_previews(wave_type)

    def _wave_preview_amplitude(self, wave_type: str) -> float:
        if wave_type not in self.wave_start_sliders or wave_type not in self.wave_end_sliders:
            return 0.0
        start_db = self.wave_start_sliders[wave_type].value() / DB_SLIDER_SCALE
        end_db = self.wave_end_sliders[wave_type].value() / DB_SLIDER_SCALE
        return max(db_to_gain(start_db), db_to_gain(end_db))

    def _update_wave_previews(self, wave_type: str) -> None:
        preview_samples = self._preview_samples_for_wave(wave_type)
        metadata = preview_samples["metadata"]
        amplitude = float(metadata.get("amplitude", self._wave_preview_amplitude(wave_type)))

        preview = self.wave_mix_previews.get(wave_type)
        if preview is not None:
            preview.set_wave_type(wave_type)
            preview.set_amplitude(amplitude)
            preview.set_samples(preview_samples["shape"])

        envelope_preview = self.wave_envelope_previews.get(wave_type)
        if envelope_preview is not None:
            envelope_preview.set_envelope(preview_samples["envelope"], metadata)

        stereo_field_preview = self.wave_stereo_field_previews.get(wave_type)
        if stereo_field_preview is not None:
            stereo_field_preview.set_wave_type(wave_type)
            stereo_field_preview.set_stereo_data(
                preview_samples["left_level"],
                preview_samples["right_level"],
                preview_samples["pan"],
                metadata,
            )

        previews = self.wave_stereo_previews.get(wave_type)
        if previews is not None:
            dance = float(metadata.get("dance", 0.0))
            for output_preview, key in zip(previews, ["left", "right"]):
                output_preview.set_wave_type(wave_type)
                output_preview.set_amplitude(amplitude)
                output_preview.set_samples(preview_samples[key])
                output_preview.set_motion_depth(dance)

    def _update_mix_preview(self, wave_type: str) -> None:
        self._update_wave_previews(wave_type)

    def _update_stereo_preview(self, wave_type: str) -> None:
        self._update_wave_previews(wave_type)

    def _update_wave_stereo_labels(self, wave_type: str) -> None:
        if wave_type not in self.wave_pan_sliders:
            return
        self.wave_pan_labels[wave_type].setText(self._pan_picture_text(self.wave_pan_sliders[wave_type].value()))
        self.wave_width_labels[wave_type].setText(self._width_picture_text(self.wave_width_sliders[wave_type].value()))
        self.wave_dance_labels[wave_type].setText(self._dance_picture_text(self.wave_dance_sliders[wave_type].value()))
        self._update_stereo_preview(wave_type)

    def _update_wave_envelope_labels(self, wave_type: str) -> None:
        start_value = self.wave_start_sliders[wave_type].value()
        end_value = self.wave_end_sliders[wave_type].value()
        time_percent = self.wave_time_sliders[wave_type].value()

        self.wave_start_labels[wave_type].setText(self._slider_picture_text(start_value, "loudness"))
        self.wave_end_labels[wave_type].setText(self._slider_picture_text(end_value, "loudness"))
        self.wave_time_labels[wave_type].setText(self._slider_picture_text(time_percent, "time"))
        self._update_wave_previews(wave_type)

    def _sync_duration_slider_to_spin(self, value: int) -> None:
        self._update_symbolic_labels()
        self._schedule_generate("duration_slider")

    def _sync_duration_shadow_to_slider(self, value: float) -> None:
        self._update_symbolic_labels()
        self._schedule_generate("duration_shadow")

    def _set_curve(self, curve_type: str) -> None:
        for index in range(self.curve_combo.count()):
            if self.curve_combo.itemData(index) == curve_type:
                self.curve_combo.setCurrentIndex(index)
                return


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("WaveToy")

    window = WaveToyWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
