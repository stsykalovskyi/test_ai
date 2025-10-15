"""Primary URL configuration for the test_ai project."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from .views import HomeView

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path("admin/", admin.site.urls),
    path("api/morphology/", include("ukrainian_morphology.urls")),
    path("morphology/", include("ukrainian_morphology.frontend_urls")),
    path("api/person_detection/", include("person_detection.urls")),
    path("person_detection/", include("person_detection.frontend_urls")),
    path("ocr_tts/", include("ocr_tts.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
