"""HTTP entrypoints for person detection services."""

from __future__ import annotations

import json

from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView
from PIL import Image
from pydantic import ValidationError

from ml.config import TrainingConfig

from .services.detection import PersonDetectionService


class PersonDetectionDashboardView(TemplateView):
    """Dashboard for testing person detection and triggering training."""

    template_name = "person_detection/dashboard.html"


@method_decorator(csrf_exempt, name="dispatch")
class PersonDetectView(View):
    """Accept image uploads and return person detection results."""

    service_class = PersonDetectionService
    _detector = None

    @property
    def detector(self):
        """Lazy-load the detector only when needed."""
        if self._detector is None:
            self.__class__._detector = self.service_class()
        return self._detector

    def post(self, request, *args, **kwargs):
        """Handle image upload via multipart/form-data."""
        if "image" not in request.FILES:
            return JsonResponse({"error": "No image file provided"}, status=400)

        try:
            image_file = request.FILES["image"]
            image = Image.open(image_file).convert("RGB")
        except Exception as exc:
            return JsonResponse({"error": f"Failed to load image: {str(exc)}"}, status=400)

        result = self.detector.detect(image)
        return JsonResponse(result.model_dump(), status=200)

    def get(self, request, *args, **kwargs):
        """Return API description."""
        return JsonResponse(
            {
                "description": "POST an image file to detect person type (man/woman/nobody).",
                "method": "POST multipart/form-data with 'image' field",
                "response": {
                    "label": "One of: man, woman, nobody",
                    "confidence": "Float between 0.0 and 1.0",
                },
            }
        )


@method_decorator(csrf_exempt, name="dispatch")
class TrainPersonDetectionView(View):
    """Train the person detection model and save checkpoint."""

    config_class = TrainingConfig

    def post(self, request, *args, **kwargs):
        """Trigger training of person detection model."""
        if request.body:
            try:
                payload = json.loads(request.body.decode("utf-8"))
            except json.JSONDecodeError:
                return JsonResponse({"error": "Invalid JSON payload"}, status=400)
        else:
            payload = {}

        try:
            config = self.config_class.model_validate(payload)
        except ValidationError as exc:
            return JsonResponse(
                {"error": "Validation failed", "details": exc.errors()},
                status=422,
            )

        # Lazy import to avoid loading heavy dependencies at module import time
        from ml.training.person_pipeline import PersonClassificationPipeline
        pipeline = PersonClassificationPipeline(config)

        # Add device info to response
        import torch
        device_used = pipeline.model.device
        cuda_available = torch.cuda.is_available()

        try:
            pipeline.fit()
            checkpoint_path = pipeline.save_checkpoint()
        except FileNotFoundError as exc:
            return JsonResponse({"error": str(exc)}, status=404)
        except ValueError as exc:
            return JsonResponse({"error": str(exc)}, status=400)
        except RuntimeError as exc:
            return JsonResponse({"error": str(exc)}, status=500)
        except Exception as exc:
            return JsonResponse({"error": str(exc)}, status=500)

        return JsonResponse(
            {
                "status": "completed",
                "message": "Person detection model training finished.",
                "checkpoint": str(checkpoint_path),
                "metadata": pipeline.model.metadata,
                "device_info": {
                    "device_used": device_used,
                    "cuda_available": cuda_available,
                },
            },
            status=200,
        )
