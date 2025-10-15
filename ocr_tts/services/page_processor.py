from django.utils import timezone
from .ocr_service import OCRService


class PageProcessor:
    """Service for processing individual pages - OCR only, no audio"""

    def __init__(self, document):
        """
        Initialize processor with document settings

        Args:
            document: Document instance containing language settings
        """
        self.document = document
        # Use ocr_languages if available, fallback to language
        ocr_lang = getattr(document, 'ocr_languages', None) or document.language
        self.ocr_service = OCRService(language=ocr_lang)

    def process_page(self, page):
        """
        Process a page: extract text from image only (no audio)

        Args:
            page: Page instance

        Returns:
            Page: Updated page with extracted text
        """
        # Extract text from image
        extracted_text = self.ocr_service.extract_text(page.image)
        page.text_content = extracted_text

        # Save text file
        text_file = self.ocr_service.save_text_to_file(
            extracted_text,
            filename=f'page_{page.id}_text.txt'
        )
        page.text_file.save(f'page_{page.id}_text.txt', text_file, save=False)

        # Mark as processed
        page.processed = True
        page.processed_at = timezone.now()
        page.save()

        return page
