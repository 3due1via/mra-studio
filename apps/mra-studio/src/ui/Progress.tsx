type Props = { value: number; label?: string; showValue?: boolean; tone?: "blue" | "green" | "gold" | "purple" };

export function MraProgress({ value, label, showValue = true, tone = "blue" }: Props) {
  const safeValue = Math.max(0, Math.min(100, Math.round(value)));
  return (
    <div className="mra-progress-block">
      {label || showValue ? <div className="mra-progress-label"><span>{label}</span>{showValue ? <strong>{safeValue}%</strong> : null}</div> : null}
      <div className={`mra-progress mra-progress-${tone}`} role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={safeValue}>
        <i style={{ width: `${safeValue}%` }} />
      </div>
    </div>
  );
}
