import hashlib
from django.db import transaction
from django.utils import timezone
from django.db.models import Q
from ..models import IngestionJob, RawRecord, DataSource
from core.models import Tenant
from .parser_sap import parse_sap_csv
from .parser_utility import parse_utility_csv
from .parser_travel import parse_travel_csv
from emissions.services.normalization import normalize_raw_record

def calculate_file_hash(file_bytes):
    sha256 = hashlib.sha256()
    sha256.update(file_bytes)
    return sha256.hexdigest()

def ingest_file(tenant: Tenant, data_source: DataSource, file_obj, uploaded_by: str):
    """
    Main orchestrator for file ingestion.
    Parses file, creates RawRecord objects, and triggers normalization.
    """
    # Read file contents
    file_bytes = file_obj.read()
    file_hash = calculate_file_hash(file_bytes)
    file_name = file_obj.name

    # Check for duplicate file within the same tenant
    duplicate_job = IngestionJob.objects.filter(
        tenant=tenant,
        file_hash=file_hash,
        status__in=[IngestionJob.Status.COMPLETED, IngestionJob.Status.COMPLETED_WITH_ERRORS]
    ).first()
    
    if duplicate_job:
        # Create a failed job with duplicate error details
        job = IngestionJob.objects.create(
            tenant=tenant,
            data_source=data_source,
            file_name=file_name,
            file_hash=file_hash,
            status=IngestionJob.Status.FAILED,
            error_summary=[{
                'row': 0,
                'field': 'file',
                'message': f'Duplicate file upload detected. This file was already ingested in Job: {duplicate_job.id}'
            }],
            uploaded_by=uploaded_by,
            started_at=timezone.now(),
            completed_at=timezone.now()
        )
        return job

    # Create ingestion job
    job = IngestionJob.objects.create(
        tenant=tenant,
        data_source=data_source,
        file_name=file_name,
        file_hash=file_hash,
        status=IngestionJob.Status.PROCESSING,
        uploaded_by=uploaded_by,
        started_at=timezone.now()
    )

    try:
        # 1. Parse file content
        content_str = file_bytes.decode('utf-8', errors='ignore')
        
        if data_source.source_type == DataSource.SourceType.SAP:
            parsed_rows, parse_errors = parse_sap_csv(content_str)
        elif data_source.source_type == DataSource.SourceType.UTILITY:
            parsed_rows, parse_errors = parse_utility_csv(content_str)
        elif data_source.source_type == DataSource.SourceType.TRAVEL:
            parsed_rows, parse_errors = parse_travel_csv(content_str)
        else:
            raise ValueError(f"Unknown data source type: {data_source.source_type}")

        total_rows = len(parsed_rows)
        job.total_rows = total_rows
        job.save()

        successful_rows = 0
        failed_rows = 0
        job_errors = []

        # 2. Iterate and save RawRecords & trigger normalization
        for parsed_row in parsed_rows:
            row_num = parsed_row['row_number']
            raw_data = parsed_row['raw_data']
            is_valid = parsed_row['is_valid']
            validation_errors = parsed_row['errors']

            with transaction.atomic():
                raw_rec = RawRecord.objects.create(
                    tenant=tenant,
                    ingestion_job=job,
                    source_row_number=row_num,
                    raw_data=raw_data,
                    is_valid=is_valid,
                    validation_errors=validation_errors
                )

                if is_valid:
                    # Ingest was successful at row level, trigger normalization
                    try:
                        # normalize_raw_record will create the EmissionRecord
                        normalize_raw_record(raw_rec, data_source)
                        successful_rows += 1
                    except Exception as norm_ex:
                        # Normalization failed (e.g. emission factor missing, calc error)
                        raw_rec.is_valid = False
                        norm_error = {'row': row_num, 'field': 'normalization', 'message': str(norm_ex)}
                        raw_rec.validation_errors = [norm_error]
                        raw_rec.save()
                        
                        failed_rows += 1
                        job_errors.append(norm_error)
                else:
                    # Parse level row errors
                    failed_rows += 1
                    for err in validation_errors:
                        job_errors.append({
                            'row': row_num,
                            'field': err.get('field', 'unknown'),
                            'message': err.get('message', 'Validation error')
                        })

        # Save parse-level general errors
        for err in parse_errors:
            if err.get('row') == 0: # General file level errors
                job_errors.append(err)

        # Update job stats
        job.successful_rows = successful_rows
        job.failed_rows = failed_rows
        job.error_summary = job_errors
        
        if failed_rows == 0:
            job.status = IngestionJob.Status.COMPLETED
        elif successful_rows > 0:
            job.status = IngestionJob.Status.COMPLETED_WITH_ERRORS
        else:
            job.status = IngestionJob.Status.FAILED

    except Exception as ex:
        job.status = IngestionJob.Status.FAILED
        job.error_summary = [{'row': 0, 'field': 'processing', 'message': f'Fatal ingestion error: {str(ex)}'}]

    job.completed_at = timezone.now()
    job.save()
    return job
