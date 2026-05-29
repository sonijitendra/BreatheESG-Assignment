"""
Emissions models: EmissionFactor, EmissionRecord, ReviewAction.

EmissionRecord is the *mutable analytical layer* — it is created by
normalising a RawRecord and then moves through the review workflow
(pending → reviewed → approved → locked).
"""

import uuid

from django.db import models

from core.models import Tenant
from ingestion.models import DataSource, RawRecord


class EmissionFactor(models.Model):
    """
    Conversion factor that maps an activity quantity (litres of diesel,
    kWh of electricity, passenger-km of flight) to kgCO2e.

    Tenant-specific factors override the system defaults (tenant=NULL).
    """

    class Scope(models.IntegerChoices):
        SCOPE_1 = 1, 'Scope 1'
        SCOPE_2 = 2, 'Scope 2'
        SCOPE_3 = 3, 'Scope 3'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        Tenant,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='emission_factors',
    )
    category = models.CharField(max_length=50)
    subcategory = models.CharField(max_length=100)
    scope = models.SmallIntegerField(choices=Scope.choices)
    unit_numerator = models.CharField(max_length=20)
    unit_denominator = models.CharField(max_length=20)
    factor_value = models.DecimalField(max_digits=12, decimal_places=6)
    source_reference = models.CharField(max_length=255)
    valid_from = models.DateField()
    valid_to = models.DateField(null=True, blank=True)
    region = models.CharField(max_length=100, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['category', 'subcategory']
        indexes = [
            models.Index(fields=['category', 'subcategory', 'scope', 'valid_from']),
            models.Index(fields=['tenant', 'category']),
        ]

    def __str__(self):
        return f'{self.category}/{self.subcategory} — {self.factor_value} {self.unit_numerator}/{self.unit_denominator}'


class EmissionRecord(models.Model):
    """
    Normalised emission data derived from a RawRecord.

    Moves through the review lifecycle:
    pending → reviewed → approved → locked  (happy path)
    pending → flagged → reviewed → …        (anomaly path)
    reviewed → rejected → pending → …       (correction loop)
    """

    class Scope(models.IntegerChoices):
        SCOPE_1 = 1, 'Scope 1'
        SCOPE_2 = 2, 'Scope 2'
        SCOPE_3 = 3, 'Scope 3'

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        FLAGGED = 'flagged', 'Flagged'
        REVIEWED = 'reviewed', 'Reviewed'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'
        LOCKED = 'locked', 'Locked'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        Tenant, on_delete=models.CASCADE, related_name='emission_records',
    )
    raw_record = models.OneToOneField(
        RawRecord, on_delete=models.CASCADE, related_name='emission_record',
    )
    data_source = models.ForeignKey(
        DataSource, on_delete=models.CASCADE, related_name='emission_records',
    )
    scope = models.SmallIntegerField(choices=Scope.choices)
    category = models.CharField(max_length=100)
    description = models.CharField(max_length=500, blank=True, default='')
    activity_date = models.DateField()
    reporting_period_start = models.DateField(null=True, blank=True)
    reporting_period_end = models.DateField(null=True, blank=True)

    # Activity quantities
    quantity_value = models.DecimalField(max_digits=14, decimal_places=4)
    quantity_unit = models.CharField(max_length=30)
    original_quantity_value = models.DecimalField(
        max_digits=14, decimal_places=4, null=True, blank=True,
    )
    original_quantity_unit = models.CharField(max_length=30, blank=True, default='')

    # Emission calculation
    emission_factor = models.ForeignKey(
        EmissionFactor, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='emission_records',
    )
    emission_factor_value = models.DecimalField(
        max_digits=12, decimal_places=6, null=True, blank=True,
    )
    co2e_kg = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    co2e_tonnes = models.DecimalField(max_digits=14, decimal_places=6, null=True, blank=True)

    # Review workflow
    status = models.CharField(
        max_length=20, default=Status.PENDING, choices=Status.choices,
    )
    flags = models.JSONField(default=list)
    analyst_notes = models.TextField(blank=True, default='')
    reviewed_by = models.CharField(max_length=255, blank=True, default='')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.CharField(max_length=255, blank=True, default='')
    approved_at = models.DateTimeField(null=True, blank=True)
    locked_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', 'scope', 'status']),
            models.Index(fields=['tenant', 'status', 'activity_date']),
            models.Index(fields=['tenant', 'data_source', 'activity_date']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return (
            f'{self.category} — {self.quantity_value} {self.quantity_unit} '
            f'({self.get_status_display()})'
        )


class ReviewAction(models.Model):
    """
    Immutable log of a single review workflow transition.
    """

    class ActionType(models.TextChoices):
        REVIEW = 'review', 'Review'
        APPROVE = 'approve', 'Approve'
        REJECT = 'reject', 'Reject'
        FLAG = 'flag', 'Flag'
        LOCK = 'lock', 'Lock'
        EDIT = 'edit', 'Edit'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        Tenant, on_delete=models.CASCADE, related_name='review_actions',
    )
    emission_record = models.ForeignKey(
        EmissionRecord, on_delete=models.CASCADE, related_name='review_actions',
    )
    action = models.CharField(max_length=20, choices=ActionType.choices)
    from_status = models.CharField(max_length=20)
    to_status = models.CharField(max_length=20)
    performed_by = models.CharField(max_length=255)
    reason = models.TextField(blank=True, default='')
    changes = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['emission_record', 'created_at']),
            models.Index(fields=['tenant', 'action', '-created_at']),
            models.Index(fields=['performed_by', '-created_at']),
        ]

    def __str__(self):
        return f'{self.action}: {self.from_status} → {self.to_status}'
