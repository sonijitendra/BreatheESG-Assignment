"""
Ingestion models: DataSource, IngestionJob, RawRecord.

These form the *immutable intake layer*. Once a CSV row is parsed and
stored as a RawRecord it is never mutated — all downstream
transformations produce separate EmissionRecord rows.
"""

import uuid

from django.db import models

from core.models import Tenant


class DataSource(models.Model):
    """
    A configured upstream data feed (e.g. SAP procurement, utility bills).
    """

    class SourceType(models.TextChoices):
        SAP = 'sap', 'SAP Fuel & Procurement'
        UTILITY = 'utility', 'Utility Electricity'
        TRAVEL = 'travel', 'Corporate Travel'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        Tenant, on_delete=models.CASCADE, related_name='data_sources',
    )
    name = models.CharField(max_length=255)
    source_type = models.CharField(max_length=20, choices=SourceType.choices)
    description = models.TextField(blank=True, default='')
    configuration = models.JSONField(default=dict)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', 'source_type']),
            models.Index(fields=['tenant', 'is_active']),
        ]

    def __str__(self):
        return f'{self.name} ({self.get_source_type_display()})'


class IngestionJob(models.Model):
    """
    Tracks the lifecycle of a single file upload.
    """

    class Status(models.TextChoices):
        PROCESSING = 'processing', 'Processing'
        COMPLETED = 'completed', 'Completed'
        COMPLETED_WITH_ERRORS = 'completed_with_errors', 'Completed with Errors'
        FAILED = 'failed', 'Failed'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        Tenant, on_delete=models.CASCADE, related_name='ingestion_jobs',
    )
    data_source = models.ForeignKey(
        DataSource, on_delete=models.CASCADE, related_name='jobs',
    )
    file_name = models.CharField(max_length=500)
    file_hash = models.CharField(max_length=64, blank=True, default='')
    status = models.CharField(
        max_length=20,
        default=Status.PROCESSING,
        choices=Status.choices,
    )
    total_rows = models.IntegerField(default=0)
    successful_rows = models.IntegerField(default=0)
    failed_rows = models.IntegerField(default=0)
    error_summary = models.JSONField(default=list)
    uploaded_by = models.CharField(max_length=255)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['tenant', 'status']),
            models.Index(fields=['tenant', 'data_source', '-started_at']),
            models.Index(fields=['file_hash']),
        ]

    def __str__(self):
        return f'{self.file_name} — {self.get_status_display()}'


class RawRecord(models.Model):
    """
    Immutable verbatim copy of a single parsed CSV row.

    Validation errors are stored alongside the data so the user can
    inspect and re-upload if necessary.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        Tenant, on_delete=models.CASCADE, related_name='raw_records',
    )
    ingestion_job = models.ForeignKey(
        IngestionJob, on_delete=models.CASCADE, related_name='raw_records',
    )
    source_row_number = models.IntegerField()
    raw_data = models.JSONField()
    is_valid = models.BooleanField(default=True)
    validation_errors = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['source_row_number']
        indexes = [
            models.Index(fields=['ingestion_job', 'source_row_number']),
            models.Index(fields=['tenant', 'is_valid']),
        ]

    def __str__(self):
        return f'Row {self.source_row_number} of {self.ingestion_job_id}'
