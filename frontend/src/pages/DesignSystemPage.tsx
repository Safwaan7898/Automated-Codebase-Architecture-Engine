import React, { useState } from 'react';
import { useTheme } from '../contexts/ThemeContext';
import {
  Button,
  Input,
  Select,
  Checkbox,
  Switch,
  Modal,
  Drawer,
  ToastContainer,
  type ToastProps,
  Badge,
  SeverityChip,
  ProgressBar,
  EmptyState,
  Card,
  StatCard,
  ScoreRing,
  Sparkline,
  DataTable,
  CodeBlock,
  DiffViewer,
  FileDropzone,
  CommandPalette,
  Breadcrumbs,
  Avatar,
  Stepper
} from '../components/ui';
import { Sun, Moon, Laptop } from 'lucide-react';

export const DesignSystemPage: React.FC = () => {
  const { theme, setTheme } = useTheme();
  const [modalOpen, setModalOpen] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [commandOpen, setCommandOpen] = useState(false);
  const [switchVal, setSwitchVal] = useState(true);
  const [checkVal, setCheckVal] = useState(true);
  const [inputVal, setInputVal] = useState('archlens_core_v2');
  const [currentStep, setCurrentStep] = useState(1);
  const [toasts, setToasts] = useState<Array<Omit<ToastProps, 'onClose'>>>([]);

  const addToast = (type: 'success' | 'warning' | 'error' | 'info') => {
    const id = Math.random().toString();
    const titles = {
      success: 'Analysis Completed',
      warning: 'High Coupling Detected',
      error: 'Circular Dependency Found',
      info: 'Cache Synchronized'
    };
    setToasts((prev) => [
      ...prev,
      {
        id,
        type,
        title: titles[type],
        message: `Event logged cleanly at ${new Date().toLocaleTimeString()}`
      }
    ]);
  };

  const removeToast = (id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  // Sample data for DataTable
  const sampleTableData = [
    { id: 'MOD-01', name: 'AuthService', language: 'TypeScript', risk: 'LOW', complexity: 12 },
    { id: 'MOD-02', name: 'GraphEngine', language: 'Python', risk: 'HIGH', complexity: 48 },
    { id: 'MOD-03', name: 'ParserWorker', language: 'Java', risk: 'MEDIUM', complexity: 26 },
    { id: 'MOD-04', name: 'SecurityScanner', language: 'Python', risk: 'CRITICAL', complexity: 62 },
    { id: 'MOD-05', name: 'ReportGenerator', language: 'TypeScript', risk: 'LOW', complexity: 15 }
  ];

  const tableColumns = [
    { key: 'id', header: 'Module ID', width: '120px' },
    { key: 'name', header: 'Component Name', sortable: true },
    { key: 'language', header: 'Stack', sortable: true },
    {
      key: 'risk',
      header: 'Severity',
      sortable: true,
      render: (item: any) => <SeverityChip severity={item.risk} />
    },
    {
      key: 'complexity',
      header: 'Cyclomatic Complexity',
      sortable: true,
      render: (item: any) => (
        <span className="font-mono font-bold text-[var(--agencia-text)]">
          {item.complexity}
        </span>
      )
    }
  ];

  const sampleDiff = `@@ -12,6 +12,8 @@ export function resolveGraphCycles(nodes, edges) {
-  const visited = new Set();
-  const recStack = new Set();
+  const visited = new Map();
+  const tarjanStack = [];
+  let cycleCount = 0;
   // Perform strongly connected components analysis
   return tarjanSCC(nodes, edges);
 }`;

  return (
    <div className="min-h-screen bg-[var(--agencia-bg)] text-[var(--agencia-text)] transition-colors duration-300">
      {/* Toast Manager */}
      <ToastContainer toasts={toasts} onClose={removeToast} />

      {/* Command Palette */}
      <CommandPalette isOpen={commandOpen} onClose={() => setCommandOpen(false)} />

      {/* Header Sticky Bar */}
      <header className="sticky top-0 z-40 backdrop-blur-xl bg-[var(--agencia-bg)]/80 border-b border-[var(--agencia-border)] px-8 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-4">
            <span className="font-display text-3xl font-bold tracking-widest text-[var(--accent-text)]">
              AGENCIA
            </span>
            <span className="text-xs font-mono uppercase tracking-widest px-2.5 py-1 rounded-full border border-[var(--agencia-border)] bg-[var(--agencia-surface)]">
              Design System v2.0
            </span>
          </div>

          <div className="flex items-center gap-3">
            {/* Theme Toggle */}
            <div className="flex items-center p-1 rounded-xl border border-[var(--agencia-border)] bg-[var(--agencia-surface)]">
              <button
                onClick={() => setTheme('light')}
                className={`p-1.5 rounded-lg transition-colors ${
                  theme === 'light'
                    ? 'bg-[var(--agencia-lime)] text-[var(--agencia-obsidian)]'
                    : 'text-[var(--agencia-text-muted)] hover:text-[var(--agencia-text)]'
                }`}
                title="Light Theme"
              >
                <Sun className="w-4 h-4" />
              </button>
              <button
                onClick={() => setTheme('dark')}
                className={`p-1.5 rounded-lg transition-colors ${
                  theme === 'dark'
                    ? 'bg-[var(--agencia-lime)] text-[var(--agencia-obsidian)]'
                    : 'text-[var(--agencia-text-muted)] hover:text-[var(--agencia-text)]'
                }`}
                title="Dark Theme"
              >
                <Moon className="w-4 h-4" />
              </button>
              <button
                onClick={() => setTheme('system')}
                className={`p-1.5 rounded-lg transition-colors ${
                  theme === 'system'
                    ? 'bg-[var(--agencia-lime)] text-[var(--agencia-obsidian)]'
                    : 'text-[var(--agencia-text-muted)] hover:text-[var(--agencia-text)]'
                }`}
                title="System Theme"
              >
                <Laptop className="w-4 h-4" />
              </button>
            </div>

            <Button variant="secondary" size="sm" onClick={() => setCommandOpen(true)}>
              ⌘K Quick Search
            </Button>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="max-w-7xl mx-auto px-8 py-12 space-y-16">
        {/* Intro Hero */}
        <section className="space-y-4">
          <p className="font-mono text-xs uppercase tracking-widest text-[var(--accent-text)]">
            AESTHETIC & ARCHITECTURE SPECIFICATION
          </p>
          <h1 className="font-display text-7xl font-bold uppercase tracking-tight text-[var(--agencia-text)]">
            LUXURY-BRUTALIST HYBRID TOKENS
          </h1>
          <p className="max-w-3xl text-sm leading-relaxed text-[var(--agencia-text-muted)]">
            High-contrast dark obsidian (<code className="font-mono text-xs text-[var(--accent-text)]">#0B0D0C</code>) paired with warm paper-gray (<code className="font-mono text-xs text-[var(--accent-text)]">#F2F4EF</code>) in light mode. Accented with electric neon lime (<code className="font-mono text-xs text-[var(--accent-text)]">#C6F432</code>). Red is strictly reserved for critical security vulnerabilities, high risks, and cyclic dependencies.
          </p>
        </section>

        {/* Section 1: Color Tokens */}
        <section className="space-y-6">
          <h2 className="font-heading text-xl font-bold tracking-wide border-b border-[var(--agencia-border)] pb-3">
            01. Core Color System
          </h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-4">
            <div className="p-4 rounded-xl border border-[var(--agencia-border)] bg-[var(--agencia-bg)]">
              <div className="h-14 rounded-lg bg-[var(--agencia-bg)] border border-[var(--agencia-border)] mb-2" />
              <p className="text-xs font-semibold">Background</p>
              <p className="text-[11px] font-mono text-[var(--agencia-text-muted)]">#0B0D0C / #F2F4EF</p>
            </div>
            <div className="p-4 rounded-xl border border-[var(--agencia-border)] bg-[var(--agencia-surface)]">
              <div className="h-14 rounded-lg bg-[var(--agencia-surface)] border border-[var(--agencia-border)] mb-2" />
              <p className="text-xs font-semibold">Surface Glass</p>
              <p className="text-[11px] font-mono text-[var(--agencia-text-muted)]">Frosted Panel</p>
            </div>
            <div className="p-4 rounded-xl border border-[var(--agencia-border)] bg-[var(--agencia-surface)]">
              <div className="h-14 rounded-lg bg-[var(--agencia-lime)] rounded-lg mb-2 shadow-[0_0_15px_rgba(198,244,50,0.3)]" />
              <p className="text-xs font-semibold">Accent Lime</p>
              <p className="text-[11px] font-mono text-[var(--agencia-text-muted)]">#C6F432</p>
            </div>
            <div className="p-4 rounded-xl border border-[var(--agencia-border)] bg-[var(--agencia-surface)]">
              <div className="h-14 rounded-lg bg-[var(--agencia-red)] rounded-lg mb-2" />
              <p className="text-xs font-semibold">Reserved Red</p>
              <p className="text-[11px] font-mono text-[var(--agencia-text-muted)]">#FF2D20 (Risks Only)</p>
            </div>
            <div className="p-4 rounded-xl border border-[var(--agencia-border)] bg-[var(--agencia-surface)]">
              <div className="h-14 rounded-lg bg-[var(--agencia-amber)] rounded-lg mb-2" />
              <p className="text-xs font-semibold">Medium Amber</p>
              <p className="text-[11px] font-mono text-[var(--agencia-text-muted)]">#F59E0B</p>
            </div>
            <div className="p-4 rounded-xl border border-[var(--agencia-border)] bg-[var(--agencia-surface)]">
              <div className="h-14 rounded-lg bg-[var(--agencia-text)] rounded-lg mb-2" />
              <p className="text-xs font-semibold">Contrast Text</p>
              <p className="text-[11px] font-mono text-[var(--agencia-text-muted)]">Obsidian / Paper</p>
            </div>
          </div>
        </section>

        {/* Section 2: Buttons */}
        <section className="space-y-6">
          <h2 className="font-heading text-xl font-bold tracking-wide border-b border-[var(--agencia-border)] pb-3">
            02. Action Elements (Buttons)
          </h2>
          <div className="flex flex-wrap gap-4 items-center">
            <Button variant="primary">Primary Action</Button>
            <Button variant="secondary">Secondary Action</Button>
            <Button variant="ghost">Ghost Trigger</Button>
            <Button variant="danger">Security Terminate</Button>
            <Button variant="primary" isLoading>Computing Graph...</Button>
          </div>
        </section>

        {/* Section 3: StatCards, ScoreRing & Sparkline */}
        <section className="space-y-6">
          <h2 className="font-heading text-xl font-bold tracking-wide border-b border-[var(--agencia-border)] pb-3">
            03. Architectural Telemetry & Gauges
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            <StatCard
              label="Analyzed Nodes"
              value={1420}
              change="+14.2%"
              trend="up"
            />
            <StatCard
              label="Coupling Edges"
              value={4890}
              change="+3.8%"
              trend="up"
            />
            <StatCard
              label="Circular Dependencies"
              value={3}
              change="-2 this commit"
              trend="down"
            />
            <Card className="flex items-center justify-between p-6">
              <div>
                <p className="text-xs font-mono uppercase tracking-wider text-[var(--agencia-text-muted)]">
                  Health Index
                </p>
                <p className="text-sm font-semibold text-[var(--agencia-text)] mt-1">
                  System Grade A
                </p>
                <div className="mt-3">
                  <Sparkline data={[60, 65, 72, 70, 78, 85, 92]} />
                </div>
              </div>
              <ScoreRing score={92} size={84} />
            </Card>
          </div>
        </section>

        {/* Section 4: Form Inputs & Select */}
        <section className="space-y-6">
          <h2 className="font-heading text-xl font-bold tracking-wide border-b border-[var(--agencia-border)] pb-3">
            04. Inputs & Toggles
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <Input
              label="Repository URL"
              value={inputVal}
              onChange={(e) => setInputVal(e.target.value)}
              helperText="Target remote Git repository or local identifier"
            />
            <Select
              label="Target Architecture Preset"
              options={[
                { value: 'microservices', label: 'Hexagonal / Ports & Adapters' },
                { value: 'modular-monolith', label: 'Clean Architecture (Layered)' },
                { value: 'event-driven', label: 'Event-Driven Reactive' }
              ]}
              value="microservices"
              onChange={() => {}}
            />
            <div className="space-y-4 pt-2">
              <Checkbox
                label="Deep AST Security & Taint Propagation"
                checked={checkVal}
                onChange={(e) => setCheckVal(e.target.checked)}
              />
              <Switch
                label="Incremental WebSocket Synchronization"
                checked={switchVal}
                onChange={setSwitchVal}
              />
            </div>
          </div>
        </section>

        {/* Section 5: Badges & Severity Chips */}
        <section className="space-y-6">
          <h2 className="font-heading text-xl font-bold tracking-wide border-b border-[var(--agencia-border)] pb-3">
            05. Badges & Reserved Severity Indicators
          </h2>
          <div className="flex flex-wrap gap-4 items-center">
            <Badge variant="accent">STABLE</Badge>
            <Badge variant="outline">JAVA 21</Badge>
            <Badge variant="warning">PENDING APPROVAL</Badge>
            <SeverityChip severity="LOW" />
            <SeverityChip severity="MEDIUM" />
            <SeverityChip severity="HIGH" />
            <SeverityChip severity="CRITICAL" />
          </div>
        </section>

        {/* Section 6: Progress & Stepper */}
        <section className="space-y-6">
          <h2 className="font-heading text-xl font-bold tracking-wide border-b border-[var(--agencia-border)] pb-3">
            06. Pipeline Progression & Stepper
          </h2>
          <div className="space-y-6">
            <Stepper
              steps={[
                { title: 'Fetch & Clone', description: 'AST Ingestion' },
                { title: 'Graph Building', description: 'Tarjan & PageRank' },
                { title: 'Security Taint', description: 'OSV & Secret Scan' },
                { title: 'Report Ready', description: 'Export PDF / JSON' }
              ]}
              currentStep={currentStep}
            />
            <div className="flex gap-3">
              <Button size="sm" variant="secondary" onClick={() => setCurrentStep((s) => Math.max(0, s - 1))}>
                Previous Stage
              </Button>
              <Button size="sm" variant="primary" onClick={() => setCurrentStep((s) => Math.min(3, s + 1))}>
                Next Stage
              </Button>
            </div>
            <div className="space-y-2">
              <p className="text-xs font-mono text-[var(--agencia-text-muted)]">Buffer Parsing Progress: 74%</p>
              <ProgressBar value={74} />
            </div>
          </div>
        </section>

        {/* Section 7: DataTable */}
        <section className="space-y-6">
          <h2 className="font-heading text-xl font-bold tracking-wide border-b border-[var(--agencia-border)] pb-3">
            07. Sortable & Paginated Data Table
          </h2>
          <DataTable data={sampleTableData} columns={tableColumns} />
        </section>

        {/* Section 8: CodeBlock & DiffViewer */}
        <section className="space-y-6">
          <h2 className="font-heading text-xl font-bold tracking-wide border-b border-[var(--agencia-border)] pb-3">
            08. Code Highlighting & Diff Engine
          </h2>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <CodeBlock
              filename="engine/tarjan_scc.py"
              language="python"
              code={`def tarjan_scc(adjacency_list: dict[str, list[str]]) -> list[list[str]]:
    index = 0
    indices = {}
    lowlink = {}
    on_stack = set()
    stack = []
    sccs = []
    # Identify cyclic subgraphs in O(V + E)
    return sccs`}
            />
            <DiffViewer
              filename="refactor/decouple_scc.patch"
              oldVersion="v1.2.0"
              newVersion="v2.0.0"
              diffText={sampleDiff}
            />
          </div>
        </section>

        {/* Section 9: File Dropzone */}
        <section className="space-y-6">
          <h2 className="font-heading text-xl font-bold tracking-wide border-b border-[var(--agencia-border)] pb-3">
            09. Universal Codebase Dropzone
          </h2>
          <FileDropzone onFileSelect={(f) => console.log('File selected:', f)} />
        </section>

        {/* Section 10: Modals, Drawers & Toasts */}
        <section className="space-y-6">
          <h2 className="font-heading text-xl font-bold tracking-wide border-b border-[var(--agencia-border)] pb-3">
            10. Overlay Modals, Drawers & Notifications
          </h2>
          <div className="flex flex-wrap gap-4 items-center">
            <Button variant="secondary" onClick={() => setModalOpen(true)}>
              Open Modal Dialog
            </Button>
            <Button variant="secondary" onClick={() => setDrawerOpen(true)}>
              Open Side Drawer
            </Button>
            <Button variant="ghost" onClick={() => addToast('success')}>
              Trigger Success Toast
            </Button>
            <Button variant="ghost" onClick={() => addToast('warning')}>
              Trigger Warning Toast
            </Button>
            <Button variant="ghost" onClick={() => addToast('error')}>
              Trigger Reserved Red Toast
            </Button>
          </div>

          <Modal
            isOpen={modalOpen}
            onClose={() => setModalOpen(false)}
            title="Export Diagnostic Package"
          >
            <div className="space-y-4">
              <p className="text-sm text-[var(--agencia-text-muted)]">
                Confirm compilation of diagnostic report including full Tarjan SCC cycle paths, OSV vulnerability matches, and before/after metrics.
              </p>
              <div className="flex justify-end gap-3 pt-2">
                <Button variant="ghost" onClick={() => setModalOpen(false)}>Cancel</Button>
                <Button variant="primary" onClick={() => setModalOpen(false)}>Confirm Generation</Button>
              </div>
            </div>
          </Modal>

          <Drawer
            isOpen={drawerOpen}
            onClose={() => setDrawerOpen(false)}
            title="Node Blast Radius Inspector"
          >
            <div className="space-y-4 text-xs font-mono">
              <div className="p-3 rounded-lg border border-[var(--agencia-border)] bg-[var(--agencia-surface)]">
                <p className="text-[var(--agencia-text-muted)]">Entity</p>
                <p className="text-sm font-semibold text-[var(--accent-text)]">com.archlens.engine.GraphService</p>
              </div>
              <p className="text-[var(--agencia-text-muted)] leading-relaxed">
                Modifying this component impacts 24 downstream dependents across 3 distinct domain modules.
              </p>
            </div>
          </Drawer>
        </section>

        {/* Section 11: Breadcrumbs & Avatar */}
        <section className="space-y-6">
          <h2 className="font-heading text-xl font-bold tracking-wide border-b border-[var(--agencia-border)] pb-3">
            11. Breadcrumbs, Avatars & Empty States
          </h2>
          <div className="space-y-6">
            <Breadcrumbs
              items={[
                { label: 'Workspaces', href: '/dashboard' },
                { label: 'customer-churn-prediction', href: '/graph' },
                { label: 'Security Diagnostics' }
              ]}
            />
            <div className="flex items-center gap-4">
              <Avatar name="Alex Vance" size="sm" status="online" />
              <Avatar name="Sarah Connor" size="md" status="busy" />
              <Avatar name="Gordon Freeman" size="lg" status="pending" />
              <Avatar name="Ada Lovelace" size="xl" status="offline" />
            </div>
            <EmptyState
              title="No Cyclic Violations Detected"
              description="The analyzed repository maintains strict acyclic dependency layering according to clean architecture rules."
            />
          </div>
        </section>
      </main>
    </div>
  );
};
