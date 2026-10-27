import { Fragment, type ReactNode } from 'react';
import { ChevronRight, Home } from 'lucide-react';
import { Link } from 'react-router-dom';

export interface BreadcrumbItem {
  label: string;
  href?: string;
  icon?: ReactNode;
}

export interface BreadcrumbsProps {
  items: BreadcrumbItem[];
  showHome?: boolean;
  className?: string;
}

export const Breadcrumbs = ({
  items,
  showHome = true,
  className = ''
}: BreadcrumbsProps) => {
  return (
    <nav className={`flex items-center space-x-2 text-xs font-mono ${className}`} aria-label="Breadcrumb">
      {showHome && (
        <>
          <Link
            to="/dashboard"
            className="flex items-center text-[var(--agencia-text-muted)] hover:text-[var(--agencia-text)] transition-colors"
          >
            <Home className="w-3.5 h-3.5" />
          </Link>
          <ChevronRight className="w-3 h-3 text-[var(--agencia-text-muted)] opacity-40 shrink-0" />
        </>
      )}

      {items.map((item, index) => {
        const isLast = index === items.length - 1;

        return (
          <Fragment key={index}>
            <div className="flex items-center space-x-1.5">
              {item.icon && <span className="opacity-70">{item.icon}</span>}
              {isLast || !item.href ? (
                <span className="font-semibold text-[var(--agencia-text)]">
                  {item.label}
                </span>
              ) : (
                <Link
                  to={item.href}
                  className="text-[var(--agencia-text-muted)] hover:text-[var(--agencia-text)] transition-colors"
                >
                  {item.label}
                </Link>
              )}
            </div>
            {!isLast && (
              <ChevronRight className="w-3 h-3 text-[var(--agencia-text-muted)] opacity-40 shrink-0" />
            )}
          </Fragment>
        );
      })}
    </nav>
  );
};
