import React, { useState, useEffect, useRef } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { useTheme } from '../contexts/ThemeContext';
import {
  Sun,
  Moon,
  Laptop,
  ArrowRight,
  GitBranch,
  FolderArchive,
  FileCode,
  ShieldAlert,
  ChevronDown,
  Terminal
} from 'lucide-react';
import { Button } from '../components/ui/Button';

// Mini Interactive Canvas Dependency Graph
const HeroMiniGraph: React.FC = () => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animationFrameId: number;
    let width = (canvas.width = canvas.parentElement?.clientWidth || 600);
    let height = (canvas.height = canvas.parentElement?.clientHeight || 400);

    const handleResize = () => {
      if (!canvas || !canvas.parentElement) return;
      width = canvas.width = canvas.parentElement.clientWidth;
      height = canvas.height = canvas.parentElement.clientHeight;
    };
    window.addEventListener('resize', handleResize);

    const nodes = [
      { id: '1', name: 'AppRouter', x: width * 0.2, y: height * 0.3, vx: 0.2, vy: 0.15, radius: 8, isRed: false },
      { id: '2', name: 'AuthService', x: width * 0.45, y: height * 0.2, vx: -0.18, vy: 0.25, radius: 10, isRed: false },
      { id: '3', name: 'GraphEngine', x: width * 0.55, y: height * 0.65, vx: 0.22, vy: -0.2, radius: 12, isRed: false },
      { id: '4', name: 'TarjanSCC', x: width * 0.75, y: height * 0.35, vx: -0.15, vy: -0.18, radius: 9, isRed: false },
      { id: '5', name: 'CycleVulnerability', x: width * 0.35, y: height * 0.7, vx: 0.12, vy: 0.14, radius: 11, isRed: true }, // PULSES RED
      { id: '6', name: 'ReportWorker', x: width * 0.8, y: height * 0.75, vx: -0.1, vy: 0.16, radius: 8, isRed: false },
    ];

    const edges = [
      [0, 1],
      [1, 2],
      [2, 3],
      [2, 4],
      [4, 1], // Cycle edge!
      [3, 5],
    ];

    let mouseX = width / 2;
    let mouseY = height / 2;

    const handleMouseMove = (e: MouseEvent) => {
      const rect = canvas.getBoundingClientRect();
      mouseX = e.clientX - rect.left;
      mouseY = e.clientY - rect.top;
    };
    canvas.addEventListener('mousemove', handleMouseMove);

    let pulse = 0;

    const render = () => {
      pulse += 0.04;
      ctx.clearRect(0, 0, width, height);
      const isLight = document.documentElement.getAttribute('data-theme') === 'light';

      // Draw Edges
      edges.forEach(([fromIdx, toIdx]) => {
        const from = nodes[fromIdx];
        const to = nodes[toIdx];
        const isCycleEdge = (fromIdx === 4 && toIdx === 1) || (fromIdx === 2 && toIdx === 4);

        ctx.beginPath();
        ctx.moveTo(from.x, from.y);
        ctx.lineTo(to.x, to.y);

        if (isCycleEdge) {
          ctx.strokeStyle = 'rgba(255, 45, 32, 0.6)';
          ctx.lineWidth = 1.5;
          ctx.setLineDash([4, 4]);
        } else {
          ctx.strokeStyle = isLight ? 'rgba(63, 98, 18, 0.4)' : 'rgba(198, 244, 50, 0.25)';
          ctx.lineWidth = 1;
          ctx.setLineDash([]);
        }
        ctx.stroke();
      });

      // Update and Draw Nodes
      nodes.forEach((node) => {
        // Drift
        node.x += node.vx;
        node.y += node.vy;

        if (node.x < 30 || node.x > width - 30) node.vx *= -1;
        if (node.y < 30 || node.y > height - 30) node.vy *= -1;

        // Subtle mouse reaction
        const dx = mouseX - node.x;
        const dy = mouseY - node.y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < 120) {
          node.x -= (dx / dist) * 0.6;
          node.y -= (dy / dist) * 0.6;
        }

        ctx.setLineDash([]);
        if (node.isRed) {
          // Pulsing Red Node for Cyclic Vulnerability
          const glowRadius = node.radius + Math.sin(pulse) * 4;
          ctx.beginPath();
          ctx.arc(node.x, node.y, Math.max(2, glowRadius + 6), 0, Math.PI * 2);
          ctx.fillStyle = 'rgba(255, 45, 32, 0.2)';
          ctx.fill();

          ctx.beginPath();
          ctx.arc(node.x, node.y, node.radius, 0, Math.PI * 2);
          ctx.fillStyle = '#FF2D20';
          ctx.fill();
          ctx.strokeStyle = '#FFFFFF';
          ctx.lineWidth = 1.5;
          ctx.stroke();
        } else {
          // Standard Lime / White Glass Nodes
          ctx.beginPath();
          ctx.arc(node.x, node.y, node.radius, 0, Math.PI * 2);
          ctx.fillStyle = '#C6F432';
          ctx.fill();
          ctx.strokeStyle = 'rgba(255, 255, 255, 0.4)';
          ctx.lineWidth = 1;
          ctx.stroke();
        }

        // Label
        const isLight = document.documentElement.getAttribute('data-theme') === 'light';
        ctx.font = '10px JetBrains Mono, monospace';
        ctx.fillStyle = node.isRed ? '#FF2D20' : (isLight ? '#0F172A' : 'rgba(255, 255, 255, 0.7)');
        ctx.fillText(node.name, node.x + 12, node.y + 4);
      });

      animationFrameId = requestAnimationFrame(render);
    };

    render();

    return () => {
      window.removeEventListener('resize', handleResize);
      canvas.removeEventListener('mousemove', handleMouseMove);
      cancelAnimationFrame(animationFrameId);
    };
  }, []);

  return <canvas ref={canvasRef} className="w-full h-full cursor-crosshair" />;
};

export const WelcomePage: React.FC = () => {
  const { theme, setTheme } = useTheme();
  const navigate = useNavigate();
  const [activeFaq, setActiveFaq] = useState<number | null>(null);
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);

  const faqs = [
    {
      q: 'Does ArchLens execute or compile my codebase?',
      a: 'Never. ArchLens uses pure Tree-sitter Abstract Syntax Tree (AST) static analysis. Your code is parsed into tokens and grammatical structures without being executed, ensuring 100% security.'
    },
    {
      q: 'How are circular dependencies surfaced?',
      a: 'We execute Tarjan’s Strongly Connected Components (SCC) algorithm in O(V + E) time. Every cyclic recursion is mapped into an explicit dependency chain and marked with reserved red indicators.'
    },
    {
      q: 'What input formats and repositories are supported?',
      a: 'You can analyze public/private Git repositories (GitHub, GitLab, Bitbucket), compressed archives (ZIP, TAR, TAR.GZ), raw multi-file directories, or pasted snippets.'
    },
    {
      q: 'How does the role-based security model function?',
      a: 'We enforce 7 strictly isolated roles (ADMIN, ENGINEERING_MANAGER, SENIOR_DEVELOPER, DEVELOPER, SECURITY_ANALYST, QA_ENGINEER, VIEWER) with cryptographic JWT rotation and backend API gates.'
    }
  ];

  return (
    <div className="min-h-screen bg-[var(--agencia-bg)] text-[var(--agencia-text)] selection:bg-[var(--agencia-lime)] selection:text-[var(--agencia-obsidian)] transition-colors duration-300">
      {/* ── Fixed Sticky Glass Navbar ─────────────────────────────────────────────── */}
      <header className="sticky top-0 z-50 backdrop-blur-xl bg-[var(--agencia-bg)]/80 border-b border-[var(--agencia-border)] px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          {/* Left: Brand */}
          <Link to="/" className="flex items-center gap-3 group">
            <div className="w-9 h-9 rounded-xl bg-[var(--agencia-lime)] flex items-center justify-center text-[var(--agencia-obsidian)] font-display font-black text-xl shadow-[0_0_20px_rgba(198,244,50,0.3)] transition-transform group-hover:scale-105">
              A
            </div>
            <div className="flex flex-col">
              <span className="font-display text-2xl font-bold tracking-wider text-[var(--agencia-text)]">
                ARCHLENS
              </span>
              <span className="text-[9px] font-mono tracking-widest text-[var(--agencia-text-muted)] uppercase -mt-1">
                Architecture Visualizer
              </span>
            </div>
          </Link>

          {/* Center Pill Menu */}
          <nav className="hidden md:flex items-center gap-6 px-6 py-2 rounded-full border border-[var(--agencia-border)] bg-[var(--agencia-surface)]/80 backdrop-blur-xl">
            {[
              { label: 'INGESTION', href: '/ingestion' },
              { label: 'TOPOLOGY', href: '/graph' },
              { label: 'DIAGNOSTICS', href: '/security' },
              { label: 'REFACTORING', href: '/refactor' },
              { label: 'DESIGN SYSTEM', href: '/design-system' }
            ].map((link) => (
              <Link
                key={link.label}
                to={link.href}
                className="text-xs font-mono font-medium tracking-wider text-[var(--agencia-text-muted)] hover:text-[var(--accent-text)] transition-colors"
              >
                {link.label}
              </Link>
            ))}
          </nav>

          {/* Right: Theme Toggle & Sign in / Get started */}
          <div className="flex items-center gap-3">
            {/* Theme Toggle */}
            <div className="flex items-center p-1 rounded-full border border-[var(--agencia-border)] bg-[var(--agencia-surface)]">
              <button
                onClick={() => setTheme('light')}
                className={`p-1.5 rounded-full transition-colors ${
                  theme === 'light'
                    ? 'bg-[var(--agencia-lime)] text-[var(--agencia-obsidian)]'
                    : 'text-[var(--agencia-text-muted)] hover:text-[var(--agencia-text)]'
                }`}
                title="Light Theme"
              >
                <Sun className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={() => setTheme('dark')}
                className={`p-1.5 rounded-full transition-colors ${
                  theme === 'dark'
                    ? 'bg-[var(--agencia-lime)] text-[var(--agencia-obsidian)]'
                    : 'text-[var(--agencia-text-muted)] hover:text-[var(--agencia-text)]'
                }`}
                title="Dark Theme"
              >
                <Moon className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={() => setTheme('system')}
                className={`p-1.5 rounded-full transition-colors ${
                  theme === 'system'
                    ? 'bg-[var(--agencia-lime)] text-[var(--agencia-obsidian)]'
                    : 'text-[var(--agencia-text-muted)] hover:text-[var(--agencia-text)]'
                }`}
                title="System Theme"
              >
                <Laptop className="w-3.5 h-3.5" />
              </button>
            </div>

            <Link to="/login">
              <Button variant="ghost" size="sm">Sign In</Button>
            </Link>
            <Link to="/register">
              <Button variant="primary" size="sm">Get Started</Button>
            </Link>
          </div>
        </div>
      </header>

      {/* ── Marquee Ticker ────────────────────────────────────────────────────────── */}
      <div className="w-full border-b border-[var(--agencia-border)] bg-[var(--agencia-surface)]/50 py-2 overflow-hidden select-none">
        <div className="flex gap-8 whitespace-nowrap animate-marquee text-[11px] font-mono uppercase tracking-[0.2em] text-[var(--agencia-text-muted)]">
          <span className="text-[var(--accent-text)] font-bold">⚡ REAL-TIME AST INGESTION</span>
          <span>{'//'}</span>
          <span>TARJAN STRONGLY CONNECTED COMPONENTS</span>
          <span>{'//'}</span>
          <span>No placeholder data in your analysis results</span>
          <span>{'//'}</span>
          <span>MULTI-LANGUAGE JAVA & PYTHON PARSING</span>
          <span>{'//'}</span>
          <span>DEEP DEPENDENCY BLAST RADIUS</span>
          <span>{'//'}</span>
          <span className="text-[var(--agencia-red)] font-bold">RESERVED RED HIGH RISK PROTECTION</span>
        </div>
      </div>

      {/* ── Hero Section with Live Mini Interactive Graph ─────────────────────────── */}
      <section className="relative overflow-hidden py-16 md:py-24 px-6">
        {/* Radial Spotlight Gradient */}
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[400px] bg-gradient-to-b from-[var(--agencia-lime)]/10 to-transparent blur-3xl pointer-events-none" />

        <div className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
          {/* Left Hero Text */}
          <div className="lg:col-span-7 space-y-6">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-[var(--agencia-border)] bg-[var(--agencia-surface)] text-xs font-mono text-[var(--accent-text)]">
              <span className="w-2 h-2 rounded-full bg-[var(--agencia-lime)] animate-pulse" />
              AUTONOMOUS CODEBASE ARCHITECTURE INTELLIGENCE
            </div>

            <h1 className="font-display text-6xl sm:text-7xl lg:text-8xl font-black uppercase tracking-tight text-[var(--agencia-text)] leading-[0.9]">
              VISUALIZE.
              <br />
              <span className="text-[var(--accent-text)]">DECOUPLE.</span>
              <br />
              REFACTOR.
            </h1>

            <p className="max-w-xl text-base text-[var(--agencia-text-muted)] font-sans leading-relaxed">
              ArchLens statically decompiles complex repositories into interactive topological dependency graphs. Surface cyclic deadlocks, detect AST security vulnerabilities, and generate automated refactoring roadmaps with live verification.
            </p>

            <div className="flex flex-wrap items-center gap-4 pt-4">
              <Link to="/register">
                <Button variant="primary" size="lg" className="px-8 shadow-[0_0_30px_rgba(198,244,50,0.3)]">
                  Launch Ingestion <ArrowRight className="w-4 h-4 ml-2" />
                </Button>
              </Link>
              <Button variant="secondary" size="lg" onClick={() => navigate('/graph')}>
                Explore 3D Topology
              </Button>
            </div>
          </div>

          {/* Right Live Mini Dependency Graph Card */}
          <div className="lg:col-span-5 relative">
            <div className="relative h-[380px] rounded-2xl glass-card border border-[var(--agencia-border)] overflow-hidden shadow-2xl flex flex-col">
              <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--agencia-border)] bg-[var(--agencia-surface)]/80">
                <div className="flex items-center gap-2">
                  <div className="flex gap-1.5">
                    <span className="w-2.5 h-2.5 rounded-full bg-red-500/80" />
                    <span className="w-2.5 h-2.5 rounded-full bg-yellow-500/80" />
                    <span className="w-2.5 h-2.5 rounded-full bg-green-500/80" />
                  </div>
                  <span className="text-[11px] font-mono text-[var(--agencia-text-muted)] ml-2">
                    live_telemetry_graph.canvas (illustrative example)
                  </span>
                </div>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[var(--agencia-red)]/10 text-[var(--agencia-red)] font-semibold border border-[var(--agencia-red)]/30">
                  1 CYCLIC NODE DETECTED (illustrative example)
                </span>
              </div>

              {/* Interactive Canvas */}
              <div className="flex-1 relative">
                <HeroMiniGraph />
                <div className="absolute bottom-3 left-4 right-4 flex items-center justify-between text-[10px] font-mono text-[var(--agencia-text-muted)] bg-[var(--agencia-surface)]/80 backdrop-blur-md px-3 py-1.5 rounded-lg border border-[var(--agencia-border)]">
                  <span>Mouse over to drift entities</span>
                  <span className="text-[var(--accent-text)]">6 Nodes • 6 Edges</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── Section (a): 'Drop Anything' Bento Grid ───────────────────────────────── */}
      <section className="py-20 px-6 border-t border-[var(--agencia-border)] bg-[var(--agencia-surface)]/20">
        <div className="max-w-7xl mx-auto space-y-12">
          <div className="text-center max-w-2xl mx-auto space-y-3">
            <span className="text-xs font-mono uppercase tracking-widest text-[var(--accent-text)]">
              UNIVERSAL INPUT ENGINE
            </span>
            <h2 className="font-display text-5xl font-black uppercase text-[var(--agencia-text)]">
              DROP ANYTHING. ANALYZE INSTANTLY.
            </h2>
            <p className="text-sm text-[var(--agencia-text-muted)]">
              ArchLens accepts any repository source or package archive with automated content-based language detection.
            </p>
          </div>

          {/* Bento Grid */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            <div className="md:col-span-2 p-8 rounded-2xl glass-card border border-[var(--agencia-border)] flex flex-col justify-between hover:border-[var(--agencia-lime)] transition-colors group">
              <div className="space-y-4">
                <div className="w-12 h-12 rounded-xl bg-[var(--agencia-surface)] border border-[var(--agencia-border)] flex items-center justify-center text-[var(--accent-text)]">
                  <GitBranch className="w-6 h-6" />
                </div>
                <h3 className="font-heading text-xl font-bold text-[var(--agencia-text)]">
                  Remote Git Repositories
                </h3>
                <p className="text-xs text-[var(--agencia-text-muted)] leading-relaxed">
                  Direct GitHub, GitLab, Bitbucket clones with branch, commit, and subpath selection. Tokens stay purely in memory.
                </p>
              </div>
              <div className="mt-6 p-3 rounded-xl bg-[var(--agencia-surface)] font-mono text-[11px] text-[var(--agencia-text-muted)] flex items-center gap-2">
                <Terminal className="w-3.5 h-3.5 text-[var(--accent-text)]" />
                <span>git clone --depth 1 https://github.com/user/repo</span>
              </div>
            </div>

            <div className="p-8 rounded-2xl glass-card border border-[var(--agencia-border)] flex flex-col justify-between hover:border-[var(--agencia-lime)] transition-colors">
              <div className="space-y-4">
                <div className="w-12 h-12 rounded-xl bg-[var(--agencia-surface)] border border-[var(--agencia-border)] flex items-center justify-center text-[var(--accent-text)]">
                  <FolderArchive className="w-6 h-6" />
                </div>
                <h3 className="font-heading text-lg font-bold text-[var(--agencia-text)]">
                  ZIP & TAR Archives
                </h3>
                <p className="text-xs text-[var(--agencia-text-muted)] leading-relaxed">
                  Safely unpacks archives with Zip-Slip, Symlink, and Zip-Bomb isolation guards.
                </p>
              </div>
              <span className="text-[11px] font-mono text-[var(--accent-text)] mt-4">
                Up to 100MB unpack limit
              </span>
            </div>

            <div className="p-8 rounded-2xl glass-card border border-[var(--agencia-border)] flex flex-col justify-between hover:border-[var(--agencia-lime)] transition-colors">
              <div className="space-y-4">
                <div className="w-12 h-12 rounded-xl bg-[var(--agencia-surface)] border border-[var(--agencia-border)] flex items-center justify-center text-[var(--accent-text)]">
                  <FileCode className="w-6 h-6" />
                </div>
                <h3 className="font-heading text-lg font-bold text-[var(--agencia-text)]">
                  Raw Code & Snippets
                </h3>
                <p className="text-xs text-[var(--agencia-text-muted)] leading-relaxed">
                  Paste isolated modules or classes to instantly evaluate cyclomatic complexity and abstract coupling.
                </p>
              </div>
              <span className="text-[11px] font-mono text-[var(--accent-text)] mt-4">
                Multi-language AST
              </span>
            </div>
          </div>
        </div>
      </section>

      {/* ── Section (b): Interactive Graph Preview & Blast Radius ──────────────────── */}
      <section className="py-20 px-6 border-t border-[var(--agencia-border)]">
        <div className="max-w-7xl mx-auto space-y-12">
          <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
            <div>
              <span className="text-xs font-mono uppercase tracking-widest text-[var(--accent-text)]">
                DEPENDENCY IMPACT & BLAST RADIUS (illustrative example)
              </span>
              <h2 className="font-display text-5xl font-black uppercase text-[var(--agencia-text)] mt-1">
                INTERACTIVE GRAPH EXPLORER
              </h2>
            </div>
            <p className="text-xs font-mono text-[var(--agencia-text-muted)] max-w-md">
              Hover nodes below to simulate real-time blast radius inspection. Discover cascading failures before touching code.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[
              {
                id: 'auth',
                name: 'com.archlens.auth.TokenService',
                risk: 'HIGH',
                dependents: 18,
                desc: 'Core JWT authentication broker. Changes impact all downstream controller endpoints.'
              },
              {
                id: 'graph',
                name: 'com.archlens.engine.TarjanSCC',
                risk: 'LOW',
                dependents: 4,
                desc: 'Graph cycle decomposition engine. Pure algorithm without side-effects.'
              },
              {
                id: 'storage',
                name: 'com.archlens.storage.ReportRepository',
                risk: 'MEDIUM',
                dependents: 9,
                desc: 'Persists serialized JSON and markdown diagnostic artifacts.'
              }
            ].map((node) => (
              <div
                key={node.id}
                onMouseEnter={() => setHoveredNode(node.id)}
                onMouseLeave={() => setHoveredNode(null)}
                className={`p-6 rounded-2xl glass-card border transition-[transform,border-color,box-shadow] duration-200 will-change-transform cursor-pointer ${
                  hoveredNode === node.id
                    ? 'border-[var(--agencia-lime)] shadow-[0_0_25px_rgba(198,244,50,0.2)] scale-[1.02]'
                    : 'border-[var(--agencia-border)]'
                }`}
              >
                <div className="flex items-center justify-between mb-4">
                  <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-[var(--agencia-surface)] text-[var(--agencia-text-muted)] border border-[var(--agencia-border)]">
                    AST Node
                  </span>
                  <span
                    className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded ${
                      node.risk === 'HIGH'
                        ? 'bg-[var(--agencia-red)]/15 text-[var(--agencia-red)]'
                        : node.risk === 'MEDIUM'
                        ? 'bg-[var(--agencia-amber)]/15 text-[var(--agencia-amber)]'
                        : 'bg-[var(--agencia-lime)]/15 text-[var(--accent-text)]'
                    }`}
                  >
                    {node.risk} IMPACT
                  </span>
                </div>

                <h4 className="font-mono text-sm font-bold text-[var(--agencia-text)] mb-2 truncate">
                  {node.name}
                </h4>
                <p className="text-xs text-[var(--agencia-text-muted)] leading-relaxed mb-6">
                  {node.desc}
                </p>

                <div className="pt-4 border-t border-[var(--agencia-border)] flex items-center justify-between text-xs font-mono">
                  <span className="text-[var(--agencia-text-muted)]">Downstream Dependents:</span>
                  <span className="text-[var(--accent-text)] font-bold">{node.dependents} Modules</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Section (c): Security Diagnostics with Severity Bars ──────────────────── */}
      <section className="py-20 px-6 border-t border-[var(--agencia-border)] bg-[var(--agencia-surface)]/20">
        <div className="max-w-7xl mx-auto space-y-12">
          <div className="text-center max-w-2xl mx-auto space-y-3">
            <span className="text-xs font-mono uppercase tracking-widest text-[var(--agencia-red)]">
              RESERVED RED SAFETY SPECIFICATION (illustrative example)
            </span>
            <h2 className="font-display text-5xl font-black uppercase text-[var(--agencia-text)]">
              SECURITY DIAGNOSTICS & TAINT TRACKING
            </h2>
            <p className="text-sm text-[var(--agencia-text-muted)]">
              Red is strictly reserved for high risk vulnerabilities and circular deadlocks. Never for decorative elements.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            <div className="p-8 rounded-2xl glass-card border border-[var(--agencia-border)] space-y-6">
              <h3 className="font-heading text-lg font-bold text-[var(--agencia-text)]">
                Vulnerability Severity Breakdown
              </h3>
              <div className="space-y-4">
                <div>
                  <div className="flex justify-between text-xs font-mono mb-1.5">
                    <span className="text-[var(--agencia-red)] font-semibold">Critical / High (Reserved Red)</span>
                    <span className="text-[var(--agencia-red)] font-bold">2 Findings</span>
                  </div>
                  <div className="h-2 rounded-full bg-[var(--agencia-surface)] overflow-hidden">
                    <div className="h-full bg-[var(--agencia-red)] w-[24%]" />
                  </div>
                </div>

                <div>
                  <div className="flex justify-between text-xs font-mono mb-1.5">
                    <span className="text-[var(--agencia-amber)] font-semibold">Medium Risk (Warning Amber)</span>
                    <span className="text-[var(--agencia-amber)] font-bold">7 Findings</span>
                  </div>
                  <div className="h-2 rounded-full bg-[var(--agencia-surface)] overflow-hidden">
                    <div className="h-full bg-[var(--agencia-amber)] w-[48%]" />
                  </div>
                </div>

                <div>
                  <div className="flex justify-between text-xs font-mono mb-1.5">
                    <span className="text-[var(--agencia-text-muted)] font-semibold">Low / Informational</span>
                    <span className="text-[var(--accent-text)] font-bold">14 Findings</span>
                  </div>
                  <div className="h-2 rounded-full bg-[var(--agencia-surface)] overflow-hidden">
                    <div className="h-full bg-[var(--agencia-lime)] w-[75%]" />
                  </div>
                </div>
              </div>
            </div>

            <div className="p-8 rounded-2xl glass-card border border-[var(--agencia-border)] flex flex-col justify-between">
              <div>
                <div className="flex items-center gap-2 text-[var(--agencia-red)] mb-4">
                  <ShieldAlert className="w-5 h-5" />
                  <span className="text-xs font-mono font-bold uppercase tracking-wider">
                    OSV & AST Taint Analysis Active
                  </span>
                </div>
                <h4 className="font-heading text-xl font-bold text-[var(--agencia-text)] mb-3">
                  CWE & OWASP Categorization
                </h4>
                <p className="text-xs text-[var(--agencia-text-muted)] leading-relaxed">
                  Every security smell links directly to code snippets, exact line offsets, and remediation diff patches. False positives can be marked and excluded with full audit accountability.
                </p>
              </div>
              <div className="mt-6 flex flex-wrap gap-2">
                <span className="text-[10px] font-mono px-2 py-1 rounded bg-[var(--agencia-surface)] text-[var(--agencia-text-muted)] border border-[var(--agencia-border)]">
                  CWE-798 Hardcoded Secrets
                </span>
                <span className="text-[10px] font-mono px-2 py-1 rounded bg-[var(--agencia-surface)] text-[var(--agencia-text-muted)] border border-[var(--agencia-border)]">
                  CWE-89 SQL Injection
                </span>
                <span className="text-[10px] font-mono px-2 py-1 rounded bg-[var(--agencia-surface)] text-[var(--agencia-text-muted)] border border-[var(--agencia-border)]">
                  OWASP A01:2021 Broken Access
                </span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── Section (d): Refactoring Metric Counters ──────────────────────────────── */}
      <section className="py-20 px-6 border-t border-[var(--agencia-border)]">
        <div className="max-w-7xl mx-auto space-y-12">
          <div className="text-center max-w-2xl mx-auto space-y-3">
            <span className="text-xs font-mono uppercase tracking-widest text-[var(--accent-text)]">
              ARCHITECTURAL HEALTH ENHANCEMENT (illustrative example)
            </span>
            <h2 className="font-display text-5xl font-black uppercase text-[var(--agencia-text)]">
              BEFORE & AFTER REFACTORING METRICS
            </h2>
            <p className="text-sm text-[var(--agencia-text-muted)]">
              Simulate refactoring impacts with real graph transformations and verified before/after diffs.
            </p>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
            <div className="p-6 rounded-2xl glass-card border border-[var(--agencia-border)] text-center space-y-2">
              <span className="text-xs font-mono text-[var(--agencia-text-muted)] uppercase">
                Cyclomatic Complexity
              </span>
              <p className="font-display text-5xl font-black text-[var(--accent-text)]">-42%</p>
              <p className="text-[11px] font-mono text-[var(--agencia-text-muted)]">From 64 → 37 avg</p>
            </div>

            <div className="p-6 rounded-2xl glass-card border border-[var(--agencia-border)] text-center space-y-2">
              <span className="text-xs font-mono text-[var(--agencia-text-muted)] uppercase">
                Circular Deadlocks
              </span>
              <p className="font-display text-5xl font-black text-[var(--accent-text)]">0</p>
              <p className="text-[11px] font-mono text-[var(--agencia-text-muted)]">From 5 down to ZERO</p>
            </div>

            <div className="p-6 rounded-2xl glass-card border border-[var(--agencia-border)] text-center space-y-2">
              <span className="text-xs font-mono text-[var(--agencia-text-muted)] uppercase">
                Instability Index
              </span>
              <p className="font-display text-5xl font-black text-[var(--accent-text)]">0.18</p>
              <p className="text-[11px] font-mono text-[var(--agencia-text-muted)]">Normalized Martin Metric</p>
            </div>

            <div className="p-6 rounded-2xl glass-card border border-[var(--agencia-border)] text-center space-y-2">
              <span className="text-xs font-mono text-[var(--agencia-text-muted)] uppercase">
                System Health Score
              </span>
              <p className="font-display text-5xl font-black text-[var(--accent-text)]">94<span className="text-2xl">/100</span></p>
              <p className="text-[11px] font-mono text-[var(--agencia-text-muted)]">Grade A Architecture</p>
            </div>
          </div>
        </div>
      </section>

      {/* ── Section (e): Report Preview ───────────────────────────────────────────── */}
      <section className="py-20 px-6 border-t border-[var(--agencia-border)] bg-[var(--agencia-surface)]/20">
        <div className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
          <div className="lg:col-span-6 space-y-6">
            <span className="text-xs font-mono uppercase tracking-widest text-[var(--accent-text)]">
              EXPORTABLE AUDIT DELIVERABLES
            </span>
            <h2 className="font-display text-5xl font-black uppercase text-[var(--agencia-text)]">
              COMPLETE DIAGNOSTIC REPORTS
            </h2>
            <p className="text-sm text-[var(--agencia-text-muted)] leading-relaxed">
              Export self-contained HTML, machine-readable JSON, security SARIF, and print-ready PDF formats. Every report contains real coverage figures, dependency tables, and reproducible algorithm metadata.
            </p>
            <div className="flex gap-4">
              <Link to="/reports">
                <Button variant="secondary" size="md">
                  View Sample Reports <ArrowRight className="w-4 h-4 ml-2" />
                </Button>
              </Link>
            </div>
          </div>

          <div className="lg:col-span-6">
            <div className="p-6 rounded-2xl glass-card border border-[var(--agencia-border)] shadow-2xl space-y-4">
              <div className="flex items-center justify-between border-b border-[var(--agencia-border)] pb-4">
                <div>
                  <p className="text-xs font-mono text-[var(--accent-text)]">REPORT ID: REP-76A95893 (illustrative example)</p>
                  <p className="font-heading font-bold text-sm text-[var(--agencia-text)]">
                    customer-churn-prediction (Production Scan &mdash; illustrative example)
                  </p>
                </div>
                <span className="text-[10px] font-mono px-2 py-1 rounded bg-[var(--agencia-lime)] text-[var(--agencia-obsidian)] font-bold">
                  GRADE A
                </span>
              </div>
              <div className="grid grid-cols-3 gap-3 text-center py-2 font-mono text-xs">
                <div className="p-2 rounded bg-[var(--agencia-surface)]">
                  <p className="text-[var(--agencia-text-muted)]">Files</p>
                  <p className="font-bold text-[var(--agencia-text)]">6</p>
                </div>
                <div className="p-2 rounded bg-[var(--agencia-surface)]">
                  <p className="text-[var(--agencia-text-muted)]">AST Edges</p>
                  <p className="font-bold text-[var(--agencia-text)]">27</p>
                </div>
                <div className="p-2 rounded bg-[var(--agencia-surface)]">
                  <p className="text-[var(--agencia-text-muted)]">Cycles</p>
                  <p className="font-bold text-[var(--accent-text)]">0</p>
                </div>
              </div>
              <p className="text-[11px] font-mono text-[var(--agencia-text-muted)] border-t border-[var(--agencia-border)] pt-3">
                Includes full Tarjan SCC cycle paths, OSV vulnerability matching, and before/after metrics.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ── Section (f): Animated 4-Step Pipeline ─────────────────────────────────── */}
      <section className="py-20 px-6 border-t border-[var(--agencia-border)]">
        <div className="max-w-7xl mx-auto space-y-12">
          <div className="text-center max-w-2xl mx-auto space-y-3">
            <span className="text-xs font-mono uppercase tracking-widest text-[var(--accent-text)]">
              EXECUTION PIPELINE
            </span>
            <h2 className="font-display text-5xl font-black uppercase text-[var(--agencia-text)]">
              HOW IT WORKS IN 4 STEPS
            </h2>
            <p className="text-sm text-[var(--agencia-text-muted)]">
              From raw source files to interactive 3D topology in sub-second streaming intervals.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            {[
              {
                step: '01',
                title: 'Universal Ingestion',
                desc: 'Git clone or archive decompression with rigorous zip-slip and SSRF security gates.'
              },
              {
                step: '02',
                title: 'AST Tree-sitter Parsing',
                desc: 'Deconstructs syntax into language-agnostic symbols without compiling or running code.'
              },
              {
                step: '03',
                title: 'Graph & Taint Analysis',
                desc: 'Computes Tarjan SCC cycles, PageRank centrality, Martin instability, and OSV vulnerabilities.'
              },
              {
                step: '04',
                title: 'Refactor & Export',
                desc: 'Generates unified git diff patches and generates verifiable multi-format diagnostic reports.'
              }
            ].map((p, idx) => (
              <div key={idx} className="p-6 rounded-2xl glass-card border border-[var(--agencia-border)] space-y-3 relative overflow-hidden group hover:border-[var(--agencia-lime)] transition-colors">
                <span className="font-display text-5xl font-black text-[var(--accent-text)]/20 group-hover:text-[var(--accent-text)]/40 transition-colors">
                  {p.step}
                </span>
                <h4 className="font-heading text-lg font-bold text-[var(--agencia-text)]">
                  {p.title}
                </h4>
                <p className="text-xs text-[var(--agencia-text-muted)] leading-relaxed font-sans">
                  {p.desc}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Section (g): FAQ Accordion ────────────────────────────────────────────── */}
      <section className="py-20 px-6 border-t border-[var(--agencia-border)] bg-[var(--agencia-surface)]/20">
        <div className="max-w-4xl mx-auto space-y-12">
          <div className="text-center space-y-3">
            <span className="text-xs font-mono uppercase tracking-widest text-[var(--accent-text)]">
              FREQUENTLY ASKED QUESTIONS
            </span>
            <h2 className="font-display text-5xl font-black uppercase text-[var(--agencia-text)]">
              CLEAR ARCHITECTURAL ANSWERS
            </h2>
          </div>

          <div className="space-y-4">
            {faqs.map((faq, idx) => {
              const isOpen = activeFaq === idx;
              return (
                <div
                  key={idx}
                  className="rounded-xl glass-card border border-[var(--agencia-border)] overflow-hidden transition-colors"
                >
                  <button
                    onClick={() => setActiveFaq(isOpen ? null : idx)}
                    className="w-full p-5 text-left flex items-center justify-between gap-4 font-heading font-semibold text-sm text-[var(--agencia-text)]"
                  >
                    <span>{faq.q}</span>
                    <ChevronDown
                      className={`w-4 h-4 text-[var(--agencia-text-muted)] transition-transform duration-300 shrink-0 ${
                        isOpen ? 'rotate-180 text-[var(--accent-text)]' : ''
                      }`}
                    />
                  </button>
                  <AnimatePresence>
                    {isOpen && (
                      <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.2 }}
                      >
                        <div className="px-5 pb-5 pt-1 text-xs text-[var(--agencia-text-muted)] font-sans leading-relaxed border-t border-[var(--agencia-border)]/50">
                          {faq.a}
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* ── Section (h): Final High-Impact CTA & Footer ───────────────────────────── */}
      <section className="py-24 px-6 border-t border-[var(--agencia-border)] text-center relative overflow-hidden">
        <div className="max-w-3xl mx-auto space-y-8 relative z-10">
          <span className="text-xs font-mono uppercase tracking-widest text-[var(--accent-text)]">
            READY TO VISUALIZE YOUR CODEBASE?
          </span>
          <h2 className="font-display text-6xl sm:text-7xl font-black uppercase text-[var(--agencia-text)] leading-none">
            START YOUR ARCHITECTURAL SCAN NOW
          </h2>
          <p className="text-sm text-[var(--agencia-text-muted)] max-w-xl mx-auto">
            Zero configuration required. Ingest your Git repository or code archive in seconds and uncover unseen architectural deadlocks.
          </p>
          <div className="flex justify-center gap-4">
            <Link to="/register">
              <Button variant="primary" size="lg" className="px-10 shadow-[0_0_30px_rgba(198,244,50,0.4)]">
                Create Free Account <ArrowRight className="w-4 h-4 ml-2" />
              </Button>
            </Link>
          </div>
        </div>
      </section>

      {/* ── Minimalist Luxury-Brutalist Footer ─────────────────────────────────────── */}
      <footer className="border-t border-[var(--agencia-border)] py-8 px-6 bg-[var(--agencia-bg)]">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4 text-xs font-mono text-[var(--agencia-text-muted)]">
          <div className="flex items-center gap-2">
            <span className="font-display font-bold text-sm text-[var(--agencia-text)]">ARCHLENS</span>
            <span>© 2026 ARCHLENS ENGINE. ALL RIGHTS RESERVED.</span>
          </div>
          <div className="flex items-center gap-6">
            <Link to="/design-system" className="hover:text-[var(--accent-text)] transition-colors">
              DESIGN SYSTEM
            </Link>
            <Link to="/login" className="hover:text-[var(--accent-text)] transition-colors">
              RBAC PORTAL
            </Link>
            <a href="https://github.com" target="_blank" rel="noreferrer" className="hover:text-[var(--accent-text)] transition-colors">
              GITHUB
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
};
