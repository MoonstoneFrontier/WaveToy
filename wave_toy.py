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
    cycles = 2.35
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
        self.zoom_factor = 1.0
        self.zoom_center = 0.5
        self.update()
        event.accept()

    def _visible_slice(self, data: np.ndarray) -> np.ndarray:
        if data.size == 0 or self.zoom_factor <= 1.01:
            return data

        total = data.shape[0]
        visible = max(32, int(total / self.zoom_factor))
        visible = min(visible, total)

        center = int(total * self.zoom_center)
        start = max(0, min(total - visible, center - visible // 2))
        end = start + visible
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
        self._preview_stop_timer = QTimer(self)
        self._preview_stop_timer.setSingleShot(True)
        self._preview_stop_timer.timeout.connect(lambda: self._set_preview_motion(False))

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
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        self.setCentralWidget(scroll)

        root = QWidget()
        root.setMinimumSize(QSize(1060, 720))
        scroll.setWidget(root)

        outer = QVBoxLayout(root)
        outer.setContentsMargins(16, 14, 16, 14)
        outer.setSpacing(10)

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

            start_label = QLabel(self._slider_picture_text(default_start[wave_type] * DB_SLIDER_SCALE, "loudness"))
            start_slider = QSlider(Qt.Horizontal)
            start_slider.setRange(-20 * DB_SLIDER_SCALE, 0)
            start_slider.setValue(default_start[wave_type] * DB_SLIDER_SCALE)
            start_slider.setTickInterval(2 * DB_SLIDER_SCALE)
            start_slider.setToolTip("Starting size of this wave.")
            self._connect_scheduled_generate(start_slider.valueChanged, "wave_start_slider")
            start_slider.valueChanged.connect(lambda value, wt=wave_type: self._update_wave_envelope_labels(wt))

            end_label = QLabel(self._slider_picture_text(default_end[wave_type] * DB_SLIDER_SCALE, "loudness"))
            end_slider = QSlider(Qt.Horizontal)
            end_slider.setRange(-20 * DB_SLIDER_SCALE, 0)
            end_slider.setValue(default_end[wave_type] * DB_SLIDER_SCALE)
            end_slider.setTickInterval(2 * DB_SLIDER_SCALE)
            end_slider.setToolTip("Ending size of this wave.")
            self._connect_scheduled_generate(end_slider.valueChanged, "wave_end_slider")
            end_slider.valueChanged.connect(lambda value, wt=wave_type: self._update_wave_envelope_labels(wt))

            time_label = QLabel("🐢 Slow")
            time_slider = QSlider(Qt.Horizontal)
            time_slider.setRange(1, 100 * PERCENT_SLIDER_SCALE)
            time_slider.setValue(100 * PERCENT_SLIDER_SCALE)
            time_slider.setTickInterval(10 * PERCENT_SLIDER_SCALE)
            time_slider.setToolTip("How slowly or quickly this wave changes.")
            self._connect_scheduled_generate(time_slider.valueChanged, "wave_time_slider")
            time_slider.valueChanged.connect(lambda value, wt=wave_type: self._update_wave_envelope_labels(wt))

            pan_label = QLabel(self._pan_picture_text(default_wave_pan[wave_type] * PERCENT_SLIDER_SCALE))
            pan_slider = QSlider(Qt.Horizontal)
            pan_slider.setRange(-100 * PERCENT_SLIDER_SCALE, 100 * PERCENT_SLIDER_SCALE)
            pan_slider.setValue(default_wave_pan[wave_type] * PERCENT_SLIDER_SCALE)
            pan_slider.setToolTip("Where this ingredient sits between the left and right ear.")
            self._connect_scheduled_generate(pan_slider.valueChanged, "wave_pan_slider")
            pan_slider.valueChanged.connect(lambda value, wt=wave_type: self._update_wave_stereo_labels(wt))

            width_label = QLabel("↔️ Medium")
            width_slider = QSlider(Qt.Horizontal)
            width_slider.setRange(0, 100 * PERCENT_SLIDER_SCALE)
            width_slider.setValue(65 * PERCENT_SLIDER_SCALE)
            width_slider.setToolTip("How wide this ingredient feels in stereo space.")
            self._connect_scheduled_generate(width_slider.valueChanged, "wave_width_slider")
            width_slider.valueChanged.connect(lambda value, wt=wave_type: self._update_wave_stereo_labels(wt))

            dance_label = QLabel("😴 Still")
            dance_slider = QSlider(Qt.Horizontal)
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

            shape_stage = make_stage("Shape", shape_preview, [mute_button, solo_button])
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

        self.note_combo = QComboBox()
        self.note_combo.addItems(NOTE_NAMES)
        self.note_combo.setCurrentText("A")

        self.octave_slider = QSlider(Qt.Horizontal)
        self.octave_slider.setRange(2 * OCTAVE_SLIDER_SCALE, 6 * OCTAVE_SLIDER_SCALE)
        self.octave_slider.setValue(4 * OCTAVE_SLIDER_SCALE)
        self.octave_label = QLabel("🧸 Middle")

        self.cents_slider = QSlider(Qt.Horizontal)
        self.cents_slider.setRange(-50 * 100, 50 * 100)
        self.cents_slider.setValue(0)
        self.cents_label = QLabel("🎯 Center")

        self.base_pitch_label = QLabel("Pitch: 🎵 ready")
        self.base_pitch_label.setObjectName("symbolHint")

        self.tuning_method_combo = QComboBox()
        for method_id, method in TUNING_METHODS.items():
            self.tuning_method_combo.addItem(str(method["label"]), method_id)
            index = self.tuning_method_combo.count() - 1
            self.tuning_method_combo.setItemData(index, str(method["tooltip"]), Qt.ToolTipRole)
        self.tuning_method_combo.setToolTip("Choose how notes are spaced.")

        self.tuning_root_combo = QComboBox()
        self.tuning_root_combo.addItems(NOTE_NAMES)
        self.tuning_root_combo.setCurrentText("A")
        self.tuning_root_combo.setToolTip("Pick the home note for tunings that lean around a root.")

        self.tuning_reference_spin = QDoubleSpinBox()
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

        overview_box = self._toy_group("Wave Overview")
        overview_box.setMinimumWidth(280)
        overview_box.setMaximumWidth(370)
        overview_layout = QVBoxLayout(overview_box)
        overview_layout.setContentsMargins(10, 18, 10, 10)
        overview_layout.setSpacing(6)
        self.canvas = WaveCanvas()
        self.canvas.setMinimumSize(QSize(260, 180))
        self.canvas.setMaximumSize(QSize(340, 240))
        overview_layout.addWidget(self.canvas, 0, Qt.AlignCenter)
        right.addWidget(overview_box, 0, Qt.AlignTop | Qt.AlignRight)

        motion_box = self._toy_group("3. Change Over Time")
        motion_box.setMinimumWidth(280)
        motion_layout = QGridLayout(motion_box)
        motion_layout.setHorizontalSpacing(12)
        motion_layout.setVerticalSpacing(10)
        motion_layout.setColumnStretch(0, 1)
        motion_layout.setColumnStretch(1, 2)

        self.duration_slider = QSlider(Qt.Horizontal)
        self.duration_slider.setRange(int(0.5 * SECONDS_SLIDER_SCALE), int(MAX_PREVIEW_SECONDS * SECONDS_SLIDER_SCALE))
        self.duration_slider.setValue(int(1.5 * SECONDS_SLIDER_SCALE))
        self.duration_label = QLabel("⏱️ Short")
        self.duration_slider.valueChanged.connect(self._sync_duration_slider_to_spin)

        self.pitch_start = QSlider(Qt.Horizontal)
        self.pitch_start.setRange(36 * MIDI_SLIDER_SCALE, 84 * MIDI_SLIDER_SCALE)
        self.pitch_start.setValue(69 * MIDI_SLIDER_SCALE)
        self.pitch_start_label = QLabel("🎵 Middle")

        self.pitch_end = QSlider(Qt.Horizontal)
        self.pitch_end.setRange(36 * MIDI_SLIDER_SCALE, 84 * MIDI_SLIDER_SCALE)
        self.pitch_end.setValue(69 * MIDI_SLIDER_SCALE)
        self.pitch_end_label = QLabel("🎵 Middle")

        self.loud_start = QSlider(Qt.Horizontal)
        self.loud_start.setRange(0, 100 * PERCENT_SLIDER_SCALE)
        self.loud_start.setValue(40 * PERCENT_SLIDER_SCALE)
        self.loud_start_label = QLabel("🌿 Medium")

        self.loud_end = QSlider(Qt.Horizontal)
        self.loud_end.setRange(0, 100 * PERCENT_SLIDER_SCALE)
        self.loud_end.setValue(40 * PERCENT_SLIDER_SCALE)
        self.loud_end_label = QLabel("🌿 Medium")

        self.curve_combo = QComboBox()
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

        self.paul_amount_slider = QSlider(Qt.Horizontal)
        self.paul_amount_slider.setRange(1 * PAULSTRETCH_SCALE, 30 * PAULSTRETCH_SCALE)
        self.paul_amount_slider.setValue(1 * PAULSTRETCH_SCALE)

        self.paul_evolution_slider = QSlider(Qt.Horizontal)
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
        self.auto_pan_rate = QSlider(Qt.Horizontal)
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
            button.setMaximumHeight(54)
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

    def _toy_group(self, title: str) -> QGroupBox:
        box = QGroupBox(title)
        box.setObjectName("toyGroup")
        box.setMinimumHeight(90)
        return box

    def _make_percent_slider(self, minimum: int, maximum: int, value: int) -> QSlider:
        slider = QSlider(Qt.Horizontal)
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
            """
        self.setStyleSheet(base_style + self._slider_style_sheet())

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
        self.base_pitch_label.setText(f"Pitch: {self._pitch_picture_text(midi_value)} • {tuning_name} • {base_frequency:.1f} Hz")

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

        self.canvas.set_data(audio, freq_env, loud_env, msg, self._visual_conditions_from_ui())
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
        if not self.live_loop_enabled:
            self._start_preview_motion_for_current_duration()

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
        self._restart_live_loop(regenerate=True)

    def _disable_live_loop(self) -> None:
        self.live_loop_enabled = False
        self.live_loop_timer.stop()
        self.live_loop_is_refreshing = False
        self._preview_stop_timer.stop()
        self._set_preview_motion(False)
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
        self.octave_slider.setValue(int(loaded_octave * OCTAVE_SLIDER_SCALE))
        loaded_cents = float(ui.get("cents", settings.get("cents", 0.0)))
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

        self._set_wave_levels(start_levels, end_levels, times)
        self._set_wave_stereo(wave_pan, wave_width, wave_dance)
        for wave_type in WAVE_ORDER:
            button = self.wave_mute_buttons.get(wave_type)
            if button is not None:
                button.blockSignals(True)
                button.setChecked(bool(wave_muted.get(wave_type, False)))
                button.setText("🤫 Quiet" if button.isChecked() else "🎵 On")
                button.blockSignals(False)
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

    def _preset_pure_a4(self) -> None:
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
