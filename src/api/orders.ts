import type { PaginatedResponse } from '../types/api';
import type { Order, OrderFilters } from '../types/order';
import { mockOrders } from '../mocks/orders';
import { mockDelay } from '../mocks/utils';
import { apiGet } from './client';
import { useMockData } from './dataSource';

export async function getOrders(filters: OrderFilters, signal?: AbortSignal): Promise<PaginatedResponse<Order>> {
  if (!useMockData) {
    const params = new URLSearchParams();
    Object.entries(filters).forEach(([key, value]) => { if (value !== '' && value !== false) params.set(key, String(value)); });
    return apiGet<PaginatedResponse<Order>>(`/orders?${params.toString()}`, signal);
  }
  const idSearch = filters.id.trim();
  const items = mockOrders.filter((order) =>
    (!idSearch || String(order.id).includes(idSearch)) &&
    (!filters.status || order.status === filters.status) &&
    (!filters.assignmentStatus || order.assignmentStatus === filters.assignmentStatus) &&
    (!filters.orderType || order.orderType === filters.orderType) &&
    (!filters.vip || String(order.vip) === filters.vip) &&
    (!filters.parentOnly || order.parentId !== null)
  );
  return mockDelay({ items, pagination: { limit: 50, offset: 0, total: items.length } }, signal);
}

export async function getOrder(id: number, signal?: AbortSignal): Promise<Order> {
  if (!useMockData) return apiGet<Order>(`/orders/${id}`, signal);
  const order = mockOrders.find((item) => item.id === id);
  if (!order) throw { code: 'ORDER_NOT_FOUND', message: `Заявка ${id} не найдена`, status: 404 };
  return mockDelay(order, signal, 220);
}

