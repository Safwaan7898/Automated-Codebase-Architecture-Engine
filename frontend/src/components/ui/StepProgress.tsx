import { Check } from 'lucide-react'

export interface StepItem {
  id: string
  label: string
  description?: string
}

export interface StepProgressProps {
  steps: StepItem[]
  currentStepIndex: number
  className?: string
}

export function StepProgress({ steps, currentStepIndex, className = '' }: StepProgressProps) {
  return (
    <div className={`w-full flex items-center justify-between relative ${className}`}>
      {steps.map((step, idx) => {
        const isCompleted = idx < currentStepIndex
        const isCurrent = idx === currentStepIndex

        return (
          <div key={step.id} className="flex-1 flex flex-col items-center relative group">
            {/* Connector Line */}
            {idx > 0 && (
              <div
                className={`absolute top-4 -left-1/2 w-full h-0.5 -z-10 transition-colors duration-300 ${
                  idx <= currentStepIndex ? 'bg-[#C6F432]' : 'bg-[var(--border)]'
                }`}
              />
            )}
            <div
              className={`w-8 h-8 rounded-full flex items-center justify-center font-mono text-xs font-bold transition-colors duration-200 border ${
                isCompleted
                  ? 'bg-[#C6F432] border-[#C6F432] text-[#0B0D0C] shadow-[0_0_12px_rgba(198,244,50,0.4)]'
                  : isCurrent
                  ? 'bg-[var(--card-bg)] border-[#C6F432] text-[var(--accent-text)] dark:text-[#C6F432] shadow-[0_0_15px_rgba(198,244,50,0.5)] ring-2 ring-[#C6F432]/20'
                  : 'bg-[var(--input-bg)] border-[var(--border)] text-[var(--text-muted)]'
              }`}
            >
              {isCompleted ? <Check size={14} className="stroke-[3]" /> : idx + 1}
            </div>
            <span
              className={`text-[11px] font-['Space_Grotesk',sans-serif] font-bold tracking-wider uppercase mt-2 text-center ${
                isCurrent ? 'text-[var(--text-primary)]' : 'text-[var(--text-muted)]'
              }`}
            >
              {step.label}
            </span>
          </div>
        )
      })}
    </div>
  )
}
