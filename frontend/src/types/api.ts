export interface ApiError {
  code: string;
  message: string;
  status?: number;
  details?: Record<string, unknown>;
  fieldErrors?: Record<string, string>;
  traceId?: string;
}

export interface PaginationMeta {
  limit: number;
  offset: number;
  total: number;
}

export interface PaginatedResponse<T> {
  items: T[];
  pagination: PaginationMeta;
}

export interface RequestOptions {
  signal?: AbortSignal;
  timeoutMs?: number;
}
