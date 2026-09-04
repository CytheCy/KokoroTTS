import numpy as np

from kokoro_reader.engine import KokoroEngine


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
