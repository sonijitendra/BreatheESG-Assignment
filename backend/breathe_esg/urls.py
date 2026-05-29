"""
Root URL configuration for breathe_esg project.

All API endpoints are structured by tenant: /api/<tenant_slug>/.
"""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/<slug:tenant_slug>/', include([
        path('', include('core.urls')),
        path('', include('ingestion.urls')),
        path('', include('emissions.urls')),
    ])),
]
