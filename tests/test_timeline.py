from datetime import date
import json

from kokoro_reader.timeline import load_timeline


def note(folder, filename, day, category, body="Event text.", extra=""):
    path = folder / filename
    path.write_text(
        f"---\ntitle: {path.stem}\ndate: {day}\ncategory: {category}\n{extra}---\n\n{body}",
        encoding="utf-8",
    )
    return path


def test_dates_hierarchy_ids_and_inclusive_years(tmp_path):
    settings = tmp_path / ".settings"
    settings.mkdir()
    (settings / "categories.json").write_text(json.dumps([
        {"id": "c", "name": "Computer", "parent_id": None},
        {"id": "a", "name": "AI", "parent_id": "c"},
        {"id": "b", "name": "Brain", "parent_id": "a"},
    ]))
    note(tmp_path, "a-late.md", "2050-12-31", "Old name", extra="category_id: b\n")
    note(tmp_path, "z-early.md", '"2040-01-01"', "AI")
    note(tmp_path, "middle.md", "2045-01-01", "Computer")
    note(tmp_path, "unrelated.md", "2045-01-01", "Longevity, Health")
    timeline = load_timeline(tmp_path)
    assert not timeline.warnings
    assert timeline.category_path("Brain") == "Computer / AI / Brain"
    assert [e.path.name for e in timeline.select("Computer", 2040, 2050)] == [
        "z-early.md", "middle.md", "a-late.md"
    ]
    assert [e.date for e in timeline.select("AI", 2050, 2050)] == [date(2050, 12, 31)]
    assert "Longevity, Health" in timeline.parents
    assert "category_id" not in timeline.events[0].narration()


def test_invalid_notes_recovery_and_title_only_events(tmp_path):
    note(tmp_path, "invalid.md", "not-a-date", "AI")
    note(tmp_path, "empty.md", "2040-01-01", "AI", body="")
    path = note(tmp_path, "quoted.md", "2039-01-01", "AI")
    path.write_text(path.read_text().replace("title: quoted", 'title: "Turn" Replacing YouTube')
                    .replace("category: AI", "category: AI\nlabels: Test\nUnindented label"))
    (tmp_path / "no-meta.md").write_text("Text without metadata")
    (tmp_path / "ignored.txt").write_text("Ignore")
    timeline = load_timeline(tmp_path)
    assert len(timeline.events) == 2
    assert timeline.events[0].title == '"Turn" Replacing YouTube'
    assert len(timeline.warnings) == 3
    assert timeline.select(None, 2050, 2040) == []


def test_bad_hierarchy_and_cycles_do_not_break_notes(tmp_path):
    settings = tmp_path / ".settings"
    settings.mkdir()
    (settings / "categories.json").write_text('{}')
    note(tmp_path, "one.md", "2040-01-01", "AI")
    timeline = load_timeline(tmp_path)
    assert len(timeline.events) == 1
    assert len(timeline.warnings) == 1
    timeline.parents = {"AI": "Computer", "Computer": "AI"}
    assert not timeline.includes("AI", "Other")
    assert timeline.category_path("AI") == "Computer / AI"
