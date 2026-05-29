"""
Root URL configuration for breathe_esg project.

All API endpoints are structured by tenant: /api/<tenant_slug>/.
Exposes a root health check endpoint at /health/.
"""

from django.contrib import admin
from django.urls import include, path
from django.http import JsonResponse
from django.utils import timezone

def health_check(request):
    return JsonResponse({
        'status': 'healthy',
        'timestamp': timezone.now().isoformat(),
        'service': 'Breathe ESG Ingestion Platform'
    })

urlpatterns = [
    path('admin/', admin.site.urls),
    path('health/', health_check, name='health-check'),
    path('api/<slug:tenant_slug>/', include([
        path('', include('core.urls')),
        path('', include('ingestion.urls')),
        path('', include('emissions.urls')),
    ])),
]
