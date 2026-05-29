from rest_framework import serializers
from .models import Tenant, AuditLog

class TenantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tenant
        fields = ['id', 'name', 'slug', 'is_active', 'created_at', 'updated_at']

class AuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = [
            'id', 'tenant', 'entity_type', 'entity_id', 'action',
            'changes', 'performed_by', 'ip_address', 'user_agent', 'created_at'
        ]
