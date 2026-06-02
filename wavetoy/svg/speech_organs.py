"""SVG builders for speech-organ visualization foundations."""

from __future__ import annotations

from html import escape

from wavetoy.speech_organs import ResonanceTractState, SpeechOrganState


def _fmt(value: float) -> str:
    return f"{float(value):.3f}".rstrip("0").rstrip(".")


def _particles(color: str, amount: float, x1: float, y1: float, x2: float, y2: float, prefix: str) -> str:
    count = max(0, min(5, int(round(float(amount) * 5))))
    if count <= 0:
        return ""
    parts: list[str] = []
    for index in range(count):
        t = (index + 1) / (count + 1)
        x = x1 + (x2 - x1) * t
        y = y1 + (y2 - y1) * t + ((index % 2) - 0.5) * 9
        parts.append(f'<circle id="{prefix}-{index}" cx="{_fmt(x)}" cy="{_fmt(y)}" r="{_fmt(2.8 + amount * 3.5)}" fill="{color}" opacity="0.72"/>')
    return "".join(parts)


def anatomical_mouth_svg(state: SpeechOrganState, *, overlay: bool = True, label: str = "Anatomical Mouth") -> str:
    """Return a resolution-independent frontal anatomical mouth SVG."""

    state = state.clamped()
    mouth_w = 88 + (1.0 - state.lip_rounding) * 64 + state.lip_spread * 24
    mouth_h = 18 + state.lip_open * 106 + state.jaw_open * 26
    cx, cy = 200.0, 139.0
    top_y = cy - mouth_h / 2.0
    bottom_y = cy + mouth_h / 2.0
    tongue_x = cx - 54 + state.tongue_frontness * 108
    tongue_y = bottom_y - 16 - state.tongue_body_height * max(22, mouth_h * 0.55)
    upper_teeth_y = top_y + 12 + state.closure_strength * 22
    lower_teeth_y = bottom_y - 14 - state.closure_strength * 20
    airflow = _particles("#2d9cdb", state.airflow * (1.0 - state.closure_strength), cx + mouth_w * 0.22, cy, 340, cy - 10, "oral-air") if overlay else ""
    nasal = _particles("#2ecc71", state.nasal_airflow, cx, 66, 325, 49, "nasal-air") if overlay else ""
    burst = _particles("#f39c12", state.burst_strength, cx + mouth_w * 0.18, cy + 8, 332, cy + 28, "burst") if overlay else ""
    fric = _particles("#8e44ad", state.airflow * (1.0 - state.lip_open) * (1.0 - state.closure_strength), cx + 18, cy - 12, 318, cy - 30, "frication") if overlay else ""
    voice = _particles("#e74c3c", state.voiced_gain, 72, 222, 122, 195, "voicing") if overlay else ""
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 280" role="img" aria-label="{escape(label)}">
  <rect width="400" height="280" rx="26" fill="#fff7e6"/>
  <ellipse id="oral_cavity" cx="200" cy="143" rx="{_fmt(mouth_w / 2 + 18)}" ry="{_fmt(mouth_h / 2 + 16)}" fill="#2b0f1a" stroke="#8c2f39" stroke-width="7"/>
  <path id="upper_lip" d="M {_fmt(cx - mouth_w / 2 - 18)} {_fmt(top_y + 5)} C {_fmt(cx - mouth_w * .30)} {_fmt(top_y - 22 - state.lip_rounding * 14)} {_fmt(cx + mouth_w * .30)} {_fmt(top_y - 22 - state.lip_rounding * 14)} {_fmt(cx + mouth_w / 2 + 18)} {_fmt(top_y + 5)}" fill="none" stroke="#d1495b" stroke-width="{_fmt(7 + state.lip_rounding * 8)}" stroke-linecap="round"/>
  <path id="lower_lip" d="M {_fmt(cx - mouth_w / 2 - 16)} {_fmt(bottom_y - 2)} C {_fmt(cx - mouth_w * .22)} {_fmt(bottom_y + 31 + state.jaw_open * 10)} {_fmt(cx + mouth_w * .22)} {_fmt(bottom_y + 31 + state.jaw_open * 10)} {_fmt(cx + mouth_w / 2 + 16)} {_fmt(bottom_y - 2)}" fill="none" stroke="#e85d75" stroke-width="{_fmt(8 + state.lip_rounding * 7)}" stroke-linecap="round"/>
  <path id="palate" d="M 124 95 C 164 67 248 67 288 99" fill="none" stroke="#ffd6a5" stroke-width="11" stroke-linecap="round"/>
  <path id="upper_teeth" d="M 144 {_fmt(upper_teeth_y)} L 258 {_fmt(upper_teeth_y)}" stroke="#ffffff" stroke-width="13" stroke-linecap="round"/>
  <path id="lower_teeth" d="M 150 {_fmt(lower_teeth_y)} L 252 {_fmt(lower_teeth_y)}" stroke="#f8f9fa" stroke-width="11" stroke-linecap="round"/>
  <path id="tongue" d="M 132 {_fmt(bottom_y - 12)} C {_fmt(tongue_x - 70)} {_fmt(tongue_y + 48)} {_fmt(tongue_x - 18)} {_fmt(tongue_y - 28)} {_fmt(tongue_x + 64)} {_fmt(tongue_y)} C {_fmt(tongue_x + 52)} {_fmt(tongue_y + 48)} 260 {_fmt(bottom_y - 10)} 132 {_fmt(bottom_y - 12)}" fill="#ff8fa3" stroke="#b23a48" stroke-width="4"/>
  {airflow}{nasal}{burst}{fric}{voice}
  <text x="18" y="26" fill="#1d3557" font-size="15" font-weight="700">{escape(label)}</text>
</svg>'''


def vocal_tract_side_svg(state: SpeechOrganState, *, resonance: ResonanceTractState | None = None, overlay: bool = True, label: str = "Vocal Tract Cutaway") -> str:
    """Return a side-cutaway SVG for lips, tongue, velum, nasal cavity, pharynx, larynx, and resonance."""

    state = state.clamped()
    resonance = (resonance or ResonanceTractState.neutral()).clamped()
    jaw_y = 172 + state.jaw_open * 42
    lip_x = 318 + state.lip_rounding * 14
    tongue_peak_x = 190 + state.tongue_frontness * 72
    tongue_peak_y = 214 - state.tongue_body_height * 72
    velum_y = 103 + state.velum_open * 34
    oral = _particles("#2d9cdb", state.airflow * (1.0 - state.closure_strength), 202, 167, lip_x + 48, 154, "side-oral") if overlay else ""
    nasal = _particles("#2ecc71", state.nasal_airflow, 193, 82, 310, 58, "side-nasal") if overlay else ""
    voice = _particles("#e74c3c", state.voiced_gain, 112, 242, 132, 202, "side-voice") if overlay else ""
    glottis_gap = 4 + state.glottal_open * 18
    vibration_opacity = 0.18 + state.voiced_gain * 0.62
    oral_opacity = 0.10 + resonance.resonance_depth * 0.18
    pharynx_opacity = 0.10 + resonance.chest_resonance * 0.16
    nasal_opacity = 0.08 + resonance.nasal_coupling * 0.26
    head_opacity = 0.08 + resonance.head_resonance * 0.18
    f1_y = 210 - resonance.formant_shift_f1 * 18 - (resonance.darkness - 0.5) * 18
    f2_y = 176 - resonance.formant_shift_f2 * 15 - (resonance.brightness - 0.5) * 16
    f3_y = 145 - resonance.formant_shift_f3 * 12 - (resonance.head_resonance - 0.5) * 15
    resonance_overlay = f'''
  <ellipse id="oral_resonance_chamber" cx="235" cy="151" rx="{_fmt(54 + resonance.oral_cavity_width * 20)}" ry="{_fmt(18 + resonance.oral_cavity_height * 18)}" fill="#f9c74f" opacity="{_fmt(oral_opacity)}"/>
  <ellipse id="pharyngeal_resonance_chamber" cx="128" cy="164" rx="{_fmt(20 + resonance.pharyngeal_volume * 18)}" ry="{_fmt(56 + resonance.resonance_depth * 20)}" fill="#9b5de5" opacity="{_fmt(pharynx_opacity)}"/>
  <path id="nasal_coupling_path" d="M 178 103 C 215 92 255 82 311 64" fill="none" stroke="#2ecc71" stroke-width="{_fmt(2 + resonance.nasal_coupling * 7)}" opacity="{_fmt(nasal_opacity)}" stroke-linecap="round"/>
  <circle id="head_resonance_indicator" cx="276" cy="47" r="{_fmt(9 + resonance.head_resonance * 13)}" fill="#00bbf9" opacity="{_fmt(head_opacity)}"/>
  <circle id="chest_resonance_indicator" cx="103" cy="286" r="{_fmt(8 + resonance.chest_resonance * 12)}" fill="#6d4c41" opacity="{_fmt(pharynx_opacity)}"/>
  <path id="formant_band_f1" d="M 140 {_fmt(f1_y)} C 190 {_fmt(f1_y - 12)} 250 {_fmt(f1_y - 10)} 325 {_fmt(f1_y - 2)}" fill="none" stroke="#ff6b6b" stroke-width="2" opacity="0.36"/>
  <path id="formant_band_f2" d="M 150 {_fmt(f2_y)} C 205 {_fmt(f2_y - 11)} 263 {_fmt(f2_y - 7)} 334 {_fmt(f2_y)}" fill="none" stroke="#4d96ff" stroke-width="2" opacity="0.32"/>
  <path id="formant_band_f3" d="M 162 {_fmt(f3_y)} C 215 {_fmt(f3_y - 9)} 276 {_fmt(f3_y - 6)} 340 {_fmt(f3_y + 2)}" fill="none" stroke="#f15bb5" stroke-width="2" opacity="0.28"/>
  <text x="333" y="{_fmt(f1_y + 4)}" fill="#9d0208" font-size="9">F1</text>
  <text x="344" y="{_fmt(f2_y + 4)}" fill="#1d4ed8" font-size="9">F2</text>
  <text x="350" y="{_fmt(f3_y + 4)}" fill="#9d4edd" font-size="9">F3</text>'''
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 420 300" role="img" aria-label="{escape(label)}">
  <rect width="420" height="300" rx="24" fill="#f7fbff"/>
  <path id="pharynx" d="M 128 78 C 108 120 111 204 132 252" fill="none" stroke="#8d6e63" stroke-width="18" stroke-linecap="round"/>
  {resonance_overlay}
  <path id="nasal_cavity" d="M 154 71 C 211 34 282 42 331 70 C 279 83 219 92 154 91 Z" fill="#d7f9e8" stroke="#2ecc71" stroke-width="4"/>
  <path id="palate" d="M 141 113 C 198 81 270 91 318 123" fill="none" stroke="#d29b6f" stroke-width="12" stroke-linecap="round"/>
  <path id="velum" d="M 178 112 C 194 {_fmt(velum_y)} 212 {_fmt(velum_y + 16)} 222 {_fmt(velum_y + 39)}" fill="none" stroke="#c77d5c" stroke-width="9" stroke-linecap="round"/>
  <path id="oral_cavity" d="M 142 126 C 194 107 269 123 {_fmt(lip_x)} 145 C 273 169 202 184 143 171 Z" fill="#301018" opacity="0.82"/>
  <path id="tongue" d="M 126 210 C 162 212 {_fmt(tongue_peak_x - 43)} {_fmt(tongue_peak_y + 28)} {_fmt(tongue_peak_x)} {_fmt(tongue_peak_y)} C {_fmt(tongue_peak_x + 64)} {_fmt(tongue_peak_y + 14)} 261 {_fmt(jaw_y)} 128 {_fmt(jaw_y)} Z" fill="#ff8fa3" stroke="#b23a48" stroke-width="4"/>
  <path id="teeth" d="M 296 130 L 323 140 M 296 168 L 322 159" stroke="#ffffff" stroke-width="9" stroke-linecap="round"/>
  <path id="lips" d="M {_fmt(lip_x)} 136 C {_fmt(lip_x + 23)} 142 {_fmt(lip_x + 23)} 160 {_fmt(lip_x)} 167" fill="none" stroke="#d1495b" stroke-width="{_fmt(8 + state.lip_rounding * 7)}" stroke-linecap="round"/>
  <ellipse id="larynx" cx="119" cy="246" rx="30" ry="25" fill="#ffe0bd" stroke="#e74c3c" stroke-width="{_fmt(2 + state.glottal_closure * 5)}"/>
  <path id="vocal_fold_left" d="M 106 246 C 111 239 116 239 121 {_fmt(246 - glottis_gap / 2)}" stroke="#8c1c13" stroke-width="5" fill="none" stroke-linecap="round"/>
  <path id="vocal_fold_right" d="M 106 252 C 113 257 118 257 121 {_fmt(246 + glottis_gap / 2)}" stroke="#8c1c13" stroke-width="5" fill="none" stroke-linecap="round"/>
  <ellipse id="vocal_fold_vibration" cx="122" cy="249" rx="{_fmt(10 + state.voiced_gain * 13)}" ry="{_fmt(6 + state.voiced_gain * 10)}" fill="none" stroke="#e74c3c" stroke-width="3" opacity="{_fmt(vibration_opacity)}"/>
  <text x="74" y="286" fill="#8c1c13" font-size="10" font-weight="700">voice box / larynx</text>
  {oral}{nasal}{voice}
  <text x="18" y="27" fill="#1d3557" font-size="15" font-weight="700">{escape(label)}</text>
</svg>'''


def voice_source_svg(state: SpeechOrganState, profile: dict[str, object] | None = None) -> str:
    """Return a compact SVG voice-source readout separated from articulation."""

    profile = dict(profile or {})
    tension = float(profile.get("vocal_fold_tension", state.glottal_closure))
    thickness = float(profile.get("vocal_fold_thickness", 0.5))
    breathiness = float(profile.get("breathiness", state.glottal_open))
    rasp = float(profile.get("rasp", 0.0))
    jitter = float(profile.get("jitter", 0.0))
    shimmer = float(profile.get("shimmer", 0.0))
    closure = state.glottal_closure
    bars = [("tension", tension), ("thickness", thickness), ("closure", closure), ("breathiness", breathiness), ("rasp", rasp), ("jitter", jitter), ("shimmer", shimmer)]
    rows = []
    for idx, (name, value) in enumerate(bars):
        y = 38 + idx * 22
        rows.append(f'<text x="18" y="{y + 6}" font-size="11" fill="#1d3557">{name}</text><rect x="94" y="{y}" width="126" height="10" rx="5" fill="#dee2e6"/><rect x="94" y="{y}" width="{_fmt(126 * max(0.0, min(1.0, value)))}" height="10" rx="5" fill="#e74c3c"/>')
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 240 205" role="img" aria-label="Voice Source"><rect width="240" height="205" rx="18" fill="#fff5f5"/><text x="18" y="23" fill="#1d3557" font-size="14" font-weight="700">Voice Source</text>{"".join(rows)}</svg>'
