import { Search, SlidersHorizontal, X } from 'lucide-react';
import type { OrderFilters as Filters } from '../../../types/order';

export const emptyOrderFilters: Filters = {
  search: '', status: '', assignmentStatus: '', orderType: '', vip: '', hasParent: false,
  executorId: '', from: '', to: '', limit: 5, offset: 0, sort: 'createdAt', order: 'desc',
};

export function OrderFilters({ value, executors, onChange }: { value: Filters; executors: Array<{ id: number; name: string }>; onChange: (filters: Filters) => void }) {
  const update = <K extends keyof Filters>(key: K, next: Filters[K]) => onChange({ ...value, [key]: next, offset: key === 'offset' ? value.offset : 0 });
  const activeCount = [value.search, value.status, value.assignmentStatus, value.orderType, value.vip, value.hasParent, value.executorId, value.from, value.to].filter(Boolean).length;
  return <section className="filters expanded panel">
    <div className="filters-title"><SlidersHorizontal size={17} /><strong>Фильтры</strong>{activeCount > 0 && <span>{activeCount}</span>}</div>
    <label className="search-field"><Search size={17} /><span className="sr-only">Поиск</span><input placeholder="ID, тема или текст" value={value.search} onChange={(event) => update('search', event.target.value)} /></label>
    <select aria-label="Статус заявки" value={value.status} onChange={(event) => update('status', event.target.value as Filters['status'])}><option value="">Все статусы заявки</option><option value="processed">Обработана</option><option value="await">Ожидает</option><option value="accept">Принята</option><option value="reject">Отклонена</option></select>
    <select aria-label="Статус назначения" value={value.assignmentStatus} onChange={(event) => update('assignmentStatus', event.target.value as Filters['assignmentStatus'])}><option value="">Все назначения</option><option value="pending">Ожидание</option><option value="reserved">Резерв</option><option value="assigned">Назначена</option><option value="unassigned">Не назначена</option><option value="failed">Ошибка</option></select>
    <select aria-label="Тип заявки" value={value.orderType} onChange={(event) => update('orderType', event.target.value)}><option value="">Все типы</option><option>Проверка договора</option><option>Кредитный анализ</option><option>Повторная проверка</option><option>Консультация</option><option>Проверка сделки</option></select>
    <select aria-label="VIP" value={value.vip} onChange={(event) => update('vip', event.target.value as Filters['vip'])}><option value="">VIP и обычные</option><option value="true">Только VIP</option><option value="false">Без VIP</option></select>
    <select aria-label="Исполнитель" value={value.executorId} onChange={(event) => update('executorId', event.target.value)}><option value="">Все исполнители</option>{executors.map((executor) => <option value={executor.id} key={executor.id}>{executor.name}</option>)}</select>
    <label className="date-filter"><span>С</span><input type="date" value={value.from} onChange={(event) => update('from', event.target.value)} /></label>
    <label className="date-filter"><span>По</span><input type="date" value={value.to} onChange={(event) => update('to', event.target.value)} /></label>
    <select aria-label="Сортировка" value={`${value.sort}:${value.order}`} onChange={(event) => { const [sort, order] = event.target.value.split(':') as [Filters['sort'], Filters['order']]; onChange({ ...value, sort, order, offset: 0 }); }}><option value="createdAt:desc">Сначала новые</option><option value="createdAt:asc">Сначала старые</option><option value="id:desc">ID по убыванию</option><option value="processingTimeMs:desc">Долгие решения</option></select>
    <label className="check-filter"><input type="checkbox" checked={value.hasParent} onChange={(event) => update('hasParent', event.target.checked)} />Только повторные</label>
    {activeCount > 0 && <button className="button ghost" onClick={() => onChange(emptyOrderFilters)}><X size={15} />Сбросить</button>}
  </section>;
}
