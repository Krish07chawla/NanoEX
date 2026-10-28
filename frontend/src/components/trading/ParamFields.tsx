import { Field, Input } from '../ui';
import type { StrategyType } from '../../types';

/** Renders one number input per strategy parameter, using the backend's param schema. */
export function ParamFields({
  type,
  values,
  onChange,
}: {
  type?: StrategyType;
  values: Record<string, number>;
  onChange: (v: Record<string, number>) => void;
}) {
  if (!type) return null;
  return (
    <div className="grid grid-cols-2 gap-3">
      {Object.entries(type.params).map(([name, spec]) => (
        <Field key={name} label={name.replace(/_/g, ' ')} hint={spec.description}>
          <Input
            type="number"
            min={spec.min}
            max={spec.max}
            step={spec.type === 'int' ? 1 : 0.01}
            value={values[name] ?? spec.default}
            onChange={(e) => onChange({ ...values, [name]: Number(e.target.value) })}
          />
        </Field>
      ))}
    </div>
  );
}

export function defaultsFor(type?: StrategyType): Record<string, number> {
  return type ? Object.fromEntries(Object.entries(type.params).map(([k, v]) => [k, v.default])) : {};
}
