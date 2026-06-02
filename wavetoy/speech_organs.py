"""Normalized speech-organ state for render-only articulation visualization.

The values in :class:`SpeechOrganState` are intentionally normalized to 0..1
(except ``voice_pitch`` in Hz) so desktop widgets, SVG views, generic animation
JSON, and future rig/export layers can share one anatomical snapshot without
changing WaveToy's saved articulation-chain format.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


def _clamp01(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = default
    return max(0.0, min(1.0, number))


@dataclass(frozen=True)
class SpeechOrganState:
    """Single normalized anatomical state used by renderers and animation."""

    jaw_open: float
    lip_open: float
    lip_rounding: float
    lip_spread: float
    tongue_tip_height: float
    tongue_blade_height: float
    tongue_body_height: float
    tongue_back_height: float
    tongue_frontness: float
    tongue_retraction: float
    velum_open: float
    velum_closed: float
    nasal_airflow: float
    glottal_open: float
    glottal_closure: float
    voiced_gain: float
    airflow: float
    closure_strength: float
    burst_strength: float
    voice_pitch: float

    @classmethod
    def neutral(cls) -> "SpeechOrganState":
        return cls(
            jaw_open=0.35,
            lip_open=0.35,
            lip_rounding=0.10,
            lip_spread=0.55,
            tongue_tip_height=0.50,
            tongue_blade_height=0.50,
            tongue_body_height=0.50,
            tongue_back_height=0.50,
            tongue_frontness=0.50,
            tongue_retraction=0.50,
            velum_open=0.0,
            velum_closed=1.0,
            nasal_airflow=0.0,
            glottal_open=0.35,
            glottal_closure=0.55,
            voiced_gain=0.65,
            airflow=0.45,
            closure_strength=0.0,
            burst_strength=0.0,
            voice_pitch=220.0,
        )

    @classmethod
    def from_articulation(cls, phoneme: Any, *, voiced_gain: float | None = None) -> "SpeechOrganState":
        """Create a render-only anatomical snapshot from an ArticulationPhoneme-like object."""

        mouth_open = _clamp01(getattr(phoneme, "mouth_open", 0.35), 0.35)
        tongue_height = _clamp01(getattr(phoneme, "tongue_height", 0.50), 0.50)
        tongue_frontness = _clamp01(getattr(phoneme, "tongue_frontness", 0.50), 0.50)
        lip_rounding = _clamp01(getattr(phoneme, "lip_rounding", 0.10), 0.10)
        closure = _clamp01(getattr(phoneme, "closure", 0.0), 0.0)
        nasal_open = _clamp01(getattr(phoneme, "nasal_open", 0.0), 0.0)
        air_pressure = _clamp01(getattr(phoneme, "air_pressure", 0.45), 0.45)
        teeth_gap = _clamp01(getattr(phoneme, "teeth_gap", 0.50), 0.50)
        burst = _clamp01(getattr(phoneme, "burst_strength", 0.0), 0.0)
        strength = _clamp01(getattr(phoneme, "voice_strength", 0.65), 0.65)
        is_voiced = bool(getattr(phoneme, "voiced", True))
        voice = _clamp01(strength if voiced_gain is None else voiced_gain, 0.65) if is_voiced else 0.0
        try:
            pitch = float(getattr(phoneme, "voice_pitch", 220.0))
        except (TypeError, ValueError):
            pitch = 220.0
        pitch = max(60.0, min(880.0, pitch))

        lip_open = _clamp01(max(mouth_open * 0.86, teeth_gap * 0.36) * (1.0 - closure * 0.72), 0.35)
        lip_spread = _clamp01((1.0 - lip_rounding) * (0.45 + tongue_frontness * 0.45), 0.55)
        tongue_retraction = _clamp01(1.0 - tongue_frontness, 0.50)
        back_bias = tongue_retraction * 0.35
        return cls(
            jaw_open=_clamp01(mouth_open * (1.0 - closure * 0.18), 0.35),
            lip_open=lip_open,
            lip_rounding=lip_rounding,
            lip_spread=lip_spread,
            tongue_tip_height=_clamp01(tongue_height * (0.62 + tongue_frontness * 0.38), 0.50),
            tongue_blade_height=_clamp01(tongue_height * (0.72 + tongue_frontness * 0.22), 0.50),
            tongue_body_height=tongue_height,
            tongue_back_height=_clamp01(tongue_height * 0.74 + back_bias, 0.50),
            tongue_frontness=tongue_frontness,
            tongue_retraction=tongue_retraction,
            velum_open=nasal_open,
            velum_closed=_clamp01(1.0 - nasal_open, 1.0),
            nasal_airflow=_clamp01(nasal_open * air_pressure, 0.0),
            glottal_open=_clamp01((1.0 - voice) * 0.68 + air_pressure * 0.22, 0.35),
            glottal_closure=voice,
            voiced_gain=voice,
            airflow=air_pressure,
            closure_strength=closure,
            burst_strength=burst,
            voice_pitch=pitch,
        )

    def clamped(self) -> "SpeechOrganState":
        data = self.to_json_dict()
        for key in data:
            if key != "voice_pitch":
                data[key] = _clamp01(data[key])
        data["voice_pitch"] = max(60.0, min(880.0, float(data["voice_pitch"])))
        return SpeechOrganState(**data)

    def to_json_dict(self) -> dict[str, float]:
        return {key: float(value) for key, value in asdict(self).items()}

    def summary_metrics(self) -> dict[str, float]:
        tongue_height = (self.tongue_tip_height + self.tongue_blade_height + self.tongue_body_height + self.tongue_back_height) / 4.0
        return {
            "jaw_open": self.jaw_open,
            "lip_rounding": self.lip_rounding,
            "tongue_frontness": self.tongue_frontness,
            "tongue_height": tongue_height,
            "voiced_gain": self.voiced_gain,
            "airflow": self.airflow,
        }
