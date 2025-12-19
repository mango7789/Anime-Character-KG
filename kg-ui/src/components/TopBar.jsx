// src/components/TopBar.jsx

import React from 'react'

export default function TopBar({ mode }) {
  return (
    <div className="topbar">
      <h1></h1>
      <div className="badge">
        <span style={{ width: 8, height: 8, borderRadius: 999, background: mode === 'qa' ? 'var(--accent2)' : 'var(--accent)' }} />
        当前模式：{mode === 'qa' ? '问答' : '推荐'}
      </div>
    </div>
  )
}
