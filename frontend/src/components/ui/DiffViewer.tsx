import { Plus, Minus } from 'lucide-react';

export interface DiffViewerProps {
  diffText: string;
  filename?: string;
  oldVersion?: string;
  newVersion?: string;
  className?: string;
}

export const DiffViewer = ({
  diffText,
  filename,
  oldVersion,
  newVersion,
  className = ''
}: DiffViewerProps) => {
  const lines = diffText.trim().split('\n');

  let oldLineNum = 1;
  let newLineNum = 1;

  const parsedLines = lines.map((line, idx) => {
    let type: 'add' | 'del' | 'meta' | 'normal' = 'normal';
    let currentOld: number | string = '';
    let currentNew: number | string = '';

    if (line.startsWith('@@')) {
      type = 'meta';
    } else if (line.startsWith('+') && !line.startsWith('+++')) {
      type = 'add';
      currentNew = newLineNum++;
    } else if (line.startsWith('-') && !line.startsWith('---')) {
      type = 'del';
      currentOld = oldLineNum++;
    } else if (line.startsWith('+++') || line.startsWith('---')) {
      type = 'meta';
    } else {
      type = 'normal';
      currentOld = oldLineNum++;
      currentNew = newLineNum++;
    }

    return { raw: line, type, currentOld, currentNew, idx };
  });

  const additions = parsedLines.filter((l) => l.type === 'add').length;
  const deletions = parsedLines.filter((l) => l.type === 'del').length;

  return (
    <div className={`rounded-xl border border-[var(--agencia-border)] bg-[var(--agencia-surface)] overflow-hidden font-mono text-xs ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-[var(--agencia-border)] bg-[var(--agencia-glass-border)]">
        <div className="flex items-center gap-3">
          <span className="font-semibold text-[var(--agencia-text)]">{filename || 'Unified Diff'}</span>
          {(oldVersion || newVersion) && (
            <span className="text-[11px] text-[var(--agencia-text-muted)]">
              {oldVersion} → {newVersion}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2 text-xs">
          <span className="flex items-center gap-0.5 text-[var(--accent-text)] font-semibold">
            <Plus className="w-3.5 h-3.5" /> {additions}
          </span>
          <span className="flex items-center gap-0.5 text-[var(--agencia-red)] font-semibold">
            <Minus className="w-3.5 h-3.5" /> {deletions}
          </span>
        </div>
      </div>

      {/* Diff Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <tbody>
            {parsedLines.map(({ raw, type, currentOld, currentNew, idx }) => {
              let bg = 'hover:bg-[var(--agencia-glass-border)]';
              let textColor = 'text-[var(--agencia-text)]';
              const gutterBg = 'text-[var(--agencia-text-muted)] opacity-40';

              if (type === 'add') {
                bg = 'bg-lime-500/10 hover:bg-lime-500/15';
                textColor = 'text-[var(--accent-text)]';
              } else if (type === 'del') {
                bg = 'bg-red-500/10 hover:bg-red-500/15';
                textColor = 'text-red-700 dark:text-[var(--agencia-red)]';
              } else if (type === 'meta') {
                bg = 'bg-blue-500/5 text-blue-700 dark:text-blue-400 font-semibold';
                textColor = 'text-blue-700 dark:text-blue-400';
              }

              return (
                <tr key={idx} className={`leading-6 transition-colors ${bg}`}>
                  <td className={`w-10 text-right pr-3 pl-2 select-none font-mono text-[11px] ${gutterBg}`}>
                    {currentOld}
                  </td>
                  <td className={`w-10 text-right pr-3 pl-2 select-none font-mono text-[11px] ${gutterBg}`}>
                    {currentNew}
                  </td>
                  <td className="w-6 text-center select-none font-mono font-bold">
                    {type === 'add' ? '+' : type === 'del' ? '-' : ' '}
                  </td>
                  <td className={`pl-2 pr-4 font-mono whitespace-pre ${textColor}`}>
                    {raw.replace(/^[+\- ]/, '') || ' '}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};
