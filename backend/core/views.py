from rest_framework import viewsets, mixins
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from .models import Tenant, AuditLog
from .serializers import TenantSerializer, AuditLogSerializer

class TenantViewSet(viewsets.ModelViewSet):
    queryset = Tenant.objects.filter(is_active=True)
    serializer_class = TenantSerializer
    lookup_field = 'slug'

class AuditLogViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    queryset = AuditLog.objects.all()
    serializer_class = AuditLogSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['entity_type', 'entity_id', 'action', 'performed_by']
    search_fields = ['performed_by', 'entity_id']
    ordering_fields = ['created_at']
    ordering = ['-created_at']

    def get_queryset(self):
        queryset = super().get_queryset()
        tenant_slug = self.kwargs.get('tenant_slug') or self.request.query_params.get('tenant')
        if tenant_slug:
            queryset = queryset.filter(tenant__slug=tenant_slug)
        return queryset
