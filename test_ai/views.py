"""Core project views."""

from django.views.generic import TemplateView


class HomeView(TemplateView):
    template_name = "home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "dashboard_url": "/morphology/dashboard/",
                "api_url": "/api/morphology/inflect/",
                "docs_url": "/docs/morphology_model.md",
            }
        )
        return context
