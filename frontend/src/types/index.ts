export interface Tenant {
  id: string;
  name: string;
  slug: string;
}

export interface DataSource {
  id: string;
  name: string;
  source_type: 'sap' | 'utility' | 'travel';
  description: string;
  is_active: boolean;
}

export interface IngestionJob {
  id: string;
  data_source: DataSource;
  file_name: string;
  status: 'processing' | 'completed' | 'completed_with_errors' | 'failed';
  total_rows: number;
  successful_rows: number;
  failed_rows: number;
  error_summary: ErrorSummaryItem[];
  uploaded_by: string;
  started_at: string;
  completed_at: string | null;
}

export interface ErrorSummaryItem {
  row: number;
  field: string;
  message: string;
}

export interface EmissionRecord {
  id: string;
  scope: 1 | 2 | 3;
  category: string;
  description: string;
  activity_date: string;
  reporting_period_start: string | null;
  reporting_period_end: string | null;
  quantity_value: number;
  quantity_unit: string;
  original_quantity_value: number | null;
  original_quantity_unit: string;
  emission_factor_value: number | null;
  co2e_kg: number | null;
  co2e_tonnes: number | null;
  status: 'pending' | 'flagged' | 'reviewed' | 'approved' | 'rejected' | 'locked';
  flags: string[];
  analyst_notes: string;
  reviewed_by: string;
  reviewed_at: string | null;
  approved_by: string;
  approved_at: string | null;
  locked_at: string | null;
  data_source_name: string;
  data_source_type: string;
  raw_data: Record<string, unknown>;
  created_at: string;
}

export interface EmissionRecordDetail extends EmissionRecord {
  review_actions: ReviewAction[];
}

export interface ReviewAction {
  id: string;
  emission_record: string;
  action: string;
  from_status: string;
  to_status: string;
  performed_by: string;
  reason: string;
  changes: Record<string, unknown>;
  created_at: string;
}

export interface DashboardSummary {
  total_records: number;
  total_co2e_tonnes: number;
  by_scope: { scope: number; count: number; co2e_tonnes: number }[];
  by_status: { status: string; count: number }[];
  by_source: { source_type: string; count: number; co2e_tonnes: number }[];
  recent_jobs: IngestionJob[];
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface RecordFilters {
  scope?: number[];
  status?: string[];
  source_type?: string[];
  date_from?: string;
  date_to?: string;
  search?: string;
  page?: number;
  page_size?: number;
}

export interface AuditFilters {
  action?: string;
  performed_by?: string;
  date_from?: string;
  date_to?: string;
  search?: string;
  page?: number;
  page_size?: number;
}

export interface BulkReviewResult {
  successful_count: number;
  failed_count: number;
  errors: string[];
}
