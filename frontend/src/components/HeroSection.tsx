import React, { useEffect, useRef } from 'react'
import { ArrowRight, ShieldAlert, Cpu, GitFork, Activity } from 'lucide-react'

interface HeroSectionProps {
  onCtaClick: () => void
  onQuickLoadFlask: () => void
  onQuickLoadJava: () => void
  onQuickLoadVulnerable: () => void
  loading: boolean
}

export const HeroSection: React.FC<HeroSectionProps> = ({
  onCtaClick,
  onQuickLoadFlask,
  onQuickLoadJava,
  onQuickLoadVulnerable,
  loading,
}) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null)

  // Subtle interactive particle mesh background giving a luxury-brutalist high-contrast aesthetic
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    let animId: number
    let width = (canvas.width = window.innerWidth)
    let height = (canvas.height = window.innerHeight)

    const handleResize = () => {
      if (!canvas) return
      width = canvas.width = window.innerWidth
      height = canvas.height = window.innerHeight
    }
    window.addEventListener('resize', handleResize)

    // Generate node particles representing code topology
    const particles = Array.from({ length: 42 }, () => ({
      x: Math.random() * width,
      y: Math.random() * height,
      vx: (Math.random() - 0.5) * 0.4,
      vy: (Math.random() - 0.5) * 0.4,
      radius: Math.random() * 2 + 1,
      color: Math.random() > 0.85 ? '#ef4444' : Math.random() > 0.6 ? '#3b82f6' : '#ffffff',
    }))

    const render = () => {
      ctx.clearRect(0, 0, width, height)

      // Draw subtle grid lines
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.02)'
      ctx.lineWidth = 1
      const step = 80
      for (let x = 0; x < width; x += step) {
        ctx.beginPath()
        ctx.moveTo(x, 0)
        ctx.lineTo(x, height)
        ctx.stroke()
      }
      for (let y = 0; y < height; y += step) {
        ctx.beginPath()
        ctx.moveTo(0, y)
        ctx.lineTo(width, y)
        ctx.stroke()
      }

      // Update and draw particles
      particles.forEach((p, i) => {
        p.x += p.vx
        p.y += p.vy
        if (p.x < 0 || p.x > width) p.vx *= -1
        if (p.y < 0 || p.y > height) p.vy *= -1

        ctx.fillStyle = p.color
        ctx.globalAlpha = p.color === '#ef4444' ? 0.7 : 0.4
        ctx.beginPath()
        ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2)
        ctx.fill()

        // Connect nearby nodes
        for (let j = i + 1; j < particles.length; j++) {
          const p2 = particles[j]
          const dx = p.x - p2.x
          const dy = p.y - p2.y
          const dist = Math.sqrt(dx * dx + dy * dy)
          if (dist < 130) {
            ctx.beginPath()
            ctx.moveTo(p.x, p.y)
            ctx.lineTo(p2.x, p2.y)
            ctx.strokeStyle = p.color === '#ef4444' || p2.color === '#ef4444' 
              ? 'rgba(239, 68, 68, 0.25)' 
              : 'rgba(255, 255, 255, 0.08)'
            ctx.lineWidth = 0.8
            ctx.stroke()
          }
        }
      })

      ctx.globalAlpha = 1.0
      animId = requestAnimationFrame(render)
    }

    render()

    return () => {
      window.removeEventListener('resize', handleResize)
      cancelAnimationFrame(animId)
    }
  }, [])

  return (
    <section className="relative min-h-screen flex flex-col justify-between pt-32 pb-12 px-6 md:px-12 bg-[#060606] overflow-hidden">
      {/* Background Mesh (75% brightness) */}
      <canvas
        ref={canvasRef}
        className="absolute inset-0 w-full h-full pointer-events-none opacity-75"
      />

      {/* Spotlight Radial Gradient Overlay */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background: 'radial-gradient(circle at 50% 0%, rgba(255, 255, 255, 0.12) 0%, transparent 70%)',
        }}
      />

      {/* Hero Content */}
      <div className="relative z-10 max-w-7xl mx-auto w-full my-auto flex flex-col items-start justify-center">
        {/* Metric Badges Top Header */}
        <div className="flex flex-wrap items-center gap-3 mb-6">
          <span className="px-3 py-1 rounded-full bg-white/5 border border-white/10 text-white/70 font-mono text-xs uppercase tracking-widest flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-blue-500 animate-pulse" />
            AUTOMATED ARCHITECTURE ENGINE
          </span>
          <span className="px-3 py-1 rounded-full bg-red-500/10 border border-red-500/30 text-red-400 font-mono text-xs uppercase tracking-widest flex items-center gap-1.5">
            <ShieldAlert className="w-3.5 h-3.5" />
            AST SECURITY & SMELL AUDIT
          </span>
          <span className="px-3 py-1 rounded-full bg-white/5 border border-white/10 text-white/50 font-mono text-xs uppercase tracking-widest hidden sm:flex items-center gap-1.5">
            <Cpu className="w-3.5 h-3.5" />
            60FPS WEBGL FORCE ENGINE
          </span>
        </div>

        {/* Massive Display Heading (Agencia style: font-size 15rem / clamp) */}
        <h1 className="agencia-display text-[clamp(3.8rem,11.5vw,14.5rem)] text-white tracking-[0.02em] font-normal select-none mb-4 leading-[0.88]">
          CODEBASE<br />
          ARCHITECTURE<br />
          <span className="text-white [text-shadow:0_2px_24px_rgba(255,255,255,0.25)]">
            INTELLIGENCE
          </span>
        </h1>

        {/* Sub-heading in Inter */}
        <p className="max-w-2xl text-base md:text-xl text-white/65 font-normal leading-relaxed mb-10">
          High-performance force-directed topology, AST security diagnostics, cycle breakers,
          and simulated refactoring metrics for enterprise Python & Java codebases.
        </p>

        {/* CTA Button & Quick Launch Row */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-6 w-full sm:w-auto">
          {/* Large Primary Glassmorphic CTA Button */}
          <button
            id="hero-primary-cta"
            onClick={onCtaClick}
            disabled={loading}
            className="agencia-glass-btn flex items-center justify-between sm:justify-start gap-6 px-10 py-5 text-sm md:text-base font-mono uppercase tracking-widest text-white group cursor-pointer shadow-glass-luxury"
          >
            <span className="flex items-center gap-3 font-semibold">
              <Activity className="w-5 h-5 text-blue-400" />
              <span>{loading ? 'ANALYZING PIPELINE…' : 'INITIALIZE INGESTION'}</span>
            </span>
            <div className="w-9 h-9 rounded-full bg-white flex items-center justify-center text-black shadow-md transition-transform duration-300 group-hover:scale-105">
              <ArrowRight className="w-4 h-4 agencia-btn-icon transition-transform duration-300 group-hover:translate-x-1" />
            </div>
          </button>

          {/* Quick Demo Launchers */}
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs font-mono uppercase tracking-wider text-agencia-muted mr-1">
              Sample Repos:
            </span>
            <button
              onClick={onQuickLoadFlask}
              className="px-3.5 py-2 rounded-full bg-white/5 hover:bg-white/15 border border-white/10 text-xs font-mono text-white/80 hover:text-white transition-colors duration-150 flex items-center gap-1.5"
              title="Analyze Python Flask sample repository"
            >
              <GitFork className="w-3.5 h-3.5 text-blue-400" />
              Python Flask
            </button>
            <button
              onClick={onQuickLoadJava}
              className="px-3.5 py-2 rounded-full bg-white/5 hover:bg-white/15 border border-white/10 text-xs font-mono text-white/80 hover:text-white transition-colors duration-150 flex items-center gap-1.5"
              title="Analyze Java Spring sample repository"
            >
              <GitFork className="w-3.5 h-3.5 text-amber-400" />
              Java Spring
            </button>
            <button
              onClick={onQuickLoadVulnerable}
              className="px-3.5 py-2 rounded-full bg-red-500/10 hover:bg-red-500/25 border border-red-500/30 text-xs font-mono text-red-300 hover:text-red-200 transition-colors duration-150 flex items-center gap-1.5"
              title="Analyze vulnerable fixture repository with known security flaws and cycles"
            >
              <ShieldAlert className="w-3.5 h-3.5 text-red-400" />
              Vulnerable Fixtures
            </button>
          </div>
        </div>
      </div>

      {/* Horizontal Services Marquee in Bebas Neue (size 2xl, white/30) fading in from right */}
      <div className="relative z-10 w-full overflow-hidden border-t border-white/5 pt-8 mt-12">
        <div className="flex items-center gap-12 whitespace-nowrap agencia-display text-2xl md:text-3xl text-white/30 tracking-widest select-none">
          <span>FEEDBACK ARC SET HEURISTICS</span>
          <span>·</span>
          <span>LOUVAIN COMMUNITY CLUSTERING</span>
          <span>·</span>
          <span>AST SECURITY AUDITING</span>
          <span>·</span>
          <span>REAL-TIME BLAST RADIUS HIGHLIGHT</span>
          <span>·</span>
          <span>60FPS WEBGL FORCE TOPOLOGY</span>
          <span>·</span>
          <span>LIVE OSV.DEV CVE STREAMING</span>
          <span>·</span>
          <span>CYCLE BREAKING & INTERFACE INVERSION</span>
        </div>
      </div>
    </section>
  )
}
