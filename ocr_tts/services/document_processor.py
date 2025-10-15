from django.utils import timezone
from .ocr_service import OCRService
from .tts_service import TTSService


class DocumentProcessor:
    """Service for processing OCRDocument - extract text and generate audio"""

    def __init__(self, language='uk', tts_provider='gtts'):
        self.language = language
        self.tts_provider = tts_provider
        self.ocr_service = OCRService(language=language)
        self.tts_service = TTSService(language=language, provider=tts_provider)

    def process_document(self, ocr_document):
        """
        Process an OCRDocument: extract text from image and generate audio

        Args:
            ocr_document: OCRDocument instance

        Returns:
            OCRDocument: Updated document with text and audio
        """
        # Extract text from image
        extracted_text = self.ocr_service.extract_text(ocr_document.image)
        ocr_document.text_content = extracted_text

        # Save text file
        text_file = self.ocr_service.save_text_to_file(
            extracted_text,
            filename=f'text_{ocr_document.id}.txt'
        )
        ocr_document.text_file.save(f'text_{ocr_document.id}.txt', text_file, save=False)

        # Generate audio from text with appropriate extension
        audio_extension = '.wav' if self.tts_provider == 'gemini' else '.mp3'
        audio_filename = f'audio_{ocr_document.id}{audio_extension}'

        audio_file = self.tts_service.save_audio_to_file(
            extracted_text,
            filename=audio_filename,
            voice=ocr_document.tts_voice if hasattr(ocr_document, 'tts_voice') else 'Zephyr'
        )
        ocr_document.audio_file.save(audio_filename, audio_file, save=False)

        # Mark as processed
        ocr_document.processed = True
        ocr_document.processed_at = timezone.now()
        ocr_document.save()

        return ocr_document
