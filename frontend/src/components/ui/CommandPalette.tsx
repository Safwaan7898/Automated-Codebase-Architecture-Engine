import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, Compass, FileText, Activity, Shield, Sparkles, Terminal, CornerDownLeft } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export interface CommandItem {
  id: string;
  title: string;
  category: 'Navigation' | 'Actions' | 'Tools' | 'Settings';
  icon?: React.ReactNode;
  shortcut?: string;
  onSelect: () => void;
}

export interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
  customActions?: CommandItem[];
}

export const CommandPalette: React.FC<CommandPaletteProps> = ({
  isOpen,
  onClose,
  customActions = []
}) => {
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();

  const defaultActions: CommandItem[] = [
    {
      id: 'nav-dashboard',
      title: 'Go to Dashboard',
      category: 'Navigation',
      icon: <Activity className="w-4 h-4 text-[var(--accent-text)]" />,
      shortcut: 'G D',
      onSelect: () => navigate('/dashboard')
    },
    {
      id: 'nav-graph',
      title: 'Open Topology Graph (2D/3D)',
      category: 'Navigation',
      icon: <Compass className="w-4 h-4 text-cyan-400" />,
      shortcut: 'G T',
      onSelect: () => navigate('/graph')
    },
    {
      id: 'nav-security',
      title: 'View Security Diagnostics & Smells',
      category: 'Navigation',
      icon: <Shield className="w-4 h-4 text-[var(--agencia-red)]" />,
      shortcut: 'G S',
      onSelect: () => navigate('/security')
    },
    {
      id: 'nav-refactor',
      title: 'Inspect Refactoring Proposals',
      category: 'Navigation',
      icon: <Sparkles className="w-4 h-4 text-[var(--accent-text)]" />,
      shortcut: 'G R',
      onSelect: () => navigate('/refactoring')
    },
    {
      id: 'nav-reports',
      title: 'Generate Full Diagnostic Report',
      category: 'Navigation',
      icon: <FileText className="w-4 h-4 text-amber-400" />,
      shortcut: 'G P',
      onSelect: () => navigate('/reports')
    },
    {
      id: 'nav-design-system',
      title: 'Design System Showcase',
      category: 'Tools',
      icon: <Terminal className="w-4 h-4 text-purple-400" />,
      onSelect: () => navigate('/design-system')
    }
  ];

  const allActions = [...defaultActions, ...customActions];

  const filtered = allActions.filter((item) =>
    item.title.toLowerCase().includes(query.toLowerCase()) ||
    item.category.toLowerCase().includes(query.toLowerCase())
  );

  useEffect(() => {
    if (isOpen) {
      setQuery('');
      setSelectedIndex(0);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isOpen]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!isOpen) return;

      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedIndex((prev) => (prev + 1) % (filtered.length || 1));
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedIndex((prev) => (prev - 1 + (filtered.length || 1)) % (filtered.length || 1));
      } else if (e.key === 'Enter') {
        e.preventDefault();
        if (filtered[selectedIndex]) {
          filtered[selectedIndex].onSelect();
          onClose();
        }
      } else if (e.key === 'Escape') {
        e.preventDefault();
        onClose();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, filtered, selectedIndex, onClose]);

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-start justify-center pt-24 px-4">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black/70 backdrop-blur-md"
          />

          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: -20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: -20 }}
            transition={{ duration: 0.2, ease: [0.2, 0.8, 0.2, 1] }}
            className="relative w-full max-w-xl rounded-2xl glass-card border border-[var(--agencia-border)] shadow-2xl overflow-hidden z-10"
          >
            {/* Search Input Bar */}
            <div className="flex items-center gap-3 px-4 py-3.5 border-b border-[var(--agencia-border)] bg-[var(--agencia-surface)]">
              <Search className="w-5 h-5 text-[var(--agencia-text-muted)] shrink-0" />
              <input
                ref={inputRef}
                type="text"
                value={query}
                onChange={(e) => {
                  setQuery(e.target.value);
                  setSelectedIndex(0);
                }}
                placeholder="Type a command or search sections..."
                className="w-full bg-transparent text-sm text-[var(--agencia-text)] placeholder-[var(--placeholder)] focus:outline-none font-sans"
              />
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-[var(--agencia-border)] text-[var(--agencia-text-muted)]">
                ESC
              </span>
            </div>

            {/* List */}
            <div className="max-h-80 overflow-y-auto p-2 space-y-1">
              {filtered.length === 0 ? (
                <div className="py-8 text-center text-xs text-[var(--agencia-text-muted)]">
                  No commands match &quot;{query}&quot;
                </div>
              ) : (
                filtered.map((item, idx) => {
                  const isSelected = idx === selectedIndex;
                  return (
                    <div
                      key={item.id}
                      onClick={() => {
                        item.onSelect();
                        onClose();
                      }}
                      onMouseEnter={() => setSelectedIndex(idx)}
                      className={`flex items-center justify-between px-3 py-2.5 rounded-xl cursor-pointer transition-colors ${
                        isSelected
                          ? 'bg-[var(--agencia-lime)] text-[var(--agencia-obsidian)] font-semibold'
                          : 'text-[var(--agencia-text)] hover:bg-[var(--agencia-glass-border)]'
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        <span className={isSelected ? 'text-[var(--agencia-obsidian)]' : ''}>
                          {item.icon}
                        </span>
                        <div className="text-xs">
                          <span>{item.title}</span>
                          <span
                            className={`ml-2 text-[10px] uppercase font-mono px-1.5 py-0.5 rounded ${
                              isSelected
                                ? 'bg-black/10 text-black'
                                : 'bg-[var(--agencia-surface)] text-[var(--agencia-text-muted)] border border-[var(--agencia-border)]'
                            }`}
                          >
                            {item.category}
                          </span>
                        </div>
                      </div>

                      <div className="flex items-center gap-2">
                        {item.shortcut && (
                          <span
                            className={`text-[10px] font-mono px-1.5 py-0.5 rounded ${
                              isSelected ? 'bg-black/10 text-black' : 'text-[var(--agencia-text-muted)]'
                            }`}
                          >
                            {item.shortcut}
                          </span>
                        )}
                        {isSelected && <CornerDownLeft className="w-3.5 h-3.5" />}
                      </div>
                    </div>
                  );
                })
              )}
            </div>

            {/* Footer */}
            <div className="px-4 py-2 bg-[var(--agencia-surface)]/80 border-t border-[var(--agencia-border)] flex items-center justify-between text-[11px] font-mono text-[var(--agencia-text-muted)]">
              <span>Navigate with ↑ / ↓</span>
              <span>Execute with ↵</span>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
};
