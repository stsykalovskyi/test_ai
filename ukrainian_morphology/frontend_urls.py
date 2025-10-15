from django.urls import path

from .views import MorphologyDashboardView


app_name = "ukrainian_morphology_frontend"

urlpatterns = [
    path("dashboard/", MorphologyDashboardView.as_view(), name="dashboard"),
]
