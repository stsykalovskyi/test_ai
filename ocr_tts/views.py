from django.shortcuts import render
from django.http import JsonResponse, FileResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from .models import OCRDocument, ImageDocument, ExtractedText, AudioFile
from .services import DocumentProcessor, OCRService, TTSService
import json


@csrf_exempt
@require_http_methods(["POST"])
def upload_and_process_image(request):
    """Upload image, extract text, and generate speech using unified model"""
    try:
        if 'image' not in request.FILES:
            return JsonResponse({'error': 'No image file provided'}, status=400)

        image_file = request.FILES['image']
        language = request.POST.get('language', 'uk')
        ocr_languages = request.POST.get('ocr_languages', 'uk')
        tts_provider = request.POST.get('tts_provider', 'gtts')
        tts_voice = request.POST.get('tts_voice', 'Zephyr')

        # Debug logging
        print(f"DEBUG: language={language}, ocr_languages={ocr_languages}, tts_provider={tts_provider}, tts_voice={tts_voice}")
        print(f"DEBUG: POST data: {dict(request.POST)}")

        # Ensure defaults are set
        if not tts_provider:
            tts_provider = 'gtts'
        if not tts_voice:
            tts_voice = 'Zephyr'
        if not ocr_languages:
            ocr_languages = 'uk'

        # Create OCR document
        ocr_doc = OCRDocument.objects.create(
            image=image_file,
            language=language,
            ocr_languages=ocr_languages,
            tts_provider=tts_provider,
            tts_voice=tts_voice
        )

        # Process document: extract text and generate audio
        processor = DocumentProcessor(language=ocr_languages, tts_provider=tts_provider)
        ocr_doc = processor.process_document(ocr_doc)

        return JsonResponse({
            'success': True,
            'document_id': ocr_doc.id,
            'text': ocr_doc.text_content,
            'text_file_url': ocr_doc.text_file.url if ocr_doc.text_file else None,
            'audio_file_url': ocr_doc.audio_file.url if ocr_doc.audio_file else None
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET"])
def list_documents(request):
    """List all processed documents from unified model"""
    documents = OCRDocument.objects.filter(processed=True)
    data = []

    for doc in documents:
        try:
            item = {
                'id': doc.id,
                'uploaded_at': doc.uploaded_at.isoformat(),
                'image_url': doc.image.url,
                'text': doc.text_content[:100] + '...' if doc.text_content else '',
                'text_file_url': doc.text_file.url if doc.text_file else None,
                'audio_file_url': doc.audio_file.url if doc.audio_file else None,
                'language': doc.language,
                'ocr_languages': doc.ocr_languages,
                'tts_provider': doc.tts_provider,
                'tts_voice': doc.tts_voice
            }
            data.append(item)
        except Exception:
            continue

    return JsonResponse({'documents': data})


def dashboard(request):
    """Render OCR/TTS dashboard (single image)"""
    return render(request, 'ocr_tts/dashboard.html')


def multipage_dashboard(request):
    """Render multi-page document dashboard"""
    return render(request, 'ocr_tts/multipage_dashboard.html')


def library_dashboard(request):
    """Render books library dashboard"""
    return render(request, 'ocr_tts/library_dashboard.html')


# Multi-page document views

@require_http_methods(["GET"])
def list_all_documents(request):
    """List all multi-page documents"""
    try:
        from .models import Document

        documents = Document.objects.all().order_by('-created_at')
        data = []

        for doc in documents:
            data.append({
                'id': doc.id,
                'title': doc.title,
                'description': doc.description,
                'language': doc.language,
                'ocr_languages': doc.ocr_languages,
                'tts_provider': doc.tts_provider,
                'tts_voice': doc.tts_voice,
                'total_pages': doc.total_pages,
                'processed_pages': doc.processed_pages,
                'is_complete': doc.is_complete,
                'audio_generated': doc.audio_generated,
                'audio_generated_at': doc.audio_generated_at.isoformat() if doc.audio_generated_at else None,
                'combined_text_url': doc.combined_text_file.url if doc.combined_text_file else None,
                'combined_audio_url': doc.combined_audio_file.url if doc.combined_audio_file else None,
                'created_at': doc.created_at.isoformat(),
                'updated_at': doc.updated_at.isoformat()
            })

        return JsonResponse({
            'success': True,
            'documents': data,
            'total': len(data)
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def update_document(request, document_id):
    """Update document metadata"""
    try:
        from .models import Document

        document = Document.objects.get(id=document_id)

        # Update fields if provided
        if 'title' in request.POST:
            document.title = request.POST.get('title', '')
        if 'description' in request.POST:
            document.description = request.POST.get('description', '')
        if 'language' in request.POST:
            document.language = request.POST.get('language', 'uk')
        if 'ocr_languages' in request.POST:
            document.ocr_languages = request.POST.get('ocr_languages', 'uk')
        if 'tts_provider' in request.POST:
            document.tts_provider = request.POST.get('tts_provider', 'gtts')
        if 'tts_voice' in request.POST:
            document.tts_voice = request.POST.get('tts_voice', 'Zephyr')

        document.save()

        return JsonResponse({
            'success': True,
            'document_id': document.id,
            'title': document.title,
            'description': document.description,
            'language': document.language,
            'ocr_languages': document.ocr_languages,
            'tts_provider': document.tts_provider,
            'tts_voice': document.tts_voice
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def create_document(request):
    """Create a new multi-page document"""
    try:
        from .models import Document

        title = request.POST.get('title', '')
        description = request.POST.get('description', '')
        language = request.POST.get('language', 'uk')
        ocr_languages = request.POST.get('ocr_languages', 'uk')
        tts_provider = request.POST.get('tts_provider', 'gtts')
        tts_voice = request.POST.get('tts_voice', 'Zephyr')

        document = Document.objects.create(
            title=title,
            description=description,
            language=language,
            ocr_languages=ocr_languages,
            tts_provider=tts_provider,
            tts_voice=tts_voice
        )

        return JsonResponse({
            'success': True,
            'document_id': document.id,
            'title': document.title,
            'total_pages': document.total_pages
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET"])
def get_document(request, document_id):
    """Get document details"""
    try:
        from .models import Document

        document = Document.objects.get(id=document_id)

        return JsonResponse({
            'success': True,
            'document': {
                'id': document.id,
                'title': document.title,
                'description': document.description,
                'language': document.language,
                'ocr_languages': document.ocr_languages,
                'tts_provider': document.tts_provider,
                'tts_voice': document.tts_voice,
                'total_pages': document.total_pages,
                'processed_pages': document.processed_pages,
                'is_complete': document.is_complete,
                'created_at': document.created_at.isoformat()
            }
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=404)


@require_http_methods(["GET"])
def list_pages(request, document_id):
    """List all pages in a document"""
    try:
        from .models import Document

        document = Document.objects.get(id=document_id)
        pages = document.pages.all()

        data = []
        for page in pages:
            data.append({
                'id': page.id,
                'page_number': page.page_number,
                'image_url': page.image.url,
                'text': page.text_content,  # Return full text, not truncated
                'text_file_url': page.text_file.url if page.text_file else None,
                'processed': page.processed,
                'uploaded_at': page.uploaded_at.isoformat()
            })

        return JsonResponse({
            'success': True,
            'document_id': document_id,
            'pages': data
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=404)


@csrf_exempt
@require_http_methods(["POST"])
def add_page(request, document_id):
    """Add a new page to a document"""
    try:
        from .models import Document, Page

        if 'image' not in request.FILES:
            return JsonResponse({'error': 'No image file provided'}, status=400)

        document = Document.objects.get(id=document_id)
        image_file = request.FILES['image']

        # Auto-increment page number
        last_page = document.pages.order_by('-page_number').first()
        page_number = (last_page.page_number + 1) if last_page else 1

        page = Page.objects.create(
            document=document,
            page_number=page_number,
            image=image_file
        )

        return JsonResponse({
            'success': True,
            'page_id': page.id,
            'page_number': page.page_number,
            'document_id': document_id
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def process_page(request, page_id):
    """Process a specific page (OCR only, no audio)"""
    try:
        from .models import Page
        from .services import PageProcessor

        page = Page.objects.get(id=page_id)
        processor = PageProcessor(page.document)
        page = processor.process_page(page)

        return JsonResponse({
            'success': True,
            'page_id': page.id,
            'page_number': page.page_number,
            'text': page.text_content,
            'text_file_url': page.text_file.url if page.text_file else None,
            'processed': page.processed
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET"])
def get_page(request, page_id):
    """Get page details including full text"""
    try:
        from .models import Page

        page = Page.objects.get(id=page_id)

        return JsonResponse({
            'success': True,
            'page': {
                'id': page.id,
                'page_number': page.page_number,
                'image_url': page.image.url,
                'text_content': page.text_content,
                'text_file_url': page.text_file.url if page.text_file else None,
                'processed': page.processed,
                'uploaded_at': page.uploaded_at.isoformat(),
                'processed_at': page.processed_at.isoformat() if page.processed_at else None
            }
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=404)


@csrf_exempt
@require_http_methods(["POST"])
def update_page_text(request, page_id):
    """Update page text content"""
    try:
        from .models import Page
        from .services import OCRService

        page = Page.objects.get(id=page_id)

        # Allow empty text - use empty string if not provided
        new_text = request.POST.get('text_content', '')

        # Update text content
        page.text_content = new_text

        # Update text file if there's text
        if new_text:
            ocr_service = OCRService(language=page.document.language)
            text_file = ocr_service.save_text_to_file(
                new_text,
                filename=f'page_{page.id}_text.txt'
            )
            page.text_file.save(f'page_{page.id}_text.txt', text_file, save=False)

        page.save()

        return JsonResponse({
            'success': True,
            'page_id': page.id,
            'text_content': page.text_content,
            'text_file_url': page.text_file.url if page.text_file else None
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def update_page_image(request, page_id):
    """Update page image and reprocess OCR"""
    try:
        from .models import Page
        from .services import PageProcessor

        if 'image' not in request.FILES:
            return JsonResponse({'error': 'No image file provided'}, status=400)

        page = Page.objects.get(id=page_id)
        image_file = request.FILES['image']

        # Update the image
        page.image = image_file
        page.save()

        # Reprocess the page with OCR
        processor = PageProcessor(page.document)
        page = processor.process_page(page)

        return JsonResponse({
            'success': True,
            'page_id': page.id,
            'page_number': page.page_number,
            'image_url': page.image.url,
            'text': page.text_content,
            'text_file_url': page.text_file.url if page.text_file else None,
            'processed': page.processed
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def delete_page(request, page_id):
    """Delete a page from document"""
    try:
        from .models import Page

        page = Page.objects.get(id=page_id)
        document_id = page.document.id
        page_number = page.page_number

        # Delete the page
        page.delete()

        # Renumber remaining pages
        remaining_pages = Page.objects.filter(
            document_id=document_id,
            page_number__gt=page_number
        ).order_by('page_number')

        for p in remaining_pages:
            p.page_number -= 1
            p.save()

        return JsonResponse({
            'success': True,
            'message': f'Page {page_number} deleted',
            'document_id': document_id
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def generate_document_audio(request, document_id):
    """Generate audio for entire document from all pages"""
    try:
        from .models import Document
        from .services import DocumentAudioGenerator

        document = Document.objects.get(id=document_id)

        if not document.is_complete:
            return JsonResponse({
                'error': f'Document is not complete. Processed {document.processed_pages}/{document.total_pages} pages.'
            }, status=400)

        generator = DocumentAudioGenerator(document)
        document = generator.generate_audio()

        return JsonResponse({
            'success': True,
            'document_id': document.id,
            'combined_text_url': document.combined_text_file.url if document.combined_text_file else None,
            'combined_audio_url': document.combined_audio_file.url if document.combined_audio_file else None,
            'audio_generated': document.audio_generated,
            'audio_generated_at': document.audio_generated_at.isoformat() if document.audio_generated_at else None
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
