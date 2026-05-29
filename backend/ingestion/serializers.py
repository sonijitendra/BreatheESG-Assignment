from rest_framework import serializers
from .models import DataSource, IngestionJob, RawRecord

class DataSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataSource
        fields = ['id', 'name', 'source_type', 'description', 'configuration', 'is_active', 'created_at', 'updated_at']

class IngestionJobSerializer(serializers.ModelSerializer):
    data_source_name = serializers.CharField(source='data_source.name', read_only=True)
    data_source_type = serializers.CharField(source='data_source.source_type', read_only=True)

    class Meta:
        model = IngestionJob
        fields = [
            'id', 'data_source', 'data_source_name', 'data_source_type', 'file_name', 
            'file_hash', 'status', 'total_rows', 'successful_rows', 'failed_rows', 
            'error_summary', 'uploaded_by', 'started_at', 'completed_at'
        ]

class RawRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = RawRecord
        fields = ['id', 'ingestion_job', 'source_row_number', 'raw_data', 'is_valid', 'validation_errors', 'created_at']
