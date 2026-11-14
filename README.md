# Kokoro Reader

A small, native Qt app for Fedora KDE that turns pasted text into a WAV file with
Kokoro-82M. Text is chunked and synthesized on a background thread, so even long
documents do not freeze the window. Speech generation happens on your computer.

Before chunking, the app automatically removes Markdown formatting, HTML tags,
link destinations, web addresses, emoji, invisible Unicode controls, and symbols
that do not translate usefully to speech. Words, numbers, accented letters,
paragraph breaks, and natural sentence punctuation are retained.

## Install on this Fedora machine

The system default Python 3.14 is too new for Kokoro 0.9.4, so `setup.sh` selects
the already-installed Python 3.12 automatically.

```bash
./setup.sh
./run.sh
```

The setup script creates an isolated `.venv`, installs the app, and adds **Kokoro
Reader** to KDE's application menu. When the app opens, it starts loading the
Kokoro-82M model and selected voice in the background. The first run may download
them from Hugging Face; later runs use the local cache. No pasted text is sent to
a service.

If Fedora dependencies are missing:

```bash
sudo dnf install python3.12 espeak-ng libsndfile
```

## Use

1. Open the **Paste** tab and paste a document into the notepad area.
2. For Markdown text, click **Remove Headings** to delete lines beginning with `#`.
3. Choose an American or British Kokoro voice.
4. Use **Settings…** to choose the permanent audio output folder.
5. Enter a filename and select **Create audio**. Playback starts automatically as
   soon as the first speech segment is ready; the rest continues generating in the
   background while you listen.

When generation and live playback finish, the completed recording remains
available through **Play audio**. The same button pauses and resumes the live
stream while speech is still being generated.

For timeline narration, open the **Event** tab and click **Choose folder…**.
Select your timeline folder (for example,
`/home/cport/Desktop/Obsidian20xx/Timeline`). The reader loads `.md` files directly
inside that folder, using the `date`, `title`, and `category` (or `cat`) YAML
metadata. When `.settings/categories.json` is present, it uses category IDs and
parent relationships to build the category / subcategory selector. Choosing a
parent includes all its descendants; **All categories** includes every event.
Category names containing commas are kept intact.

Choose inclusive **Start year** and **End year** values. The preview shows the
matching events in metadata date order, with filename order breaking date ties.
The default audio filename uses the selected category or subcategory and year
range, such as `AI-2040-2050.wav` (or `All categories-2040-2050.wav`). You can
enter a custom filename; changing filters keeps that custom name.
The **Read Year** checkbox is checked by default; uncheck it to omit years from
the preview and speech. Enabled years use “Year 2040.” so the text cleaner does
not mistake them for numbered-list markers. This preference is remembered.
Set **Pause between events** in seconds (0–60, including fractional seconds).
It defaults to 1 second and is remembered. The pause is inserted between events
in both live playback and the saved WAV; 0 adds no silence between events.
Click **Create audio** to read their years (when enabled), titles, and bodies as one continuous
recording with the same voice, streaming playback, pause, cancel, and WAV output
controls as Paste. Metadata itself is excluded. Notes with only a title are also
included. Invalid or missing dates are skipped, and file issues are available
through **Show file issues…**. The reader can recover the scalar fields from
non-standard YAML exports such as unescaped title quotes or multiline labels.
The chosen folder is remembered; **Reload** refreshes notes after external edits.
Pasted text stays intact when switching tabs, and source notes are never modified.

To convert a folder, choose a voice and click **Batch folder…**, then select the
folder containing `.md` files. The app reads the Markdown files directly in that
folder, removes lines beginning with `#`, and creates one WAV per file in the
configured audio output folder. For example, `MTTRC/01-the-first-day.md` becomes
`MTTRC - 01-the-first-day.wav`. The source Markdown files are left unchanged.
The progress bar tracks files, and **Cancel** stops the batch while keeping WAVs
that already finished.

Output is a mono 24 kHz WAV. Each file is written to a hidden temporary file and
moved into place only after generation succeeds, so cancellation or an error does
not leave a broken WAV behind. If the requested filename already exists, the app
automatically chooses the first available numbered name instead of overwriting it.

## AppImage later

The app already has a standard Python entry point and freedesktop desktop file,
which are the inputs an AppImage build needs. Kokoro brings PyTorch and model
weights, so the eventual AppImage will be large. The Hugging Face model cache is
deliberately not bundled yet; keeping it external avoids redistributing model
artifacts and lets one cache serve both development and packaged builds.

Before publishing, add a project icon, license metadata, and an AppImage build
recipe pinned to the Fedora-compatible Python 3.12 environment. Test the result on
a second Fedora/KDE machine with no development packages installed.

## Tests

```bash
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m pytest
```
