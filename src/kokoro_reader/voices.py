"""Voices supplied by the official Kokoro-82M model."""

from __future__ import annotations

VOICES: tuple[tuple[str, str], ...] = (
    ("Heart — American female", "af_heart"),
    ("Bella — American female", "af_bella"),
    ("Nicole — American female", "af_nicole"),
    ("Sarah — American female", "af_sarah"),
    ("Sky — American female", "af_sky"),
    ("Aoede — American female", "af_aoede"),
    ("Jessica — American female", "af_jessica"),
    ("Kore — American female", "af_kore"),
    ("Nova — American female", "af_nova"),
    ("River — American female", "af_river"),
    ("Adam — American male", "am_adam"),
    ("Michael — American male", "am_michael"),
    ("Echo — American male", "am_echo"),
    ("Eric — American male", "am_eric"),
    ("Fenrir — American male", "am_fenrir"),
    ("Liam — American male", "am_liam"),
    ("Onyx — American male", "am_onyx"),
    ("Puck — American male", "am_puck"),
    ("Alice — British female", "bf_alice"),
    ("Emma — British female", "bf_emma"),
    ("Isabella — British female", "bf_isabella"),
    ("Lily — British female", "bf_lily"),
    ("Daniel — British male", "bm_daniel"),
    ("Fable — British male", "bm_fable"),
    ("George — British male", "bm_george"),
    ("Lewis — British male", "bm_lewis"),
)


def language_for_voice(voice: str) -> str:
    """Map a Kokoro English voice prefix to its pipeline language."""
    if voice.startswith("a"):
        return "a"
    if voice.startswith("b"):
        return "b"
    raise ValueError(f"Unsupported voice: {voice}")

