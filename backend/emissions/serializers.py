from rest_framework import serializers
from .models import EmissionFactor, EmissionRecord, ReviewAction

class EmissionFactorSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmissionFactor
        fields = '__all__'

class ReviewActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReviewAction
        fields = '__all__'

class EmissionRecordSerializer(serializers.ModelSerializer):
    data_source_name = serializers.CharField(source='data_source.name', read_only=True)
    data_source_type = serializers.CharField(source='data_source.source_type', read_only=True)
    raw_data = serializers.JSONField(source='raw_record.raw_data', read_only=True)
    review_actions = ReviewActionSerializer(many=True, read_only=True)

    class Meta:
        model = EmissionRecord
        fields = [
            'id', 'scope', 'category', 'description', 'activity_date',
            'reporting_period_start', 'reporting_period_end', 'quantity_value', 'quantity_unit',
            'original_quantity_value', 'original_quantity_unit', 'emission_factor',
            'emission_factor_value', 'co2e_kg', 'co2e_tonnes', 'status', 'flags',
            'analyst_notes', 'reviewed_by', 'reviewed_at', 'approved_by', 'approved_at',
            'locked_at', 'data_source_name', 'data_source_type', 'raw_data', 'review_actions', 'created_at'
        ]
