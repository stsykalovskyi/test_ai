from django.utils import timezone
from django.core.files.base import ContentFile
from .tts_service import TTSService
from io import BytesIO
import re


class DocumentAudioGenerator:
    """Service for generating audio from entire document after all pages are processed"""

    def __init__(self, document):
        """
        Initialize generator with document settings

        Args:
            document: Document instance
        """
        self.document = document
        self.tts_service = TTSService(
            language=document.language,
            provider=document.tts_provider
        )

    def generate_audio(self):
        """
        Generate audio page by page and concatenate.

        Process:
        1. Get combined text with page dividers (===PAGE_X===)
        2. Split by dividers to get individual page text blocks
        3. Generate audio for each page block separately
        4. Concatenate all audio files
        5. Save combined audio

        Returns:
            Document: Updated document with combined audio file
        """
        if not self.document.is_complete:
            raise Exception("Not all pages are processed yet")

        # Get combined text from all pages (includes dividers)
        combined_text = self.document.get_combined_text()

        if not combined_text:
            raise Exception("No text content found in pages")

        # Save combined text file (with dividers for reference)
        text_file = ContentFile(combined_text.encode('utf-8'))
        self.document.combined_text_file.save(
            f'document_{self.document.id}_full_text.txt',
            text_file,
            save=False
        )

        # Split text by page dividers
        page_blocks = re.split(r'===PAGE_\d+===\n?', combined_text)
        page_blocks = [block.strip() for block in page_blocks if block.strip()]

        if not page_blocks:
            raise Exception("No text blocks found after splitting")

        # Generate audio for each page block
        audio_buffers = []
        for i, text_block in enumerate(page_blocks, 1):
            print(f"Generating audio for page block {i}/{len(page_blocks)}...")

            if self.document.tts_provider == 'gtts':
                audio_buffer = self.tts_service.text_to_speech_gtts(text_block)
            else:  # gemini
                audio_buffer = self.tts_service.text_to_speech_gemini(
                    text_block,
                    voice=self.document.tts_voice
                )

            audio_buffers.append(audio_buffer)

        # Concatenate audio buffers
        combined_audio = self._concatenate_audio_buffers(
            audio_buffers,
            self.document.tts_provider
        )

        # Save combined audio
        audio_extension = '.wav' if self.document.tts_provider == 'gemini' else '.mp3'
        audio_filename = f'document_{self.document.id}_audiobook{audio_extension}'

        self.document.combined_audio_file.save(audio_filename, combined_audio, save=False)

        # Mark audio as generated
        self.document.audio_generated = True
        self.document.audio_generated_at = timezone.now()
        self.document.save()

        return self.document

    def _concatenate_audio_buffers(self, buffers, provider):
        """
        Concatenate multiple audio buffers into one.

        For MP3: Simply concatenate bytes (works for MP3 format)
        For WAV: Need to properly merge WAV headers and data

        Args:
            buffers: List of BytesIO audio buffers
            provider: 'gtts' (MP3) or 'gemini' (WAV)

        Returns:
            ContentFile: Combined audio file
        """
        if provider == 'gtts':
            # MP3: Simple concatenation
            combined = BytesIO()
            for buffer in buffers:
                buffer.seek(0)
                combined.write(buffer.read())
            combined.seek(0)
            return ContentFile(combined.read())
        else:
            # WAV: Proper concatenation (placeholder - simple concat for now)
            # TODO: Implement proper WAV concatenation with header merging
            combined = BytesIO()
            for i, buffer in enumerate(buffers):
                buffer.seek(0)
                data = buffer.read()
                if i == 0:
                    # Keep first file's header
                    combined.write(data)
                else:
                    # Skip WAV header (44 bytes) for subsequent files
                    combined.write(data[44:] if len(data) > 44 else data)
            combined.seek(0)
            return ContentFile(combined.read())
