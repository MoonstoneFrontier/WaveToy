"""Normalized speech-organ state for render-only articulation visualization.

The values in :class:`SpeechOrganState` are intentionally normalized to 0..1
(except ``voice_pitch`` in Hz) so desktop widgets, SVG views, generic animation
JSON, and future rig/export layers can share one anatomical snapshot without
changing WaveToy's saved articulation-chain format.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from typing import Any



def _clamp(value: Any, minimum: float, maximum: float, default: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = default
    return max(minimum, min(maximum, number))

def _clamp01(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = default
    return max(0.0, min(1.0, number))


@dataclass(frozen=True)
class VoiceBoxState:
    """Non-destructive larynx/voice-box layer upstream of articulation."""

    vocal_fold_length: float = 0.50
    vocal_fold_thickness: float = 0.50
    vocal_fold_tension: float = 0.50
    vocal_fold_mass: float = 0.50
    vocal_fold_symmetry: float = 0.50
    glottal_closure: float = 0.55
    glottal_leak: float = 0.10
    breathiness: float = 0.18
    rasp: float = 0.05
    jitter: float = 0.02
    shimmer: float = 0.02
    vocal_damage: float = 0.0
    age_looseness: float = 0.20
    larynx_height: float = 0.50
    vocal_tract_length: float = 0.50
    resonance_depth: float = 0.50

    @classmethod
    def neutral(cls) -> "VoiceBoxState":
        return cls()

    @classmethod
    def from_voice_source_profile(cls, profile: Any) -> "VoiceBoxState":
        """Derive neutral voice-box defaults from a VoiceSourceProfile-like object."""

        return cls(
            vocal_fold_length=_clamp01(getattr(profile, "vocal_fold_length", 0.50), 0.50),
            vocal_fold_thickness=_clamp01(getattr(profile, "vocal_fold_thickness", 0.50), 0.50),
            vocal_fold_tension=_clamp01(getattr(profile, "vocal_fold_tension", 0.50), 0.50),
            glottal_closure=_clamp01(getattr(profile, "glottal_closure", 0.55), 0.55),
            breathiness=_clamp01(getattr(profile, "breathiness", 0.18), 0.18),
            rasp=_clamp01(getattr(profile, "rasp", 0.05), 0.05),
            jitter=_clamp01(getattr(profile, "jitter", 0.02), 0.02),
            shimmer=_clamp01(getattr(profile, "shimmer", 0.02), 0.02),
            age_looseness=_clamp01(getattr(profile, "age_looseness", 0.20), 0.20),
            larynx_height=_clamp01(getattr(profile, "larynx_height", 0.50), 0.50),
            vocal_tract_length=_clamp01(getattr(profile, "vocal_tract_length", 0.50), 0.50),
        )

    @classmethod
    def from_json_dict(cls, data: dict[str, Any] | None) -> "VoiceBoxState":
        source = dict(data or {})
        values = {name: _clamp01(source.get(name, getattr(cls(), name)), getattr(cls(), name)) for name in cls.__dataclass_fields__}
        return cls(**values)

    def clamped(self) -> "VoiceBoxState":
        return VoiceBoxState.from_json_dict(self.to_json_dict())

    def to_json_dict(self) -> dict[str, float]:
        return {key: _clamp01(value) for key, value in asdict(self).items()}

    def pitch_bias(self) -> float:
        """Return a small render-copy pitch multiplier bias, centered on neutral."""

        tension = self.vocal_fold_tension - 0.50
        length = self.vocal_fold_length - 0.50
        thickness = self.vocal_fold_thickness - 0.50
        mass = self.vocal_fold_mass - 0.50
        age = self.age_looseness - 0.20
        return tension * 0.22 - length * 0.16 - thickness * 0.10 - mass * 0.10 - age * 0.06

    def formant_bias_metadata(self) -> dict[str, float]:
        """Future-safe metadata for formant/resonance work without changing DSP here."""

        return {
            "larynx_height_bias": self.larynx_height - 0.50,
            "vocal_tract_length_bias": self.vocal_tract_length - 0.50,
            "resonance_depth_bias": self.resonance_depth - 0.50,
        }

    def apply_to_speech_organ_state(self, state: "SpeechOrganState") -> "SpeechOrganState":
        """Map this upstream larynx state onto a render-copy speech-organ snapshot."""

        vb = self.clamped()
        leak_breath = _clamp01(vb.glottal_leak * 0.55 + vb.breathiness * 0.45, 0.0)
        pitch = max(60.0, min(880.0, state.voice_pitch * (1.0 + vb.pitch_bias())))
        airflow = _clamp01(state.airflow + leak_breath * 0.18, state.airflow)
        open_bias = leak_breath * 0.45 + (1.0 - vb.glottal_closure) * 0.18
        closure = _clamp01(state.glottal_closure * 0.45 + vb.glottal_closure * 0.55 - vb.glottal_leak * 0.18, state.glottal_closure)
        return replace(
            state,
            glottal_closure=closure,
            glottal_open=_clamp01(state.glottal_open * 0.55 + open_bias, state.glottal_open),
            airflow=airflow,
            voice_pitch=pitch,
        ).clamped()


@dataclass(frozen=True)
class ResonanceTractState:
    """Render-only resonance layer between voice box and final articulation.

    Most fields are normalized 0..1 around the neutral value 0.50. Formant
    shift fields are -1..1 offsets and ``formant_scale`` is a conservative
    0.5..1.5 multiplier. The state is deliberately separate from phoneme data
    so presets and diagnostics can color the voice without mutating saved
    articulation chains.
    """

    oral_cavity_length: float = 0.50
    oral_cavity_width: float = 0.50
    oral_cavity_height: float = 0.50
    pharyngeal_volume: float = 0.50
    pharyngeal_tension: float = 0.50
    nasal_coupling: float = 0.0
    chest_resonance: float = 0.50
    head_resonance: float = 0.50
    larynx_height: float = 0.50
    vocal_tract_length: float = 0.50
    resonance_depth: float = 0.50
    brightness: float = 0.50
    darkness: float = 0.50
    formant_scale: float = 1.0
    formant_shift_f1: float = 0.0
    formant_shift_f2: float = 0.0
    formant_shift_f3: float = 0.0

    @classmethod
    def neutral(cls) -> "ResonanceTractState":
        return cls()

    @classmethod
    def from_voice_box_and_speech_organs(cls, voice_box: Any, speech_state: Any | None = None) -> "ResonanceTractState":
        """Derive a safe default from upstream voice-box plus current organs."""

        speech_state = speech_state or SpeechOrganState.neutral()
        vb = voice_box if voice_box is not None else VoiceBoxState.neutral()
        mouth_open = _clamp01(getattr(speech_state, "jaw_open", 0.35), 0.35)
        lip_rounding = _clamp01(getattr(speech_state, "lip_rounding", 0.10), 0.10)
        tongue_frontness = _clamp01(getattr(speech_state, "tongue_frontness", 0.50), 0.50)
        tongue_body = _clamp01(getattr(speech_state, "tongue_body_height", 0.50), 0.50)
        velum = _clamp01(getattr(speech_state, "velum_open", 0.0), 0.0)
        return cls(
            oral_cavity_length=_clamp01(0.40 + (1.0 - lip_rounding) * 0.22 + (1.0 - tongue_frontness) * 0.12, 0.50),
            oral_cavity_width=_clamp01(0.34 + mouth_open * 0.38 + (1.0 - lip_rounding) * 0.12, 0.50),
            oral_cavity_height=_clamp01(0.32 + mouth_open * 0.48 + (1.0 - tongue_body) * 0.10, 0.50),
            pharyngeal_volume=_clamp01(0.42 + _clamp01(getattr(vb, "resonance_depth", 0.50), 0.50) * 0.18 + _clamp01(getattr(vb, "age_looseness", 0.20), 0.20) * 0.08, 0.50),
            pharyngeal_tension=_clamp01(0.42 + _clamp01(getattr(vb, "vocal_fold_tension", 0.50), 0.50) * 0.20 - _clamp01(getattr(vb, "age_looseness", 0.20), 0.20) * 0.08, 0.50),
            nasal_coupling=_clamp01(velum * 0.80 + _clamp01(getattr(speech_state, "nasal_airflow", 0.0), 0.0) * 0.20, 0.0),
            chest_resonance=_clamp01(0.42 + _clamp01(getattr(vb, "resonance_depth", 0.50), 0.50) * 0.20 + _clamp01(getattr(vb, "vocal_fold_thickness", 0.50), 0.50) * 0.08, 0.50),
            head_resonance=_clamp01(0.40 + _clamp01(getattr(vb, "larynx_height", 0.50), 0.50) * 0.18 + tongue_frontness * 0.12, 0.50),
            larynx_height=_clamp01(getattr(vb, "larynx_height", 0.50), 0.50),
            vocal_tract_length=_clamp01(getattr(vb, "vocal_tract_length", 0.50), 0.50),
            resonance_depth=_clamp01(getattr(vb, "resonance_depth", 0.50), 0.50),
        ).clamped()

    @classmethod
    def from_json_dict(cls, data: dict[str, Any] | None) -> "ResonanceTractState":
        source = dict(data or {})
        values: dict[str, float] = {}
        defaults = cls()
        for name in cls.__dataclass_fields__:
            default = getattr(defaults, name)
            if name.startswith("formant_shift_"):
                values[name] = _clamp(source.get(name, default), -1.0, 1.0, default)
            elif name == "formant_scale":
                values[name] = _clamp(source.get(name, default), 0.5, 1.5, default)
            else:
                values[name] = _clamp01(source.get(name, default), default)
        return cls(**values)

    def clamped(self) -> "ResonanceTractState":
        return ResonanceTractState.from_json_dict(self.to_json_dict())

    def to_json_dict(self) -> dict[str, float]:
        data = asdict(self)
        return ResonanceTractState.from_json_dict(data).__dict__.copy()

    def bias_metadata(self) -> dict[str, float]:
        return {
            "resonance_formant_scale": self.formant_scale,
            "resonance_brightness": self.brightness,
            "resonance_darkness": self.darkness,
            "nasal_coupling": self.nasal_coupling,
            "chest_resonance": self.chest_resonance,
            "head_resonance": self.head_resonance,
        }


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
