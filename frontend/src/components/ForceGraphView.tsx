import React, { useEffect, useRef, useMemo, useCallback } from 'react'
import type { DependencyGraph, GraphNode } from '../types'

interface ForceGraphViewProps {
  graph: DependencyGraph | null
  onNodeClick: (node: GraphNode) => void
  selectedNodeId: string | null
  blastRadiusNodeId: string | null
  is3DMode: boolean
  isLayerBands: boolean
  clustersCollapsed: boolean
  searchQuery: string
  selectedSeverity: string
  selectedLayer: string
  onFpsUpdate?: (fps: number) => void
}

// Architectural Layer Palette
const LAYER_COLORS: Record<string, string> = {
  Presentation: '#38bdf8', // Sky blue
  Service: '#a855f7', // Purple
  Domain: '#10b981', // Emerald
  'Data / Infrastructure': '#f59e0b', // Amber
  External: '#64748b', // Slate
  Default: '#60a5fa', // Blue
}

// Community Palette
const COMMUNITY_COLORS = [
  '#3b82f6',
  '#10b981',
  '#f59e0b',
  '#8b5cf6',
  '#ec4899',
  '#06b6d4',
  '#84cc16',
  '#f97316',
]

interface SimNode extends GraphNode {
  x: number
  y: number
  z: number
  vx: number
  vy: number
  vz: number
  radius: number
  color: string
}

interface SimEdge {
  source: SimNode
  target: SimNode
  edge_type: string
  is_cycle: boolean
  weight: number
}

export const ForceGraphView: React.FC<ForceGraphViewProps> = ({
  graph,
  onNodeClick,
  selectedNodeId,
  blastRadiusNodeId,
  is3DMode,
  isLayerBands,
  clustersCollapsed,
  searchQuery,
  selectedSeverity,
  selectedLayer,
  onFpsUpdate,
}) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null)
  const containerRef = useRef<HTMLDivElement | null>(null)

  // Camera transform
  const transformRef = useRef({ x: 0, y: 0, k: 1 })
  const rot3DRef = useRef({ rotX: 0.3, rotY: 0.3 })
  const isDraggingRef = useRef(false)
  const dragStartRef = useRef({ x: 0, y: 0 })
  const hoveredNodeRef = useRef<SimNode | null>(null)
  const draggedNodeRef = useRef<SimNode | null>(null)

  // Simulation physics state
  const nodesRef = useRef<SimNode[]>([])
  const edgesRef = useRef<SimEdge[]>([])
  const animFrameRef = useRef<number | null>(null)
  const lastTimeRef = useRef<number>(performance.now())
  const frameCountRef = useRef<number>(0)

  // 1. Process & filter graph data into simulation nodes and edges
  const { filteredNodes, filteredEdges, blastRadiusNeighbors } = useMemo(() => {
    if (!graph || !graph.nodes || graph.nodes.length === 0) {
      return { filteredNodes: [], filteredEdges: [], blastRadiusNeighbors: new Set<string>() }
    }

    // Identify blast radius neighbors if blastRadiusNodeId is set
    const blastNeighbors = new Set<string>()
    if (blastRadiusNodeId) {
      blastNeighbors.add(blastRadiusNodeId)
      graph.edges.forEach((e) => {
        const s = typeof e.source === 'string' ? e.source : e.source.id
        const t = typeof e.target === 'string' ? e.target : e.target.id
        if (s === blastRadiusNodeId) blastNeighbors.add(t)
        if (t === blastRadiusNodeId) blastNeighbors.add(s)
      })
    }

    // Filter nodes
    const query = searchQuery.toLowerCase().trim()
    const nodeMap = new Map<string, SimNode>()

    graph.nodes.forEach((n) => {
      // Search filter
      if (query && !n.id.toLowerCase().includes(query) && !n.label.toLowerCase().includes(query)) {
        return
      }

      // Severity filter
      const risk = n.risk_score ?? 10
      const sev = (selectedSeverity || 'all').toLowerCase()
      if (sev === 'critical' && risk < 80) return
      if (sev === 'high' && (risk < 60 || risk >= 80)) return
      if (sev === 'medium' && (risk < 30 || risk >= 60)) return
      if (sev === 'vulnerable' && !n.is_vulnerable && risk < 60) return
      if (sev === 'clean' && (n.is_vulnerable || risk >= 60)) return

      // Layer filter
      const lyr = (selectedLayer || 'all').toLowerCase()
      if (lyr !== 'all' && (n.layer || '').toLowerCase() !== lyr) return

      // Node size = centrality (proportional to centrality, min 6px, max 26px)
      const centralityScore = n.centrality ?? 0.3
      const radius = Math.max(6, Math.min(26, 7 + centralityScore * 28))

      // Node color = community or layer
      let color = LAYER_COLORS[n.layer || 'Default'] || '#3b82f6'
      if (n.community !== undefined) {
        color = COMMUNITY_COLORS[n.community % COMMUNITY_COLORS.length]
      }

      // Initial coordinates
      const existing = nodesRef.current.find((prev) => prev.id === n.id)
      const x = existing ? existing.x : (Math.random() - 0.5) * 600
      const y = existing ? existing.y : (Math.random() - 0.5) * 600
      const z = existing ? existing.z : (Math.random() - 0.5) * 300

      const simNode: SimNode = {
        ...n,
        x,
        y,
        z,
        vx: 0,
        vy: 0,
        vz: 0,
        radius,
        color,
      }
      nodeMap.set(n.id, simNode)
    })

    // Filter edges
    const simEdges: SimEdge[] = []
    graph.edges.forEach((e) => {
      const sId = typeof e.source === 'string' ? e.source : e.source.id
      const tId = typeof e.target === 'string' ? e.target : e.target.id

      const sNode = nodeMap.get(sId)
      const tNode = nodeMap.get(tId)

      if (sNode && tNode) {
        simEdges.push({
          source: sNode,
          target: tNode,
          edge_type: e.edge_type,
          is_cycle: Boolean(e.is_cycle),
          weight: e.weight ?? 1.0,
        })
      }
    })

    return {
      filteredNodes: Array.from(nodeMap.values()),
      filteredEdges: simEdges,
      blastRadiusNeighbors: blastNeighbors,
    }
  }, [graph, searchQuery, selectedSeverity, selectedLayer, blastRadiusNodeId])

  // Zoom-to-fit calculation
  const zoomToFit = useCallback(() => {
    const canvas = canvasRef.current
    const nodes = nodesRef.current
    if (!canvas || nodes.length === 0) return

    const width = canvas.width || 800
    const height = canvas.height || 600

    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity
    for (let i = 0; i < nodes.length; i++) {
      const n = nodes[i]
      if (n.x < minX) minX = n.x
      if (n.x > maxX) maxX = n.x
      if (n.y < minY) minY = n.y
      if (n.y > maxY) maxY = n.y
    }

    if (!isFinite(minX) || !isFinite(maxX)) return

    const padding = 70
    const graphWidth = Math.max(120, maxX - minX + padding * 2)
    const graphHeight = Math.max(120, maxY - minY + padding * 2)

    const scaleX = (width * 0.88) / graphWidth
    const scaleY = (height * 0.88) / graphHeight
    const targetZoom = Math.min(1.25, Math.max(0.2, Math.min(scaleX, scaleY)))

    const centerX = (minX + maxX) / 2
    const centerY = (minY + maxY) / 2

    transformRef.current = {
      x: -centerX * targetZoom,
      y: -centerY * targetZoom,
      k: targetZoom,
    }
  }, [])

  // Pre-relaxation pass to immediately separate colliding nodes on load
  const relaxInitialLayout = useCallback(() => {
    const nodes = nodesRef.current
    const edges = edgesRef.current
    const numNodes = nodes.length
    if (numNodes === 0) return

    // Run 35 fast simulation steps
    for (let step = 0; step < 35; step++) {
      for (let i = 0; i < numNodes; i++) {
        const n1 = nodes[i]
        for (let j = i + 1; j < numNodes; j++) {
          const n2 = nodes[j]
          const dx = n2.x - n1.x
          const dy = n2.y - n1.y
          const d2 = dx * dx + dy * dy + 1e-4
          const dist = Math.sqrt(d2)

          // Charge force
          const charge = 500 / d2
          const fx = (dx / dist) * charge
          const fy = (dy / dist) * charge
          n1.vx -= fx
          n1.vy -= fy
          n2.vx += fx
          n2.vy += fy

          // Minimum node spacing to avoid node and label overlap
          const minSpacing = n1.radius + n2.radius + 42
          if (dist < minSpacing) {
            const overlap = minSpacing - dist
            const push = (overlap * 0.5) / dist
            n1.x -= dx * push
            n1.y -= dy * push
            n2.x += dx * push
            n2.y += dy * push
          }
        }
      }

      // Spring tension for edges
      for (let i = 0; i < edges.length; i++) {
        const e = edges[i]
        const dx = e.target.x - e.source.x
        const dy = e.target.y - e.source.y
        const dist = Math.sqrt(dx * dx + dy * dy) + 1e-4
        const force = (dist - 100) * 0.03
        const fx = (dx / dist) * force
        const fy = (dy / dist) * force
        e.source.vx += fx
        e.source.vy += fy
        e.target.vx -= fx
        e.target.vy -= fy
      }

      for (let i = 0; i < numNodes; i++) {
        const n = nodes[i]
        n.vx *= 0.8
        n.vy *= 0.8
        n.x += n.vx
        n.y += n.vy
      }
    }
  }, [])

  // Sync ref and trigger relaxation & zoom-to-fit on load
  useEffect(() => {
    nodesRef.current = filteredNodes
    edgesRef.current = filteredEdges
    if (filteredNodes.length > 0) {
      relaxInitialLayout()
      zoomToFit()
    }
  }, [filteredNodes, filteredEdges, relaxInitialLayout, zoomToFit])


  // Force simulation loop (60fps target with LOD and adaptive edge bundling)
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    let pulsePhase = 0

    const render = (time: number) => {
      // FPS measurement
      frameCountRef.current++
      if (time - lastTimeRef.current >= 1000) {
        if (onFpsUpdate) onFpsUpdate(frameCountRef.current)
        frameCountRef.current = 0
        lastTimeRef.current = time
      }

      pulsePhase = (time / 400) % (Math.PI * 2)

      const width = canvas.width
      const height = canvas.height
      const nodes = nodesRef.current
      const edges = edgesRef.current
      const { x: tx, y: ty, k: zoom } = transformRef.current
      const { rotX, rotY } = rot3DRef.current

      // ── Physics Force Simulation Tick ────────────────────────────────────
      const numNodes = nodes.length

      // 1. Center gravity & Layer banding
      for (let i = 0; i < numNodes; i++) {
        const n = nodes[i]

        if (isLayerBands && n.layer) {
          // Horizontal band target Y coordinates
          let targetY = 0
          if (n.layer === 'Presentation') targetY = -220
          else if (n.layer === 'Service') targetY = -70
          else if (n.layer === 'Domain') targetY = 80
          else if (n.layer === 'Data / Infrastructure') targetY = 230
          n.vy += (targetY - n.y) * 0.04
          n.vx *= 0.88
        } else {
          // Radial gravity to center
          n.vx -= n.x * 0.001
          n.vy -= n.y * 0.001
        }

        // Community cluster attraction when collapsed
        if (clustersCollapsed && n.community !== undefined) {
          const angle = (n.community * Math.PI * 2) / 6
          const targetClusterX = Math.cos(angle) * 160
          const targetClusterY = Math.sin(angle) * 160
          n.vx += (targetClusterX - n.x) * 0.02
          n.vy += (targetClusterY - n.y) * 0.02
        }

        if (is3DMode) {
          n.vz -= n.z * 0.001
        }
      }

      // 2. Charge Force & Collision Force with Minimum Node Spacing
      const chargeStrength = numNodes > 1000 ? 120 : 450
      for (let i = 0; i < numNodes; i++) {
        const n1 = nodes[i]
        for (let j = i + 1; j < numNodes; j++) {
          const n2 = nodes[j]
          const dx = n2.x - n1.x
          const dy = n2.y - n1.y
          const d2 = dx * dx + dy * dy + 1e-4

          if (d2 < 360000) {
            // max interaction distance ~600px
            const dist = Math.sqrt(d2)
            const charge = chargeStrength / d2
            const fx = (dx / dist) * charge
            const fy = (dy / dist) * charge
            n1.vx -= fx
            n1.vy -= fy
            n2.vx += fx
            n2.vy += fy

            // Minimum node spacing buffer so nodes and their labels never overlap
            const minSpacing = n1.radius + n2.radius + 38
            if (dist < minSpacing) {
              const overlap = minSpacing - dist
              const sep = (overlap / minSpacing) * 0.9
              const sepX = (dx / dist) * sep
              const sepY = (dy / dist) * sep
              n1.vx -= sepX
              n1.vy -= sepY
              n2.vx += sepX
              n2.vy += sepY

              // Gentle spatial separation
              const nudge = (overlap * 0.35) / dist
              n1.x -= dx * nudge
              n1.y -= dy * nudge
              n2.x += dx * nudge
              n2.y += dy * nudge
            }
          }
        }
      }

      // 3. Link spring tension
      const idealDist = isLayerBands ? 60 : 90
      for (let i = 0; i < edges.length; i++) {
        const e = edges[i]
        const dx = e.target.x - e.source.x
        const dy = e.target.y - e.source.y
        const dist = Math.sqrt(dx * dx + dy * dy) + 1e-4
        const force = (dist - idealDist) * 0.03
        const fx = (dx / dist) * force
        const fy = (dy / dist) * force

        e.source.vx += fx
        e.source.vy += fy
        e.target.vx -= fx
        e.target.vy -= fy
      }

      // 4. Position update & velocity damping
      const damping = 0.84
      for (let i = 0; i < numNodes; i++) {
        const n = nodes[i]
        if (draggedNodeRef.current === n) continue
        n.vx *= damping
        n.vy *= damping
        n.x += n.vx
        n.y += n.vy

        if (is3DMode) {
          n.vz *= damping
          n.z += n.vz
        }
      }

      // ── Canvas Rendering ──────────────────────────────────────────────────
      ctx.clearRect(0, 0, width, height)
      ctx.save()
      ctx.translate(width / 2 + tx, height / 2 + ty)
      ctx.scale(zoom, zoom)

      const isLight = document.documentElement.getAttribute('data-theme') === 'light'

      // Layer band background stripes when layer view is active
      if (isLayerBands) {
        const bands = [
          { name: 'PRESENTATION LAYER', y: -260, h: 100, color: isLight ? 'rgba(56, 189, 248, 0.08)' : 'rgba(56, 189, 248, 0.05)' },
          { name: 'SERVICE LAYER', y: -110, h: 100, color: isLight ? 'rgba(168, 85, 247, 0.08)' : 'rgba(168, 85, 247, 0.05)' },
          { name: 'DOMAIN LAYER', y: 40, h: 100, color: isLight ? 'rgba(16, 185, 129, 0.08)' : 'rgba(16, 185, 129, 0.05)' },
          { name: 'DATA & INFRASTRUCTURE', y: 190, h: 100, color: isLight ? 'rgba(245, 158, 11, 0.08)' : 'rgba(245, 158, 11, 0.05)' },
        ]
        bands.forEach((b) => {
          ctx.fillStyle = b.color
          ctx.fillRect(-1500, b.y, 3000, b.h)
          ctx.strokeStyle = isLight ? 'rgba(11, 13, 12, 0.08)' : 'rgba(255, 255, 255, 0.05)'
          ctx.lineWidth = 1
          ctx.strokeRect(-1500, b.y, 3000, b.h)
          ctx.fillStyle = isLight ? 'rgba(11, 13, 12, 0.55)' : 'rgba(255, 255, 255, 0.25)'
          ctx.font = '11px "JetBrains Mono", monospace'
          ctx.fillText(b.name, -500, b.y + 20)
        })
      }

      // 3D coordinate projection helper
      const project = (n: SimNode) => {
        if (!is3DMode) return { px: n.x, py: n.y, scale: 1 }
        // 3D Euler rotation around X and Y
        const cosY = Math.cos(rotY)
        const sinY = Math.sin(rotY)
        const cosX = Math.cos(rotX)
        const sinX = Math.sin(rotX)

        const x1 = n.x * cosY + n.z * sinY
        const z1 = -n.x * sinY + n.z * cosY
        const y2 = n.y * cosX - z1 * sinX
        const z2 = n.y * sinX + z1 * cosX

        const fov = 700
        const scale = fov / (fov + z2)
        return { px: x1 * scale, py: y2 * scale, scale: Math.max(0.4, scale) }
      }

      // Draw Edges (with Level-of-Detail / Zoom culling for 5k+ node performance)
      // When zoomed way out (zoom < 0.35) or low-weight, skip tiny edges to sustain 60fps
      const isLODActive = zoom < 0.35 && edges.length > 2000

      for (let i = 0; i < edges.length; i++) {
        const e = edges[i]
        if (isLODActive && !e.is_cycle && e.weight < 2.0) continue

        const p1 = project(e.source)
        const p2 = project(e.target)

        const isCycle = e.is_cycle
        const isBlastActive = blastRadiusNodeId !== null
        const isBlastEdge =
          isBlastActive &&
          blastRadiusNeighbors.has(e.source.id) &&
          blastRadiusNeighbors.has(e.target.id)

        ctx.beginPath()
        ctx.moveTo(p1.px, p1.py)
        ctx.lineTo(p2.px, p2.py)

        if (isCycle) {
          // Circular dependencies: dashed red edge with flow
          ctx.strokeStyle = '#ef4444'
          ctx.lineWidth = 2.2 / zoom
          ctx.setLineDash([6 / zoom, 4 / zoom])
          ctx.lineDashOffset = -time * 0.02
        } else if (isBlastEdge) {
          // High intensity spotlight edge
          ctx.strokeStyle = isLight ? '#0284c7' : '#38bdf8'
          ctx.lineWidth = 2.0 / zoom
          ctx.setLineDash([])
        } else if (isBlastActive) {
          // Dim non-blast edges
          ctx.strokeStyle = isLight ? 'rgba(11, 13, 12, 0.04)' : 'rgba(255, 255, 255, 0.03)'
          ctx.lineWidth = 0.5 / zoom
          ctx.setLineDash([])
        } else {
          ctx.strokeStyle = isLight ? 'rgba(11, 13, 12, 0.18)' : 'rgba(255, 255, 255, 0.12)'
          ctx.lineWidth = Math.min(2.0, Math.max(0.6, e.weight * 0.8)) / zoom
          ctx.setLineDash([])
        }

        ctx.stroke()
      }
      ctx.setLineDash([])

      // Draw Nodes
      for (let i = 0; i < numNodes; i++) {
        const n = nodes[i]
        const p = project(n)
        const r = n.radius * p.scale

        const isSelected = selectedNodeId === n.id
        const isHovered = hoveredNodeRef.current === n
        const isVulnerable = n.is_vulnerable || (n.risk_score ?? 0) >= 60
        const isBlastActive = blastRadiusNodeId !== null
        const inBlastRadius = blastRadiusNeighbors.has(n.id)

        // Dim node if blast radius is active and node is not in blast
        const alpha = isBlastActive && !inBlastRadius ? 0.15 : 1.0

        ctx.save()
        ctx.globalAlpha = alpha

        // Red glow & pulsing circle for high risk / vulnerability
        if (isVulnerable) {
          const pulse = (Math.sin(pulsePhase) + 1) * 0.5
          const glowR = r + 6 + pulse * 6
          const grad = ctx.createRadialGradient(p.px, p.py, r, p.px, p.py, glowR)
          grad.addColorStop(0, 'rgba(239, 68, 68, 0.7)')
          grad.addColorStop(1, 'rgba(239, 68, 68, 0)')

          ctx.fillStyle = grad
          ctx.beginPath()
          ctx.arc(p.px, p.py, glowR, 0, Math.PI * 2)
          ctx.fill()
        }

        // Selected / Hovered highlight ring
        if (isSelected || isHovered) {
          ctx.strokeStyle = isLight ? '#0F172A' : '#ffffff'
          ctx.lineWidth = 2.5 / zoom
          ctx.beginPath()
          ctx.arc(p.px, p.py, r + 4, 0, Math.PI * 2)
          ctx.stroke()
        }

        // Node Body
        ctx.fillStyle = isVulnerable ? '#ef4444' : n.color
        ctx.beginPath()
        ctx.arc(p.px, p.py, r, 0, Math.PI * 2)
        ctx.fill()

        // Subtle dark border
        ctx.strokeStyle = isLight ? 'rgba(11, 13, 12, 0.25)' : '#060606'
        ctx.lineWidth = 1.2
        ctx.stroke()

        // Node Label (Visible if zoomed in or node is prominent/selected)
        const showLabel = zoom > 0.7 || isSelected || isHovered || n.radius > 16
        if (showLabel) {
          ctx.fillStyle = isSelected ? (isLight ? '#0284c7' : '#38bdf8') : (isLight ? '#0F172A' : '#ffffff')
          ctx.font = `${Math.max(9, Math.min(13, 11 / zoom))}px "JetBrains Mono", monospace`
          ctx.textAlign = 'center'
          ctx.textBaseline = 'top'
          ctx.fillText(n.label || n.id, p.px, p.py + r + 3)
        }

        ctx.restore()
      }

      ctx.restore()
      animFrameRef.current = requestAnimationFrame(render)
    }

    animFrameRef.current = requestAnimationFrame(render)

    return () => {
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current)
    }
  }, [
    is3DMode,
    isLayerBands,
    clustersCollapsed,
    selectedNodeId,
    blastRadiusNodeId,
    blastRadiusNeighbors,
    onFpsUpdate,
  ])

  // Resize canvas to fill parent container
  useEffect(() => {
    const canvas = canvasRef.current
    const container = containerRef.current
    if (!canvas || !container) return

    const handleResize = () => {
      const rect = container.getBoundingClientRect()
      const w = Math.floor(rect.width) || container.clientWidth || 800
      const h = Math.floor(rect.height) || container.clientHeight || 600
      if (canvas.width !== w || canvas.height !== h) {
        canvas.width = w
        canvas.height = h
      }
    }

    handleResize()
    const observer = new ResizeObserver(handleResize)
    observer.observe(container)
    window.addEventListener('resize', handleResize)
    return () => {
      observer.disconnect()
      window.removeEventListener('resize', handleResize)
    }
  }, [])

  // Mouse & Touch interaction handlers for pan, zoom, click, drag
  const handleMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current
    if (!canvas) return
    const rect = canvas.getBoundingClientRect()
    const mx = e.clientX - rect.left
    const my = e.clientY - rect.top

    isDraggingRef.current = true
    dragStartRef.current = { x: mx, y: my }

    // Hit test for clicked node
    const { x: tx, y: ty, k: zoom } = transformRef.current
    const worldX = (mx - canvas.width / 2 - tx) / zoom
    const worldY = (my - canvas.height / 2 - ty) / zoom

    let hitNode: SimNode | null = null
    for (let i = nodesRef.current.length - 1; i >= 0; i--) {
      const n = nodesRef.current[i]
      const dx = n.x - worldX
      const dy = n.y - worldY
      if (dx * dx + dy * dy <= n.radius * n.radius * 1.5) {
        hitNode = n
        break
      }
    }

    if (hitNode) {
      draggedNodeRef.current = hitNode
      onNodeClick(hitNode)
    }
  }

  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current
    if (!canvas) return
    const rect = canvas.getBoundingClientRect()
    const mx = e.clientX - rect.left
    const my = e.clientY - rect.top

    if (isDraggingRef.current) {
      const dx = mx - dragStartRef.current.x
      const dy = my - dragStartRef.current.y

      if (draggedNodeRef.current) {
        // Dragging a node in 2D
        const zoom = transformRef.current.k
        draggedNodeRef.current.x += dx / zoom
        draggedNodeRef.current.y += dy / zoom
      } else if (is3DMode) {
        // Rotating in 3D mode
        rot3DRef.current.rotY += dx * 0.005
        rot3DRef.current.rotX += dy * 0.005
      } else {
        // Panning in 2D
        transformRef.current.x += dx
        transformRef.current.y += dy
      }

      dragStartRef.current = { x: mx, y: my }
    } else {
      // Hover hit-test
      const { x: tx, y: ty, k: zoom } = transformRef.current
      const worldX = (mx - canvas.width / 2 - tx) / zoom
      const worldY = (my - canvas.height / 2 - ty) / zoom

      let hovered: SimNode | null = null
      for (let i = nodesRef.current.length - 1; i >= 0; i--) {
        const n = nodesRef.current[i]
        const dx = n.x - worldX
        const dy = n.y - worldY
        if (dx * dx + dy * dy <= n.radius * n.radius * 1.5) {
          hovered = n
          break
        }
      }
      hoveredNodeRef.current = hovered
      canvas.style.cursor = hovered ? 'pointer' : isDraggingRef.current ? 'grabbing' : 'grab'
    }
  }

  const handleMouseUp = () => {
    isDraggingRef.current = false
    draggedNodeRef.current = null
  }

  const handleWheel = (e: React.WheelEvent<HTMLCanvasElement>) => {
    e.preventDefault()
    const zoomFactor = e.deltaY < 0 ? 1.12 : 0.89
    const newK = Math.max(0.1, Math.min(6.0, transformRef.current.k * zoomFactor))
    transformRef.current.k = newK
  }

  return (
    <div
      ref={containerRef}
      id="graph-viewport"
      className="relative w-full h-full min-h-[500px] overflow-hidden select-none bg-transparent"
    >
      <canvas
        ref={canvasRef}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onWheel={handleWheel}
        className="w-full h-full block cursor-grab active:cursor-grabbing"
      />
    </div>
  )
}
