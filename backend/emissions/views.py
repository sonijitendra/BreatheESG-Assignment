from rest_framework import viewsets, status, mixins
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters import rest_framework as filters
from rest_framework.filters import SearchFilter, OrderingFilter
from django.db.models import Sum, Count
from django.utils import timezone
from .models import EmissionFactor, EmissionRecord, ReviewAction
from ingestion.models import IngestionJob
from .serializers import EmissionFactorSerializer, EmissionRecordSerializer, ReviewActionSerializer
from .services.review_service import review_record, bulk_review
from ingestion.serializers import IngestionJobSerializer

class EmissionRecordFilter(filters.FilterSet):
    scope = filters.BaseInFilter(field_name='scope')
    status = filters.BaseInFilter(field_name='status')
    source_type = filters.BaseInFilter(field_name='data_source__source_type')
    start_date = filters.DateFilter(field_name='activity_date', lookup_expr='gte')
    end_date = filters.DateFilter(field_name='activity_date', lookup_expr='lte')

    class Meta:
        model = EmissionRecord
        fields = ['scope', 'status', 'source_type', 'start_date', 'end_date']

class EmissionRecordViewSet(viewsets.ModelViewSet):
    queryset = EmissionRecord.objects.all().prefetch_related('review_actions')
    serializer_class = EmissionRecordSerializer
    filter_backends = [filters.DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = EmissionRecordFilter
    search_fields = ['category', 'description', 'analyst_notes']
    ordering_fields = ['activity_date', 'co2e_tonnes', 'status', 'created_at']
    ordering = ['-activity_date']

    def get_queryset(self):
        queryset = super().get_queryset()
        tenant_slug = self.kwargs.get('tenant_slug') or self.request.query_params.get('tenant')
        if tenant_slug:
            queryset = queryset.filter(tenant__slug=tenant_slug)
        return queryset

    @action(detail=True, methods=['post'], url_path='review')
    def apply_review(self, request, tenant_slug=None, pk=None):
        record = self.get_object()
        action_name = request.data.get('action')
        reason = request.data.get('reason', '')
        changes = request.data.get('changes', {})
        performed_by = request.data.get('performed_by', 'system_analyst')

        if not action_name:
            return Response({'error': 'Action is required'}, status=status.HTTP_400_BAD_REQUEST)

        # Get client IP & User Agent for immutable Audit Logging
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
            
        ua = request.META.get('HTTP_USER_AGENT', '')

        try:
            updated_record = review_record(
                record=record,
                action=action_name,
                performed_by=performed_by,
                reason=reason,
                changes=changes,
                ip_address=ip,
                user_agent=ua
            )
            return Response(self.get_serializer(updated_record).data, status=status.HTTP_200_OK)
        except ValueError as val_ex:
            return Response({'error': str(val_ex)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as ex:
            return Response({'error': f"Review failed: {str(ex)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'], url_path='bulk-review')
    def apply_bulk_review(self, request, tenant_slug=None):
        record_ids = request.data.get('record_ids', [])
        action_name = request.data.get('action')
        reason = request.data.get('reason', '')
        performed_by = request.data.get('performed_by', 'system_analyst')

        if not record_ids or not action_name:
            return Response({'error': 'record_ids and action are required'}, status=status.HTTP_400_BAD_REQUEST)

        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        ip = x_forwarded_for.split(',')[0] if x_forwarded_for else request.META.get('REMOTE_ADDR')
        ua = request.META.get('HTTP_USER_AGENT', '')

        success, failed, errors = bulk_review(
            record_ids=record_ids,
            action=action_name,
            performed_by=performed_by,
            reason=reason,
            ip_address=ip,
            user_agent=ua
        )

        return Response({
            'successful_count': success,
            'failed_count': failed,
            'errors': errors
        }, status=status.HTTP_200_OK if failed == 0 else status.HTTP_207_MULTI_STATUS)

class DashboardSummaryViewSet(viewsets.ViewSet):
    """
    Exposes aggregated metrics by scope, source, and review status.
    """
    def list(self, request, tenant_slug=None):
        t_slug = tenant_slug or request.query_params.get('tenant')
        
        records_query = EmissionRecord.objects.all()
        jobs_query = IngestionJob.objects.all()
        
        if t_slug:
            records_query = records_query.filter(tenant__slug=t_slug)
            jobs_query = jobs_query.filter(tenant__slug=t_slug)

        # 1. Total statistics
        total_stats = records_query.aggregate(
            count=Count('id'),
            co2e_t=Sum('co2e_tonnes')
        )
        total_records = total_stats['count'] or 0
        total_co2e_tonnes = float(total_stats['co2e_t'] or 0.0)

        # 2. Aggregations by Scope
        scope_aggregations = records_query.values('scope').annotate(
            count=Count('id'),
            co2e_t=Sum('co2e_tonnes')
        )
        by_scope = [
            {
                'scope': item['scope'],
                'count': item['count'],
                'co2e_tonnes': float(item['co2e_t'] or 0.0)
            }
            for item in scope_aggregations
        ]

        # 3. Aggregations by Status
        status_aggregations = records_query.values('status').annotate(
            count=Count('id')
        )
        by_status = [
            {
                'status': item['status'],
                'count': item['count']
            }
            for item in status_aggregations
        ]

        # 4. Aggregations by Source
        source_aggregations = records_query.values('data_source__source_type').annotate(
            count=Count('id'),
            co2e_t=Sum('co2e_tonnes')
        )
        by_source = [
            {
                'source_type': item['data_source__source_type'],
                'count': item['count'],
                'co2e_tonnes': float(item['co2e_t'] or 0.0)
            }
            for item in source_aggregations
        ]

        # 5. Recent Ingestion Jobs (last 5)
        recent_jobs = jobs_query.order_by('-started_at')[:5]
        jobs_serializer = IngestionJobSerializer(recent_jobs, many=True)

        return Response({
            'total_records': total_records,
            'total_co2e_tonnes': round(total_co2e_tonnes, 4),
            'by_scope': by_scope,
            'by_status': by_status,
            'by_source': by_source,
            'recent_jobs': jobs_serializer.data
        }, status=status.HTTP_200_OK)

class EmissionFactorViewSet(viewsets.ModelViewSet):
    queryset = EmissionFactor.objects.all()
    serializer_class = EmissionFactorSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        tenant_slug = self.kwargs.get('tenant_slug') or self.request.query_params.get('tenant')
        if tenant_slug:
            queryset = queryset.filter(tenant__slug=tenant_slug)
        return queryset
