import React from 'react'
import { Terminal, Database, Sparkles, GitBranch } from 'lucide-react'

export const ContentRevealSection: React.FC = () => {
  return (
    <section id="metrics-reveal-section" className="relative py-28 px-6 md:px-12 max-w-7xl mx-auto w-full border-t border-white/5">
      {/* Massive Text Reveal Mask Animation (font-size: 14rem / clamp, tracking: 0.2em) */}
      <div className="overflow-hidden mb-12">
        <h2 className="agencia-display text-[clamp(3.5rem,10.5vw,13.5rem)] text-white tracking-[0.16em] uppercase select-none text-reveal-mask">
          PRECISION TOPOLOGY
        </h2>
      </div>

      {/* Two-Column Editorial Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-start">
        {/* Left Column: Left-aligned text description (max-width: 448px, color: white/60) */}
        <div className="lg:col-span-7 max-w-[448px]">
          <span className="text-xs font-mono uppercase tracking-widest text-blue-400 block mb-3">
            01 // ARCHITECTURAL LEVEL-OF-DETAIL
          </span>
          <p className="text-white/60 text-base md:text-lg leading-relaxed mb-6 font-normal">
            Engineered for million-line codebases. Our hybrid WebGL force simulation dynamically computes
            betweenness centrality, isolates god modules, and highlights the blast radius of structural modifications in real-time.
          </p>
          <p className="text-white/40 text-xs md:text-sm font-mono leading-relaxed">
            By leveraging edge-bundling and adaptive level-of-detail culling at distant zoom coordinates, the visualization engine delivers a consistent 60 frames-per-second experience across graphs with over 5,000 nodes.
          </p>
        </div>

        {/* Right Column: Circular border links (48px x 48px) & specs */}
        <div className="lg:col-span-5 flex flex-col items-start lg:items-end justify-between h-full gap-8">
          <div className="flex items-center gap-4">
            <a
              href="https://github.com"
              target="_blank"
              rel="noreferrer"
              className="w-12 h-12 rounded-full border border-white/20 hover:border-white bg-white/5 hover:bg-white/10 flex items-center justify-center text-white/80 hover:text-white transition-[transform,colors] duration-200 hover:scale-105 will-change-transform"
              aria-label="GitHub Repository"
            >
              <GitBranch className="w-5 h-5 text-white/80" />
            </a>

            <a
              href="#ingestion-section"
              className="w-12 h-12 rounded-full border border-white/20 hover:border-white bg-white/5 hover:bg-white/10 flex items-center justify-center text-white/80 hover:text-white transition-[transform,colors] duration-200 hover:scale-105 will-change-transform"
              aria-label="CLI Integration"
            >
              <Terminal className="w-5 h-5" />
            </a>

            <a
              href="https://osv.dev"
              target="_blank"
              rel="noreferrer"
              className="w-12 h-12 rounded-full border border-white/20 hover:border-white bg-white/5 hover:bg-white/10 flex items-center justify-center text-white/80 hover:text-white transition-[transform,colors] duration-200 hover:scale-105 will-change-transform"
              aria-label="OSV.dev Vulnerabilities"
            >
              <Database className="w-5 h-5" />
            </a>

            <a
              href="#graph-viewport"
              className="w-12 h-12 rounded-full border border-blue-500/40 hover:border-blue-400 bg-blue-500/10 hover:bg-blue-500/20 flex items-center justify-center text-blue-400 hover:text-white transition-[transform,colors] duration-200 hover:scale-105 will-change-transform"
              aria-label="Launch 3D WebGL Graph"
            >
              <Sparkles className="w-5 h-5" />
            </a>
          </div>

          {/* Quick Specifications Tag Block */}
          <div className="text-left lg:text-right font-mono text-xs text-white/40 space-y-1">
            <div>CENTRALITY: PAGERANK + BETWEENNESS</div>
            <div>CLUSTERING: LOUVAIN MODULARITY</div>
            <div>CYCLE RESOLUTION: FEEDBACK ARC SET (FAS)</div>
            <div>PERFORMANCE TARGET: 60 FPS @ 5K+ NODES</div>
          </div>
        </div>
      </div>
    </section>
  )
}
