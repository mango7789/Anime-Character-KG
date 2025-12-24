// src/api/client.js
import { BASE_URL } from "../components/Constant";
import { QA_BASE_URL } from "../components/Constant";

async function postApi(endpoint, body, base_url = BASE_URL) {
  const res = await fetch(`${base_url}/${endpoint}`, {
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
  return postApi("qa", { query: query.trim() }, QA_BASE_URL);
}

// 期望返回 { items, subgraph, focusNodeIds }
export async function recommend({ query, userId, topK = 5, filters } = {}) {
  return postApi("recommend", { query, userId, topK: Number(topK), filters });
}

export async function queryPath({ entityA, entityB }) {
  return postApi("query-path", { entityA, entityB });
}

export async function fetchGraph(mode) {
  return postApi("graph/init", { mode });
}
