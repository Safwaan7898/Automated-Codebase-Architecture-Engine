import { motion, AnimatePresence } from 'framer-motion';
import { CheckCircle2, AlertTriangle, AlertOctagon, Info, X } from 'lucide-react';

export type ToastType = 'success' | 'warning' | 'error' | 'info';

export interface ToastProps {
  id: string;
  type: ToastType;
  title: string;
  message?: string;
  onClose: (id: string) => void;
}

const icons = {
  success: <CheckCircle2 className="w-5 h-5 text-[var(--accent-text)]" />,
  warning: <AlertTriangle className="w-5 h-5 text-[var(--agencia-amber)]" />,
  error: <AlertOctagon className="w-5 h-5 text-[var(--agencia-red)]" />,
  info: <Info className="w-5 h-5 text-[var(--agencia-text-muted)]" />
};

export const ToastItem = ({ id, type, title, message, onClose }: ToastProps) => {
  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 16, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: -10, scale: 0.9 }}
      transition={{ duration: 0.25, ease: [0.2, 0.8, 0.2, 1] }}
      className="flex items-start gap-3 p-4 min-w-[320px] max-w-md rounded-xl glass-card shadow-2xl border border-[var(--agencia-border)] backdrop-blur-xl"
    >
      <div className="shrink-0 mt-0.5">{icons[type]}</div>
      <div className="flex-1">
        <h4 className="font-heading font-semibold text-sm text-[var(--agencia-text)]">{title}</h4>
        {message && <p className="text-xs text-[var(--agencia-text-muted)] mt-1 font-sans">{message}</p>}
      </div>
      <button
        onClick={() => onClose(id)}
        className="shrink-0 p-1 rounded-lg text-[var(--agencia-text-muted)] hover:text-[var(--agencia-text)] hover:bg-[var(--agencia-glass-border)] transition-colors"
      >
        <X className="w-4 h-4" />
      </button>
    </motion.div>
  );
};

export interface ToastContainerProps {
  toasts: Array<Omit<ToastProps, 'onClose'>>;
  onClose: (id: string) => void;
}

export const ToastContainer = ({ toasts, onClose }: ToastContainerProps) => {
  return (
    <div className="fixed bottom-6 right-6 z-50 flex flex-col gap-2 pointer-events-none">
      <AnimatePresence>
        {toasts.map((toast) => (
          <div key={toast.id} className="pointer-events-auto">
            <ToastItem {...toast} onClose={onClose} />
          </div>
        ))}
      </AnimatePresence>
    </div>
  );
};
