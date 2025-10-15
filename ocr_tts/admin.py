from django.contrib import admin
from .models import Document, Page, OCRDocument, ImageDocument, ExtractedText, AudioFile


class PageInline(admin.TabularInline):
    model = Page
    extra = 0
    fields = ['page_number', 'image', 'processed', 'uploaded_at']
    readonly_fields = ['uploaded_at']
    ordering = ['page_number']


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'language', 'tts_provider', 'total_pages', 'processed_pages', 'is_complete', 'created_at']
    list_filter = ['language', 'tts_provider', 'created_at']
    readonly_fields = ['created_at', 'updated_at', 'total_pages', 'processed_pages', 'is_complete']
    search_fields = ['title', 'description']
    inlines = [PageInline]

    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description')
        }),
        ('Settings', {
            'fields': ('language', 'tts_provider', 'tts_voice')
        }),
        ('Status', {
            'fields': ('total_pages', 'processed_pages', 'is_complete', 'created_at', 'updated_at')
        }),
    )


@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    list_display = ['id', 'document', 'page_number', 'processed', 'uploaded_at']
    list_filter = ['processed', 'uploaded_at', 'document']
    readonly_fields = ['uploaded_at', 'processed_at']
    search_fields = ['text_content', 'document__title']
    ordering = ['document', 'page_number']

    fieldsets = (
        ('Page Information', {
            'fields': ('document', 'page_number', 'image')
        }),
        ('Extracted Content', {
            'fields': ('text_content', 'text_file', 'audio_file')
        }),
        ('Status', {
            'fields': ('processed', 'uploaded_at', 'processed_at')
        }),
    )


@admin.register(OCRDocument)
class OCRDocumentAdmin(admin.ModelAdmin):
    list_display = ['id', 'uploaded_at', 'language', 'processed', 'has_text', 'has_audio']
    list_filter = ['processed', 'language', 'uploaded_at']
    readonly_fields = ['uploaded_at', 'processed_at']
    search_fields = ['text_content']

    def has_text(self, obj):
        return bool(obj.text_content)
    has_text.boolean = True
    has_text.short_description = 'Text Extracted'

    def has_audio(self, obj):
        return bool(obj.audio_file)
    has_audio.boolean = True
    has_audio.short_description = 'Audio Generated'


@admin.register(ImageDocument)
class ImageDocumentAdmin(admin.ModelAdmin):
    list_display = ['id', 'uploaded_at', 'processed']
    list_filter = ['processed', 'uploaded_at']
    readonly_fields = ['uploaded_at']


@admin.register(ExtractedText)
class ExtractedTextAdmin(admin.ModelAdmin):
    list_display = ['id', 'image_document', 'created_at']
    readonly_fields = ['created_at']


@admin.register(AudioFile)
class AudioFileAdmin(admin.ModelAdmin):
    list_display = ['id', 'extracted_text', 'language', 'created_at']
    list_filter = ['language', 'created_at']
    readonly_fields = ['created_at']
