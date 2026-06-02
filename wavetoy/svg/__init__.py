"""SVG/audio representation primitives for future vector editing."""

from .audio_objects import EditableHandle, SvgAudioObject, WaveExpression, svg_metadata_for_clip
from .speech_organs import anatomical_mouth_svg, vocal_tract_side_svg, voice_source_svg

__all__ = [
    "EditableHandle",
    "SvgAudioObject",
    "WaveExpression",
    "svg_metadata_for_clip",
    "anatomical_mouth_svg",
    "vocal_tract_side_svg",
    "voice_source_svg",
]
