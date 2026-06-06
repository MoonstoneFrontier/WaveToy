import sys

try:
    import wave_toy
except ImportError:
    sys.modules.pop("wave_toy", None)
    from tests.test_performance_timeline_undo import _install_qt_stubs

    _install_qt_stubs()
    import wave_toy


def _source() -> str:
    return wave_toy.Path(wave_toy.__file__).read_text(encoding="utf-8")


def _speech_builder_source() -> str:
    source = _source()
    start = source.index('def _build_articulation_timeline_tab')
    end = source.index('def _make_articulation_chain_summary_card')
    return source[start:end]


def test_speech_builder_transport_labels_identify_playback_target():
    source = _speech_builder_source()

    assert '▶ Preview Voice' in _source()
    assert '▶ Play Selected Phoneme' in _source()
    assert '▶ Preview Chain' in _source()
    assert '▶ Preview Word' in source
    assert 'Create Word' in _source()


def test_speech_builder_avoids_unclear_transport_labels():
    source = _speech_builder_source()

    assert '("▶ Play",' not in source
    assert '"▶ Preview"' not in source
    assert '"Render"' not in source


def test_create_word_label_does_not_imply_playback():
    source = _speech_builder_source()

    assert 'make_primary_action_button("Create Word", self._create_articulation_word' in source
    assert 'Create a named Speech Asset from the current chain' in source
