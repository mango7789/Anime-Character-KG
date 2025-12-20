// src/api/client.js

const BASE_URL = "http://10.176.40.144:5000/api";

async function postApi(endpoint, body) {
  const res = await fetch(`${BASE_URL}/${endpoint}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

// 期望返回 { answer, evidence, subgraph, focusNodeIds }
export async function qa(query) {
  if (!query?.trim()) throw new Error("Query 不能为空");
  return postApi("qa", { query: query.trim() });
}

// 期望返回 { items, subgraph, focusNodeIds }
export async function recommend({ query, userId, topK = 5, filters } = {}) {
  return postApi("recommend", { query, userId, topK: Number(topK), filters });
}

export async function fetchGraph() {
  return postApi("graph/init", {});
}
