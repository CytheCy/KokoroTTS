from kokoro_reader.output_naming import available_path


def test_uses_requested_name_when_it_is_available(tmp_path):
    requested = tmp_path / "narration.wav"

    assert available_path(requested) == requested


def test_uses_first_available_numbered_name(tmp_path):
    (tmp_path / "narration.wav").touch()
    (tmp_path / "narration-2.wav").touch()

    assert available_path(tmp_path / "narration.wav") == tmp_path / "narration-3.wav"


def test_preserves_extension_case(tmp_path):
    (tmp_path / "recording.WAV").touch()

    assert available_path(tmp_path / "recording.WAV") == tmp_path / "recording-2.WAV"
