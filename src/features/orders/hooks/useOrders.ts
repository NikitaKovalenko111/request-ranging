import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { getOrder, getOrders } from '../../../api/orders';
import type { OrderFilters } from '../../../types/order';
import { env } from '../../../shared/config/env';
import { queryKeys } from '../../../shared/config/queryKeys';

export function useOrders(filters: OrderFilters) {
  return useQuery({ queryKey: queryKeys.orders(filters), queryFn: ({ signal }) => getOrders(filters, signal), refetchInterval: env.pollIntervalMs, placeholderData: keepPreviousData });
}

export function useOrder(id: number) {
  return useQuery({ queryKey: queryKeys.order(id), queryFn: ({ signal }) => getOrder(id, signal), refetchInterval: env.pollIntervalMs });
}

