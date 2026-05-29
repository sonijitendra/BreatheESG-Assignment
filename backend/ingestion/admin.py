from django.contrib import admin

from .models import DataSource, IngestionJob, RawRecord


@admin.register(DataSource)
class DataSourceAdmin(admin.ModelAdmin):
    list_display = ('name', 'tenant', 'source_type', 'is_active', 'created_at')
    list_filter = ('source_type', 'is_active')
    search_fields = ('name',)


@admin.register(IngestionJob)
class IngestionJobAdmin(admin.ModelAdmin):
    list_display = ('file_name', 'tenant', 'data_source', 'status', 'total_rows', 'successful_rows', 'failed_rows', 'started_at')
    list_filter = ('status',)
    search_fields = ('file_name',)


@admin.register(RawRecord)
class RawRecordAdmin(admin.ModelAdmin):
    list_display = ('id', 'ingestion_job', 'source_row_number', 'is_valid', 'created_at')
    list_filter = ('is_valid',)
    readonly_fields = ('raw_data', 'validation_errors')
