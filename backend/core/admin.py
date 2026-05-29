from django.contrib import admin

from .models import AuditLog, Tenant


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'entity_type', 'entity_id', 'action', 'performed_by', 'created_at')
    list_filter = ('action', 'entity_type')
    search_fields = ('entity_id', 'performed_by')
    readonly_fields = (
        'id', 'tenant', 'entity_type', 'entity_id', 'action',
        'changes', 'performed_by', 'ip_address', 'user_agent', 'created_at',
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
