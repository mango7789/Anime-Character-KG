// src/components/InteractionPanel.jsx

import React, { useMemo, useState } from 'react'
import { mockQa, mockRecommend, qa, recommend } from '../api/client'
import ResultView from './ResultView'


export default function InteractionPanel({ mode, store }) {
  const {
    setGraph,
    setResult,
    setFocusNodeIds,
    isLoading,
    setIsLoading,
    error,
    setError
  } = store

  // 统一的输入框：问答用 query；推荐用 userId/query/topK
  const [queryText, setQueryText] = useState('')
  const [userId, setUserId] = useState('')
  const [topK, setTopK] = useState(5)
  const [useMock, setUseMock] = useState(true)

  const placeholder = useMemo(() => {
    return mode === 'qa'
      ? '例如：某药物A的适应症是什么？它与实体B的关系路径？'
      : '例如：我想为 user123 推荐 5 个相关条目，或者输入偏好/约束。'
  }, [mode])

  const submit = async () => {
    setError(null)
    setIsLoading(true)
    try {
      let data
      if (mode === 'qa') {
        if (!queryText.trim()) throw new Error('请输入问题')
        data = useMock ? await mockQa(queryText.trim()) : await qa(queryText.trim())
        setResult({ answer: data.answer, evidence: data.evidence })
      } else {
        const payload = { query: queryText.trim() || undefined, userId: userId.trim() || undefined, topK: Number(topK) || 5 }
        data = useMock ? await mockRecommend(payload) : await recommend(payload)
        setResult({ items: data.items || [] })
      }

      if (data?.subgraph) setGraph(normalizeGraph(data.subgraph))
      setFocusNodeIds((data?.focusNodeIds || []).map(String))

    } catch (e) {
      setError(e)
    } finally {
      setIsLoading(false)
    }
  }

  const clearAll = () => {
    setError(null)
    setResult(null)
    setGraph({ nodes: [], links: [] })
    setFocusNodeIds([])
  }

  return (
    <div className="panel-right">
      <div className="panel-header">
        <div className="title">输入与结果</div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <label className="badge" style={{ cursor: 'pointer' }}>
            <input type="checkbox" checked={useMock} onChange={(e) => setUseMock(e.target.checked)} />
            使用 Mock
          </label>
          <button className="icon-btn" onClick={clearAll}>清空</button>
        </div>
      </div>

      <div className="form">
        {mode === 'rec' && (
          <div className="row">
            <input
              value={userId}
              onChange={(e) => setUserId(e.target.value)}
              placeholder="userId（可选）"
              className="textarea"
              style={{ minHeight: 44, resize: 'none' }}
            />
            <input
              type="number"
              value={topK}
              onChange={(e) => setTopK(e.target.value)}
              min={1}
              max={50}
              className="textarea"
              style={{ minHeight: 44, width: 120, resize: 'none' }}
            />
          </div>
        )}

        <textarea
          value={queryText}
          onChange={(e) => setQueryText(e.target.value)}
          className="textarea"
          placeholder={placeholder}
        />

        <div className="row">
          <button className="primary" onClick={submit} disabled={isLoading}>
            {isLoading ? (
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: 10 }}>
                <span className="spinner" />
                生成中…
              </span>
            ) : (mode === 'qa' ? '提问' : '生成推荐')}
          </button>
          <button className="secondary" onClick={() => setQueryText('')}>清空输入</button>
        </div>

        <div className="notice">
          后端对接建议：
          <ol style={{ margin: '6px 0 0', paddingLeft: 18 }}>
            <li>问答接口返回：answer + subgraph + focusNodeIds</li>
            <li>推荐接口返回：items + subgraph + focusNodeIds</li>
            <li>subgraph: nodes[{`{id,name,group,...}`}] links[{`{source,target,type,...}`}]</li>
          </ol>
        </div>
      </div>

      <hr className="sep" />

      <div className="result">
        <Result mode={mode} store={store} />
      </div>
    </div>
  )
}

function Result({ mode, store }) {
  // 这里做一个轻量的“延迟加载”以避免循环依赖
  // const ResultView = require('./ResultView').default
  return <ResultView mode={mode} result={store.result} error={store.error} />
}

function normalizeGraph(subgraph) {
  // 兼容：source/target 可能是对象（neo4j->前端常见）或字符串
  const nodes = (subgraph.nodes || []).map(n => ({
    id: String(n.id),
    name: n.name ?? n.title ?? n.label ?? String(n.id),
    group: n.group ?? n.type ?? 'entity',
    ...n
  }))

  const links = (subgraph.links || []).map(e => ({
    source: typeof e.source === 'object' ? String(e.source.id) : String(e.source),
    target: typeof e.target === 'object' ? String(e.target.id) : String(e.target),
    type: e.type ?? e.label ?? 'rel',
    ...e
  }))

  return { nodes, links }
}
