// src/api/client.js
import { BASE_URL } from "../components/Constant";

async function postApi(endpoint, body) {
  const res = await fetch(`${BASE_URL}/${endpoint}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  let data;
  try {
    data = await res.json();
  } catch {
    data = null;
  }

  if (!res.ok) {
    throw new Error(data?.error || `HTTP ${res.status}`);
  }

  return data;
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

export async function queryPath({ entityA, entityB }) {
  return postApi("query-path", { entityA, entityB });
}

export async function fetchGraph() {
  return postApi("graph/init", {});
}
