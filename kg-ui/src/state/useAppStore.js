// src/state/useAppStore.js

import { useMemo, useState } from 'react'

export const Modes = {
  QA: 'qa',
  REC: 'rec'
}

export function useAppStore() {
  const [mode, setMode] = useState(Modes.QA)

  // 当前展示的图谱数据（全局）
  const [graph, setGraph] = useState({ nodes: [], links: [] })

  // 最后一次任务结果（右侧面板展示）
  const [result, setResult] = useState(null)

  // 聚焦节点（用于自动 zoomToFit）
  const [focusNodeIds, setFocusNodeIds] = useState([])

  // loading / error
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState(null)

  const api = useMemo(() => ({
    mode, setMode,
    graph, setGraph,
    result, setResult,
    focusNodeIds, setFocusNodeIds,
    isLoading, setIsLoading,
    error, setError
  }), [mode, graph, result, focusNodeIds, isLoading, error])

  return api
}
