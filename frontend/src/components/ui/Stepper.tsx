import { Fragment } from 'react';
import { Check } from 'lucide-react';

export interface StepperItem {
  title: string;
  description?: string;
}

export interface StepperProps {
  steps: StepperItem[];
  currentStep: number;
  direction?: 'horizontal' | 'vertical';
  className?: string;
}

export const Stepper = ({
  steps,
  currentStep,
  direction = 'horizontal',
  className = ''
}: StepperProps) => {
  return (
    <div
      className={`flex ${
        direction === 'horizontal' ? 'flex-row items-center justify-between w-full' : 'flex-col space-y-4'
      } ${className}`}
    >
      {steps.map((step, index) => {
        const isCompleted = index < currentStep;
        const isCurrent = index === currentStep;

        return (
          <Fragment key={index}>
            <div
              className={`flex ${
                direction === 'horizontal' ? 'flex-col items-center text-center' : 'flex-row items-start space-x-3'
              }`}
            >
              {/* Step circle indicator */}
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center font-mono text-xs font-bold transition-colors duration-200 ${
                  isCompleted
                    ? 'bg-[var(--agencia-lime)] text-[var(--agencia-obsidian)] shadow-[0_0_12px_rgba(198,244,50,0.3)]'
                    : isCurrent
                    ? 'border-2 border-[var(--agencia-lime)] text-[var(--accent-text)] bg-[var(--agencia-surface)]'
                    : 'border border-[var(--agencia-border)] text-[var(--agencia-text-muted)] bg-[var(--agencia-surface)]/50'
                }`}
              >
                {isCompleted ? <Check className="w-4 h-4 stroke-[3]" /> : index + 1}
              </div>

              {/* Step info */}
              <div className={`${direction === 'horizontal' ? 'mt-2' : ''}`}>
                <p
                  className={`text-xs font-heading font-medium tracking-wide ${
                    isCurrent
                      ? 'text-[var(--agencia-text)] font-semibold'
                      : isCompleted
                      ? 'text-[var(--agencia-text)]'
                      : 'text-[var(--agencia-text-muted)]'
                  }`}
                >
                  {step.title}
                </p>
                {step.description && (
                  <p className="text-[11px] text-[var(--agencia-text-muted)] mt-0.5 max-w-[120px]">
                    {step.description}
                  </p>
                )}
              </div>
            </div>

            {/* Connecting line */}
            {index < steps.length - 1 && (
              <div
                className={`${
                  direction === 'horizontal'
                    ? 'flex-1 h-[2px] mx-3'
                    : 'w-[2px] h-6 ml-4 my-1'
                } transition-colors duration-300 ${
                  index < currentStep ? 'bg-[var(--agencia-lime)]' : 'bg-[var(--agencia-border)]'
                }`}
              />
            )}
          </Fragment>
        );
      })}
    </div>
  );
};
