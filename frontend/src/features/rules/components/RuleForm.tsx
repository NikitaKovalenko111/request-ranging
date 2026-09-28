import { useEffect } from 'react';
import { useForm, useFieldArray } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Button } from '../../../shared/components/Button';
import { Input } from '../../../shared/components/Input';
import { Switch } from '../../../shared/components/Switch';
import { FormField } from '../../../shared/components/form/FormField';
import { RuleExpressionEditor } from './RuleExpressionEditor';
import { ruleFormSchema, type RuleFormValues } from '../model/ruleForm.schema';
import type { RuleDraft, RuleExpression } from '../../../types/rule';
import type { RuleSchema } from '../../../types/ruleSchema';

const emptyExpression: RuleExpression = {
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
    serverFieldErrors,
}: {
    schema: RuleSchema;
    initial?: RuleDraft;
    onSubmit: (draft: RuleDraft) => void;
    onCancel: () => void;
    loading?: boolean;
    serverFieldErrors?: Record<string, string>;
}) {
    const form = useForm<RuleFormValues>({
        defaultValues: (initial ?? emptyDraft) as RuleFormValues,
        resolver: zodResolver(ruleFormSchema),
    });

    const whenArray = useFieldArray({ control: form.control, name: 'when' });
    const reqArray = useFieldArray({ control: form.control, name: 'requirements' });

    // Применяем server fieldErrors к форме
    useEffect(() => {
        if (!serverFieldErrors) return;
        Object.entries(serverFieldErrors).forEach(([path, message]) => {
            form.setError(path as never, { type: 'server', message });
        });
    }, [serverFieldErrors, form]);

    const submit = form.handleSubmit((values) => {
        onSubmit({
            ...values,
            description: values.description || null,
        } as RuleDraft);
    });

    return (
        <form onSubmit={submit} noValidate>
            <FormField
                label="Название"
                required
                error={form.formState.errors.name?.message}
            >
                <Input
                    {...form.register('name')}
                    invalid={!!form.formState.errors.name}
                />
            </FormField>

            <FormField label="Описание" error={form.formState.errors.description?.message}>
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
                {form.formState.errors.requirements?.message ? (
                    <div className="form-error" role="alert">
                        {form.formState.errors.requirements.message}
                    </div>
                ) : null}
            </section>

            <FormField
                label="Приоритет"
                error={form.formState.errors.priority?.message}
            >
                <Input
                    type="number"
                    {...form.register('priority', { valueAsNumber: true })}
                    invalid={!!form.formState.errors.priority}
                />
            </FormField>

            <FormField label="Активность">
                <Switch
                    checked={form.watch('active')}
                    onChange={(v) => form.setValue('active', v, { shouldDirty: true })}
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