import pytest

from kokoro_reader.voices import language_for_voice


def test_voice_language_mapping():
    assert language_for_voice("af_heart") == "a"
    assert language_for_voice("bm_george") == "b"


def test_unknown_voice_is_rejected():
    with pytest.raises(ValueError):
        language_for_voice("unknown")

