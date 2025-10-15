from django.urls import path

from .views import InflectView, TrainModelView


app_name = "ukrainian_morphology"

urlpatterns = [
    path("inflect/", InflectView.as_view(), name="inflect"),
    path("train/", TrainModelView.as_view(), name="train"),
]
