from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TenantViewSet, AuditLogViewSet

router = DefaultRouter()
router.register(r'tenants', TenantViewSet, basename='tenant')
router.register(r'audit', AuditLogViewSet, basename='audit')

urlpatterns = [
    path('', include(router.urls)),
]
