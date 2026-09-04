from kokoro_reader.text_cleaning import clean_for_speech


def test_removes_markdown_but_keeps_readable_text():
    source = "# **A title**\n\n- Read *this* [helpful page](https://example.com)."
    assert clean_for_speech(source) == 'A title\n\nRead this helpful page.'


def test_removes_emoji_symbols_and_invisible_characters_without_joining_words():
    source = "Hello🚀world © 2026. Good\u200bnight 👨\u200d👩\u200d👧!"
    assert clean_for_speech(source) == "Hello world 2026. Good night!"


def test_normalizes_speakable_typographic_punctuation():
    source = "“Café”—she said… It’s ready."
    assert clean_for_speech(source) == '"Café"-she said... It\'s ready.'


def test_removes_html_urls_and_markdown_reference_destinations():
    source = "<b>Open</b> www.example.com or [the guide][docs].\n\n[docs]: https://example.com"
    assert clean_for_speech(source) == "Open or the guide."


def test_keeps_paragraphs_and_common_sentence_punctuation():
    source = "First: yes, it is (ready)!\n\nSecond paragraph?"
    assert clean_for_speech(source) == source

