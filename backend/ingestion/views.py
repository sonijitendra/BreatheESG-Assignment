from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.shortcuts import get_object_or_anchor
from .models import DataSource, IngestionJob, RawRecord
from core.models import Tenant
from .serializers import DataSourceSerializer, IngestionJobSerializer, RawRecordSerializer
from .services.ingestion_service import ingest_file

class TenantViewMixin:
    """
    Mixin to automatically filter queries by the URL tenant_slug.
    """
    def get_tenant(self):
        tenant_slug = self.kwargs.get('tenant_slug')
        try:
            return Tenant.objects.get(slug=tenant_slug)
        except Tenant.DoesNotExist:
            from rest_framework.exceptions import NotFound
            raise NotFound(f"Tenant '{tenant_slug}' not found.")

class DataSourceViewSet(TenantViewMixin, viewsets.ModelViewSet):
    serializer_class = DataSourceSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['source_type', 'is_active']
    search_fields = ['name', 'description']

    def get_queryset(self):
        tenant = self.get_tenant()
        return DataSource.objects.filter(tenant=tenant)

    def perform_create(self, serializer):
        tenant = self.get_tenant()
        serializer.save(tenant=tenant)

    @action(detail=True, methods=['post'], url_path='upload')
    def upload_file(self, request, tenant_slug=None, pk=None):
        data_source = self.get_object()
        tenant = self.get_tenant()
        
        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response({'error': 'No file was uploaded. Please attach a CSV file under key "file".'}, status=status.HTTP_400_BAD_REQUEST)
            
        uploaded_by = request.data.get('uploaded_by', 'system_analyst')
        
        try:
            job = ingest_file(
                tenant=tenant,
                data_source=data_source,
                file_obj=file_obj,
                uploaded_by=uploaded_by
            )
            serializer = IngestionJobSerializer(job)
            
            if job.status == IngestionJob.Status.FAILED:
                return Response(serializer.data, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as ex:
            return Response({'error': f"Ingestion initiation failed: {str(ex)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class IngestionJobViewSet(TenantViewMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = IngestionJobSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['status']
    ordering_fields = ['started_at', 'completed_at']
    ordering = ['-started_at']

    def get_queryset(self):
        tenant = self.get_tenant()
        return IngestionJob.objects.filter(tenant=tenant)

class RawRecordViewSet(TenantViewMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = RawRecordSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['is_valid', 'ingestion_job']

    def get_queryset(self):
        tenant = self.get_tenant()
        return RawRecord.objects.filter(tenant=tenant)
