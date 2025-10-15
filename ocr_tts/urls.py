from django.urls import path
from . import views

app_name = 'ocr_tts'

urlpatterns = [
    # Dashboards
    path('dashboard/', views.dashboard, name='dashboard'),
    path('multipage/', views.multipage_dashboard, name='multipage_dashboard'),
    path('library/', views.library_dashboard, name='library_dashboard'),

    # Old single-image API
    path('api/upload/', views.upload_and_process_image, name='upload'),
    path('api/documents/', views.list_documents, name='list_documents'),

    # Multi-page document endpoints
    path('api/documents/list/', views.list_all_documents, name='list_all_documents'),
    path('api/documents/create/', views.create_document, name='create_document'),
    path('api/documents/<int:document_id>/', views.get_document, name='get_document'),
    path('api/documents/<int:document_id>/update/', views.update_document, name='update_document'),
    path('api/documents/<int:document_id>/pages/', views.list_pages, name='list_pages'),
    path('api/documents/<int:document_id>/pages/add/', views.add_page, name='add_page'),
    path('api/documents/<int:document_id>/generate-audio/', views.generate_document_audio, name='generate_document_audio'),
    path('api/pages/<int:page_id>/', views.get_page, name='get_page'),
    path('api/pages/<int:page_id>/process/', views.process_page, name='process_page'),
    path('api/pages/<int:page_id>/update-text/', views.update_page_text, name='update_page_text'),
    path('api/pages/<int:page_id>/update-image/', views.update_page_image, name='update_page_image'),
    path('api/pages/<int:page_id>/delete/', views.delete_page, name='delete_page'),
]
