import { motion } from 'framer-motion'

export interface ScoreRingProps {
  score: number // 0 to 100
  size?: number
  strokeWidth?: number
  label?: string
  className?: string
}

export function ScoreRing({
  score,
  size = 120,
  strokeWidth = 8,
  label = 'HEALTH',
  className = '',
}: ScoreRingProps) {
  const radius = (size - strokeWidth * 2) / 2
  const circumference = 2 * Math.PI * radius
  const dashOffset = circumference - (score / 100) * circumference

  // Color logic: Red is reserved for < 50, amber for 50-74, lime for 75+
  const color =
    score >= 75 ? '#C6F432' : score >= 50 ? '#F59E0B' : '#FF2D20'

  return (
    <div
      className={`relative inline-flex items-center justify-center font-sans ${className}`}
      style={{ width: size, height: size }}
    >
      <svg width={size} height={size} className="transform -rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke="var(--border)"
          strokeWidth={strokeWidth}
          fill="none"
        />
        <motion.circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke={color}
          strokeWidth={strokeWidth}
          strokeDasharray={circumference}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset: dashOffset }}
          transition={{ duration: 1.2, ease: [0.2, 0.8, 0.2, 1] }}
          strokeLinecap="round"
          fill="none"
          style={{
            filter: `drop-shadow(0 0 8px ${color}80)`,
          }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
        <span
          className="font-mono font-bold leading-none"
          style={{ fontSize: size * 0.28, color }}
        >
          {score}
        </span>
        {label && (
          <span
            className="text-[var(--text-muted)] font-['Space_Grotesk'] font-bold uppercase tracking-widest mt-1"
            style={{ fontSize: size * 0.08 }}
          >
            {label}
          </span>
        )}
      </div>
    </div>
  )
}
