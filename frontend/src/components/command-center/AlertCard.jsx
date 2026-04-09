/**
 * AlertCard - Display a single action item requiring attention
 *
 * Shows priority-based styling with title, description, and action buttons.
 */
import { Link } from 'react-router-dom';
import { XCircle, AlertTriangle, Clock, Info, Calendar, Zap, Cpu } from 'lucide-react';
import { formatRelativeTime } from '../../utils/formatting';

const priorityConfig = {
  1: {
    label: 'Critical',
    border: 'border-red-500/50',
    bg: 'bg-red-500/10',
    icon: <XCircle size={20} className="text-red-400" />,
    badge: 'bg-red-500/20 text-red-400'
  },
  2: {
    label: 'High',
    border: 'border-orange-500/50',
    bg: 'bg-orange-500/10',
    icon: <AlertTriangle size={20} className="text-orange-400" />,
    badge: 'bg-orange-500/20 text-orange-400'
  },
  3: {
    label: 'Medium',
    border: 'border-yellow-500/50',
    bg: 'bg-yellow-500/10',
    icon: <Clock size={20} className="text-yellow-400" />,
    badge: 'bg-yellow-500/20 text-yellow-400'
  },
  4: {
    label: 'Low',
    border: 'border-blue-500/50',
    bg: 'bg-blue-500/10',
    icon: <Info size={20} className="text-blue-400" />,
    badge: 'bg-blue-500/20 text-blue-400'
  }
};

const typeIcons = {
  blocked_po: <AlertTriangle size={16} />,
  overdue_so: <Clock size={16} />,
  due_today_so: <Calendar size={16} />,
  overrunning_op: <Zap size={16} />,
  idle_resource: <Cpu size={16} />,
};

export default function AlertCard({
  type,
  priority,
  title,
  description,
  entityType: _entityType,
  entityId: _entityId,
  entityCode: _entityCode,
  suggestedActions = [],
  createdAt,
  metadata: _metadata = {}
}) {
  const config = priorityConfig[priority] || priorityConfig[4];
  const typeIcon = typeIcons[type];

  return (
    <div className={`${config.bg} ${config.border} border rounded-lg p-4`}>
      <div className="flex items-start gap-3">
        <div className="flex-shrink-0 mt-0.5">
          {config.icon}
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              {typeIcon && (
                <span className="text-[var(--text-secondary)]">{typeIcon}</span>
              )}
              <h4 className="text-[var(--text-primary)] font-medium truncate">
                {title}
              </h4>
            </div>
            <span className={`${config.badge} text-xs px-2 py-0.5 rounded-full whitespace-nowrap`}>
              {config.label}
            </span>
          </div>

          <p className="text-[var(--text-secondary)] text-sm mt-1">
            {description}
          </p>

          {createdAt && (
            <p className="text-[var(--text-muted)] text-xs mt-2">
              {formatRelativeTime(createdAt)}
            </p>
          )}

          {suggestedActions.length > 0 && (
            <div className="flex flex-wrap gap-2 mt-3">
              {suggestedActions.map((action, idx) => (
                <Link
                  key={idx}
                  to={action.url}
                  className="text-sm px-3 py-1 bg-[var(--bg-elevated)] hover:bg-[var(--border-active)] text-[var(--text-secondary)] rounded transition-colors"
                >
                  {action.label}
                </Link>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
