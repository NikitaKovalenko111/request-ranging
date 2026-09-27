import type { PaginatedResponse } from '../types/api';
import type { Order, OrderFilters, OrderOption } from '../types/order';
import { mockOrders } from '../mocks/orders';
import { mockDelay } from '../mocks/utils';
import { apiGet } from './client';
import { useMockData } from './dataSource';

export async function getOrders(filters: OrderFilters, signal?: AbortSignal): Promise<PaginatedResponse<Order>> {
  if (!useMockData) {
    const params = new URLSearchParams();
    Object.entries(filters).forEach(([key, value]) => { if (value !== '' && value !== false && value != null) params.set(key, String(value)); });
    return apiGet<PaginatedResponse<Order>>(`/orders?${params.toString()}`, signal);
  }
  const search = filters.search.trim().toLowerCase();
  const filtered = mockOrders.filter((order) =>
    (!search || String(order.id).includes(search) || order.text.toLowerCase().includes(search) || order.subject.toLowerCase().includes(search)) &&
    (!filters.status || order.status === filters.status) &&
    (!filters.assignmentStatus || order.assignmentStatus === filters.assignmentStatus) &&
    (!filters.orderType || order.orderType === filters.orderType) &&
    (!filters.vip || String(order.vip) === filters.vip) &&
    (!filters.hasParent || order.parentId !== null) &&
    (!filters.executorId || order.assignedExecutorId === Number(filters.executorId)) &&
    (!filters.from || new Date(order.createdAt) >= new Date(filters.from)) &&
    (!filters.to || new Date(order.createdAt) <= new Date(`${filters.to}T23:59:59.999`))
  );
  const sorted = [...filtered].sort((a, b) => {
    const aValue = filters.sort === 'createdAt' ? new Date(a.createdAt).getTime() : filters.sort === 'processingTimeMs' ? (a.processingTimeMs ?? -1) : a.id;
    const bValue = filters.sort === 'createdAt' ? new Date(b.createdAt).getTime() : filters.sort === 'processingTimeMs' ? (b.processingTimeMs ?? -1) : b.id;
    return (aValue - bValue) * (filters.order === 'asc' ? 1 : -1);
  });
  const items = sorted.slice(filters.offset, filters.offset + filters.limit);
  return mockDelay({ items, pagination: { limit: filters.limit, offset: filters.offset, total: filtered.length } }, signal);
}

export async function getOrderOptions(signal?: AbortSignal): Promise<{ items: OrderOption[] }> {
  if (!useMockData) return apiGet<{ items: OrderOption[] }>('/orders/options', signal);
  return mockDelay({ items: mockOrders.map((order) => ({ id: order.id, label: `#${order.id} · ${order.orderType}`, status: order.status, vip: order.vip })) }, signal, 180);
}

export async function getOrder(id: number, signal?: AbortSignal): Promise<Order> {
  if (!useMockData) return apiGet<Order>(`/orders/${id}`, signal);
  const order = mockOrders.find((item) => item.id === id);
  if (!order) throw { code: 'ORDER_NOT_FOUND', message: `Заявка ${id} не найдена`, status: 404 };
  return mockDelay(order, signal, 220);
}
