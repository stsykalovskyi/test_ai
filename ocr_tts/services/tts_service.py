from gtts import gTTS
from django.core.files.base import ContentFile
from io import BytesIO
import os
import base64
import wave


class TTSService:
    """Service for converting text to speech using gTTS or Google Gemini"""

    def __init__(self, language='uk', provider='gtts'):
        """
        Initialize TTS service

        Args:
            language: Language code for speech synthesis (default: 'uk' for Ukrainian)
            provider: TTS provider - 'gtts' or 'gemini' (default: 'gtts')
        """
        self.language = language
        self.provider = provider

    def text_to_speech_gtts(self, text, slow=False):
        """Convert text to speech using gTTS (MP3 format)"""
        try:
            tts = gTTS(text=text, lang=self.language, slow=slow)
            audio_buffer = BytesIO()
            tts.write_to_fp(audio_buffer)
            audio_buffer.seek(0)
            return audio_buffer
        except Exception as e:
            raise Exception(f"gTTS conversion failed: {str(e)}")

    def text_to_speech_gemini(self, text, voice='Zephyr'):
        """Convert text to speech using Google Gemini (WAV format)"""
        try:
            from google import genai
            from google.genai import types
        except ImportError:
            raise Exception("google-genai must be installed to use Gemini TTS")

        try:
            api_key = os.getenv("GOOGLE_API_KEY")
            client_kwargs = {}
            if api_key:
                client_kwargs["api_key"] = api_key
            client = genai.Client(**client_kwargs)

            config = types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice),
                    )
                ),
            )

            model = os.getenv("GOOGLE_TTS_MODEL", "gemini-2.5-flash-preview-tts")
            response = client.models.generate_content(
                model=model,
                contents=text,
                config=config,
            )

            audio_bytes = self._extract_audio_bytes(response)
            if not audio_bytes:
                raise Exception("No audio data returned by Gemini")

            if isinstance(audio_bytes, str):
                audio_bytes = base64.b64decode(audio_bytes)
            elif isinstance(audio_bytes, memoryview):
                audio_bytes = audio_bytes.tobytes()

            # Convert to WAV format
            audio_buffer = BytesIO()
            channels = int(os.getenv("GOOGLE_TTS_CHANNELS", "1"))
            sample_rate = int(os.getenv("GOOGLE_TTS_SAMPLE_RATE", "24000"))
            sample_width = int(os.getenv("GOOGLE_TTS_SAMPLE_WIDTH", "2"))

            with wave.open(audio_buffer, "wb") as wf:
                wf.setnchannels(channels)
                wf.setsampwidth(sample_width)
                wf.setframerate(sample_rate)
                wf.writeframes(bytes(audio_bytes))

            audio_buffer.seek(0)
            return audio_buffer
        except Exception as e:
            raise Exception(f"Gemini TTS conversion failed: {str(e)}")

    @staticmethod
    def _extract_audio_bytes(response):
        """Extract audio bytes from Gemini response"""
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

    def text_to_speech(self, text, slow=False, voice='Zephyr'):
        """
        Convert text to speech audio

        Args:
            text: Text content to convert to speech
            slow: Whether to use slow speech rate (default: False) - gTTS only
            voice: Voice name for Gemini (default: 'Zephyr')

        Returns:
            BytesIO: Audio data in MP3 (gTTS) or WAV (Gemini) format
        """
        if self.provider == 'gemini':
            return self.text_to_speech_gemini(text, voice=voice)
        else:
            return self.text_to_speech_gtts(text, slow=slow)

    def save_audio_to_file(self, text, filename='audio.mp3', slow=False, voice='Zephyr'):
        """
        Convert text to speech and save as ContentFile for Django FileField

        Args:
            text: Text content to convert
            filename: Name for the audio file
            slow: Whether to use slow speech rate (gTTS only)
            voice: Voice name for Gemini

        Returns:
            ContentFile: Django ContentFile object with audio data
        """
        # Adjust filename extension based on provider
        if self.provider == 'gemini' and filename.endswith('.mp3'):
            filename = filename.replace('.mp3', '.wav')

        audio_buffer = self.text_to_speech(text, slow=slow, voice=voice)
        return ContentFile(audio_buffer.read(), name=filename)
