import { describe, expect, it } from 'vitest';
import { getAssignmentByOrderId } from './assignments';
import { getDashboard } from './dashboard';
import { getOrders } from './orders';
import type { OrderFilters } from '../types/order';

const filters: OrderFilters = {
  search: '', status: '', assignmentStatus: '', orderType: '', vip: '', hasParent: false,
  executorId: '', from: '', to: '', limit: 5, offset: 0, sort: 'createdAt', order: 'desc',
};

describe('доменные потоки данных', () => {
  it('возвращает назначение и Decision Trace одним контрактом', async () => {
    const result = await getAssignmentByOrderId('1048');
    expect(result.assignment?.orderId).toBe('1048');
    expect(result.decisionTrace?.selectedExecutorId).toBe('28');
  });

  it('фильтрует повторные заявки и сохраняет пагинацию', async () => {
    const result = await getOrders({ ...filters, hasParent: true });
    expect(result.items.every((order) => order.parentId !== null)).toBe(true);
    expect(result.pagination.limit).toBe(5);
  });

  it('поддерживает пустой mock-сценарий Dashboard', async () => {
    const result = await getDashboard({ bucket: 'minute' }, 'empty');
    expect(result.timeline).toEqual([]);
    expect(result.latestAssignments).toEqual([]);
  });

  it('возвращает контролируемую ошибку mock Dashboard', async () => {
    await expect(getDashboard({ bucket: 'minute' }, 'error')).rejects.toMatchObject({ code: 'MOCK_DASHBOARD_ERROR' });
  });
});

