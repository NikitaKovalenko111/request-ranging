import { Controller, type Control } from 'react-hook-form';
import { Select } from '../../../shared/components/Select';
import { Input } from '../../../shared/components/Input';
import { BooleanSelect } from '../../../shared/components/form/BooleanSelect';
import { EnumSelect } from '../../../shared/components/form/EnumSelect';
import { MultiValueInput } from '../../../shared/components/form/MultiValueInput';
import type { RuleSchema, RuleFieldDefinition, RuleOperator } from '../../../types/ruleSchema';
import type { RuleDraft, RuleExpression } from '../../../types/rule';

export function RuleOperandEditor({
    control,
    name,
    schema,
    fieldDef,
    operator,
}: {
    control: Control<RuleDraft>;
    name: string;
    schema: RuleSchema;
    fieldDef?: RuleFieldDefinition;
    operator?: RuleOperator;
}) {
    return (
        <Controller
            control={control}
            name={name as never}
            render={({ field }) => {
                const value = field.value as RuleExpression['right'];

                const needsArray =
                    operator === 'BETWEEN' || operator === 'IN' || operator === 'NOT_IN';

                const setType = (type: 'CONSTANT' | 'FIELD') => {
                    if (type === 'CONSTANT') {
                        field.onChange({ type: 'CONSTANT', value: needsArray ? [] : '' });
                    } else {
                        field.onChange({ type: 'FIELD', source: 'EXECUTOR', field: '' });
                    }
                };

                // Ветка FIELD
                if (value.type === 'FIELD') {
                    return (
                        <>
                            <Select value="FIELD" onChange={() => setType('CONSTANT')}>
                                <option value="FIELD">Поле</option>
                                <option value="CONSTANT">Константа</option>
                            </Select>
                            <Select
                                value={value.field}
                                onChange={(e) => field.onChange({ ...value, field: e.target.value })}
                            >
                                <option value="">— поле —</option>
                                {schema.executorFields.map((f) => (
                                    <option key={f.name} value={f.name}>
                                        {f.label}
                                    </option>
                                ))}
                            </Select>
                        </>
                    );
                }

                // Ветка CONSTANT + BETWEEN / IN / NOT_IN → MultiValueInput
                if (needsArray) {
                    return (
                        <>
                            <Select value="CONSTANT" onChange={() => setType('FIELD')}>
                                <option value="CONSTANT">Константа</option>
                                <option value="FIELD">Поле</option>
                            </Select>
                            <MultiValueInput
                                values={(value.value as Array<string | number>) ?? []}
                                onChange={(v) => field.onChange({ type: 'CONSTANT', value: v })}
                                minItems={operator === 'BETWEEN' ? 2 : 1}
                                maxItems={operator === 'BETWEEN' ? 2 : undefined}
                                numeric={fieldDef?.dataType === 'NUMBER'}
                            />
                        </>
                    );
                }

                // Ветка CONSTANT по типу поля
                const dt = fieldDef?.dataType;
                return (
                    <>
                        <Select value="CONSTANT" onChange={() => setType('FIELD')}>
                            <option value="CONSTANT">Константа</option>
                            <option value="FIELD">Поле</option>
                        </Select>
                        {dt === 'BOOLEAN' && (
                            <BooleanSelect
                                value={(value.value as boolean | null) ?? null}
                                onChange={(v) => field.onChange({ type: 'CONSTANT', value: v })}
                            />
                        )}
                        {dt === 'ENUM' && fieldDef?.options && (
                            <EnumSelect
                                value={value.value as string | number | null}
                                onChange={(v) => field.onChange({ type: 'CONSTANT', value: v })}
                                options={fieldDef.options}
                            />
                        )}
                        {dt === 'NUMBER' && (
                            <Input
                                type="number"
                                value={String(value.value ?? '')}
                                onChange={(e) =>
                                    field.onChange({ type: 'CONSTANT', value: Number(e.target.value) })
                                }
                            />
                        )}
                        {dt === 'STRING_ARRAY' && (
                            <MultiValueInput
                                values={(value.value as Array<string | number>) ?? []}
                                onChange={(v) => field.onChange({ type: 'CONSTANT', value: v })}
                            />
                        )}
                        {(dt === 'STRING' || dt === 'UUID' || !dt) && (
                            <Input
                                value={String(value.value ?? '')}
                                onChange={(e) =>
                                    field.onChange({ type: 'CONSTANT', value: e.target.value })
                                }
                            />
                        )}
                    </>
                );
            }}
        />
    );
}