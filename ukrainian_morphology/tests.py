from __future__ import annotations

import json
from pathlib import Path

from django.conf import settings
from django.test import Client, SimpleTestCase

from .schemas import InflectRequest
from .services.inflection import MorphologicalInflector


class MorphologicalInflectorTests(SimpleTestCase):
    def setUp(self):
        self.inflector = MorphologicalInflector()

    def test_returns_stubbed_response(self):
        payload = InflectRequest.model_construct(
            lemma="Іван",
            case="називний",
            gender="masculine",
        )
        result = self.inflector.inflect(payload)
        self.assertEqual(result.inflected, "Іван")


class MorphologyViewsTests(SimpleTestCase):
    def setUp(self):
        self.client = Client()
        self.dataset_path = Path(settings.DATA_DIR) / "processed" / "train.csv"
        self.dataset_path.parent.mkdir(parents=True, exist_ok=True)
        self.dataset_path.write_text(
            "lemma,target_case,inflected,gender,animacy,title\n"
            "Сергій,називний,Сергій,masculine,animate,\n"
            "Сергій,родовий,Сергія,masculine,animate,\n",
            encoding="utf-8",
        )
        self.addCleanup(self._cleanup_dataset)

    def _cleanup_dataset(self):
        if self.dataset_path.exists():
            self.dataset_path.unlink()

    def test_dashboard_renders(self):
        response = self.client.get("/morphology/dashboard/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Тестування відмінювання", response.content.decode("utf-8"))

    def test_inflect_get_returns_description(self):
        response = self.client.get("/api/morphology/inflect/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("description", response.json())

    def test_inflect_post_with_invalid_payload(self):
        response = self.client.post(
            "/api/morphology/inflect/",
            data="not-json",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_inflect_post_with_valid_payload(self):
        response = self.client.post(
            "/api/morphology/inflect/",
            data=json.dumps({"lemma": "Сергій", "target_case": "називний"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["inflected"], "Сергій")

    def test_train_endpoint_uses_defaults(self):
        response = self.client.post(
            "/api/morphology/train/",
            data=json.dumps({}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "completed")
        self.assertIn("checkpoint", payload)
        self.assertEqual(payload["metadata"]["samples"], 2)

    def test_train_then_inflect_uses_model(self):
        self.client.post(
            "/api/morphology/train/",
            data=json.dumps({}),
            content_type="application/json",
        )
        service = MorphologicalInflector()
        payload = InflectRequest.model_construct(
            lemma="Сергій",
            case="родовий",
            gender="masculine",
            animacy="animate",
        )
        result = service.inflect(payload)
        self.assertEqual(result.inflected, "Сергія")
        self.assertEqual(result.confidence, 1.0)

    def test_train_endpoint_rejects_invalid_payload(self):
        response = self.client.post(
            "/api/morphology/train/",
            data=json.dumps({"max_epochs": 0}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 422)
        self.assertIn("error", response.json())
