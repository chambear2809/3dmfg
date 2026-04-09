import { Link } from "react-router-dom";

const ChevronIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
  </svg>
);

const SkeletonPulse = ({ className = "" }) => (
  <div className={`animate-pulse bg-[var(--border-subtle)] rounded ${className}`} />
);

/**
 * Reusable StatCard component for displaying metrics across admin pages.
 *
 * Brand-aligned color scheme (BLB3D blue #026DF8 / orange #EE7A08):
 * - primary: Brand blue gradient
 * - secondary: Brand orange/accent gradient
 * - success: Green (positive metrics)
 * - warning: Amber/yellow (caution)
 * - danger: Red (needs attention)
 * - neutral: Gray/white (default)
 *
 * Supports two variants:
 * - "gradient" (default): Dashboard-style with gradient background and optional icon
 * - "simple": Flat card with colored value text
 *
 * Optional `to` prop makes the card a clickable link.
 */

const colorClasses = {
  gradient: {
    primary: "from-blue-600/20 to-blue-400/5 border-blue-500/30",
    secondary: "from-amber-600/20 to-orange-500/5 border-amber-500/30",
    success: "from-green-600/20 to-green-600/5 border-green-500/30",
    warning: "from-amber-600/20 to-amber-600/5 border-amber-500/30",
    danger: "from-red-600/20 to-red-600/5 border-red-500/30",
    neutral: "from-gray-600/20 to-gray-600/5 border-gray-500/30",
    emerald: "from-green-600/20 to-green-600/5 border-green-500/30",
    cyan: "from-blue-600/20 to-blue-400/5 border-blue-500/30",
    green: "from-green-600/20 to-green-600/5 border-green-500/30",
    orange: "from-amber-600/20 to-orange-500/5 border-amber-500/30",
    red: "from-red-600/20 to-red-600/5 border-red-500/30",
    blue: "from-blue-600/20 to-blue-400/5 border-blue-500/30",
    purple: "from-purple-600/20 to-purple-600/5 border-purple-500/30",
    yellow: "from-amber-600/20 to-amber-600/5 border-amber-500/30",
    white: "from-gray-600/20 to-gray-600/5 border-gray-500/30",
  },
  simple: {
    primary: "text-[var(--primary-light)]",
    secondary: "text-[var(--accent)]",
    success: "text-green-400",
    warning: "text-amber-400",
    danger: "text-red-400",
    neutral: "text-[var(--text-primary)]",
    emerald: "text-green-400",
    cyan: "text-[var(--primary-light)]",
    green: "text-green-400",
    orange: "text-[var(--accent)]",
    red: "text-red-400",
    blue: "text-[var(--primary-light)]",
    purple: "text-purple-400",
    yellow: "text-amber-400",
    white: "text-[var(--text-primary)]",
  },
};

export default function StatCard({
  title,
  value,
  subtitle,
  color = "white",
  icon,
  variant = "gradient",
  to,
  onClick,
  active = false,
  loading = false,
}) {
  const Wrapper = to ? Link : "div";
  const wrapperProps = to
    ? { to, className: "block" }
    : {};
  const isClickable = to || onClick;

  if (variant === "simple") {
    const baseClasses = "bg-[var(--bg-card)] border rounded-xl p-4";
    const borderClasses = active ? "border-[var(--primary)]/50 bg-[var(--primary)]/10" : "border-[var(--border-subtle)]";
    const hoverClasses = isClickable && !loading ? "hover:border-[var(--border-active)] hover:bg-[var(--bg-elevated)]/50 transition-all cursor-pointer" : "";

    return (
      <Wrapper {...wrapperProps}>
        <div
          className={`${baseClasses} ${borderClasses} ${hoverClasses}`}
          onClick={loading ? undefined : onClick}
          role={onClick && !loading ? "button" : undefined}
          tabIndex={onClick && !loading ? 0 : undefined}
          onKeyDown={onClick && !loading ? (e) => e.key === 'Enter' && onClick() : undefined}
        >
          <div className="flex items-start justify-between">
            <div className="flex-1">
              {loading ? (
                <>
                  <SkeletonPulse className="h-4 w-20 mb-2" />
                  <SkeletonPulse className="h-8 w-16" />
                  {subtitle && <SkeletonPulse className="h-3 w-24 mt-2" />}
                </>
              ) : (
                <>
                  <p className="text-[var(--text-secondary)] text-sm">{title}</p>
                  <p className={`text-2xl font-bold ${colorClasses.simple[color] || colorClasses.simple.white}`}>
                    {value}
                  </p>
                  {subtitle && <p className="text-[var(--text-muted)] text-xs mt-1">{subtitle}</p>}
                </>
              )}
            </div>
            {isClickable && !loading && (
              <div className="text-[var(--text-muted)]">
                <ChevronIcon />
              </div>
            )}
          </div>
        </div>
      </Wrapper>
    );
  }

  const baseClasses = `bg-gradient-to-br ${colorClasses.gradient[color] || colorClasses.gradient.white} border rounded-xl p-6`;
  const hoverClasses = to && !loading ? "hover:scale-[1.02] hover:shadow-glow transition-all cursor-pointer" : "";

  return (
    <Wrapper {...wrapperProps}>
      <div className={`${baseClasses} ${hoverClasses}`}>
        <div className="flex items-start justify-between">
          <div className="flex-1">
            {loading ? (
              <>
                <SkeletonPulse className="h-4 w-24 mb-2" />
                <SkeletonPulse className="h-9 w-20 mt-1" />
                {subtitle && <SkeletonPulse className="h-3 w-28 mt-2" />}
              </>
            ) : (
              <>
                <p className="text-[var(--text-secondary)] text-sm font-medium">{title}</p>
                <p className="text-3xl font-bold text-[var(--text-primary)] mt-1">{value}</p>
                {subtitle && <p className="text-[var(--text-muted)] text-xs mt-1">{subtitle}</p>}
              </>
            )}
          </div>
          <div className="flex items-center gap-2">
            {icon && !loading && <div className="text-[var(--text-muted)]">{icon}</div>}
            {to && !loading && (
              <div className="text-[var(--text-muted)]">
                <ChevronIcon />
              </div>
            )}
          </div>
        </div>
      </div>
    </Wrapper>
  );
}
