from __future__ import annotations

import sys
import tempfile
import types as pytypes
import wave
from pathlib import Path
from unittest import mock

from django.core.management import call_command
from django.test import SimpleTestCase


class TextToSpeechCommandTests(SimpleTestCase):
    def test_command_generates_audio_file(self):
        fake_audio = b"\x01\x02\x03\x04"
        fake_inline = pytypes.SimpleNamespace(data=fake_audio)
        fake_part = pytypes.SimpleNamespace(inline_data=fake_inline)
        fake_content = pytypes.SimpleNamespace(parts=[fake_part])
        fake_candidate = pytypes.SimpleNamespace(content=fake_content)
        fake_response = pytypes.SimpleNamespace(candidates=[fake_candidate])

        fake_models = mock.Mock()
        fake_models.generate_content.return_value = fake_response
        fake_client_instance = mock.Mock()
        fake_client_instance.models = fake_models
        fake_client = mock.Mock(return_value=fake_client_instance)

        genai_module = pytypes.ModuleType("google.genai")
        genai_module.Client = fake_client

        class _DummyType:
            def __init__(self, *args, **kwargs):
                self.args = args
                self.kwargs = kwargs

        genai_types_module = pytypes.ModuleType("google.genai.types")
        genai_types_module.GenerateContentConfig = _DummyType
        genai_types_module.SpeechConfig = _DummyType
        genai_types_module.VoiceConfig = _DummyType
        genai_types_module.PrebuiltVoiceConfig = _DummyType

        setattr(genai_module, "types", genai_types_module)

        google_module = pytypes.ModuleType("google")
        setattr(google_module, "genai", genai_module)

        with tempfile.TemporaryDirectory() as tmpdir, mock.patch.dict(
            sys.modules,
            {
                "google": google_module,
                "google.genai": genai_module,
                "google.genai.types": genai_types_module,
            },
        ), mock.patch(
            "test_ai.management.commands.text_to_speech.sys.stdin.isatty", return_value=True
        ):
            output_path = Path(tmpdir) / "result.wav"

            call_command(
                "text_to_speech",
                "--text",
                "Привіт, світе!",
                "--output",
                str(output_path),
            )

            self.assertTrue(output_path.exists())
            with wave.open(str(output_path), "rb") as wf:
                self.assertEqual(wf.getnchannels(), 1)
                self.assertEqual(wf.getframerate(), 24000)
                self.assertEqual(wf.getsampwidth(), 2)
                self.assertEqual(wf.readframes(wf.getnframes()), fake_audio)

            fake_client.assert_called_once_with()
            fake_models.generate_content.assert_called_once()
