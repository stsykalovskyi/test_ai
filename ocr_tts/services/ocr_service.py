import pytesseract
from PIL import Image
from django.core.files.base import ContentFile
from io import BytesIO


class OCRService:
    """Service for extracting text from images using Tesseract OCR"""

    # Map language codes to Tesseract language codes
    LANGUAGE_MAP = {
        'uk': 'ukr',
        'en': 'eng',
        'ru': 'rus',
    }

    def __init__(self, language='uk'):
        """
        Initialize OCR service

        Args:
            language: Language code or comma-separated language codes (default: 'uk' for Ukrainian)
                     Examples: 'uk', 'uk,en', 'en,ru'
        """
        # Handle multiple languages separated by commas
        if ',' in language:
            lang_codes = [l.strip() for l in language.split(',')]
            tesseract_langs = [self.LANGUAGE_MAP.get(l, l) for l in lang_codes]
            self.language = '+'.join(tesseract_langs)
        else:
            # Single language
            tesseract_lang = self.LANGUAGE_MAP.get(language, language)
            self.language = tesseract_lang

    def extract_text(self, image_path):
        """
        Extract text from an image file

        Args:
            image_path: Path to the image file or Django FieldFile

        Returns:
            str: Extracted text from the image
        """
        try:
            # Open image using PIL
            if hasattr(image_path, 'path'):
                # Django FieldFile
                image = Image.open(image_path.path)
            else:
                # String path
                image = Image.open(image_path)

            # Perform OCR
            text = pytesseract.image_to_string(image, lang=self.language)

            return text.strip()
        except Exception as e:
            raise Exception(f"OCR extraction failed: {str(e)}")

    def save_text_to_file(self, text, filename='extracted_text.txt'):
        """
        Save extracted text to a ContentFile for Django FileField

        Args:
            text: Text content to save
            filename: Name for the file

        Returns:
            ContentFile: Django ContentFile object
        """
        text_bytes = text.encode('utf-8')
        return ContentFile(text_bytes, name=filename)
