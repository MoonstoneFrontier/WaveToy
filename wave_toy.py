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
import time
import wave
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

try:
    import sounddevice as sd
except Exception:
    sd = None

from PySide6.QtCore import QEvent, QMimeData, QPoint, QPointF, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QColor, QDrag, QFont, QKeySequence, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QGridLayout,
    QInputDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QMenu,
    QPushButton,
    QScrollArea,
    QSlider,
    QTabWidget,
    QToolButton,
    QSpinBox,
    QDoubleSpinBox,
    QVBoxLayout,
    QWidget,
)

SAMPLE_RATE = 44_100
MAX_PREVIEW_SECONDS = 8.0
WAVE_ORDER = ["sine", "triangle", "sawtooth", "square"]

# Internal UI resolution. Sliders remain child-friendly visually, but internally
# they have fine enough resolution for tuned harmonies and subtle modulation.
DB_SLIDER_SCALE = 100          # -2000..0 => -20.00 dB..0.00 dB
MIDI_SLIDER_SCALE = 100        # 3600..8400 => MIDI 36.00..84.00
OCTAVE_SLIDER_SCALE = 100      # 200..600 => octave 2.00..6.00
SECONDS_SLIDER_SCALE = 100     # 50..800 => 0.50s..8.00s
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
    """Imported reusable audio source for the Timeline Audio Palette."""

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
class TimelineClip:
    """Audio clip placed on the Timeline storyboard."""

    clip_id: int
    name: str
    audio: np.ndarray
    start_time_seconds: float
    lane: int
    sample_rate: int = SAMPLE_RATE
    recipe: Dict[str, object] | None = None
    source_path: str | None = None
    import_metadata: Dict[str, object] | None = None

    @property
    def duration_seconds(self) -> float:
        return max(0.0, float(len(self.audio)) / float(self.sample_rate))

    def metadata(self) -> Dict[str, object]:
        data = {
            "id": self.clip_id,
            "name": self.name,
            "start_time_seconds": self.start_time_seconds,
            "lane": self.lane,
            "duration_seconds": self.duration_seconds,
            "sample_rate": self.sample_rate,
            "recipe": self.recipe or {},
        }
        if self.source_path:
            data["source_path"] = self.source_path
        if self.import_metadata:
            data["import_metadata"] = self.import_metadata
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

    def clamped(self) -> "ArticulationPhoneme":
        family = str(self.phoneme_family or "vowel").lower()
        if family not in {"vowel", "fricative", "stop", "nasal"}:
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
        ).clamped()


VOWEL_PRESETS: Dict[str, Dict[str, object]] = {
    "EE": {"emoji": "😀", "ipa": "i", "tongue_height": 0.95, "tongue_frontness": 0.95, "mouth_open": 0.20, "lip_rounding": 0.05, "preview_color": "#b8f2e6"},
    "EH": {"emoji": "🙂", "ipa": "e", "tongue_height": 0.70, "tongue_frontness": 0.85, "mouth_open": 0.40, "lip_rounding": 0.05, "preview_color": "#caffbf"},
    "AH": {"emoji": "😮", "ipa": "a", "tongue_height": 0.20, "tongue_frontness": 0.40, "mouth_open": 0.95, "lip_rounding": 0.00, "preview_color": "#ffadad"},
    "OH": {"emoji": "😯", "ipa": "o", "tongue_height": 0.50, "tongue_frontness": 0.20, "mouth_open": 0.55, "lip_rounding": 0.60, "preview_color": "#ffd6a5"},
    "OO": {"emoji": "😗", "ipa": "u", "tongue_height": 0.90, "tongue_frontness": 0.10, "mouth_open": 0.15, "lip_rounding": 1.00, "preview_color": "#a0c4ff"},
    "UH": {"emoji": "😐", "ipa": "ə", "tongue_height": 0.45, "tongue_frontness": 0.50, "mouth_open": 0.45, "lip_rounding": 0.10, "preview_color": "#d7b9ff"},
}

FRICATIVE_PRESETS: Dict[str, Dict[str, object]] = {
    "S": {"emoji": "🦷", "ipa": "s", "phoneme_family": "fricative", "voiced": False, "air_pressure": 0.85, "teeth_gap": 0.15, "tongue_frontness": 0.85, "mouth_open": 0.28, "tongue_height": 0.72, "lip_rounding": 0.0, "duration_ms": 420, "noise_color": 0.85, "preview_color": "#d7f9ff"},
    "Z": {"emoji": "🦷", "ipa": "z", "phoneme_family": "fricative", "voiced": True, "air_pressure": 0.75, "teeth_gap": 0.18, "tongue_frontness": 0.85, "mouth_open": 0.28, "tongue_height": 0.70, "duration_ms": 420, "noise_color": 0.80, "preview_color": "#c7f9cc"},
    "SH": {"emoji": "🤫", "ipa": "ʃ", "phoneme_family": "fricative", "voiced": False, "air_pressure": 0.80, "teeth_gap": 0.25, "tongue_frontness": 0.45, "mouth_open": 0.32, "tongue_height": 0.62, "lip_rounding": 0.55, "duration_ms": 460, "noise_color": 0.62, "preview_color": "#bde0fe"},
    "F": {"emoji": "🌬", "ipa": "f", "phoneme_family": "fricative", "voiced": False, "air_pressure": 0.75, "teeth_gap": 0.20, "tongue_frontness": 0.50, "mouth_open": 0.22, "tongue_height": 0.45, "lip_rounding": 0.15, "duration_ms": 380, "noise_color": 0.55, "preview_color": "#e0fbfc"},
    "V": {"emoji": "🌬", "ipa": "v", "phoneme_family": "fricative", "voiced": True, "air_pressure": 0.65, "teeth_gap": 0.22, "tongue_frontness": 0.50, "mouth_open": 0.22, "tongue_height": 0.45, "duration_ms": 380, "noise_color": 0.50, "preview_color": "#caffbf"},
    "H": {"emoji": "💨", "ipa": "h", "phoneme_family": "fricative", "voiced": False, "air_pressure": 0.60, "teeth_gap": 0.75, "tongue_frontness": 0.45, "mouth_open": 0.55, "tongue_height": 0.35, "duration_ms": 360, "noise_color": 0.35, "preview_color": "#f1faee"},
}

STOP_PRESETS: Dict[str, Dict[str, object]] = {
    "P": {"emoji": "💥", "ipa": "p", "phoneme_family": "stop", "voiced": False, "closure": 1.0, "burst_strength": 0.75, "mouth_open": 0.12, "tongue_height": 0.35, "tongue_frontness": 0.50, "lip_rounding": 0.20, "duration_ms": 180, "noise_color": 0.50, "preview_color": "#ffd6a5"},
    "B": {"emoji": "💥", "ipa": "b", "phoneme_family": "stop", "voiced": True, "closure": 1.0, "burst_strength": 0.55, "mouth_open": 0.12, "tongue_height": 0.35, "tongue_frontness": 0.50, "duration_ms": 200, "noise_color": 0.45, "preview_color": "#fdffb6"},
    "T": {"emoji": "⚡", "ipa": "t", "phoneme_family": "stop", "voiced": False, "closure": 1.0, "burst_strength": 0.70, "tongue_frontness": 0.90, "mouth_open": 0.18, "tongue_height": 0.72, "duration_ms": 170, "noise_color": 0.85, "preview_color": "#ffadad"},
    "D": {"emoji": "⚡", "ipa": "d", "phoneme_family": "stop", "voiced": True, "closure": 1.0, "burst_strength": 0.50, "tongue_frontness": 0.90, "mouth_open": 0.18, "tongue_height": 0.70, "duration_ms": 200, "noise_color": 0.78, "preview_color": "#ffc6ff"},
    "K": {"emoji": "🪨", "ipa": "k", "phoneme_family": "stop", "voiced": False, "closure": 1.0, "burst_strength": 0.80, "tongue_frontness": 0.20, "mouth_open": 0.20, "tongue_height": 0.65, "duration_ms": 190, "noise_color": 0.38, "preview_color": "#a0c4ff"},
    "G": {"emoji": "🪨", "ipa": "g", "phoneme_family": "stop", "voiced": True, "closure": 1.0, "burst_strength": 0.55, "tongue_frontness": 0.20, "mouth_open": 0.20, "tongue_height": 0.65, "duration_ms": 220, "noise_color": 0.34, "preview_color": "#bdb2ff"},
}

NASAL_PRESETS: Dict[str, Dict[str, object]] = {
    "M": {"emoji": "👃", "ipa": "m", "phoneme_family": "nasal", "voiced": True, "nasal_open": 0.95, "closure": 0.90, "mouth_open": 0.10, "tongue_height": 0.45, "tongue_frontness": 0.45, "lip_rounding": 0.35, "duration_ms": 460, "preview_color": "#cdb4db"},
    "N": {"emoji": "👃", "ipa": "n", "phoneme_family": "nasal", "voiced": True, "nasal_open": 0.90, "closure": 0.80, "tongue_frontness": 0.85, "mouth_open": 0.12, "tongue_height": 0.65, "duration_ms": 460, "preview_color": "#bde0fe"},
    "NG": {"emoji": "👃", "ipa": "ŋ", "phoneme_family": "nasal", "voiced": True, "nasal_open": 0.90, "closure": 0.80, "tongue_frontness": 0.20, "mouth_open": 0.12, "tongue_height": 0.72, "duration_ms": 500, "preview_color": "#a2d2ff"},
}

CONSONANT_PRESET_SECTIONS: Tuple[Tuple[str, Dict[str, Dict[str, object]]], ...] = (
    ("🌬 Friction Sounds", FRICATIVE_PRESETS),
    ("💥 Pop Sounds", STOP_PRESETS),
    ("👃 Nose Sounds", NASAL_PRESETS),
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
        return f"{family_word} | {voice_word} | Closure {phoneme.closure:.2f} | Burst {phoneme.burst_strength:.2f}"
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


def _fade_and_normalize_mono(mono: np.ndarray, attack_ms: int, release_ms: int, peak: float = 0.78) -> np.ndarray:
    mono = np.asarray(mono, dtype=np.float64)
    if mono.size == 0:
        return np.zeros((0, 2), dtype=np.float32)
    attack = min(max(1, int(SAMPLE_RATE * attack_ms / 1000.0)), max(1, mono.size // 2))
    release = min(max(1, int(SAMPLE_RATE * release_ms / 1000.0)), max(1, mono.size // 2))
    mono[:attack] *= np.linspace(0.0, 1.0, attack, dtype=np.float64)
    mono[-release:] *= np.linspace(1.0, 0.0, release, dtype=np.float64)
    current_peak = float(np.max(np.abs(mono))) if mono.size else 0.0
    if current_peak > 0.0:
        mono = mono / current_peak * peak
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


def _voiced_tone(sample_count: int, phoneme: ArticulationPhoneme) -> np.ndarray:
    t = np.arange(sample_count, dtype=np.float64) / SAMPLE_RATE
    pitch = float(np.clip(phoneme.voice_pitch, 60.0, 880.0))
    tone = np.sin(2.0 * np.pi * pitch * t)
    tone += 0.35 * np.sin(2.0 * np.pi * pitch * 2.0 * t)
    tone += 0.18 * np.sin(2.0 * np.pi * pitch * 3.0 * t)
    return tone * float(np.clip(phoneme.voice_strength, 0.0, 1.0))


def _render_fricative_phoneme(phoneme: ArticulationPhoneme) -> np.ndarray:
    duration = float(np.clip(phoneme.duration_ms / 1000.0, 0.30, 0.60))
    sample_count = max(1, int(duration * SAMPLE_RATE))
    mono = _colored_noise(sample_count, phoneme) * (0.20 + phoneme.air_pressure * 0.80)
    if phoneme.voiced:
        mono += _voiced_tone(sample_count, phoneme) * 0.32
    return _fade_and_normalize_mono(mono, phoneme.attack_ms, phoneme.release_ms)


def _render_stop_phoneme(phoneme: ArticulationPhoneme) -> np.ndarray:
    duration = float(np.clip(phoneme.duration_ms / 1000.0, 0.12, 0.25))
    sample_count = max(1, int(duration * SAMPLE_RATE))
    mono = np.zeros(sample_count, dtype=np.float64)
    closure_samples = min(sample_count - 1, int(sample_count * (0.25 + phoneme.closure * 0.30)))
    burst_samples = min(sample_count - closure_samples, max(1, int(SAMPLE_RATE * 0.045)))
    burst = _colored_noise(burst_samples, phoneme) * (0.25 + phoneme.burst_strength)
    mono[closure_samples:closure_samples + burst_samples] += burst
    if phoneme.voiced and closure_samples < sample_count:
        onset = _voiced_tone(sample_count - closure_samples, phoneme)
        onset *= np.linspace(0.15, 1.0, onset.size)
        mono[closure_samples:] += onset * 0.38
    return _fade_and_normalize_mono(mono, 2, max(phoneme.release_ms, 35), peak=0.82)


def _render_nasal_phoneme(phoneme: ArticulationPhoneme) -> np.ndarray:
    duration = float(np.clip(phoneme.duration_ms / 1000.0, 0.30, 0.60))
    sample_count = max(1, int(duration * SAMPLE_RATE))
    tone = _voiced_tone(sample_count, phoneme)
    spectrum = np.fft.rfft(tone)
    freqs = np.fft.rfftfreq(sample_count, 1.0 / SAMPLE_RATE)
    nasal_center = 240.0 + (1.0 - phoneme.tongue_frontness) * 180.0
    envelope = 0.18 + 1.55 * np.exp(-0.5 * ((freqs - nasal_center) / 95.0) ** 2)
    envelope += 0.45 * np.exp(-0.5 * ((freqs - 950.0) / 260.0) ** 2)
    envelope *= 1.0 / (1.0 + (freqs / (1500.0 + phoneme.nasal_open * 1200.0)) ** 2)
    mono = np.fft.irfft(spectrum * envelope, n=sample_count) * (0.45 + phoneme.nasal_open * 0.55)
    return _fade_and_normalize_mono(mono, phoneme.attack_ms, phoneme.release_ms, peak=0.70)


def render_articulation_phoneme(phoneme: ArticulationPhoneme) -> np.ndarray:
    phoneme = phoneme.clamped()
    if phoneme.phoneme_family == "fricative":
        return _render_fricative_phoneme(phoneme)
    if phoneme.phoneme_family == "stop":
        return _render_stop_phoneme(phoneme)
    if phoneme.phoneme_family == "nasal":
        return _render_nasal_phoneme(phoneme)

    duration = max(0.12, phoneme.duration_ms / 1000.0)
    settings = SynthSettings(
        wave_start_db={"sine": -7.0, "triangle": -12.0, "sawtooth": -10.0, "square": -20.0},
        wave_end_db={"sine": -7.0, "triangle": -12.0, "sawtooth": -10.0, "square": -20.0},
        wave_delta_time={wave: duration for wave in WAVE_ORDER},
        pitch_start_hz=phoneme.voice_pitch,
        pitch_end_hz=phoneme.voice_pitch,
        loudness_start=phoneme.voice_strength,
        loudness_end=phoneme.voice_strength,
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
    duration = max(0.1, min(float(settings.duration_seconds), MAX_PREVIEW_SECONDS))

    start_levels = settings.wave_start_db or {"sine": 0.0, "triangle": -20.0, "sawtooth": -20.0, "square": -20.0}
    end_levels = settings.wave_end_db or dict(start_levels)
    delta_times = settings.wave_delta_time or {name: duration for name in WAVE_ORDER}
    muted = settings.wave_muted or {name: False for name in WAVE_ORDER}
    solo_wave = settings.solo_wave if settings.solo_wave in WAVE_ORDER else None
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
    raw_wave = waveform_from_phase(wave_type, phase)
    mono = raw_wave * gain_env
    if not is_audible:
        mono = np.zeros_like(mono)
        gain_env = np.zeros_like(gain_env)

    default_pan_offsets = {"sine": -0.45, "triangle": 0.45, "sawtooth": -0.85, "square": 0.85}
    wave_pan = settings.wave_pan or {name: default_pan_offsets[name] for name in WAVE_ORDER}
    wave_width = settings.wave_width or {name: 1.0 for name in WAVE_ORDER}
    wave_dance = settings.wave_dance or {name: 0.0 for name in WAVE_ORDER}

    time_axis = np.linspace(0.0, duration, sample_count, endpoint=False, dtype=np.float64)
    pan_base = make_curve(float(settings.pan_start), float(settings.pan_end), sample_count, settings.curve_type)
    global_width = np.clip(float(settings.stereo_width), 0.0, 1.0)
    auto_depth = np.clip(float(settings.auto_pan_depth), 0.0, 1.0)
    auto_rate = max(0.01, float(settings.auto_pan_rate))
    auto_pan = auto_depth * np.sin(2.0 * np.pi * auto_rate * time_axis)

    individual_pan = np.clip(float(wave_pan.get(wave_type, default_pan_offsets.get(wave_type, 0.0))), -1.0, 1.0)
    individual_width = np.clip(float(wave_width.get(wave_type, 1.0)), 0.0, 1.0)
    individual_dance = np.clip(float(wave_dance.get(wave_type, 0.0)), 0.0, 1.0)
    dance_phase = WAVE_ORDER.index(wave_type) * (math.pi / 2.0) if wave_type in WAVE_ORDER else 0.0
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
    duration = max(0.1, min(float(settings.duration_seconds), MAX_PREVIEW_SECONDS))
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
    delta_times = settings.wave_delta_time or {wave_type: duration for wave_type in WAVE_ORDER}

    mixed_stereo = np.zeros((total_samples, 2), dtype=np.float64)

    width = np.clip(float(settings.stereo_width), 0.0, 1.0)
    default_pan_offsets = {
        "sine": -0.45,
        "triangle": 0.45,
        "sawtooth": -0.85,
        "square": 0.85,
    }
    wave_pan = settings.wave_pan or {wave_type: default_pan_offsets[wave_type] for wave_type in WAVE_ORDER}
    wave_width = settings.wave_width or {wave_type: 1.0 for wave_type in WAVE_ORDER}
    wave_dance = settings.wave_dance or {wave_type: 0.0 for wave_type in WAVE_ORDER}
    wave_muted = settings.wave_muted or {wave_type: False for wave_type in WAVE_ORDER}
    solo_wave = settings.solo_wave if settings.solo_wave in WAVE_ORDER else None

    pan_base = make_curve(float(settings.pan_start), float(settings.pan_end), total_samples, settings.curve_type)

    auto_depth = np.clip(float(settings.auto_pan_depth), 0.0, 1.0)
    auto_rate = max(0.01, float(settings.auto_pan_rate))
    auto_pan = auto_depth * np.sin(2.0 * np.pi * auto_rate * time_axis)

    active_gain_total = 0.0

    for wave_type in WAVE_ORDER:
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
        mono_wave = waveform_from_phase(wave_type, phase) * gain_env
        individual_pan = np.clip(float(wave_pan.get(wave_type, default_pan_offsets[wave_type])), -1.0, 1.0)
        individual_width = np.clip(float(wave_width.get(wave_type, 1.0)), 0.0, 1.0)
        individual_dance = np.clip(float(wave_dance.get(wave_type, 0.0)), 0.0, 1.0)
        dance_phase = WAVE_ORDER.index(wave_type) * (math.pi / 2.0)
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
        painter.setFont(QFont("Arial", 14, QFont.Bold))

        text_rect = QRectF(rect.left() + 92, rect.top() + 18, rect.width() - 120, 52)
        painter.drawText(text_rect, Qt.AlignVCenter | Qt.TextWordWrap, self.mascot_message)



class WaveToySizing:
    """Central touch-friendly sizing tokens for WaveToy's toy UI."""

    MIN_TOUCH_TARGET = 48
    BUTTON_HEIGHT = 56
    LARGE_BUTTON_HEIGHT = 72
    ICON_STANDARD = 32
    ICON_LARGE = 48
    ICON_HERO = 64
    CARD_MIN_HEIGHT = 96
    SCROLLBAR_WIDTH = 22
    PAGE_MARGIN = 18
    CARD_PADDING = 14
    SECTION_SPACING = 14


class WaveToyTheme:
    """Shared color, spacing, and style helpers for the WaveToy interface."""

    BACKGROUND = "#7bdff2"
    SURFACE = "#ffffff"
    CARD = "#fff8d9"
    INK = "#263238"
    MUTED = "#607d8b"
    ACCENT = "#ff4fa3"
    ACCENT_DARK = "#ff2f91"
    BLUE = "#dff8ff"

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
                border: 3px solid rgba(0, 0, 0, 0.10);
                border-radius: {width // 2}px;
                width: {width}px;
                margin: 2px;
            }}
            QScrollBar::handle:vertical {{
                background: {cls.ACCENT};
                border: 3px solid white;
                border-radius: {max(8, (width - 6) // 2)}px;
                min-height: 72px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {cls.ACCENT_DARK};
            }}
            QScrollBar:horizontal {{
                background: rgba(255, 255, 255, 0.44);
                border: 3px solid rgba(0, 0, 0, 0.10);
                border-radius: {width // 2}px;
                height: {width}px;
                margin: 2px;
            }}
            QScrollBar::handle:horizontal {{
                background: {cls.ACCENT};
                border: 3px solid white;
                border-radius: {max(8, (width - 6) // 2)}px;
                min-width: 72px;
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
                padding: 8px 14px;
                border-radius: 16px;
                font-size: 16px;
                font-weight: 800;
            }}
            QComboBox, QSpinBox, QDoubleSpinBox {{
                min-height: {WaveToySizing.MIN_TOUCH_TARGET}px;
                padding: 4px 10px;
                border-radius: 14px;
            }}
            QCheckBox {{
                min-height: {WaveToySizing.MIN_TOUCH_TARGET}px;
                spacing: 10px;
                font-size: 16px;
                font-weight: 800;
            }}
            QGroupBox#toyGroup, QWidget#timelineInspector, QWidget#timelineAudioPalette, QWidget#explorerDashboardPanel {{
                margin-top: 8px;
            }}
        """


class WaveToyScrollArea(QScrollArea):
    """Unified toy-like scroll area with wheel, drag, kinetic scrolling, and large handles."""

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




class StoryboardClipWidget(QWidget):
    """Large touch-friendly storyboard clip card for the Timeline tab."""

    def __init__(self, icon: str, name: str, duration_text: str, wave_type: str, color: str) -> None:
        super().__init__()
        self.setObjectName("storyboardClip")
        self.setCursor(Qt.OpenHandCursor)
        self.setMinimumSize(QSize(260, 96))
        self.setToolTip("Drag this big sound card to rearrange the storyboard. Duplicate, mute, and solo are finger-friendly buttons.")

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
                background: #fff8d9;
                border: 4px solid {color};
                border-radius: 24px;
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
        layout.setContentsMargins(76, 10, 10, 10)
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
        self.drop_highlight_lane: int | None = None
        self.setAcceptDrops(True)

    def _refresh_size(self) -> None:
        arrangement = self.owner.timeline_clips if hasattr(self.owner, "timeline_clips") else []
        lane_count = max(1, getattr(self.owner, "timeline_lane_count", 4))
        end_time = max([clip.start_time_seconds + clip.duration_seconds for clip in arrangement] or [8.0])
        width = int(self.header_width + max(8.0, end_time + 2.0) / self.seconds_per_pixel + 80)
        height = int(self.top_pad * 2 + lane_count * self.lane_height + 34)
        self.setMinimumSize(QSize(max(980, width), max(520, height)))
        self.resize(self.minimumSize())

    def set_zoom(self, factor: float) -> None:
        self.seconds_per_pixel = min(0.08, max(0.004, self.seconds_per_pixel * factor))
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
        x = self._time_to_x(clip.start_time_seconds)
        y = self._lane_top(clip.lane) + 10
        width = max(150.0, clip.duration_seconds / self.seconds_per_pixel)
        height = 92.0
        return QRectF(x, y, width, height)

    def _clip_at(self, pos: QPoint) -> TimelineClip | None:
        for clip in reversed(getattr(self.owner, "timeline_clips", [])):
            if self._clip_rect(clip).contains(QPointF(pos)):
                return clip
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
        for second in range(0, int(max_seconds) + 2):
            x = self._time_to_x(float(second))
            painter.drawLine(QPointF(x, 4), QPointF(x, self.height() - 10))
            painter.drawText(QRectF(x + 4, 0, 70, 18), Qt.AlignLeft | Qt.AlignVCenter, f"{second}s")

        playhead_x = self._time_to_x(getattr(self.owner, "timeline_playhead_seconds", 0.0))
        painter.setPen(QPen(QColor("#ff2f91"), 5, Qt.SolidLine, Qt.RoundCap))
        painter.drawLine(QPointF(playhead_x, 0), QPointF(playhead_x, self.height()))

        for clip in getattr(self.owner, "timeline_clips", []):
            rect = self._clip_rect(clip)
            selected = clip.clip_id == self.selected_clip_id
            gradient = QLinearGradient(rect.topLeft(), rect.bottomRight())
            gradient.setColorAt(0.0, QColor("#fff8d9"))
            gradient.setColorAt(1.0, QColor("#b8f2e6" if not selected else "#ffd166"))
            painter.setPen(QPen(QColor("#ff4fa3" if selected else "#5c6bc0"), 5 if selected else 4))
            painter.setBrush(gradient)
            painter.drawRoundedRect(rect, 22, 22)

            painter.setFont(QFont("Arial", 30, QFont.Bold))
            painter.setPen(QColor("#263238"))
            painter.drawText(QRectF(rect.left() + 12, rect.top() + 10, 48, 42), Qt.AlignCenter, "🌊")
            painter.setFont(QFont("Arial", 16, QFont.Bold))
            painter.drawText(QRectF(rect.left() + 66, rect.top() + 10, rect.width() - 80, 28), Qt.AlignLeft | Qt.AlignVCenter, clip.name)
            painter.setFont(QFont("Arial", 12, QFont.Bold))
            painter.setPen(QColor("#607d8b"))
            painter.drawText(QRectF(rect.left() + 66, rect.top() + 36, rect.width() - 80, 22), Qt.AlignLeft | Qt.AlignVCenter, f"{clip.duration_seconds:.2f}s • Lane {clip.lane + 1}")

            wave_rect = rect.adjusted(14, 62, -14, -12)
            painter.setPen(QPen(QColor("#00a8cc"), 3, Qt.SolidLine, Qt.RoundCap))
            audio = np.asarray(clip.audio)
            if audio.ndim == 2 and len(audio) > 1:
                mono = audio.mean(axis=1)
                steps = max(12, min(90, int(wave_rect.width() // 4)))
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
            self.selected_clip_id = clip.clip_id
            self.drag_clip_id = clip.clip_id
            self.drag_offset_seconds = self._x_to_time(event.position().x()) - clip.start_time_seconds
            self.drag_started = False
            self.setCursor(Qt.ClosedHandCursor)
            self.owner._timeline_select_clip(clip.clip_id)
        else:
            self.selected_clip_id = None
            self.drag_clip_id = None
            self.owner._timeline_clear_selection(move_playhead_to=self._x_to_time(event.position().x()))
        self.update()

    def mouseMoveEvent(self, event) -> None:
        if self.drag_clip_id is None:
            self.setCursor(Qt.OpenHandCursor if self._clip_at(event.pos()) is not None else Qt.ArrowCursor)
            return
        clip = self.owner._timeline_clip_by_id(self.drag_clip_id)
        if clip is None:
            return
        old_start, old_lane = clip.start_time_seconds, clip.lane
        clip.start_time_seconds = max(0.0, self._x_to_time(event.position().x()) - self.drag_offset_seconds)
        clip.lane = self._lane_from_y(event.position().y())
        self.drag_started = True
        self.owner._timeline_update_duration()
        self.owner._timeline_update_inspector()
        if abs(old_start - clip.start_time_seconds) > 0.001 or old_lane != clip.lane:
            self.owner._timeline_debug(f"Clip moved id={clip.clip_id} start={clip.start_time_seconds:.3f}s lane={clip.lane}")
        self._refresh_size()
        self.update()

    def mouseReleaseEvent(self, event) -> None:
        if self.drag_clip_id is not None:
            self.owner._timeline_update_duration()
            self.owner._timeline_mark_mix_dirty()
        self.drag_clip_id = None
        self.drag_started = False
        self.setCursor(Qt.OpenHandCursor)
        self.update()

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasFormat("application/x-wavetoy-palette-id"):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event) -> None:
        if not event.mimeData().hasFormat("application/x-wavetoy-palette-id"):
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
        if not event.mimeData().hasFormat("application/x-wavetoy-palette-id"):
            event.ignore()
            return
        try:
            item_id = int(bytes(event.mimeData().data("application/x-wavetoy-palette-id")).decode("utf-8"))
        except ValueError:
            event.ignore()
            return
        start_time = self._x_to_time(event.position().x())
        lane = self._lane_from_y(event.position().y())
        self.owner._timeline_debug(f"Palette item dropped on timeline id={item_id} start={start_time:.3f}s lane={lane}")
        self.owner._timeline_add_palette_item_to_timeline(item_id, start_time, lane)
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
    """Tiny cached sample-based waveform preview used beside Wave Toy sliders."""

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

    def __init__(self) -> None:
        super().__init__()
        self.phoneme = ArticulationPhoneme.from_json_dict(VOWEL_PRESETS["AH"] | {"name": "AH", "voice_pitch": 220.0, "voice_strength": 0.65})
        self.setMinimumSize(QSize(520, 360))
        self.setToolTip("Toy vocal tract: mouth openness, tongue position, and lip rounding update as you explore vowels.")

    def set_phoneme(self, phoneme: ArticulationPhoneme) -> None:
        self.phoneme = phoneme.clamped()
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt override
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(self.rect()).adjusted(18, 18, -18, -18)
        painter.fillRect(self.rect(), QColor("#fff7e6"))

        p = self.phoneme
        mouth_open = float(np.clip(p.mouth_open, 0.0, 1.0))
        tongue_height = float(np.clip(p.tongue_height, 0.0, 1.0))
        tongue_front = float(np.clip(p.tongue_frontness, 0.0, 1.0))
        rounding = float(np.clip(p.lip_rounding, 0.0, 1.0))
        closure = float(np.clip(p.closure, 0.0, 1.0))
        nasal_open = float(np.clip(p.nasal_open, 0.0, 1.0))
        air_pressure = float(np.clip(p.air_pressure, 0.0, 1.0))

        face_rect = QRectF(rect.left() + 34, rect.top() + 8, rect.width() - 68, rect.height() - 16)
        painter.setPen(QPen(QColor("#5f4b32"), 5))
        painter.setBrush(QColor("#ffe0bd"))
        painter.drawRoundedRect(face_rect, 54, 54)

        mouth_w = face_rect.width() * (0.34 + (1.0 - rounding) * 0.30)
        mouth_h = 28 + mouth_open * 142
        mouth_cx = face_rect.center().x() + 20
        mouth_cy = face_rect.top() + face_rect.height() * 0.58
        mouth_rect = QRectF(mouth_cx - mouth_w / 2, mouth_cy - mouth_h / 2, mouth_w, mouth_h)
        painter.setPen(QPen(QColor("#8c2f39"), 8 + int(rounding * 10)))
        painter.setBrush(QColor("#301018"))
        painter.drawEllipse(mouth_rect)

        lip_rect = mouth_rect.adjusted(-12 - rounding * 18, -8 - rounding * 10, 12 + rounding * 18, 8 + rounding * 10)
        painter.setPen(QPen(QColor("#d1495b"), 5))
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(lip_rect)

        tongue_x = mouth_rect.left() + mouth_rect.width() * (0.20 + tongue_front * 0.58)
        tongue_y = mouth_rect.bottom() - 18 - tongue_height * max(24, mouth_rect.height() * 0.48)
        tongue_path = QPainterPath()
        tongue_path.moveTo(mouth_rect.left() + mouth_rect.width() * 0.18, mouth_rect.bottom() - 14)
        tongue_path.cubicTo(tongue_x - 70, tongue_y + 40, tongue_x - 10, tongue_y - 26, tongue_x + 58, tongue_y + 8)
        tongue_path.cubicTo(tongue_x + 34, tongue_y + 52, mouth_rect.right() - 38, mouth_rect.bottom() - 12, mouth_rect.left() + mouth_rect.width() * 0.18, mouth_rect.bottom() - 14)
        painter.setPen(QPen(QColor("#b23a48"), 3))
        painter.setBrush(QColor("#ff8fa3"))
        painter.drawPath(tongue_path)

        if closure > 0.08:
            closure_y = mouth_rect.center().y()
            painter.setPen(QPen(QColor("#ffb703"), 6 + int(closure * 10), Qt.SolidLine, Qt.RoundCap))
            painter.drawLine(QPointF(mouth_rect.left() + 18, closure_y), QPointF(mouth_rect.right() - 18, closure_y))
            painter.setFont(QFont("Sans Serif", 10, QFont.Bold))
            painter.setPen(QColor("#7a4f00"))
            painter.drawText(QRectF(mouth_rect.left(), mouth_rect.top() - 24, mouth_rect.width(), 20), Qt.AlignCenter, "closure")

        if air_pressure > 0.05:
            painter.setPen(QPen(QColor(78, 205, 196, 70 + int(air_pressure * 140)), 3, Qt.DashLine, Qt.RoundCap))
            for i in range(3):
                y = mouth_rect.center().y() - 24 + i * 24
                painter.drawLine(QPointF(face_rect.left() + 38, y), QPointF(mouth_rect.left() - 10, y + (i - 1) * 6))

        nose_rect = QRectF(face_rect.center().x() - 22, face_rect.top() + 136, 44, 48)
        painter.setPen(QPen(QColor("#8d6e63"), 3))
        painter.setBrush(QColor("#ffc8a2"))
        painter.drawEllipse(nose_rect)
        if nasal_open > 0.05:
            painter.setPen(QPen(QColor("#6a4c93"), 3 + int(nasal_open * 6)))
            painter.drawArc(nose_rect.adjusted(6, 12, -6, 10), 200 * 16, 140 * 16)
            painter.setPen(QPen(QColor("#6a4c93"), 2, Qt.DotLine))
            painter.drawLine(QPointF(nose_rect.center().x(), nose_rect.bottom()), QPointF(nose_rect.center().x(), mouth_rect.top()))

        if p.voiced:
            throat = QRectF(face_rect.left() + 36, face_rect.bottom() - 88, 58, 54)
            painter.setPen(QPen(QColor("#4361ee"), 3))
            painter.setBrush(QColor(67, 97, 238, 50))
            painter.drawEllipse(throat)
            painter.drawText(throat, Qt.AlignCenter, "voice")

        painter.setPen(QPen(QColor("#3a506b"), 4))
        painter.setBrush(QColor("#ffffff"))
        painter.drawEllipse(QRectF(face_rect.left() + face_rect.width() * 0.30, face_rect.top() + 80, 32, 42))
        painter.drawEllipse(QRectF(face_rect.left() + face_rect.width() * 0.62, face_rect.top() + 80, 32, 42))

        painter.setPen(QPen(QColor("#2b2d42"), 2))
        painter.setFont(QFont("Sans Serif", 14, QFont.Bold))
        f1, f2, f3 = formants_from_articulation(p)
        painter.drawText(rect.adjusted(10, rect.height() - 56, -10, -10), Qt.AlignLeft | Qt.AlignVCenter, f"{p.phoneme_family.title()}  |  F1 {f1:.0f}  F2 {f2:.0f}  F3 {f3:.0f} Hz")
        painter.end()


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
        self.wave_emotion_labels: Dict[str, QLabel] = {}
        self.visual_panel_buttons: Dict[str, VisualPanelButton] = {}
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
        self.timeline_lane_names = ["🎵 Melody Lane", "🥁 Rhythm Lane", "🌌 Atmosphere Lane", "✨ Effects Lane"]
        self.timeline_lane_count = len(self.timeline_lane_names)
        self.timeline_next_clip_id = 1
        self.timeline_selected_clip_id: int | None = None
        self.timeline_audio_palette: List[AudioPaletteItem] = []
        self.timeline_next_palette_item_id = 1
        self.timeline_selected_palette_item_id: int | None = None
        self.timeline_palette_list_widget: QWidget | None = None
        self.timeline_palette_count_label: QLabel | None = None
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

        self.phonemes_dir = Path("phonemes")
        self.current_phoneme = ArticulationPhoneme.from_json_dict(VOWEL_PRESETS["AH"] | {"name": "AH", "voice_pitch": 220.0, "voice_strength": 0.65})
        self.saved_phonemes: List[ArticulationPhoneme] = []
        self.articulation_canvas: VocalTractCanvas | None = None
        self.articulation_name_label: QLabel | None = None
        self.articulation_ipa_label: QLabel | None = None
        self.articulation_summary_label: QLabel | None = None
        self.articulation_wave_status_label: QLabel | None = None
        self.phoneme_cards_widget: QWidget | None = None
        self.articulation_sliders: Dict[str, QSlider] = {}
        self.articulation_value_labels: Dict[str, QLabel] = {}
        self.articulation_voiced_checkbox: QCheckBox | None = None
        self.phoneme_preview_audio = np.zeros((0, 2), dtype=np.float32)
        self.phoneme_loop_enabled = False
        self.phoneme_loop_timer = QTimer(self)
        self.phoneme_loop_timer.timeout.connect(self._articulation_loop_tick)

        self._build_actions()
        self._build_ui()
        self._build_shortcuts()
        self._apply_style()
        self._sync_note_to_pitch()
        self._generate_now(reason="startup", update_message=True, force=True)

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
        self.tabs = QTabWidget()
        self.tabs.setObjectName("mainTabs")
        self.setCentralWidget(self.tabs)

        scroll = WaveToyScrollArea(scroll_speed=1.05)
        self.tabs.addTab(scroll, "🧰 Classic Editor")

        root = QWidget()
        root.setMinimumSize(QSize(1060, 720))
        scroll.setWidget(root)

        outer = QVBoxLayout(root)
        outer.setContentsMargins(WaveToySizing.PAGE_MARGIN, 16, WaveToySizing.PAGE_MARGIN, 16)
        outer.setSpacing(WaveToySizing.SECTION_SPACING)

        title = QLabel("🌈 Wave Toy")
        title.setObjectName("title")

        subtitle = QLabel("Build sounds by shaping waves! Space = play. Shift+Space = live loop. Fine sliders use picture labels.")
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

        for wave_type in WAVE_ORDER:
            self._update_wave_pitch_label(wave_type)

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
        self.duration_slider.setRange(int(0.5 * SECONDS_SLIDER_SCALE), int(MAX_PREVIEW_SECONDS * SECONDS_SLIDER_SCALE))
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

        self.make_button = ToyButton("▶ Make Sound!", "#5cdb95")
        self.stop_button = ToyButton("■ Stop!", "#ff6b6b")
        self.save_button = ToyButton("💾 Save My Sound", "#ffd166")
        self.load_button = ToyButton("📂 Load Sound", "#b8f2e6")
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
        self._build_timeline_tab()
        if self.tabs is not None:
            self.tabs.setCurrentIndex(0)

    def _build_articulation_tab(self) -> None:
        if self.tabs is None:
            return
        self._load_saved_phonemes()
        tab = QWidget()
        tab.setObjectName("articulationLabTab")
        outer = QVBoxLayout(tab)
        outer.setContentsMargins(18, 16, 18, 16)
        outer.setSpacing(12)

        title = QLabel("🗣 Articulation Lab")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignCenter)
        subtitle = QLabel("Design vowel and consonant phonemes by moving a toy vocal tract. Phase 2 adds approximate fricatives, stops, and nasals — still playful, not full speech.")
        subtitle.setObjectName("subtitle")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setWordWrap(True)
        outer.addWidget(title)
        outer.addWidget(subtitle)

        main = QHBoxLayout()
        main.setSpacing(14)
        outer.addLayout(main, 1)

        explorer = self._toy_group("Vocal Explorer")
        explorer_layout = QVBoxLayout(explorer)
        explorer_layout.setContentsMargins(14, 18, 14, 14)
        explorer_layout.setSpacing(12)

        top = QHBoxLayout()
        self.articulation_name_label = QLabel("😮 AH")
        self.articulation_name_label.setObjectName("articulationPhonemeTitle")
        self.articulation_ipa_label = QLabel("IPA /a/")
        self.articulation_ipa_label.setObjectName("articulationIpaBadge")
        play_button = self._make_story_button("▶", "Play Phoneme", "#5cdb95", self._play_phoneme_preview)
        loop_button = self._make_story_button("🔁", "Loop", "#b8f2e6", self._toggle_phoneme_loop)
        stop_button = self._make_story_button("⏹", "Stop", "#ff6b6b", self._stop_phoneme_preview)
        top.addWidget(self.articulation_name_label, 2)
        top.addWidget(self.articulation_ipa_label, 1)
        top.addWidget(play_button)
        top.addWidget(loop_button)
        top.addWidget(stop_button)
        explorer_layout.addLayout(top)

        self.articulation_canvas = VocalTractCanvas()
        explorer_layout.addWidget(self.articulation_canvas, 1)
        self.articulation_summary_label = QLabel("😮 AH  |  Open Mouth | Low Tongue")
        self.articulation_summary_label.setObjectName("dashboardSummary")
        self.articulation_summary_label.setWordWrap(True)
        self.articulation_summary_label.setAlignment(Qt.AlignCenter)
        explorer_layout.addWidget(self.articulation_summary_label)

        controls = QGridLayout()
        controls.setHorizontalSpacing(14)
        controls.setVerticalSpacing(8)
        for row, (key, label, minimum, maximum, value) in enumerate((
            ("mouth_open", "👄 Mouth Open", 0, 100, 95),
            ("tongue_height", "👅 Tongue Height", 0, 100, 20),
            ("tongue_frontness", "👅 Tongue Front", 0, 100, 40),
            ("lip_rounding", "💋 Lip Round", 0, 100, 0),
            ("voice_pitch", "🎤 Voice Pitch", 60, 880, 220),
            ("voice_strength", "🔊 Voice Strength", 0, 100, 65),
            ("air_pressure", "🌬 Air Pressure", 0, 100, 45),
            ("teeth_gap", "🦷 Teeth Gap", 0, 100, 50),
            ("closure", "🔒 Closure", 0, 100, 0),
            ("burst_strength", "💥 Burst", 0, 100, 0),
            ("nasal_open", "👃 Nose Open", 0, 100, 0),
        )):
            text = QLabel(label)
            text.setObjectName("articulationControlLabel")
            slider = NoWheelSlider(Qt.Horizontal)
            slider.setRange(minimum, maximum)
            slider.setValue(value)
            slider.setMinimumHeight(56)
            value_label = QLabel("")
            value_label.setObjectName("symbolHint")
            value_label.setMinimumWidth(70)
            slider.valueChanged.connect(lambda _value, slider_key=key: self._articulation_slider_changed(slider_key))
            self.articulation_sliders[key] = slider
            self.articulation_value_labels[key] = value_label
            controls.addWidget(text, row, 0)
            controls.addWidget(slider, row, 1)
            controls.addWidget(value_label, row, 2)
        self.articulation_voiced_checkbox = QCheckBox("🎤 Voice On")
        self.articulation_voiced_checkbox.setChecked(True)
        self.articulation_voiced_checkbox.toggled.connect(lambda _checked: self._articulation_slider_changed("voiced"))
        controls.addWidget(self.articulation_voiced_checkbox, controls.rowCount(), 0, 1, 3)
        explorer_layout.addLayout(controls)
        main.addWidget(explorer, 3)

        side = QWidget()
        side.setMinimumWidth(320)
        side_layout = QVBoxLayout(side)
        side_layout.setContentsMargins(0, 0, 0, 0)
        side_layout.setSpacing(12)

        preset_box = self._toy_group("Vowels")
        preset_layout = QGridLayout(preset_box)
        preset_layout.setContentsMargins(WaveToySizing.CARD_PADDING, 20, WaveToySizing.CARD_PADDING, WaveToySizing.CARD_PADDING)
        preset_layout.setSpacing(12)
        for index, (name, data) in enumerate(VOWEL_PRESETS.items()):
            button = QPushButton(f"{data['emoji']}\n{name}")
            button.setObjectName("articulationPresetButton")
            button.setMinimumSize(QSize(148, 96))
            button.clicked.connect(lambda checked=False, preset_name=name: self._select_vowel_preset(preset_name))
            preset_layout.addWidget(button, index // 2, index % 2)
        side_layout.addWidget(CollapsibleSection("🔤 Vowels", preset_box, expanded=True))

        section_names = {
            "fricative": "🌬 Fricatives",
            "stop": "💥 Stops",
            "nasal": "👃 Nasals",
        }
        for section_title, presets in CONSONANT_PRESET_SECTIONS:
            first_preset = next(iter(presets.values()), {})
            family = str(first_preset.get("phoneme_family", "")).lower()
            consonant_box = self._toy_group(section_names.get(family, section_title))
            consonant_layout = QGridLayout(consonant_box)
            consonant_layout.setContentsMargins(WaveToySizing.CARD_PADDING, 20, WaveToySizing.CARD_PADDING, WaveToySizing.CARD_PADDING)
            consonant_layout.setSpacing(12)
            for index, (name, data) in enumerate(presets.items()):
                button = QPushButton(f"{data['emoji']}\n{name}")
                button.setObjectName("articulationPresetButton")
                button.setMinimumSize(QSize(148, 90))
                button.clicked.connect(lambda checked=False, preset_name=name, preset_data=data: self._select_consonant_preset(preset_name, preset_data))
                consonant_layout.addWidget(button, index // 2, index % 2)
            side_layout.addWidget(CollapsibleSection(section_names.get(family, section_title), consonant_box, expanded=False))

        save_button = self._make_story_button("💾", "Save Phoneme", "#ffd166", self._save_current_phoneme)
        side_layout.addWidget(save_button)

        cards_box = self._toy_group("Saved Phonemes")
        cards_layout = QVBoxLayout(cards_box)
        cards_layout.setContentsMargins(WaveToySizing.CARD_PADDING, 20, WaveToySizing.CARD_PADDING, WaveToySizing.CARD_PADDING)
        card_scroll = WaveToyScrollArea(scroll_speed=0.9)
        card_scroll.setMinimumHeight(230)
        self.phoneme_cards_widget = QWidget()
        card_scroll.setWidget(self.phoneme_cards_widget)
        cards_layout.addWidget(card_scroll, 1)
        side_layout.addWidget(CollapsibleSection("💾 Saved Phonemes", cards_box, expanded=True), 1)
        main.addWidget(side, 1)

        self.tabs.insertTab(min(2, self.tabs.count()), tab, "🗣 Articulation Lab")
        self._refresh_phoneme_cards()
        self._select_vowel_preset("AH", play=False)

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
        summary = articulation_summary(p)
        if self.articulation_summary_label is not None:
            self.articulation_summary_label.setText(f"{p.name} /{p.ipa}/  |  {summary}")
        if self.articulation_wave_status_label is not None:
            self.articulation_wave_status_label.setText(f"🗣 {p.name} /{p.ipa}/  |  {summary}")
        for key, label in self.articulation_value_labels.items():
            value = self._articulation_slider_value(key)
            label.setText(f"{value:.0f} Hz" if key == "voice_pitch" else f"{value:.2f}")
        if regenerate:
            self.phoneme_preview_audio = render_articulation_phoneme(p)

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
        self.phoneme_preview_audio = render_articulation_phoneme(self.current_phoneme)
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
        card.setStyleSheet(f"QWidget#phonemeCard {{ background: {phoneme.preview_color}; border-radius: 22px; }}")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 10, 12, 10)
        title = QLabel(f"/{phoneme.ipa}/  {phoneme.name}")
        title.setObjectName("phonemeCardTitle")
        title.setWordWrap(True)
        summary = QLabel(articulation_summary(phoneme))
        summary.setObjectName("phonemeCardSummary")
        summary.setWordWrap(True)
        row = QHBoxLayout()
        actions = (
            ("▶", lambda checked=False, p=phoneme: self._play_saved_phoneme(p)),
            ("Load", lambda checked=False, p=phoneme: self._load_saved_phoneme(p)),
            ("Rename", lambda checked=False, p=phoneme: self._rename_saved_phoneme(p)),
            ("Duplicate", lambda checked=False, p=phoneme: self._duplicate_saved_phoneme(p)),
            ("Delete", lambda checked=False, p=phoneme: self._delete_saved_phoneme(p)),
        )
        for text, callback in actions:
            button = QPushButton(text)
            button.setMinimumHeight(WaveToySizing.MIN_TOUCH_TARGET)
            button.clicked.connect(callback)
            row.addWidget(button)
        layout.addWidget(title)
        layout.addWidget(summary)
        layout.addLayout(row)
        return card

    def _play_saved_phoneme(self, phoneme: ArticulationPhoneme) -> None:
        self._play_audio_array(render_articulation_phoneme(phoneme))

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
                border: 4px solid rgba(0, 0, 0, 0.18);
                border-radius: 24px;
                font-size: 22px;
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

    def _build_timeline_tab(self) -> None:
        if self.tabs is None:
            return
        tab = QWidget()
        tab.setObjectName("timelineStoryboardTab")
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(14)

        title = QLabel("🎬 Timeline Storyboard")
        title.setObjectName("timelineStoryboardTitle")
        title.setAlignment(Qt.AlignCenter)
        subtitle = QLabel("Drop the current sound, drag big clips across lanes, play the story, then export the mix.")
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
            self._make_story_button("▶️", "Play Story", "#5cdb95", self._timeline_play_story),
            self._make_story_button("⏹", "Stop", "#ff6b6b", self._timeline_stop_story),
            self._make_story_button("🎚", "Mix Story", "#ffd166", self._timeline_render_mix),
            self._make_story_button("➕", "Drop Sound", "#b8f2e6", self._drop_story_sound),
            self._make_story_button("🛤️", "Add Lane", "#d7b9ff", self._add_story_lane),
            self._make_story_button("🔍", "Zoom In", "#caffbf", lambda checked=False: self._timeline_zoom(0.72)),
            self._make_story_button("🔎", "Zoom Out", "#ffc6ff", lambda checked=False: self._timeline_zoom(1.28)),
        ]
        for button in buttons:
            button.setMinimumHeight(72)
            transport_layout.addWidget(button)
        layout.addWidget(transport)

        edit_bar = QWidget()
        edit_layout = QHBoxLayout(edit_bar)
        edit_layout.setContentsMargins(0, 0, 0, 0)
        edit_layout.setSpacing(10)
        for icon, label, color, callback in (
            ("⧉", "Duplicate Clip", "#f1c0e8", self._timeline_duplicate_selected),
            ("🗑️", "Delete Clip", "#ffadad", self._timeline_delete_selected),
            ("💾", "Export Last Mix", "#fdffb6", self._timeline_export_last_mix),
        ):
            button = self._make_story_button(icon, label, color, callback)
            button.setMinimumHeight(66)
            edit_layout.addWidget(button)
        layout.addWidget(edit_bar)

        split = QHBoxLayout()
        split.setSpacing(12)

        palette = QWidget()
        palette.setObjectName("timelineAudioPalette")
        palette.setMinimumWidth(300)
        palette.setMaximumWidth(370)
        palette_layout = QVBoxLayout(palette)
        palette_layout.setContentsMargins(12, 12, 12, 12)
        palette_layout.setSpacing(10)
        palette_title = QLabel("🎧 Audio Palette")
        palette_title.setObjectName("timelineInspectorTitle")
        palette_subtitle = QLabel("Import sounds, then drag cards into lanes or tap ➕ Add.")
        palette_subtitle.setObjectName("timelineInspectorText")
        palette_subtitle.setWordWrap(True)
        import_button = self._make_story_button("📥", "Import Sounds", "#b8f2e6", self._timeline_import_sounds)
        import_button.setMinimumHeight(70)
        self.timeline_palette_count_label = QLabel("No imported sounds yet.")
        self.timeline_palette_count_label.setObjectName("timelineInspectorText")
        self.timeline_palette_count_label.setWordWrap(True)
        palette_scroll = WaveToyScrollArea(scroll_speed=0.9)
        self.timeline_palette_list_widget = QWidget()
        self.timeline_palette_list_widget.setObjectName("timelinePaletteList")
        palette_scroll.setWidget(self.timeline_palette_list_widget)
        palette_layout.addWidget(palette_title)
        palette_layout.addWidget(palette_subtitle)
        palette_layout.addWidget(import_button)
        palette_layout.addWidget(self.timeline_palette_count_label)
        palette_layout.addWidget(palette_scroll, 1)
        split.addWidget(palette)
        self._timeline_refresh_palette_cards()

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
        inspector_title = QLabel("🔎 Selected Clip")
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
        inspector_layout.addWidget(QLabel("🐞 Debug"))
        inspector_layout.addWidget(self.timeline_status_label)
        split.addWidget(inspector)
        layout.addLayout(split, 1)

        self._timeline_update_inspector()
        self.tabs.insertTab(min(3, self.tabs.count()), tab, "🎬 Timeline")
        self._timeline_debug("Timeline tab constructed")

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
            empty = QLabel("📥 Import WAV files to build your toy sound shelf.")
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
        message = f"Imported {imported} sound{'s' if imported != 1 else ''} into the Audio Palette."
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
            QMessageBox.information(self, "Audio Palette", "Select or import a palette sound first.")
            return
        self._timeline_add_palette_item_to_timeline(item.item_id, self.timeline_playhead_seconds, 0)

    def _timeline_add_palette_item_to_timeline(self, item_id: int, start_time_seconds: float, lane: int) -> None:
        item = self._timeline_palette_item_by_id(item_id)
        if item is None:
            QMessageBox.warning(self, "Audio Palette", "That palette sound is no longer available.")
            return
        clip_id = self.timeline_next_clip_id
        self.timeline_next_clip_id += 1
        clip = TimelineClip(
            clip_id=clip_id,
            name=item.name,
            audio=np.array(item.audio_data, dtype=np.float32, copy=True),
            start_time_seconds=max(0.0, start_time_seconds),
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

    def _drop_story_sound(self, checked: bool = False) -> None:
        self._timeline_debug("Drop Current Sound clicked")
        audio = self._timeline_current_audio(force=True)
        if audio.size == 0 or len(audio) < 8:
            self._timeline_debug("Drop rejected: empty audio")
            QMessageBox.warning(self, "Timeline drop failed", "Wave Toy could not find a rendered sound to drop. Try Make Sound, then Drop Sound again.")
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
            start_time_seconds=max(0.0, self.timeline_playhead_seconds),
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
        self.timeline_inspector_label.setText(
            f"{clip.name}\nID: {clip.clip_id}\nStart: {clip.start_time_seconds:.2f}s\nLane: {clip.lane + 1}\nDuration: {clip.duration_seconds:.2f}s"
        )

    def _timeline_update_duration(self) -> None:
        self.timeline_duration_seconds = max([clip.start_time_seconds + clip.duration_seconds for clip in self.timeline_clips] or [0.0])

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
            QMessageBox.warning(self, "Timeline mix", "Drop at least one sound before mixing the story.")
            self.timeline_last_mix = np.zeros((0, 2), dtype=np.float32)
            return self.timeline_last_mix
        total_samples = max(1, int(math.ceil(self.timeline_duration_seconds * SAMPLE_RATE)))
        mix = np.zeros((total_samples, 2), dtype=np.float32)
        for clip in self.timeline_clips:
            start = max(0, int(round(clip.start_time_seconds * SAMPLE_RATE)))
            end = min(total_samples, start + len(clip.audio))
            if end <= start:
                continue
            mix[start:end, :2] += np.asarray(clip.audio[: end - start, :2], dtype=np.float32)
        peak = float(np.max(np.abs(mix))) if mix.size else 0.0
        if peak > 1.0:
            mix = mix / peak
        final_peak = float(np.max(np.abs(mix))) if mix.size else 0.0
        self.timeline_last_mix = mix.astype(np.float32, copy=False)
        self.timeline_mix_dirty = False
        self._timeline_debug(f"Arrangement mixdown clip_count={len(self.timeline_clips)} duration={len(mix) / SAMPLE_RATE:.3f}s peak={final_peak:.4f}")
        return self.timeline_last_mix

    def _timeline_play_story(self, checked: bool = False) -> None:
        self._timeline_debug("Play Story clicked")
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
                "palette_sources": [item.metadata() for item in self.timeline_audio_palette],
                "clips": [clip.metadata() for clip in self.timeline_clips],
                "notes": "Imported clip metadata stores source paths only; raw audio arrays are not embedded. Reloading imported audio requires the source files to remain available.",
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

        title = QLabel("🎛 Play")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignCenter)
        subtitle = QLabel("Fast performance controls. Use Wave Explorer for toy panels or Classic Editor for every fallback control.")
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
            ("▶ Make Sound!", "#5cdb95", self._play),
            ("■ Stop!", "#ff6b6b", self._stop),
            ("💾 Save My Sound", "#ffd166", self._save),
            ("📂 Load Sound", "#b8f2e6", self._load_sound),
        ):
            button = ToyButton(label, color)
            button.setMinimumHeight(58)
            button.clicked.connect(callback)
            controls.addWidget(button)
        layout.addLayout(controls)
        layout.addStretch(1)
        self.tabs.insertTab(0, play, "🎛 Play")

    def _build_wave_explorer_tab(self) -> None:
        if self.tabs is None:
            return
        tab = QWidget()
        tab.setObjectName("waveExplorerTab")
        self.wave_explorer_tab = tab
        dashboard_layout = QGridLayout(tab)
        dashboard_layout.setContentsMargins(16, 14, 16, 14)
        dashboard_layout.setHorizontalSpacing(16)
        dashboard_layout.setVerticalSpacing(12)
        dashboard_layout.setColumnMinimumWidth(0, 210)
        dashboard_layout.setColumnMinimumWidth(1, 680)
        dashboard_layout.setColumnMinimumWidth(2, 210)
        dashboard_layout.setColumnStretch(0, 0)
        dashboard_layout.setColumnStretch(1, 1)
        dashboard_layout.setColumnStretch(2, 0)
        dashboard_layout.setRowStretch(1, 1)

        explorer_panel = QWidget()
        explorer_panel.setObjectName("explorerDashboardPanel")
        explorer_layout = QVBoxLayout(explorer_panel)
        explorer_layout.setContentsMargins(12, 12, 12, 12)
        explorer_layout.setSpacing(8)
        explorer_title = QLabel("🌊 Wave Explorer")
        explorer_title.setObjectName("dashboardExplorerTitle")
        explorer_title.setAlignment(Qt.AlignCenter)
        explorer_hint = QLabel("Keep the big waveform in the center. Open toy panels around the edges for detailed edits.")
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
        self.dashboard_canvas.setMinimumSize(QSize(720, 400))
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
        dashboard_layout.addWidget(explorer_panel, 0, 1, 3, 1)

        specs = {
            "shape": ("🎚 Shape Mix", "#5cdb95"),
            "pitch": ("🎯 Pitch Toys", "#ffd166"),
            "tuning": ("🎼 Tuning Map", "#b8f2e6"),
            "stereo": ("👂 Stereo Space", "#7bdff2"),
            "effects": ("✨ Sound Magic", "#d7b9ff"),
            "presets": ("🌈 Sound Experiments", "#ff99c8"),
        }
        positions = {
            "shape": (0, 0, Qt.AlignRight | Qt.AlignBottom),
            "pitch": (0, 2, Qt.AlignLeft | Qt.AlignBottom),
            "stereo": (1, 0, Qt.AlignRight | Qt.AlignVCenter),
            "effects": (1, 2, Qt.AlignLeft | Qt.AlignVCenter),
            "tuning": (2, 0, Qt.AlignRight | Qt.AlignTop),
            "presets": (2, 2, Qt.AlignLeft | Qt.AlignTop),
        }
        self.visual_panel_buttons.clear()
        for key, (label, color) in specs.items():
            button = VisualPanelButton(label, key, color)
            button.clicked.connect(lambda checked=False, panel_key=key: self._open_toy_panel(panel_key))
            self.visual_panel_buttons[key] = button
            row, column, alignment = positions[key]
            dashboard_layout.addWidget(button, row, column, alignment)

        self.tabs.insertTab(0, tab, "🌊 Wave Explorer")

    def _open_toy_panel(self, panel_key: str) -> None:
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
            "pitch": "🎯 Pitch Toys Panel",
            "tuning": "🎼 Tuning Map Panel",
            "stereo": "👂 Stereo Space Panel",
            "effects": "✨ Sound Magic Panel",
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
            "pitch": ("🎯 Pitch Toys", "#ffd166"),
            "tuning": ("🎼 Tuning Map", "#b8f2e6"),
            "stereo": ("👂 Stereo Space", "#7bdff2"),
            "effects": ("✨ Sound Magic", "#d7b9ff"),
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
        for row, wave_type in enumerate(WAVE_ORDER, start=1):
            self.dashboard_workspace_layout.addWidget(QLabel(f"{self._wave_icon(wave_type)} {WAVE_LABELS[wave_type]}"), row, 0)
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
        for index, wave_type in enumerate(WAVE_ORDER, start=5):
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
        for row, wave_type in enumerate(WAVE_ORDER, start=5):
            self.dashboard_workspace_layout.addWidget(QLabel(f"{self._wave_icon(wave_type)}"), row, 0)
            self.dashboard_workspace_layout.addWidget(self._make_synced_slider(self.wave_pan_sliders[wave_type]), row, 1)
            self.dashboard_workspace_layout.addWidget(self._make_synced_slider(self.wave_width_sliders[wave_type]), row, 2)
            self.dashboard_workspace_layout.addWidget(self._make_synced_slider(self.wave_dance_sliders[wave_type]), row, 3)

    def _build_effects_workspace(self) -> None:
        if self.dashboard_workspace_layout is None or self.dashboard_workspace_title is None:
            return
        self.dashboard_workspace_title.setText("✨ Sound Magic Workspace — effect playground around the wave picture.")
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
        s = self.current_settings
        live_samples = self._dashboard_audio_thumbnail()
        muted = s.wave_muted or {}
        solo = s.solo_wave if s.solo_wave in WAVE_ORDER else None
        amps = {
            wave: max(db_to_gain((s.wave_start_db or {}).get(wave, -20.0)), db_to_gain((s.wave_end_db or {}).get(wave, -20.0)))
            for wave in WAVE_ORDER
        }
        active = [wave for wave in WAVE_ORDER if not muted.get(wave, False) and (solo is None or solo == wave) and amps[wave] > 0.01]
        shape_status = f"Solo {WAVE_LABELS[solo].split()[0]}" if solo else f"{len(active)} Waves"
        self.visual_panel_buttons["shape"].set_status(shape_status, {"amps": amps, "muted": muted, "solo": solo, "samples": live_samples})

        follow = s.wave_follow_main_pitch or {wave: True for wave in WAVE_ORDER}
        notes = s.wave_note or {wave: s.note for wave in WAVE_ORDER}
        pitch_items = []
        custom = []
        for wave in WAVE_ORDER:
            color = VisualPanelButton.COLORS.get(wave, QColor("#ff4fa3"))
            note_text = s.note if follow.get(wave, True) else str(notes.get(wave, s.note))
            pitch_items.append((wave, note_text, color))
            if not follow.get(wave, True):
                custom.append(f"{wave.title()} {note_text}")
        pitch_status = f"{s.note}{int(round(s.octave))} Main" if not custom else "Custom Notes"
        self.visual_panel_buttons["pitch"].set_status(pitch_status, {"notes": pitch_items})

        tuning_label = TUNING_METHODS.get(s.tuning_method, TUNING_METHODS["equal_temperament_12"])["label"]
        self.visual_panel_buttons["tuning"].set_status(str(tuning_label), {"method": tuning_label, "root": s.tuning_root_note})

        positions = []
        wave_pan = s.wave_pan or {}
        wave_width = s.wave_width or {}
        wave_dance = s.wave_dance or {}
        for wave in WAVE_ORDER:
            positions.append((wave, wave_pan.get(wave, 0.0), wave_width.get(wave, 0.65), wave_dance.get(wave, 0.0)))
        stereo_status = "Dancing" if s.auto_pan_depth > 0.05 or any(float(item[3]) > 0.05 for item in positions) else "Wide" if s.stereo_width > 0.55 else "Centered"
        self.visual_panel_buttons["stereo"].set_status(stereo_status, {"positions": positions})

        paul_active = not (s.muted_modules or {}).get("paulstretch", True)
        effect_status = "Paulstretch On" if paul_active else "Paulstretch Off"
        self.visual_panel_buttons["effects"].set_status(effect_status, {"paul_active": paul_active, "amount": s.paulstretch_amount, "after_samples": live_samples})

        recipe_count = len(self._read_user_recipes())
        preset_status = f"{recipe_count} Saved" if recipe_count else "Try Presets"
        self.visual_panel_buttons["presets"].set_status(preset_status, {"count": recipe_count})
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
            mute_text = f"Solo {WAVE_LABELS[solo].split()[0]}"
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
        return {
            "sine": "〰️",
            "triangle": "🔺",
            "sawtooth": "📐",
            "square": "🧱",
        }.get(wave_type, "〰️")

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
                background: #7bdff2;
                border-radius: {SLIDER_GROOVE_RADIUS}px;
            }}
            QSlider::handle:horizontal {{
                background: #ff4fa3;
                border: 3px solid white;
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
                background: #7bdff2;
            }
            QScrollArea {
                background: #7bdff2;
            }
            QTabWidget#mainTabs::pane {
                border: 0;
                background: #7bdff2;
            }
            QTabBar::tab {
                background: #e9fbff;
                border: 3px solid rgba(0, 0, 0, 0.12);
                border-bottom: 0;
                border-top-left-radius: 14px;
                border-top-right-radius: 14px;
                color: #263238;
                font-size: 18px;
                font-weight: 900;
                min-height: 46px;
                padding: 10px 22px;
            }
            QTabBar::tab:selected {
                background: #ffffff;
            }
            QWidget#waveExplorerTab, QWidget#playTab, QWidget#timelineStoryboardTab {
                background: #7bdff2;
            }
            QLabel#timelineStoryboardTitle {
                font-size: 48px;
                font-weight: 900;
                color: #263238;
            }
            QLabel#timelineStoryboardSubtitle {
                font-size: 20px;
                font-weight: 900;
                color: #37474f;
            }
            QWidget#storyTransportBar {
                background: rgba(255, 255, 255, 0.72);
                border: 5px solid rgba(255, 153, 200, 0.58);
                border-radius: 28px;
            }
            QPushButton#storyTransportButton {
                min-height: 72px;
                font-size: 22px;
                font-weight: 900;
                border-radius: 24px;
                padding: 8px 14px;
            }
            QScrollArea#storyboardScroll, QWidget#storyboardLaneRoot {
                background: transparent;
            }
            QWidget#timelineCanvas {
                background: #dff8ff;
                border: 5px solid rgba(0, 0, 0, 0.12);
                border-radius: 24px;
            }
            QWidget#timelineInspector, QWidget#timelineAudioPalette {
                background: #fff8d9;
                border: 5px solid rgba(255, 153, 200, 0.72);
                border-radius: 26px;
            }
            QWidget#timelinePaletteList {
                background: transparent;
            }
            QLabel#timelineInspectorTitle {
                font-size: 24px;
                font-weight: 900;
                color: #263238;
            }
            QLabel#timelineInspectorText {
                font-size: 16px;
                font-weight: 800;
                color: #37474f;
            }
            QWidget#storyboardLane {
                background: #eefbff;
                border: 5px solid rgba(123, 223, 242, 0.78);
                border-radius: 28px;
            }
            QLabel#storyboardLaneHeader {
                background: #ffffff;
                border: 4px solid rgba(0, 0, 0, 0.14);
                border-radius: 24px;
                color: #263238;
                font-size: 22px;
                font-weight: 900;
                padding: 8px;
            }
            QWidget#storyboardClipStrip {
                background: rgba(255, 255, 255, 0.62);
                border: 3px dashed rgba(0, 0, 0, 0.12);
                border-radius: 22px;
            }
            QWidget#storyboardClip {
                background: #fff8d9;
                border: 4px solid rgba(255, 153, 200, 0.82);
                border-radius: 24px;
            }
            QLabel#storyboardClipIcon {
                font-size: 42px;
                background: #ffffff;
                border: 3px solid rgba(0, 0, 0, 0.10);
                border-radius: 18px;
            }
            QLabel#storyboardClipName {
                font-size: 20px;
                font-weight: 900;
                color: #263238;
            }
            QLabel#storyboardClipDuration {
                font-size: 16px;
                font-weight: 900;
                color: #607d8b;
            }
            QPushButton#storyboardTinyAction {
                min-width: 48px;
                min-height: 48px;
                border-radius: 16px;
                font-size: 20px;
                padding: 0;
            }
            QWidget#toyFloatingPanel {
                background: #fff8d9;
                border: 4px solid rgba(255, 153, 200, 0.75);
                border-radius: 24px;
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
                border: 4px solid rgba(0, 0, 0, 0.16);
                border-radius: 20px;
                margin-top: 16px;
                padding: 10px;
                font-size: 17px;
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
                border: 4px solid rgba(0, 0, 0, 0.18);
                border-radius: 24px;
                margin-top: 16px;
                padding: 10px;
                font-size: 18px;
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
                border: 5px solid rgba(123, 223, 242, 0.78);
                border-radius: 28px;
                padding: 8px;
            }
            QLabel#dashboardExplorerTitle {
                font-size: 30px;
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
            QLabel#workspaceTitle {
                font-size: 14px;
                font-weight: 900;
                color: #263238;
            }
            QWidget#waveCard {
                background: #f9fbff;
                border: 3px solid rgba(0, 0, 0, 0.10);
                border-radius: 16px;
            }
            QWidget#waveCardMuted {
                background: #eef1f4;
                border: 3px dashed rgba(69, 90, 100, 0.25);
                border-radius: 16px;
            }
            QWidget#waveCardSolo {
                background: #fff8d9;
                border: 4px solid #ffd166;
                border-radius: 16px;
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
                font-size: 22px;
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
                font-size: 34px;
                font-weight: 900;
                color: #263238;
            }
            QLabel#articulationIpaBadge {
                background: #ffffff;
                border: 4px solid rgba(0, 0, 0, 0.14);
                border-radius: 20px;
                font-size: 24px;
                font-weight: 900;
                padding: 10px;
            }
            QLabel#articulationControlLabel {
                font-size: 20px;
                font-weight: 900;
                color: #263238;
            }
            QLabel#phonemeCardTitle {
                font-size: 22px;
                font-weight: 900;
                color: #1d1d1d;
            }
            QLabel#phonemeCardSummary {
                font-size: 13px;
                font-weight: 900;
                color: #263238;
            }
            QPushButton#articulationPresetButton {
                border-radius: 26px;
                border: 4px solid rgba(0, 0, 0, 0.16);
                background: #fff7e6;
                font-size: 30px;
                font-weight: 900;
                padding: 8px;
            }
            QWidget#articulationLabTab {
                background: #fff1d6;
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
            QWidget#collapsibleSection {
                background: transparent;
                margin: 0;
            }
            QToolButton#collapsibleHeader {
                background: #ffffff;
                border: 4px solid rgba(255, 153, 200, 0.62);
                border-radius: 20px;
                color: #263238;
                font-size: 20px;
                font-weight: 900;
                min-height: 56px;
                padding: 8px 12px;
                text-align: left;
            }
            QToolButton#collapsibleHeader:hover {
                background: #fff8d9;
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
        for wave_type in WAVE_ORDER:
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
        for wave_type in WAVE_ORDER:
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
        return self.duration_slider.value() / SECONDS_SLIDER_SCALE

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

        for wave_type in WAVE_ORDER:
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
        audio, time_axis, freq_env, loud_env = generate_audio(self.current_settings)

        self.current_audio = audio

        wave_muted = self.current_settings.wave_muted or {}
        solo_wave = self.current_settings.solo_wave if self.current_settings.solo_wave in WAVE_ORDER else None
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
                    f"{WAVE_LABELS[wave_type]} {start_db:.1f}→{end_db:.1f} dB over {change_time:.1f}s"
                )

        active_text = ", ".join(active) if active else "no waves yet"

        if self.beginner_mode.isChecked():
            simple_wave_words = []

            for wave_type, start_db in (s.wave_start_db or {}).items():
                end_db = (s.wave_end_db or {}).get(wave_type, start_db)

                if start_db > -20 or end_db > -20:
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
        self.duration_slider.setValue(int(round(float(settings.get("duration_seconds", 1.5)) * SECONDS_SLIDER_SCALE)))
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

        for wave_type in WAVE_ORDER:
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
        for wave_type in WAVE_ORDER:
            button = self.wave_mute_buttons.get(wave_type)
            if button is not None:
                button.blockSignals(True)
                button.setChecked(bool(wave_muted.get(wave_type, False)))
                button.setText("🤫 Quiet" if button.isChecked() else "🎵 On")
                button.blockSignals(False)
        for wave_type in WAVE_ORDER:
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
        for wave_type in WAVE_ORDER:
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
        times = times or {wave_type: 100 for wave_type in WAVE_ORDER}

        for wave_type in WAVE_ORDER:
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
        for wave_type in WAVE_ORDER:
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
    app.setApplicationName("Wave Toy")

    window = WaveToyWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
