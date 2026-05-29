import axios from 'axios';
import type {
  DashboardSummary,
  DataSource,
  IngestionJob,
  EmissionRecord,
  EmissionRecordDetail,
  ReviewAction,
  PaginatedResponse,
  RecordFilters,
  AuditFilters,
  BulkReviewResult,
} from '../types';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '',
  headers: {
    'Content-Type': 'application/json',
  },
});

const TENANT = 'acme-corp';

export async function getDashboardSummary(): Promise<DashboardSummary> {
  const { data } = await api.get<DashboardSummary>(
    `/api/${TENANT}/dashboard/summary/`
  );
  return data;
}

export async function getDataSources(): Promise<DataSource[]> {
  const { data } = await api.get<DataSource[]>(
    `/api/${TENANT}/sources/`
  );
  return data;
}

export async function uploadFile(
  sourceId: string,
  file: File
): Promise<IngestionJob> {
  const formData = new FormData();
  formData.append('file', file);
  const { data } = await api.post<IngestionJob>(
    `/api/${TENANT}/sources/${sourceId}/upload/`,
    formData,
    {
      headers: { 'Content-Type': 'multipart/form-data' },
    }
  );
  return data;
}

export async function getIngestionJobs(): Promise<IngestionJob[]> {
  const { data } = await api.get<IngestionJob[]>(
    `/api/${TENANT}/jobs/`
  );
  return data;
}

export async function getIngestionJob(id: string): Promise<IngestionJob> {
  const { data } = await api.get<IngestionJob>(
    `/api/${TENANT}/jobs/${id}/`
  );
  return data;
}

export async function getEmissionRecords(
  params: RecordFilters
): Promise<PaginatedResponse<EmissionRecord>> {
  const queryParams: Record<string, string> = {};
  if (params.scope && params.scope.length > 0)
    queryParams.scope = params.scope.join(',');
  if (params.status && params.status.length > 0)
    queryParams.status = params.status.join(',');
  if (params.source_type && params.source_type.length > 0)
    queryParams.source_type = params.source_type.join(',');
  if (params.date_from) queryParams.date_from = params.date_from;
  if (params.date_to) queryParams.date_to = params.date_to;
  if (params.search) queryParams.search = params.search;
  if (params.page) queryParams.page = String(params.page);
  if (params.page_size) queryParams.page_size = String(params.page_size);

  const { data } = await api.get<PaginatedResponse<EmissionRecord>>(
    `/api/${TENANT}/records/`,
    { params: queryParams }
  );
  return data;
}

export async function getEmissionRecord(
  id: string
): Promise<EmissionRecordDetail> {
  const { data } = await api.get<EmissionRecordDetail>(
    `/api/${TENANT}/records/${id}/`
  );
  return data;
}

export async function reviewRecord(
  id: string,
  action: string,
  reason?: string,
  performedBy?: string
): Promise<EmissionRecord> {
  const { data } = await api.post<EmissionRecord>(
    `/api/${TENANT}/records/${id}/review/`,
    { action, reason, performed_by: performedBy }
  );
  return data;
}

export async function bulkReview(
  ids: string[],
  action: string,
  performedBy: string,
  reason?: string
): Promise<BulkReviewResult> {
  const { data } = await api.post<BulkReviewResult>(
    `/api/${TENANT}/records/bulk-review/`,
    { record_ids: ids, action, performed_by: performedBy, reason }
  );
  return data;
}

export async function getAuditTrail(
  params: AuditFilters
): Promise<PaginatedResponse<ReviewAction>> {
  const queryParams: Record<string, string> = {};
  if (params.action) queryParams.action = params.action;
  if (params.performed_by) queryParams.performed_by = params.performed_by;
  if (params.date_from) queryParams.date_from = params.date_from;
  if (params.date_to) queryParams.date_to = params.date_to;
  if (params.search) queryParams.search = params.search;
  if (params.page) queryParams.page = String(params.page);
  if (params.page_size) queryParams.page_size = String(params.page_size);

  const { data } = await api.get<PaginatedResponse<ReviewAction>>(
    `/api/${TENANT}/audit/`,
    { params: queryParams }
  );
  return data;
}

export default api;
