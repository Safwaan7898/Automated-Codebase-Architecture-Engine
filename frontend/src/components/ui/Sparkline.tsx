export interface SparklineProps {
  data: number[];
  width?: number;
  height?: number;
  color?: string;
  fill?: boolean;
  className?: string;
}

export const Sparkline = ({
  data,
  width = 120,
  height = 36,
  color = 'var(--agencia-lime)',
  fill = true,
  className = ''
}: SparklineProps) => {
  if (!data || data.length < 2) {
    return <div style={{ width, height }} className={`inline-block ${className}`} />;
  }

  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min === 0 ? 1 : max - min;
  const padding = 4;

  const points = data.map((val, idx) => {
    const x = (idx / (data.length - 1)) * (width - padding * 2) + padding;
    const y = height - padding - ((val - min) / range) * (height - padding * 2);
    return `${x},${y}`;
  });

  const pathD = `M ${points.join(' L ')}`;
  const areaD = `${pathD} L ${width - padding},${height} L ${padding},${height} Z`;
  const gradId = `sparkline-grad-${Math.random().toString(36).substring(2, 9)}`;

  return (
    <svg
      width={width}
      height={height}
      className={`inline-block overflow-visible ${className}`}
      viewBox={`0 0 ${width} ${height}`}
    >
      <defs>
        <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.25" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      {fill && <path d={areaD} fill={`url(#${gradId})`} />}
      <path
        d={pathD}
        fill="none"
        stroke={color}
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      {/* End pulse dot */}
      {points.length > 0 && (
        <circle
          cx={points[points.length - 1].split(',')[0]}
          cy={points[points.length - 1].split(',')[1]}
          r="3"
          fill={color}
          className="animate-pulse"
        />
      )}
    </svg>
  );
};
