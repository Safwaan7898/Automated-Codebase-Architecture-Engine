import { ShieldAlert, AlertTriangle, Info, CheckCircle2 } from 'lucide-react'

export type SeverityLevel = 'critical' | 'high' | 'medium' | 'low' | 'info'

export interface SeverityChipProps {
  severity: SeverityLevel | string
  label?: string
  className?: string
}

export function SeverityChip({ severity, label, className = '' }: SeverityChipProps) {
  const norm = (severity || 'low').toLowerCase()

  if (norm === 'critical' || norm === 'high') {
    return (
      <span
        className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold uppercase tracking-wider bg-[#FF2D20]/15 border border-[#FF2D20] text-[#B91C1C] dark:text-[#FF2D20] shadow-[0_0_10px_rgba(255,45,32,0.25)] ${className}`}
      >
        <ShieldAlert size={11} className="shrink-0" />
        <span>{label || norm}</span>
      </span>
    )
  }

  if (norm === 'medium') {
    return (
      <span
        className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold uppercase tracking-wider bg-[#F59E0B]/15 border border-[#F59E0B] text-[#92400e] dark:text-[#F59E0B] ${className}`}
      >
        <AlertTriangle size={11} className="shrink-0" />
        <span>{label || norm}</span>
      </span>
    )
  }

  if (norm === 'low') {
    return (
      <span
        className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold uppercase tracking-wider bg-[#C6F432]/15 border border-[#C6F432] text-[#0B0D0C] dark:text-[#C6F432] ${className}`}
      >
        <CheckCircle2 size={11} className="shrink-0" />
        <span>{label || norm}</span>
      </span>
    )
  }

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold uppercase tracking-wider bg-white/10 border border-[var(--border)] text-[var(--text-secondary)] ${className}`}
    >
      <Info size={11} className="shrink-0" />
      <span>{label || norm}</span>
    </span>
  )
}
