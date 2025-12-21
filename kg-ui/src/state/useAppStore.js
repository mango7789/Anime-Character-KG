// src/state/useAppStore.js
import { useMemo, useState, useEffect } from "react";
import { fetchGraph } from "../api/client";

export const Modes = {
  QUERY: "query",
  QA: "qa",
  REC: "rec",
};

export function useAppStore() {
  const [mode, setMode] = useState(Modes.QUERY);

  // 当前展示的图谱数据（全局）
  const [graph, setGraph] = useState({ nodes: [], links: [] });

  // 最后一次任务结果（右侧面板展示）
  const [result, setResult] = useState(null);

  // 聚焦节点（用于自动 zoomToFit）
  const [focusNodeIds, setFocusNodeIds] = useState([]);

  // loading / error
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  // 规范化图谱数据，保证每个节点都有 id/name/group/properties
  function normalizeGraph(subgraph) {
    const nodes = (subgraph.nodes || []).map((n) => ({
      id: String(n.id),
      name: n.name ?? String(n.id),
      group: n.group ?? "entity",
      properties: n.properties ?? {},
      ...n,
    }));

    const links = (subgraph.links || []).map((l) => ({
      source:
        typeof l.source === "object" ? String(l.source.id) : String(l.source),
      target:
        typeof l.target === "object" ? String(l.target.id) : String(l.target),
      type: l.type ?? "rel",
      ...l,
    }));

    return { nodes, links };
  }

  useEffect(() => {
    async function loadGraph() {
      setIsLoading(true);
      setError(null);
      try {
        const data = await fetchGraph(mode);
        setGraph(normalizeGraph(data));
      } catch (err) {
        setError(err?.message || String(err));
      } finally {
        setIsLoading(false);
      }
    }

    loadGraph();
  }, [mode]);

  const api = useMemo(
    () => ({
      mode,
      setMode,
      graph,
      setGraph,
      result,
      setResult,
      focusNodeIds,
      setFocusNodeIds,
      isLoading,
      setIsLoading,
      error,
      setError,
    }),
    [mode, graph, result, focusNodeIds, isLoading, error]
  );

  return api;
}
