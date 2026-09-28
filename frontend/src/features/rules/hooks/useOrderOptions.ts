import { useQuery } from '@tanstack/react-query';
import { getOrderOptions } from '../../../api/orderOptions';

export function useOrderOptions() {
    return useQuery({
        queryKey: ['orders', 'options'],
        queryFn: ({ signal }) => getOrderOptions({ signal }),
        staleTime: 60_000,
    });
}