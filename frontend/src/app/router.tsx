import { Navigate, Route, Routes } from 'react-router-dom';
import { AppLayout } from '../shared/components/AppLayout';
import { DashboardPage } from '../features/dashboard/pages/DashboardPage';
import { OrdersPage } from '../features/orders/pages/OrdersPage';
import { OrderDetailsPage } from '../features/orders/pages/OrderDetailsPage';
import { ExecutorsPage } from '../features/executors/pages/ExecutorsPage';
import { RulesPage } from '../features/rules/pages/RulesPage';
import { NotFoundPage } from '../features/not-found/NotFoundPage';

export function AppRouter() {
  return <Routes><Route element={<AppLayout />}><Route index element={<Navigate to="/dashboard" replace />} /><Route path="dashboard" element={<DashboardPage />} /><Route path="orders" element={<OrdersPage />} /><Route path="orders/:id" element={<OrderDetailsPage />} /><Route path="executors" element={<ExecutorsPage />} /><Route path="rules" element={<RulesPage />} /></Route><Route path="*" element={<NotFoundPage />} /></Routes>;
}
