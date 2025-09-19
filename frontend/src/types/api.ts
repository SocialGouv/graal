export type JobStatus = 'queued' | 'running' | 'completed' | 'failed' | 'timeout';

export interface JobProgress {
  status: JobStatus;
  percent: number;
  message: string | null;
  started_at: string;
  updated_at: string;
}

export interface ProcessJobResponse {
  job_id: string;
  status: JobStatus;
  message: string;
}

export interface JobStatusResponse {
  job_id: string;
  status: JobStatus;
  percent: number;
  message: string | null;
  started_at: string;
  updated_at: string;
}

export interface ResultsPreviewResponse {
  job_id: string;
  preview: AmendmentResult[];
  total_rows: number;
}

export interface ApiError {
  detail: string;
  status_code: number;
}

export interface AmendmentResult {
  [key: string]: string | number | null | undefined;
  // Common fields that we expect
  numero?: string;
  auteur?: string;
  objet?: string;
  dispositif?: string;
  sort?: string;
  avis_gouvernement?: string;
  // Add more fields as needed based on the actual GRAAL output
}
