"""URL routing for person detection API."""

from django.urls import path

from .views import PersonDetectView, TrainPersonDetectionView

app_name = "person_detection"

urlpatterns = [
    path("detect/", PersonDetectView.as_view(), name="detect"),
    path("train/", TrainPersonDetectionView.as_view(), name="train"),
]
