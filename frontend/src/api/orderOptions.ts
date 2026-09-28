import { apiClient } from './client';
import { useMockData } from './dataSource';
import { mockOrderOptions } from '../mocks/orderOptions';
import type { OrderOption } from '../types/order';
import type { RequestOptions } from '../types/api';

const delay = (ms: number) => new Promise((r) => setTimeout(r, ms));

export async function getOrderOptions(options?: RequestOptions): Promise<OrderOption[]> {
    if (useMockData) {
        await delay(200);
        return mockOrderOptions;
    }
    return apiClient.get('/orders/options', options);
}