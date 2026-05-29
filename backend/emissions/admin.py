from django.contrib import admin

from .models import EmissionFactor, EmissionRecord, ReviewAction


@admin.register(EmissionFactor)
class EmissionFactorAdmin(admin.ModelAdmin):
    list_display = ('category', 'subcategory', 'scope', 'factor_value', 'unit_numerator', 'unit_denominator', 'region', 'valid_from', 'valid_to')
    list_filter = ('scope', 'category')
    search_fields = ('category', 'subcategory', 'region')


@admin.register(EmissionRecord)
class EmissionRecordAdmin(admin.ModelAdmin):
    list_display = ('category', 'scope', 'quantity_value', 'quantity_unit', 'co2e_kg', 'status', 'activity_date', 'tenant')
    list_filter = ('scope', 'status', 'category')
    search_fields = ('category', 'description')


@admin.register(ReviewAction)
class ReviewActionAdmin(admin.ModelAdmin):
    list_display = ('emission_record', 'action', 'from_status', 'to_status', 'performed_by', 'created_at')
    list_filter = ('action',)
    search_fields = ('performed_by',)
    readonly_fields = (
        'id', 'tenant', 'emission_record', 'action', 'from_status',
        'to_status', 'performed_by', 'reason', 'changes', 'created_at',
    )
