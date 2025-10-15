from __future__ import annotations

import base64
import os
import sys
import wave
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError


def write_wave_file(filename: Path, pcm: bytes, channels: int, rate: int, sample_width: int) -> None:
    with wave.open(str(filename), "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(rate)
        wf.writeframes(pcm)


class Command(BaseCommand):
    help = "Synthesize speech from text using the Google Gemini TTS model."

    def add_arguments(self, parser):
        parser.add_argument(
            "--text",
            help="Plain text to synthesize. Can be combined with --text-file or piped stdin.",
        )
        parser.add_argument(
            "--text-file",
            type=Path,
            help="Path to a UTF-8 text file whose contents will be synthesized.",
        )
        parser.add_argument(
            "--output",
            type=Path,
            required=True,
            help="Destination WAV file path (created if missing).",
        )
        parser.add_argument(
            "--overwrite",
            action="store_true",
            help="Overwrite the output file if it already exists.",
        )
        parser.add_argument(
            "--model",
            default=os.getenv("GOOGLE_TTS_MODEL", "gemini-2.5-flash-preview-tts"),
            help="Gemini model name to use for synthesis (default: %(default)s).",
        )
        parser.add_argument(
            "--voice",
            default=os.getenv("GOOGLE_TTS_VOICE", "Zephyr"),
            help="Prebuilt voice to use, e.g. 'Kore'.",
        )
        parser.add_argument(
            "--channels",
            type=int,
            default=int(os.getenv("GOOGLE_TTS_CHANNELS", "1")),
            help="Number of audio channels (default: %(default)s).",
        )
        parser.add_argument(
            "--sample-rate",
            type=int,
            default=int(os.getenv("GOOGLE_TTS_SAMPLE_RATE", "24000")),
            help="Audio sample rate in Hz for the WAV header (default: %(default)s).",
        )
        parser.add_argument(
            "--sample-width",
            type=int,
            default=int(os.getenv("GOOGLE_TTS_SAMPLE_WIDTH", "2")),
            help="Sample width in bytes (default: %(default)s).",
        )
        parser.add_argument(
            "--api-key",
            help="Optional Google API key. Defaults to the GOOGLE_API_KEY environment variable.",
        )

    def handle(self, *args, **options):
        try:
            from google import genai  # type: ignore
            from google.genai import types  # type: ignore
        except ImportError as exc:  # pragma: no cover - import guard
            raise CommandError(
                "google-genai must be installed to use this command. "
                "Add it to your environment or requirements file."
            ) from exc

        text = (options.get("text") or "").strip()
        text_file: Path | None = options.get("text_file")
        if text_file:
            if not text_file.exists():
                raise CommandError(f"Text file not found: {text_file}")
            try:
                file_text = text_file.read_text(encoding="utf-8")
            except UnicodeDecodeError as exc:
                raise CommandError(f"Failed to read text file as UTF-8: {text_file}") from exc
            if text:
                text = f"{text}\n{file_text.strip()}"
            else:
                text = file_text.strip()

        if not sys.stdin.isatty():
            stdin_text = sys.stdin.read().strip()
            if stdin_text:
                text = f"{text}\n{stdin_text}".strip()

        if not text:
            raise CommandError("No text provided. Use --text, --text-file, or pipe stdin content.")

        output_path: Path = options["output"]
        if output_path.exists() and not options["overwrite"]:
            raise CommandError(
                f"{output_path} already exists. Use --overwrite to replace the existing file."
            )
        output_path.parent.mkdir(parents=True, exist_ok=True)

        channels = options["channels"]
        sample_rate = options["sample_rate"]
        sample_width = options["sample_width"]
        if channels <= 0:
            raise CommandError("Number of channels must be a positive integer.")
        if sample_rate <= 0:
            raise CommandError("Sample rate must be a positive integer.")
        if sample_width not in {1, 2, 3, 4}:
            raise CommandError("Sample width must be an integer between 1 and 4 bytes.")

        api_key = options.get("api_key") or os.getenv("GOOGLE_API_KEY")
        client_kwargs = {}
        if api_key:
            client_kwargs["api_key"] = api_key
        client = genai.Client(**client_kwargs)

        config = types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=options["voice"]),
                )
            ),
        )
        response = client.models.generate_content(
            model=options["model"],
            contents=text,
            config=config,
        )

        audio_bytes = self._extract_audio_bytes(response)
        if not audio_bytes:
            raise CommandError("No audio data returned by the model.")

        if isinstance(audio_bytes, str):
            try:
                audio_bytes = base64.b64decode(audio_bytes)
            except Exception as exc:  # pragma: no cover - defensive
                raise CommandError("Returned audio data is not valid base64.") from exc
        elif isinstance(audio_bytes, memoryview):
            audio_bytes = audio_bytes.tobytes()
        elif not isinstance(audio_bytes, (bytes, bytearray)):
            raise CommandError("Unsupported audio data type returned by the model.")

        write_wave_file(output_path, bytes(audio_bytes), channels, sample_rate, sample_width)
        self.stdout.write(self.style.SUCCESS(f"Wrote synthesized speech to {output_path.resolve()}"))

    @staticmethod
    def _extract_audio_bytes(response) -> bytes | str | memoryview | None:
        candidates = getattr(response, "candidates", []) or []
        for candidate in candidates:
            content = getattr(candidate, "content", None)
            if not content:
                continue
            parts = getattr(content, "parts", []) or []
            for part in parts:
                inline_data = getattr(part, "inline_data", None)
                if inline_data and getattr(inline_data, "data", None):
                    return inline_data.data
        return None
