import React, { useEffect, useMemo, useRef, useState } from 'react'
import ForceGraph2D from 'react-force-graph-2d'

function buildIndex(nodes) {
  const m = new Map()
  for (const n of nodes || []) m.set(String(n.id), n)
  return m
}

const DEFAULT_GRAPH = {
  nodes: [
    { id: 1, name: 'Alice', group: 'person' },
    { id: 2, name: 'Bob', group: 'person' },
    { id: 3, name: 'Carol', group: 'person' }
  ],
  links: [
    { source: 1, target: 2, type: 'friend' },
    { source: 2, target: 3, type: 'colleague' }
  ]
}

export default function GraphPanel({ graph, focusNodeIds }) {
  const fgRef = useRef(null)
  const [hoverNode, setHoverNode] = useState(null)

  /** ✅ graph 为空时，使用默认图 */
  const graphData =
    graph && graph.nodes && graph.nodes.length > 0 ? graph : DEFAULT_GRAPH

  const nodeIndex = useMemo(
    () => buildIndex(graphData.nodes),
    [graphData.nodes]
  )

  useEffect(() => {
    if (!fgRef.current || !graphData.nodes.length) return

    const fg = fgRef.current
    const ids = (focusNodeIds || []).map(String)
    const hasFocus = ids.length > 0 && ids.some(id => nodeIndex.has(id))

    const t = setTimeout(() => {
      try {
        // 合理 padding，避免缩得过小
        fg.zoomToFit(200, 300)

        if (hasFocus) {
          const focusNodes = ids
            .map(id => nodeIndex.get(id))
            .filter(Boolean)

          const cx =
            focusNodes.reduce((s, n) => s + (n.x || 0), 0) /
            focusNodes.length
          const cy =
            focusNodes.reduce((s, n) => s + (n.y || 0), 0) /
            focusNodes.length

          fg.centerAt(cx, cy, 500)
        }
      } catch { }
    }, 120)

    return () => clearTimeout(t)
  }, [graphData, focusNodeIds, nodeIndex])

  const paintNode = (node, ctx, globalScale) => {
    const label = node.name || node.id
    const fontSize = Math.max(10, 12 / globalScale)
    ctx.font = `${fontSize}px sans-serif`

    const r = 8
    ctx.beginPath()
    ctx.arc(node.x, node.y, r, 0, 2 * Math.PI)
    ctx.fillStyle =
      node === hoverNode
        ? 'rgba(255,255,255,0.95)'
        : 'rgba(255,255,255,0.75)'
    ctx.fill()

    const textWidth = ctx.measureText(label).width
    const pad = 3

    ctx.fillStyle = 'rgba(0,0,0,0.4)'
    ctx.fillRect(
      node.x + r + 4,
      node.y - fontSize / 2 - pad,
      textWidth + pad * 2,
      fontSize + pad * 2
    )

    ctx.fillStyle = '#e8eeff'
    ctx.fillText(label, node.x + r + 4 + pad, node.y + fontSize / 2)
  }

  return (
    <div
      className="panel"
      style={{
        display: 'flex',
        flexDirection: 'column',
        flex: 1,
        minHeight: 0
      }}
    >
      {/* header */}
      <div className="panel-header">
        <div className="title">图谱子图（可拖动 / 缩放）</div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button
            className="icon-btn"
            onClick={() => fgRef.current?.zoomToFit(60, 400)}
          >
            Fit
          </button>
          <button
            className="icon-btn"
            onClick={() => fgRef.current?.zoom(1, 400)}
          >
            1x
          </button>
        </div>
      </div>

      <ForceGraph2D
        ref={fgRef}
        style={{ flex: 1 }}
        graphData={graphData}
        enableNodeDrag
        cooldownTime={1000}

        /** 边：明确样式，保证可见 */
        linkWidth={2}
        linkColor={() => 'rgba(255,255,255,0.6)'}
        linkDirectionalArrowLength={6}
        linkDirectionalArrowRelPos={1}
        linkCurvature={0.08}
        linkLabel={l => l.type || ''}

        nodeLabel={n =>
          `${n.name || n.id}${n.group ? `\n(${n.group})` : ''}`
        }

        onNodeHover={n => setHoverNode(n || null)}
        onNodeClick={n => {
          if (!fgRef.current || !n) return
          fgRef.current.centerAt(n.x, n.y, 500)
          fgRef.current.zoom(2, 500)
        }}

        nodeCanvasObject={paintNode}
        nodePointerAreaPaint={(node, color, ctx) => {
          ctx.fillStyle = color
          ctx.beginPath()
          ctx.arc(node.x, node.y, 10, 0, 2 * Math.PI)
          ctx.fill()
        }}
      />
    </div>
  )
}
