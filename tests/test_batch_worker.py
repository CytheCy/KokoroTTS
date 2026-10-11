from kokoro_reader.worker import BatchSpeechWorker


class FakeEngine:
    def __init__(self):
        self.calls = []

    def synthesize(self, text, voice, destination, on_progress, is_cancelled):
        self.calls.append((text, voice, destination))
        destination.write_bytes(b"fake wav")


def test_batch_removes_headings_and_uses_folder_and_markdown_names(tmp_path):
    folder = tmp_path / "MTTRC"
    folder.mkdir()
    first = folder / "01-first-day.md"
    second = folder / "Forward.MD"
    first.write_text("# Opening\n\nThe first day.\n## Next\nMore text.")
    second.write_text("# Forward\n\nAn introduction.")
    (folder / "notes.txt").write_text("Ignore me")
    output = tmp_path / "audio"
    output.mkdir()
    (output / "MTTRC - 01-first-day.wav").write_bytes(b"existing")
    engine = FakeEngine()
    worker = BatchSpeechWorker([first, second], "af_bella", output, engine)
    completed = []
    worker.completed.connect(lambda *args: completed.append(args))

    worker.run()

    assert completed == [(2, 2, [])]
    assert engine.calls == [
        ("\nThe first day.\nMore text.", "af_bella", output / "MTTRC - 01-first-day-2.wav"),
        ("\nAn introduction.", "af_bella", output / "MTTRC - Forward.wav"),
    ]
    assert (output / "MTTRC - 01-first-day.wav").read_bytes() == b"existing"
    assert first.read_text().startswith("# Opening")


def test_batch_continues_after_unreadable_file(tmp_path):
    folder = tmp_path / "book"
    folder.mkdir()
    bad = folder / "bad.md"
    bad.write_bytes(b"\xff")
    good = folder / "good.md"
    good.write_text("# Heading\nReadable prose.")
    output = tmp_path / "audio"
    output.mkdir()
    engine = FakeEngine()
    worker = BatchSpeechWorker([bad, good], "af_bella", output, engine)
    completed = []
    worker.completed.connect(lambda *args: completed.append(args))

    worker.run()

    assert completed[0][:2] == (1, 2)
    assert completed[0][2][0].startswith("bad.md:")
    assert engine.calls[0][0] == "Readable prose."
    assert (output / "book - good.wav").exists()


def test_batch_cancellation_keeps_prior_results(tmp_path):
    folder = tmp_path / "book"
    folder.mkdir()
    files = [folder / "1.md", folder / "2.md"]
    for file in files:
        file.write_text("Prose.")
    output = tmp_path / "audio"
    output.mkdir()
    engine = FakeEngine()
    worker = BatchSpeechWorker(files, "af_bella", output, engine)
    cancelled = []
    worker.cancelled.connect(lambda *args: cancelled.append(args))
    worker.progress.connect(lambda current, total: worker.cancel() if current == 1 else None)

    worker.run()

    assert cancelled == [(1, 2)]
    assert len(engine.calls) == 1
    assert (output / "book - 1.wav").exists()
    assert not (output / "book - 2.wav").exists()
