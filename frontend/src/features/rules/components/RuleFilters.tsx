import { Input } from '../../../shared/components/Input';
import { Select } from '../../../shared/components/Select';

export function RuleFilters({
    search,
    onSearchChange,
    active,
    onActiveChange,
}: {
    search: string;
    onSearchChange: (v: string) => void;
    active: boolean | undefined;
    onActiveChange: (v: boolean | undefined) => void;
}) {
    return (
        <div className="action-row">
            <Input
                placeholder="Поиск"
                value={search}
                onChange={(e) => onSearchChange(e.target.value)}
            />
            <Select
                value={String(active ?? '')}
                onChange={(e) =>
                    onActiveChange(e.target.value === '' ? undefined : e.target.value === 'true')
                }
            >
                <option value="">Все</option>
                <option value="true">Активные</option>
                <option value="false">Неактивные</option>
            </Select>
        </div>
    );
}