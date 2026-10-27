import React from 'react'
import { ArrowUpRight, Radio, FileText, Download } from 'lucide-react'

interface NavbarProps {
  onAnalyzeClick: () => void
  onSectionClick: (section: 'hero' | 'input' | 'graph' | 'reveal' | 'diagnostics' | 'refactor') => void
  hasActiveGraph: boolean
  onOpenReports: () => void
}

export const Navbar: React.FC<NavbarProps> = ({
  onAnalyzeClick,
  onSectionClick,
  hasActiveGraph,
  onOpenReports,
}) => {
  return (
    <header className="fixed top-6 left-0 right-0 z-50 flex items-center justify-between px-6 md:px-12 max-w-7xl mx-auto pointer-events-none">
      {/* Zone 1: Logo */}
      <div className="flex items-center gap-3 pointer-events-auto cursor-pointer" onClick={() => onSectionClick('hero')}>
        <div className="w-10 h-10 rounded-full bg-white flex items-center justify-center text-black font-display text-xl tracking-wider font-bold shadow-glass-luxury transition-transform duration-300 hover:scale-105">
          AG
        </div>
        <div className="flex flex-col">
          <span className="font-display text-2xl tracking-widest text-white leading-none">
            AGENCIA <span className="text-white/40">{'//'}</span> ARCHLENS
          </span>
          <span className="text-[10px] tracking-wider text-agencia-muted font-mono uppercase flex items-center gap-1.5 mt-0.5">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
            ENGINE v2.4 · 60FPS TOPOLOGY
          </span>
        </div>
      </div>

      {/* Zone 2: Central Pill Navigation */}
      <nav className="hidden lg:flex items-center gap-6 px-7 py-3 agencia-nav-pill pointer-events-auto">
        <button
          onClick={() => onSectionClick('hero')}
          className="agencia-nav-link text-xs uppercase tracking-widest font-mono font-medium"
        >
          OVERVIEW
        </button>
        <button
          onClick={() => onSectionClick('input')}
          className="agencia-nav-link text-xs uppercase tracking-widest font-mono font-medium"
        >
          INGESTION
        </button>
        {hasActiveGraph && (
          <button
            onClick={() => onSectionClick('graph')}
            className="agencia-nav-link text-xs uppercase tracking-widest font-mono font-medium text-blue-400 font-semibold"
          >
            TOPOLOGY GRAPH
          </button>
        )}
        <button
          onClick={() => onSectionClick('reveal')}
          className="agencia-nav-link text-xs uppercase tracking-widest font-mono font-medium"
        >
          METRICS & LOD
        </button>
        <button
          onClick={() => onSectionClick('diagnostics')}
          className="agencia-nav-link text-xs uppercase tracking-widest font-mono font-medium"
        >
          SECURITY & SMELLS
        </button>
        <button
          onClick={() => onSectionClick('refactor')}
          className="agencia-nav-link text-xs uppercase tracking-widest font-mono font-medium"
        >
          REFACTOR
        </button>
        <button
          id="nav-reports-link-btn"
          onClick={onOpenReports}
          className="agencia-nav-link text-xs uppercase tracking-widest font-mono font-medium text-emerald-400 hover:text-emerald-300 flex items-center gap-1.5"
        >
          <FileText className="w-3.5 h-3.5" />
          <span>REPORTS</span>
        </button>
      </nav>

      {/* Zone 3: Right Glassmorphic CTA Buttons */}
      <div className="flex items-center gap-3 pointer-events-auto">
        <button
          id="nav-download-report-btn"
          onClick={onOpenReports}
          className="hidden sm:flex items-center gap-2 px-4 py-2 rounded-full bg-white/10 hover:bg-white/20 border border-white/15 text-xs font-mono uppercase tracking-wider text-white transition-colors duration-150 shadow-glass"
          title="Download architecture & security report (PDF, HTML, JSON)"
        >
          <Download className="w-3.5 h-3.5 text-blue-400" />
          <span>Download Report</span>
        </button>

        <button
          id="nav-cta-btn"
          onClick={onAnalyzeClick}
          className="agencia-glass-btn flex items-center gap-3 pl-5 pr-2 py-2 text-xs font-mono uppercase tracking-wider text-white group"
        >
          <span className="flex items-center gap-2">
            <Radio className="w-3.5 h-3.5 text-blue-400 animate-pulse" />
            <span>{hasActiveGraph ? 'NEW INGESTION' : 'LAUNCH ENGINE'}</span>
          </span>
          <div className="w-8 h-8 rounded-full bg-white flex items-center justify-center text-black transition-transform duration-300 group-hover:scale-105">
            <ArrowUpRight className="w-4 h-4 agencia-btn-icon transition-transform duration-300 group-hover:translate-x-1" />
          </div>
        </button>
      </div>
    </header>
  )
}
