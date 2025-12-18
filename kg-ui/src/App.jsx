// src/App.jsx

import React, { useEffect } from 'react'
import Sidebar from './components/Sidebar'
import TopBar from './components/TopBar'
import GraphPanel from './components/GraphPanel'
import InteractionPanel from './components/InteractionPanel'
import { useAppStore, Modes } from './state/useAppStore'

export default function App() {
  const store = useAppStore()

  // 切换模式时：建议清空 result，但保留 graph（你也可以选择全部清空）
  useEffect(() => {
    store.setError(null)
    store.setResult(null)
    store.setFocusNodeIds([])
  }, [store.mode])

  return (
    <div className="app">
      <Sidebar mode={store.mode} setMode={store.setMode} />

      <div className="main">
        <TopBar mode={store.mode} />

        <div className="content">
          <div className="card">
            <div className="split">
              <GraphPanel graph={store.graph} focusNodeIds={store.focusNodeIds} />
              <InteractionPanel mode={store.mode} store={store} />
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
