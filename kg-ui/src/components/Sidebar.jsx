// src/components/Sidebar.jsx

import React from 'react'
import { Modes } from '../state/useAppStore'

export default function Sidebar({ mode, setMode }) {
  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="brand-badge" />
        <div>
          <div className="brand-title">Anime Character KG</div>
          <div className="brand-sub">基于热门动画角色的知识图谱系统</div>
        </div>
      </div>

      <hr className="sidebar-divider" />

      <div className="mode-group">
        <button
          className={`mode-btn ${mode === Modes.QA ? 'active' : ''}`}
          onClick={() => setMode(Modes.QA)}
        >
          <div style={{ fontWeight: 650 }}>问答模式</div>
          <div className="small">
            输入自然语言问题，返回结构化答案及相关知识子图
          </div>
        </button>

        <button
          className={`mode-btn ${mode === Modes.REC ? 'active' : ''}`}
          onClick={() => setMode(Modes.REC)}
        >
          <div style={{ fontWeight: 650 }}>推荐模式</div>
          <div className="small">
            输入用户或约束条件，返回推荐结果及可解释子图
          </div>
        </button>
      </div>


      {/* <div className="small">
        <div style={{ marginBottom: 8, color: 'var(--text)', fontWeight: 650 }}>扩展点</div>
        <ul style={{ paddingLeft: 16, margin: 0, display: 'grid', gap: 6 }}>
          <li>更多任务：抽取/补全/检索</li>
          <li>图谱：节点详情抽屉、路径高亮</li>
          <li>权限：登录/租户/项目空间</li>
        </ul>
      </div> */}

      {/* <div style={{ marginTop: 'auto' }} className="small">
        UI 约定：后端返回 subgraph(nodes/links) + focusNodeIds，即可自动聚焦。
      </div> */}
    </aside>
  )
}
