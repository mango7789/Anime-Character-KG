// src/components/GraphPanel.jsx

import React, { useEffect, useMemo, useRef, useState } from 'react'
import ForceGraph2D from 'react-force-graph-2d'

function buildIndex(nodes) {
  const m = new Map()
  for (const n of nodes || []) m.set(String(n.id), n)
  return m
}

export default function GraphPanel({ graph, focusNodeIds }) {
  const fgRef = useRef(null)
  const [hoverNode, setHoverNode] = useState(null)

  const nodeIndex = useMemo(() => buildIndex(graph?.nodes), [graph?.nodes])

  // 自动聚焦：当 focusNodeIds 或 graph 变化后触发
  useEffect(() => {
    if (!fgRef.current) return
    if (!graph?.nodes?.length) return

    // 只在有 focusNodeIds 时 zoomToFit；否则轻微自适应全图
    const ids = (focusNodeIds || []).map(String)
    const hasFocus = ids.length > 0 && ids.some(id => nodeIndex.has(id))

    const fg = fgRef.current

    // 让力导向先稳定一下再 zoom
    const t = setTimeout(() => {
      try {
        if (hasFocus) {
          const focusNodes = ids.map(id => nodeIndex.get(id)).filter(Boolean)
          // 对 focusNodes 的边界进行适配：用“临时子图”方式交给 zoomToFit
          // react-force-graph 的 zoomToFit 会基于当前画布上的节点坐标，因此只需传入 padding + duration
          fg.zoomToFit(700, 60)
          // 再把视角 center 到 focusNodes 的几何中心
          const cx = focusNodes.reduce((a, n) => a + (n.x || 0), 0) / focusNodes.length
          const cy = focusNodes.reduce((a, n) => a + (n.y || 0), 0) / focusNodes.length
          fg.centerAt(cx, cy, 700)
        } else {
          fg.zoomToFit(700, 60)
        }
      } catch {
        // 忽略偶发的坐标未准备好错误
      }
    }, 250)

    return () => clearTimeout(t)
  }, [graph, focusNodeIds, nodeIndex])

  const paintNode = (node, ctx, globalScale) => {
    const label = node.name || node.id
    const fontSize = Math.max(10, 12 / globalScale)
    ctx.font = `${fontSize}px sans-serif`

    // 圆点
    const r = node.group === 'meta' ? 7 : node.group === 'relation' ? 6 : 8
    ctx.beginPath()
    ctx.arc(node.x, node.y, r, 0, 2 * Math.PI, false)
    // 不指定颜色（满足可定制），用 group 决定透明度，方便你后续换主题
    ctx.fillStyle = node === hoverNode ? 'rgba(255,255,255,.95)' : 'rgba(255,255,255,.75)'
    ctx.fill()

    // 文本背景
    const textWidth = ctx.measureText(label).width
    const pad = 3
    ctx.fillStyle = 'rgba(0,0,0,.35)'
    ctx.fillRect(node.x + r + 2, node.y - fontSize / 2 - pad, textWidth + pad * 2, fontSize + pad * 2)

    // 文本
    ctx.fillStyle = 'rgba(232,238,255,.95)'
    ctx.fillText(label, node.x + r + 2 + pad, node.y + fontSize / 2)
  }

  const linkLabel = (link) => link.type || ''

  return (
    <div className="panel">
      <div className="panel-header">
        <div className="title">图谱子图（可拖动/缩放）</div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button
            className="icon-btn"
            onClick={() => fgRef.current?.zoomToFit?.(700, 60)}
            title="适配视野"
          >
            Fit
          </button>
          <button
            className="icon-btn"
            onClick={() => fgRef.current?.zoom?.(1, 400)}
            title="重置缩放"
          >
            1x
          </button>
        </div>
      </div>

      <ForceGraph2D
        ref={fgRef}
        graphData={graph}
        nodeLabel={(n) => `${n.name || n.id}${n.group ? `\n(${n.group})` : ''}`}
        linkLabel={linkLabel}
        linkDirectionalArrowLength={5}
        linkDirectionalArrowRelPos={1}
        linkCurvature={0.08}
        enableNodeDrag={true}
        cooldownTime={1500}
        onNodeHover={(n) => setHoverNode(n || null)}
        onNodeClick={(n) => {
          // 点击节点：聚焦到该节点
          if (!fgRef.current || !n) return
          fgRef.current.centerAt(n.x, n.y, 500)
          fgRef.current.zoom(2.2, 500)
        }}
        nodeCanvasObject={paintNode}
        nodePointerAreaPaint={(node, color, ctx) => {
          // 增大命中范围
          const r = 10
          ctx.fillStyle = color
          ctx.beginPath()
          ctx.arc(node.x, node.y, r, 0, 2 * Math.PI, false)
          ctx.fill()
        }}
      />
    </div>
  )
}
