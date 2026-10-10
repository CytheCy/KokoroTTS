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

1. Paste a document into the notepad area.
2. For Markdown text, click **Remove Headings** to delete lines beginning with `#`.
3. Choose an American or British Kokoro voice.
4. Use **Settings…** to choose the permanent audio output folder.
5. Enter a filename and select **Create audio**. Playback starts automatically as
   soon as the first speech segment is ready; the rest continues generating in the
   background while you listen.

When generation and live playback finish, the completed recording remains
available through **Play audio**. The same button pauses and resumes the live
stream while speech is still being generated.

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
