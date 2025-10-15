"""URL routing for person detection frontend."""

from django.urls import path

from .views import PersonDetectionDashboardView

app_name = "person_detection_frontend"

urlpatterns = [
    path("dashboard/", PersonDetectionDashboardView.as_view(), name="dashboard"),
]
