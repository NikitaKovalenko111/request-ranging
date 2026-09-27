import { useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useMockData } from '../../api/dataSource';
import { env } from '../config/env';

export function useDashboardRealtime() {
  const client = useQueryClient();
  useEffect(() => {
    if (useMockData || env.realtimeMode !== 'sse') return;
    const events = new EventSource(`${env.apiBaseUrl}/events/dashboard`);
    events.onmessage = () => { void client.invalidateQueries({ queryKey: ['dashboard'] }); };
    events.onerror = () => events.close();
    return () => events.close();
  }, [client]);
}
