// src/api/client.js

// 你可以把后端服务（FastAPI/Node/Java）统一封装在这里。
// 约定：后端返回 { ok: true, data: {...} } 或 { ok:false, error:{message} }

const BASE = import.meta.env.VITE_API_BASE || ''

async function request(path, { method = 'POST', body } = {}) {
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined
  })

  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`HTTP ${res.status}: ${text || res.statusText}`)
  }

  const json = await res.json()
  if (!json?.ok) throw new Error(json?.error?.message || 'Unknown API error')
  return json.data
}

export async function qa(query) {
  // 期望后端返回：
  // { answer: string, evidence?: any, subgraph: { nodes:[], links:[] }, focusNodeIds?: string[] }
  return request('/api/qa', { body: { query } })
}

export async function recommend(payload) {
  // payload: { query?: string, userId?: string, topK?: number, filters?: {...} }
  // 返回：{ items: [{id,name,score,reason?}...], subgraph:{nodes,links}, focusNodeIds?: string[] }
  return request('/api/recommend', { body: payload })
}

// 开发阶段如果你还没接后端，可以用 mock：
export function mockQa(query) {
  const n = (id, name, group) => ({ id, name, group })
  const l = (s, t, type) => ({ source: s, target: t, type })
  const nodes = [
    n('q', 'Query', 'meta'),
    n('a', 'Answer', 'meta'),
    n('e1', '实体A', 'entity'),
    n('e2', '实体B', 'entity'),
    n('r1', '关系R', 'relation')
  ]
  const links = [
    l('q', 'e1', 'mentions'),
    l('e1', 'r1', 'edge'),
    l('r1', 'e2', 'edge'),
    l('e2', 'a', 'supports')
  ]
  return Promise.resolve({
    answer: `这是一个 mock 回答：${query}`,
    evidence: { source: 'mock' },
    subgraph: { nodes, links },
    focusNodeIds: ['e1', 'e2']
  })
}

export function mockRecommend(payload) {
  const items = Array.from({ length: payload?.topK || 5 }).map((_, i) => ({
    id: `item-${i + 1}`,
    name: `推荐条目 ${i + 1}`,
    score: Math.round((0.9 - i * 0.08) * 1000) / 1000,
    reason: '基于图谱相似度 + 路径解释'
  }))
  const nodes = [
    { id: 'u', name: payload?.userId ? `User(${payload.userId})` : 'User', group: 'user' },
    ...items.map(it => ({ id: it.id, name: it.name, group: 'item' })),
    { id: 'f', name: 'Feature', group: 'feature' }
  ]
  const links = items.map(it => ({ source: 'u', target: it.id, type: 'likes?' }))
  links.push({ source: 'u', target: 'f', type: 'has' })
  return Promise.resolve({
    items,
    subgraph: { nodes, links },
    focusNodeIds: ['u', ...items.slice(0, 3).map(x => x.id)]
  })
}
