from django.db import models


class Document(models.Model):
    """Parent model for multi-page documents (books)"""
    title = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    language = models.CharField(max_length=10, default='uk')  # For TTS
    ocr_languages = models.CharField(max_length=100, default='uk', help_text='Comma-separated OCR language codes (e.g., uk,en)')
    tts_provider = models.CharField(
        max_length=10,
        choices=[('gtts', 'Google TTS (gTTS)'), ('gemini', 'Google Gemini TTS')],
        default='gtts'
    )
    tts_voice = models.CharField(max_length=50, default='Zephyr', blank=True)
    combined_text_file = models.FileField(upload_to='documents/texts/', blank=True, null=True)
    combined_audio_file = models.FileField(upload_to='documents/audio/', blank=True, null=True)
    audio_generated = models.BooleanField(default=False)
    audio_generated_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Document'
        verbose_name_plural = 'Documents'

    def __str__(self):
        return self.title or f"Document {self.id}"

    @property
    def total_pages(self):
        return self.pages.count()

    @property
    def processed_pages(self):
        return self.pages.filter(processed=True).count()

    @property
    def is_complete(self):
        return self.total_pages > 0 and self.total_pages == self.processed_pages

    def get_combined_text(self):
        """
        Get all page texts combined with intelligent sentence merging.

        Logic:
        - Find text after last sentence (ending with ., !, ?) on current page
        - Move incomplete sentence to start of next page
        - Add page dividers (===PAGE_X===) to mark text blocks

        Returns:
            str: Combined text with page dividers
        """
        pages = self.pages.filter(processed=True).order_by('page_number')

        if not pages.exists():
            return ''

        page_texts = []
        carry_over = ''  # Text to carry to next page

        for page in pages:
            if not page.text_content:
                continue

            text = page.text_content.strip()

            # Add carried over text from previous page
            if carry_over:
                text = carry_over + ' ' + text
                carry_over = ''

            # Find last sentence-ending punctuation
            last_period = max(text.rfind('.'), text.rfind('!'), text.rfind('?'))

            if last_period != -1 and last_period < len(text) - 1:
                # There's text after the last sentence
                complete_text = text[:last_period + 1].strip()
                carry_over = text[last_period + 1:].strip()
            else:
                # All text is complete sentences
                complete_text = text
                carry_over = ''

            # Add page marker and text
            page_block = f"===PAGE_{page.page_number}===\n{complete_text}"
            page_texts.append(page_block)

        # If there's leftover text, add it to the last page
        if carry_over:
            if page_texts:
                page_texts[-1] += '\n' + carry_over

        return '\n\n'.join(page_texts)


class Page(models.Model):
    """Individual page within a document - OCR only, no audio"""

    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name='pages'
    )
    page_number = models.PositiveIntegerField()
    image = models.ImageField(upload_to='ocr_images/')
    text_content = models.TextField(blank=True)
    text_file = models.FileField(upload_to='extracted_texts/', blank=True, null=True)
    processed = models.BooleanField(default=False)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ['document', 'page_number']
        unique_together = ['document', 'page_number']
        verbose_name = 'Page'
        verbose_name_plural = 'Pages'

    def __str__(self):
        return f"{self.document} - Page {self.page_number}"


class OCRDocument(models.Model):
    """Unified model for storing image, extracted text, and generated audio"""
    TTS_PROVIDER_CHOICES = [
        ('gtts', 'Google TTS (gTTS)'),
        ('gemini', 'Google Gemini TTS'),
    ]

    image = models.ImageField(upload_to='ocr_images/')
    text_content = models.TextField(blank=True)
    text_file = models.FileField(upload_to='extracted_texts/', blank=True, null=True)
    audio_file = models.FileField(upload_to='audio_files/', blank=True, null=True)
    language = models.CharField(max_length=10, default='uk')  # For TTS
    ocr_languages = models.CharField(max_length=100, default='uk', help_text='Comma-separated OCR language codes')
    tts_provider = models.CharField(max_length=10, choices=TTS_PROVIDER_CHOICES, default='gtts')
    tts_voice = models.CharField(max_length=50, default='Zephyr', blank=True)
    processed = models.BooleanField(default=False)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ['-uploaded_at']
        verbose_name = 'OCR Document'
        verbose_name_plural = 'OCR Documents'

    def __str__(self):
        return f"Document {self.id} - {self.uploaded_at}"


class ImageDocument(models.Model):
    """Model for storing uploaded images for OCR processing"""
    image = models.ImageField(upload_to='ocr_images/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    processed = models.BooleanField(default=False)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"Image {self.id} - {self.uploaded_at}"


class ExtractedText(models.Model):
    """Model for storing text extracted from images"""
    image_document = models.OneToOneField(
        ImageDocument,
        on_delete=models.CASCADE,
        related_name='extracted_text'
    )
    text_content = models.TextField()
    text_file = models.FileField(upload_to='extracted_texts/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Text from Image {self.image_document.id}"


class AudioFile(models.Model):
    """Model for storing generated audio files from text"""
    extracted_text = models.OneToOneField(
        ExtractedText,
        on_delete=models.CASCADE,
        related_name='audio'
    )
    audio_file = models.FileField(upload_to='audio_files/')
    language = models.CharField(max_length=10, default='uk')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Audio from Text {self.extracted_text.id}"
