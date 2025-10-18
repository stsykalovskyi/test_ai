import pytesseract
from PIL import Image
from django.core.files.base import ContentFile
from io import BytesIO
import cv2
import numpy as np


class OCRService:
    """Service for extracting text from images using Tesseract OCR"""

    # Map language codes to Tesseract language codes
    LANGUAGE_MAP = {
        'uk': 'ukr',
        'en': 'eng',
        'ru': 'rus',
    }

    def __init__(self, language='uk', apply_preprocessing=True):
        """
        Initialize OCR service

        Args:
            language: Language code or comma-separated language codes (default: 'uk' for Ukrainian)
                     Examples: 'uk', 'uk,en', 'en,ru'
            apply_preprocessing: Whether to apply dewarping and perspective correction (default: True)
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

        self.apply_preprocessing = apply_preprocessing

    def preprocess_image(self, image):
        """
        Apply minimal preprocessing to improve OCR accuracy with very gentle shadow handling

        Args:
            image: PIL Image or numpy array

        Returns:
            numpy array: Preprocessed image
        """
        # Convert PIL Image to OpenCV format if needed
        if isinstance(image, Image.Image):
            img = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        else:
            img = image

        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Very gentle noise reduction (optional, minimal blur)
        denoised = cv2.GaussianBlur(gray, (3, 3), 0)

        # Use CLAHE with very conservative settings
        # Lower clipLimit (1.0) and larger tile size (16x16) for gentler processing
        clahe = cv2.createCLAHE(clipLimit=1.0, tileGridSize=(16, 16))
        enhanced = clahe.apply(denoised)

        return enhanced

    def _order_points(self, pts):
        """
        Order points in top-left, top-right, bottom-right, bottom-left order

        Args:
            pts: Array of 4 points

        Returns:
            numpy array: Ordered points
        """
        rect = np.zeros((4, 2), dtype="float32")

        # Top-left point has smallest sum, bottom-right has largest sum
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]
        rect[2] = pts[np.argmax(s)]

        # Top-right has smallest difference, bottom-left has largest difference
        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)]
        rect[3] = pts[np.argmax(diff)]

        return rect

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

            # Apply preprocessing if enabled
            if self.apply_preprocessing:
                processed_image = self.preprocess_image(image)
                # Convert back to PIL Image for pytesseract
                image = Image.fromarray(processed_image)

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
