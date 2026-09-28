import { Controller, type Control } from 'react-hook-form';
import { Select } from '../../../shared/components/Select';
import { RuleOperandEditor } from './RuleOperandEditor';
import { OPERATOR_LABELS } from '../../../types/ruleSchema';
import type { RuleSchema, RuleOperator } from '../../../types/ruleSchema';
import type { RuleDraft } from '../../../types/rule';

export function RuleExpressionEditor({
    control,
    name,
    schema,
    onRemove,
}: {
    control: Control<RuleDraft>;
    name: string;
    schema: RuleSchema;
    onRemove?: () => void;
}) {
    return (
        <div className="expression-editor">
            <Controller
                control={control}
                name={`${name}.left.source` as never}
                render={({ field: srcField }) => (
                    <Controller
                        control={control}
                        name={`${name}.left.field` as never}
                        render={({ field: fieldField, fieldState }) => {
                            const fields =
                                srcField.value === 'ORDER' ? schema.orderFields : schema.executorFields;
                            const current = fields.find((f) => f.name === fieldField.value);

                            return (
                                <>
                                    {/* Источник: заявка / исполнитель */}
                                    <Select
                                        value={srcField.value}
                                        onChange={(e) => {
                                            srcField.onChange(e.target.value);
                                            fieldField.onChange('');
                                        }}
                                    >
                                        <option value="ORDER">Заявка</option>
                                        <option value="EXECUTOR">Исполнитель</option>
                                    </Select>

                                    {/* Поле */}
                                    <Select
                                        value={fieldField.value}
                                        onChange={(e) => fieldField.onChange(e.target.value)}
                                        invalid={!!fieldState.error}
                                    >
                                        <option value="">— поле —</option>
                                        {fields.map((f) => (
                                            <option key={f.name} value={f.name}>
                                                {f.label}
                                            </option>
                                        ))}
                                    </Select>

                                    {/* Оператор + правая часть — в одном Controller, чтобы оператор был доступен RuleOperandEditor */}
                                    <Controller
                                        control={control}
                                        name={`${name}.operator` as never}
                                        render={({ field: opField }) => (
                                            <>
                                                <Select
                                                    value={opField.value}
                                                    onChange={(e) =>
                                                        opField.onChange(e.target.value as RuleOperator)
                                                    }
                                                >
                                                    {(current?.allowedOperators ?? []).map((op) => (
                                                        <option key={op} value={op}>
                                                            {OPERATOR_LABELS[op]}
                                                        </option>
                                                    ))}
                                                </Select>
                                                <RuleOperandEditor
                                                    control={control}
                                                    name={`${name}.right`}
                                                    schema={schema}
                                                    fieldDef={current}
                                                    operator={opField.value as RuleOperator}
                                                />
                                            </>
                                        )}
                                    />
                                </>
                            );
                        }}
                    />
                )}
            />
            {onRemove && (
                <button type="button" onClick={onRemove} className="link-danger">
                    Удалить
                </button>
            )}
        </div>
    );
}