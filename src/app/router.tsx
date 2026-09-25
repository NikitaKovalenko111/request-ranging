import { Navigate, Route, Routes } from 'react-router-dom';
import { AppLayout } from '../shared/components/AppLayout';
import { DashboardPage } from '../features/dashboard/pages/DashboardPage';
import { OrdersPage } from '../features/orders/pages/OrdersPage';
import { OrderDetailsPage } from '../features/orders/pages/OrderDetailsPage';
import { PlaceholderPage } from '../features/placeholders/PlaceholderPage';
import { NotFoundPage } from '../features/not-found/NotFoundPage';

export function AppRouter() {
  return <Routes><Route element={<AppLayout />}><Route index element={<Navigate to="/dashboard" replace />} /><Route path="dashboard" element={<DashboardPage />} /><Route path="orders" element={<OrdersPage />} /><Route path="orders/:id" element={<OrderDetailsPage />} /><Route path="executors" element={<PlaceholderPage title="Исполнители" />} /><Route path="rules" element={<PlaceholderPage title="Правила" />} /></Route><Route path="*" element={<NotFoundPage />} /></Routes>;
}

