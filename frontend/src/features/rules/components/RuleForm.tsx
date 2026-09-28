import { useForm, useFieldArray } from 'react-hook-form';
import { Button } from '../../../shared/components/Button';
import { Input } from '../../../shared/components/Input';
import { Switch } from '../../../shared/components/Switch';
import { FormField } from '../../../shared/components/form/FormField';
import { RuleExpressionEditor } from './RuleExpressionEditor';
import type { RuleDraft } from '../../../types/rule';
import type { RuleSchema } from '../../../types/ruleSchema';

const emptyExpression: RuleDraft['requirements'][number] = {
    left: { type: 'FIELD', source: 'ORDER', field: '' },
    operator: 'EQ',
    right: { type: 'CONSTANT', value: '' },
};

const emptyDraft: RuleDraft = {
    name: '',
    description: null,
    when: [],
    requirements: [emptyExpression],
    logic: 'AND',
    priority: 100,
    active: true,
};

export function RuleForm({
    schema,
    initial,
    onSubmit,
    onCancel,
    loading,
}: {
    schema: RuleSchema;
    initial?: RuleDraft;
    onSubmit: (draft: RuleDraft) => void;
    onCancel: () => void;
    loading?: boolean;
}) {
    const form = useForm<RuleDraft>({ defaultValues: initial ?? emptyDraft });
    const whenArray = useFieldArray({ control: form.control, name: 'when' });
    const reqArray = useFieldArray({ control: form.control, name: 'requirements' });

    const submit = form.handleSubmit((values) => {
        onSubmit({
            name: values.name,
            description: values.description || null,
            when: values.when,
            requirements: values.requirements,
            logic: values.logic,
            priority: values.priority,
            active: values.active,
        });
    });

    return (
        <form onSubmit={submit}>
            <FormField label="Название" required>
                <Input {...form.register('name', { required: true })} />
            </FormField>

            <FormField label="Описание">
                <Input {...form.register('description')} />
            </FormField>

            <section>
                <h3>When (условия применения)</h3>
                {whenArray.fields.map((f, i) => (
                    <RuleExpressionEditor
                        key={f.id}
                        control={form.control}
                        name={`when.${i}`}
                        schema={schema}
                        onRemove={() => whenArray.remove(i)}
                    />
                ))}
                <Button
                    type="button"
                    variant="secondary"
                    onClick={() => whenArray.append(emptyExpression)}
                >
                    Добавить условие
                </Button>
            </section>

            <section>
                <h3>Requirements (требования к кандидату)</h3>
                {reqArray.fields.map((f, i) => (
                    <RuleExpressionEditor
                        key={f.id}
                        control={form.control}
                        name={`requirements.${i}`}
                        schema={schema}
                        onRemove={reqArray.fields.length > 1 ? () => reqArray.remove(i) : undefined}
                    />
                ))}
                <Button
                    type="button"
                    variant="secondary"
                    onClick={() => reqArray.append(emptyExpression)}
                >
                    Добавить требование
                </Button>
            </section>

            <FormField label="Приоритет">
                <Input
                    type="number"
                    {...form.register('priority', { valueAsNumber: true, min: 0 })}
                />
            </FormField>

            <FormField label="Активность">
                <Switch
                    checked={form.watch('active')}
                    onChange={(v) => form.setValue('active', v)}
                />
            </FormField>

            <div className="dialog-actions">
                <Button type="button" variant="secondary" onClick={onCancel}>
                    Отмена
                </Button>
                <Button type="submit" loading={loading}>
                    Сохранить
                </Button>
            </div>
        </form>
    );
}
