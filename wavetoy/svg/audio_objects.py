"""Lightweight SVG-style audio object metadata.

These dataclasses are intentionally JSON-friendly and independent of PySide so
future desktop, web, and iPad-oriented frontends can share the same project
model. They do not render audio yet; WaveToy still renders sample arrays in
``wave_toy.py`` while these objects describe how generated sounds could become
editable vector signals.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class EditableHandle:
    """A named vector handle for future SVG manipulation."""

    handle_id: str
    role: str
    x: float
    y: float
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_json_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class WaveExpression:
    """Mathematical expression metadata behind a rendered sound."""

    expression_id: str
    label: str
    expression_text: str
    parameters: dict[str, Any] = field(default_factory=dict)
    renderer_hint: str = "numpy_samples"
    sample_rate: int = 44_100
    duration_seconds: float = 0.0

    def to_json_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SvgAudioObject:
    """JSON-safe visual object descriptor for SVG-like audio editors."""

    visual_object_id: str
    expression_source_id: str
    geometry: dict[str, Any] = field(default_factory=dict)
    editable_handles: list[EditableHandle] = field(default_factory=list)
    render_metadata: dict[str, Any] = field(default_factory=dict)

    def to_json_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["editable_handles"] = [handle.to_json_dict() for handle in self.editable_handles]
        return data


def svg_metadata_for_clip(clip_id: int, label: str, duration_seconds: float) -> dict[str, Any]:
    """Return a minimal future-SVG visual descriptor for a timeline clip."""

    expression_id = f"clip-expression-{clip_id}"
    expression = WaveExpression(
        expression_id=expression_id,
        label=label,
        expression_text="sample_array(source) with optional trim/stretch envelope",
        parameters={"clip_id": clip_id},
        renderer_hint="timeline_clip_samples",
        duration_seconds=float(duration_seconds),
    )
    visual = SvgAudioObject(
        visual_object_id=f"timeline-clip-{clip_id}",
        expression_source_id=expression_id,
        geometry={"kind": "timeline_clip", "duration_seconds": float(duration_seconds)},
        editable_handles=[
            EditableHandle("trim-start", "trim", 0.0, 0.5),
            EditableHandle("trim-end", "trim", 1.0, 0.5),
            EditableHandle("gain-envelope", "envelope", 0.5, 0.25),
        ],
        render_metadata={"stroke_role": "waveform_energy", "container": "glass_tube"},
    )
    return {"expression": expression.to_json_dict(), "visual_object": visual.to_json_dict()}
