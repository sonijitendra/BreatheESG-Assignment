"""
Core models: Tenant and AuditLog.

The Tenant model implements multi-tenancy — every business entity
operates within an isolated tenant boundary. AuditLog provides an
immutable, append-only trail of every mutation in the system.
"""

import uuid

from django.db import models


class Tenant(models.Model):
    """
    An organisation or business entity.

    Every data record in the system is scoped to a tenant, providing
    logical isolation between different customers.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class AuditLog(models.Model):
    """
    Immutable audit trail entry.

    Uses BigAutoField (not UUID) as PK to guarantee monotonic ordering
    for pagination and chronological queries. Every create / update /
    delete on a domain entity should produce an AuditLog row.
    """

    class Action(models.TextChoices):
        CREATE = 'create', 'Create'
        UPDATE = 'update', 'Update'
        DELETE = 'delete', 'Delete'

    id = models.BigAutoField(primary_key=True)
    tenant = models.ForeignKey(
        Tenant,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='audit_logs',
    )
    entity_type = models.CharField(max_length=100)
    entity_id = models.CharField(max_length=255)
    action = models.CharField(max_length=20, choices=Action.choices)
    changes = models.JSONField(default=dict)
    performed_by = models.CharField(max_length=255)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['entity_type', 'entity_id']),
            models.Index(fields=['tenant', 'created_at']),
            models.Index(fields=['performed_by', 'created_at']),
        ]

    def __str__(self):
        return f'{self.action} {self.entity_type}:{self.entity_id}'
