"""HTTP entrypoints exposing the morphology services."""

from __future__ import annotations

import json

from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView
from pydantic import ValidationError

from ml.config import TrainingConfig
from ml.training.pipeline import TrainingPipeline

from .constants import ANIMACY, CASES, GENDERS
from .schemas import InflectRequest
from .services.inflection import MorphologicalInflector


class MorphologyDashboardView(TemplateView):
    """Simple frontend for testing inflection and triggering training."""

    template_name = "morphology/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "cases": list(CASES.keys()),
                "genders": sorted(GENDERS),
                "animacy": sorted(ANIMACY),
            }
        )
        return context


@method_decorator(csrf_exempt, name="dispatch")
class InflectView(View):
    """Accepts JSON payloads describing the desired inflection."""

    service_class = MorphologicalInflector

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.inflector = self.service_class()

    def post(self, request, *args, **kwargs):
        try:
            payload = json.loads(request.body.decode("utf-8"))
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON payload"}, status=400)

        try:
            inflect_request = InflectRequest.model_validate(payload)
        except ValidationError as exc:
            return JsonResponse(
                {"error": "Validation failed", "details": exc.errors()},
                status=422,
            )

        result = self.inflector.inflect(inflect_request)
        return JsonResponse(result.model_dump(), status=200)

    def get(self, request, *args, **kwargs):
        return JsonResponse(
            {
                "description": "POST lemma + target_case (називний/родовий/...) to obtain an inflected form.",
                "fields": {
                    "lemma": "Base form of the name or title.",
                    "target_case": "One of: " + ", ".join(CASES.keys()),
                    "gender": f"Optional hint. Supported: {', '.join(sorted(GENDERS))}",
                    "animacy": f"Optional hint. Supported: {', '.join(sorted(ANIMACY))}",
                    "title": "Optional honorific or rank tied to the lemma.",
                },
            }
        )


@method_decorator(csrf_exempt, name="dispatch")
class TrainModelView(View):
    """Train the frequency-based inflection model and store a checkpoint."""

    pipeline_class = TrainingPipeline
    config_class = TrainingConfig

    def post(self, request, *args, **kwargs):
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

        pipeline = self.pipeline_class(config)
        try:
            pipeline.fit()
            checkpoint_path = pipeline.save_checkpoint()
        except FileNotFoundError as exc:
            return JsonResponse({"error": str(exc)}, status=404)
        except ValueError as exc:
            return JsonResponse({"error": str(exc)}, status=400)
        except RuntimeError as exc:
            return JsonResponse({"error": str(exc)}, status=500)
        except Exception as exc:  # pragma: no cover - unexpected errors
            return JsonResponse({"error": str(exc)}, status=500)

        return JsonResponse(
            {
                "status": "completed",
                "message": "Training finished using frequency baseline.",
                "checkpoint": str(checkpoint_path),
                "metadata": pipeline.model.metadata,
            },
            status=200,
        )
