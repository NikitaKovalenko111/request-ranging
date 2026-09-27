import type { ApiError } from '../types/api';

export class ApiRequestError extends Error {
    readonly code: string;
    readonly status: number;
    readonly fieldErrors?: Record<string, string>;
    readonly traceId?: string;
    readonly details?: Record<string, unknown>;

    constructor(status: number, error: ApiError) {
        super(error.message);
        this.name = 'ApiRequestError';
        this.status = status;
        this.code = error.code;
        this.fieldErrors = error.fieldErrors;
        this.traceId = error.traceId;
        this.details = error.details;
    }
}

export function isApiError(value: unknown): value is ApiRequestError {
    return value instanceof ApiRequestError;
}