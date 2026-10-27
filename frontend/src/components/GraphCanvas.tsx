import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  type Node,
  type Edge,
  BackgroundVariant,
} from 'reactflow'
import 'reactflow/dist/style.css'
import { useEffect, useMemo } from 'react'
import type { DependencyGraph, GraphNode } from '../types'

interface Props {
  graph: DependencyGraph | null
  onNodeClick?: (node: GraphNode) => void
}

const NODE_TYPE_COLORS: Record<string, string> = {
  module: '#3d59f5',
  class: '#8b5cf6',
  function: '#06b6d4',
  package: '#f59e0b',
  interface: '#10b981',
  unknown: '#6b7280',
}

const EDGE_TYPE_COLORS: Record<string, string> = {
  import: '#4b5563',
  inherit: '#f59e0b',
  implement: '#10b981',
  call: '#3d59f5',
}

function nodePosition(index: number, total: number) {
  // Arrange nodes in a spiral/grid layout
  const cols = Math.ceil(Math.sqrt(total))
  const row = Math.floor(index / cols)
  const col = index % cols
  return { x: col * 200 + (row % 2 === 0 ? 0 : 100), y: row * 120 }
}

export function GraphCanvas({ graph, onNodeClick }: Props) {
  const [nodes, setNodes, onNodesChange] = useNodesState([])
  const [edges, setEdges, onEdgesChange] = useEdgesState([])

  useEffect(() => {
    if (!graph) {
      setNodes([])
      setEdges([])
      return
    }

    const rfNodes: Node[] = graph.nodes.map((n, idx) => ({
      id: n.id,
      position: nodePosition(idx, graph.nodes.length),
      data: {
        label: (
          <div className="flex flex-col items-center gap-0.5">
            <span className="text-[10px] font-mono opacity-60">{n.type}</span>
            <span className="text-xs font-semibold truncate max-w-[120px]">{n.label}</span>
            {n.loc && (
              <span className="text-[9px] opacity-40">{n.loc} loc</span>
            )}
          </div>
        ),
        raw: n,
      },
      style: {
        background: `${NODE_TYPE_COLORS[n.type] ?? '#6b7280'}22`,
        border: `1px solid ${NODE_TYPE_COLORS[n.type] ?? '#6b7280'}`,
        borderRadius: '8px',
        color: 'var(--text)',
        padding: '6px 10px',
        minWidth: '120px',
        cursor: 'pointer',
      },
    }))

    const rfEdges: Edge[] = graph.edges.map((e, idx) => ({
      id: `e-${idx}`,
      source: typeof e.source === 'string' ? e.source : e.source.id,
      target: typeof e.target === 'string' ? e.target : e.target.id,
      style: {
        stroke: EDGE_TYPE_COLORS[e.edge_type] ?? '#4b5563',
        strokeWidth: 1.5,
        opacity: 0.6,
      },
      animated: e.edge_type === 'inherit',
      label: e.edge_type !== 'import' ? e.edge_type : undefined,
      labelStyle: { fill: 'var(--text-muted)', fontSize: 10 },
    }))

    setNodes(rfNodes)
    setEdges(rfEdges)
  }, [graph, setNodes, setEdges])

  const nodeColor = useMemo(
    () => (n: Node) => NODE_TYPE_COLORS[(n.data?.raw as GraphNode)?.type ?? 'unknown'] ?? '#6b7280',
    []
  )

  if (!graph || graph.nodes.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-text-muted text-sm">
        <div className="text-center space-y-2 animate-fade-in">
          <div className="text-4xl">🔭</div>
          <p className="text-text-muted">Run an analysis to see the dependency graph</p>
        </div>
      </div>
    )
  }

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      onNodesChange={onNodesChange}
      onEdgesChange={onEdgesChange}
      onNodeClick={(_, node) => onNodeClick?.(node.data?.raw as GraphNode)}
      fitView
      attributionPosition="bottom-right"
    >
      <Background variant={BackgroundVariant.Dots} gap={20} color="var(--border)" />
      <Controls className="[&>button]:bg-surface [&>button]:border-border [&>button]:text-text" />
      <MiniMap
        nodeColor={nodeColor}
        style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}
        maskColor="rgba(0,0,0,0.3)"
      />
    </ReactFlow>
  )
}
