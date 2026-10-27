import React from 'react'

export const Footer: React.FC = () => {
  return (
    <footer className="relative bg-[#060606] border-t border-white/5 pt-20 pb-16 px-6 md:px-12 overflow-hidden select-none">
      {/* Decorative Massive Background Text (font-size: 18rem, color: white/5) at bottom right */}
      <div className="absolute right-0 bottom-0 pointer-events-none opacity-40 translate-y-8 select-none overflow-hidden">
        <span className="agencia-display text-[clamp(6rem,18vw,20rem)] text-white/[0.04] tracking-widest leading-none block text-right pr-4">
          AGENCIA
        </span>
      </div>

      <div className="relative z-10 max-w-7xl mx-auto flex flex-col md:flex-row items-start md:items-center justify-between gap-8">
        {/* Left: Copyright & Manifesto */}
        <div>
          <span className="font-display text-2xl tracking-widest text-white block mb-1">
            AGENCIA // ARCHLENS
          </span>
          <p className="text-xs uppercase tracking-widest text-white/40 font-mono">
            © 2026 AGENCIA ARCHLENS. ALL RIGHTS RESERVED. ARCHITECTURE AT SCALE.
          </p>
        </div>

        {/* Right: Utility Links with nav-link hover underline interaction */}
        <div className="flex flex-wrap items-center gap-8">
          <a
            href="#hero-primary-cta"
            className="agencia-nav-link text-xs uppercase tracking-widest font-mono text-white/60 hover:text-white"
          >
            Overview
          </a>
          <a
            href="#ingestion-section"
            className="agencia-nav-link text-xs uppercase tracking-widest font-mono text-white/60 hover:text-white"
          >
            Ingestion Pipeline
          </a>
          <a
            href="#graph-viewport"
            className="agencia-nav-link text-xs uppercase tracking-widest font-mono text-white/60 hover:text-white"
          >
            Topology View
          </a>
          <a
            href="#diagnostics-section"
            className="agencia-nav-link text-xs uppercase tracking-widest font-mono text-white/60 hover:text-white"
          >
            Diagnostics
          </a>
          <a
            href="#refactor-section"
            className="agencia-nav-link text-xs uppercase tracking-widest font-mono text-white/60 hover:text-white"
          >
            Refactoring
          </a>
          <a
            href="https://github.com"
            target="_blank"
            rel="noreferrer"
            className="agencia-nav-link text-xs uppercase tracking-widest font-mono text-blue-400 hover:text-blue-300"
          >
            GitHub
          </a>
        </div>
      </div>
    </footer>
  )
}
