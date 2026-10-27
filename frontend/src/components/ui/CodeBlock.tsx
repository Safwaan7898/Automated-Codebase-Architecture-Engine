import { useState } from 'react';
import { Copy, Check } from 'lucide-react';

export interface CodeBlockProps {
  code: string;
  language?: string;
  filename?: string;
  showLineNumbers?: boolean;
  className?: string;
}

export const CodeBlock = ({
  code,
  language = 'typescript',
  filename,
  showLineNumbers = true,
  className = ''
}: CodeBlockProps) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const lines = code.trim().split('\n');

  return (
    <div className={`rounded-xl border border-[var(--agencia-border)] bg-[var(--agencia-surface)] overflow-hidden font-mono text-xs ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-[var(--agencia-border)] bg-[var(--agencia-glass-border)]">
        <div className="flex items-center gap-2">
          <div className="flex gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-red-500/70" />
            <span className="w-2.5 h-2.5 rounded-full bg-yellow-500/70" />
            <span className="w-2.5 h-2.5 rounded-full bg-green-500/70" />
          </div>
          {filename && (
            <span className="text-[var(--agencia-text-muted)] text-[11px] ml-2">
              {filename}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {language && (
            <span className="text-[10px] uppercase font-bold tracking-widest text-[var(--agencia-text-muted)] bg-[var(--agencia-surface)] px-2 py-0.5 rounded border border-[var(--agencia-border)]">
              {language}
            </span>
          )}
          <button
            onClick={handleCopy}
            className="flex items-center gap-1 text-[11px] text-[var(--agencia-text-muted)] hover:text-[var(--agencia-text)] px-2 py-1 rounded hover:bg-[var(--agencia-surface)] transition-colors"
            title="Copy code"
          >
            {copied ? (
              <>
                <Check className="w-3.5 h-3.5 text-[var(--accent-text)]" />
                <span className="text-[var(--accent-text)] font-semibold">Copied</span>
              </>
            ) : (
              <>
                <Copy className="w-3.5 h-3.5" />
                <span>Copy</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Code Area */}
      <div className="p-4 overflow-x-auto text-[13px] leading-relaxed">
        <pre className="font-mono">
          {lines.map((line, idx) => (
            <div key={idx} className="flex hover:bg-[var(--agencia-glass-border)] -mx-4 px-4">
              {showLineNumbers && (
                <span className="w-8 shrink-0 text-right pr-4 select-none text-[var(--agencia-text-muted)] opacity-50">
                  {idx + 1}
                </span>
              )}
              <span className="text-[var(--agencia-text)] font-mono">{line || ' '}</span>
            </div>
          ))}
        </pre>
      </div>
    </div>
  );
};
