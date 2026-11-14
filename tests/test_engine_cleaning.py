import numpy as np
import pytest
import soundfile as sf

from kokoro_reader.engine import CancelledError, KokoroEngine, SAMPLE_RATE


class FakePipeline:
    def __init__(self):
        self.received = []

    def __call__(self, text, voice):
        self.received.append((text, voice))
        yield text, "phonemes", np.zeros(240, dtype=np.float32)

    def load_voice(self, voice):
        self.loaded_voice = voice


def test_engine_cleans_text_before_it_reaches_kokoro(tmp_path):
    engine = KokoroEngine()
    pipeline = FakePipeline()
    engine._pipelines["a"] = pipeline
    destination = tmp_path / "clean.wav"

    engine.synthesize(
        "# **Hello** 🚀 [reader](https://example.com)!",
        "af_heart",
        destination,
        lambda _current, _total: None,
        lambda: False,
    )

    assert pipeline.received == [("Hello reader!", "af_heart")]
    assert destination.exists()


def test_engine_streams_each_audio_segment_while_writing_wav(tmp_path):
    engine = KokoroEngine()
    pipeline = FakePipeline()
    engine._pipelines["a"] = pipeline
    events = []

    engine.synthesize(
        "First sentence. " + "word " * 80 + "Second sentence.",
        "af_heart",
        tmp_path / "streamed.wav",
        lambda current, total: events.append(("progress", current, total)),
        lambda: False,
        lambda audio: events.append(("audio", audio)),
    )

    audio_events = [event for event in events if event[0] == "audio"]
    progress_events = [event for event in events if event[0] == "progress"]
    assert len(progress_events) > 1
    assert events.index(audio_events[0]) < events.index(progress_events[-1])
    assert all(isinstance(event[1], bytes) for event in audio_events)
    assert all(len(event[1]) % 2 == 0 for event in audio_events)


def test_engine_preloads_selected_voice():
    engine = KokoroEngine()
    pipeline = FakePipeline()
    engine._pipelines["a"] = pipeline

    engine.preload("af_heart")

    assert pipeline.loaded_voice == "af_heart"


def test_event_year_survives_cleaning_and_reaches_speech_engine(tmp_path):
    from datetime import date
    from kokoro_reader.timeline import Event

    event = Event(tmp_path / "note.md", date(2040, 7, 12), "An event", "AI", "Body.")
    engine = KokoroEngine()
    pipeline = FakePipeline()
    engine._pipelines["a"] = pipeline
    for read_year in (True, False):
        pipeline.received.clear()
        engine.synthesize(
            event.narration(read_year=read_year), "af_heart", tmp_path / "event.wav",
            lambda *_: None, lambda: False,
        )
        spoken = " ".join(text for text, _ in pipeline.received)
        assert ("Year 2040." in spoken) == read_year
        assert "An event." in spoken
        assert "July" not in spoken


@pytest.mark.parametrize("pause_seconds", [0, 0.25, 1.5])
def test_event_pause_is_written_and_streamed_only_between_events(tmp_path, pause_seconds):
    engine = KokoroEngine()

    def pipeline(text, voice):
        yield text, "phonemes", np.full(240, 0.5, dtype=np.float32)

    engine._pipelines["a"] = pipeline
    destination = tmp_path / "events.wav"
    streamed = []
    engine.synthesize(
        "unused combined preview", "af_heart", destination,
        lambda *_: None, lambda: False, streamed.append,
        event_texts=["First event.\n\nIts body.", "Second event.\n\nIts body."],
        event_pause_seconds=pause_seconds,
    )
    samples, rate = sf.read(destination)
    pause_samples = round(pause_seconds * SAMPLE_RATE)
    assert rate == SAMPLE_RATE
    assert len(samples) == 480 + pause_samples
    assert np.all(samples[:240] > 0)
    assert np.all(samples[240:240 + pause_samples] == 0)
    assert np.all(samples[240 + pause_samples:] > 0)
    pcm = np.frombuffer(b"".join(streamed), dtype="<i2") / 32768.0
    np.testing.assert_allclose(pcm, samples, atol=1 / 32768.0)


def test_event_pause_does_not_replace_short_gaps_within_an_event(tmp_path):
    engine = KokoroEngine()
    engine._pipelines["a"] = FakePipeline()
    streamed = []
    engine.synthesize(
        "unused", "af_heart", tmp_path / "long-events.wav",
        lambda *_: None, lambda: False, streamed.append,
        event_texts=["First sentence. " + "word " * 80, "Second event."],
        event_pause_seconds=2.5,
    )
    lengths = [len(audio) // 2 for audio in streamed]
    assert lengths.count(round(2.5 * SAMPLE_RATE)) == 1
    assert round(0.16 * SAMPLE_RATE) in lengths
    assert lengths[0] == lengths[-1] == 240


def test_cancellation_during_event_pause_removes_partial_wav(tmp_path):
    engine = KokoroEngine()
    engine._pipelines["a"] = FakePipeline()
    cancelled = False

    def on_audio(audio):
        nonlocal cancelled
        if len(audio) == SAMPLE_RATE * 2:
            cancelled = True

    destination = tmp_path / "cancelled.wav"
    with pytest.raises(CancelledError):
        engine.synthesize(
            "unused", "af_heart", destination,
            lambda *_: None, lambda: cancelled, on_audio,
            event_texts=["First event.", "Second event."], event_pause_seconds=1,
        )
    assert not destination.exists()
    assert not list(tmp_path.glob("*.wav"))
