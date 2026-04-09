/**
 * SummaryCard - Display a single summary statistic
 *
 * Used in the Command Center to show aggregate counts.
 */
import { Link } from 'react-router-dom';

const variants = {
  default: {
    bg: 'bg-[var(--bg-elevated)]',
    text: 'text-[var(--text-secondary)]',
    value: 'text-[var(--text-primary)]'
  },
  success: {
    bg: '',
    bgColor: 'rgba(0, 200, 83, 0.12)',
    text: 'text-[var(--success)]',
    value: 'text-[var(--success)]'
  },
  warning: {
    bg: '',
    bgColor: 'rgba(238, 122, 8, 0.12)',
    text: 'text-[var(--warning)]',
    value: 'text-amber-300'
  },
  danger: {
    bg: '',
    bgColor: 'rgba(239, 68, 68, 0.12)',
    text: 'text-[var(--error)]',
    value: 'text-red-300'
  },
  info: {
    bg: '',
    bgColor: 'rgba(2, 109, 248, 0.12)',
    text: 'text-[var(--info)]',
    value: 'text-[var(--primary-light)]'
  }
};

export default function SummaryCard({
  label,
  value,
  subtitle,
  variant = 'default',
  href,
  onClick
}) {
  const colors = variants[variant] || variants.default;

  const content = (
    <div
      className={`
        ${colors.bg} rounded-xl p-4 border border-[var(--border-subtle)]
        ${(href || onClick) ? 'hover:border-[var(--border-active)] cursor-pointer transition-colors' : ''}
      `}
      style={colors.bgColor ? { backgroundColor: colors.bgColor } : undefined}
      onClick={onClick}
    >
      <div className={`text-sm font-medium ${colors.text}`}>
        {label}
      </div>
      <div className={`text-3xl font-bold mt-1 ${colors.value}`}>
        {value}
      </div>
      {subtitle && (
        <div className="text-xs text-[var(--text-muted)] mt-1">
          {subtitle}
        </div>
      )}
    </div>
  );

  if (href) {
    return <Link to={href}>{content}</Link>;
  }

  return content;
}
