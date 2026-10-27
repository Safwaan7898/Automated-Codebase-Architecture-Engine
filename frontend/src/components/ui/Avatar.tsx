export interface AvatarProps {
  name: string;
  src?: string;
  size?: 'sm' | 'md' | 'lg' | 'xl';
  status?: 'online' | 'busy' | 'pending' | 'offline';
  className?: string;
}

export const Avatar = ({
  name,
  src,
  size = 'md',
  status,
  className = ''
}: AvatarProps) => {
  const getInitials = (str: string) => {
    return str
      .split(' ')
      .map((part) => part[0])
      .filter(Boolean)
      .slice(0, 2)
      .join('')
      .toUpperCase();
  };

  const sizeStyles = {
    sm: 'w-7 h-7 text-xs',
    md: 'w-9 h-9 text-xs',
    lg: 'w-11 h-11 text-sm',
    xl: 'w-14 h-14 text-base'
  };

  const statusStyles = {
    online: 'bg-[var(--agencia-lime)]',
    busy: 'bg-[var(--agencia-red)]',
    pending: 'bg-[var(--agencia-amber)]',
    offline: 'bg-[var(--agencia-text-muted)]'
  };

  return (
    <div className={`relative inline-flex items-center justify-center shrink-0 ${className}`}>
      {src ? (
        <img
          src={src}
          alt={name}
          className={`${sizeStyles[size]} rounded-full object-cover border border-[var(--agencia-border)] shadow-sm`}
        />
      ) : (
        <div
          className={`${sizeStyles[size]} rounded-full bg-[var(--agencia-surface)] border border-[var(--agencia-border)] flex items-center justify-center font-heading font-bold text-[var(--accent-text)] select-none shadow-inner`}
        >
          {getInitials(name)}
        </div>
      )}

      {status && (
        <span
          className={`absolute bottom-0 right-0 w-2.5 h-2.5 rounded-full ring-2 ring-[var(--agencia-surface)] ${statusStyles[status]}`}
        />
      )}
    </div>
  );
};
