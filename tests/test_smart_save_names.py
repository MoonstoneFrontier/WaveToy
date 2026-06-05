import sys

try:
    import wave_toy
except ImportError:
    sys.modules.pop("wave_toy", None)
    from tests.test_performance_timeline_undo import _install_qt_stubs

    _install_qt_stubs()
    import wave_toy


def test_suggested_speech_asset_name_includes_source_and_phonemes():
    name = wave_toy.suggested_speech_asset_name({"source_name": "Charles_up", "phonemes": ["AH", "M", "OO"]})

    assert name == "Charles_up_AH_M_OO"


def test_suggested_speech_asset_name_uses_currentwave_for_current_source():
    name = wave_toy.suggested_speech_asset_name({
        "source_mode": wave_toy.ARTICULATION_SOURCE_CURRENT,
        "phonemes": ["AH", "S", "T", "ER"],
    })

    assert name == "currentwave_AH_S_T_ER"


def test_suggested_speech_asset_name_is_filesystem_safe_and_optional_render_mode():
    name = wave_toy.suggested_speech_asset_name({
        "source_name": "Charles flat!",
        "phonemes": ["EH", "IH", "ER"],
        "render_mode": "Clip Crossfade",
        "include_render_mode": True,
    })

    assert name == "Charles_flat_EH_IH_ER_Clip_Crossfade"
    assert " " not in name
    assert "!" not in name


def test_save_name_helper_is_referenced_by_speech_save_workflows():
    source = wave_toy.Path(wave_toy.__file__).read_text(encoding="utf-8")

    assert "def suggested_speech_asset_name" in source
    assert "default_name = self._suggested_chain_asset_name()" in source
    assert "safe_name = self._suggested_chain_asset_name(include_render_mode=True)" in source
    assert "chain_name = self._suggested_chain_asset_name()" in source
    assert "Friendly phoneme name" in source and "suggested_speech_asset_name" in source
    assert "waveform_analysis_asset_name(analysis_name)" in source
    assert "formant_analysis_asset_name(analysis_name)" in source
