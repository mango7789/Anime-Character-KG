// src/components/InteractionPanel.jsx

import React, { useMemo, useState } from "react";
import { qa, recommend, queryPath } from "../api/client";
import ResultView from "./ResultView";
import { MODE_BG, MODE_COLORS } from "./Constant";

export default function InteractionPanel({ mode, store }) {
  const {
    setGraph,
    setResult,
    setFocusNodeIds,
    isLoading,
    setIsLoading,
    error,
    setError,
  } = store;

  // 输入状态
  const [queryText, setQueryText] = useState("");
  const [userId, setUserId] = useState("");
  const [topK, setTopK] = useState(5);
  const [entityA, setEntityA] = useState("");
  const [entityB, setEntityB] = useState("");

  // 占位提示
  const placeholder = useMemo(() => {
    if (mode === "qa") {
      return "例如：角色“利威尔·阿克曼”出自哪部作品？他的声优是谁？";
    } else if (mode === "rec") {
      return "例如：为“利威尔·阿克曼”推荐 5 个相关角色或人物。";
    } else if (mode === "query") {
      return "查询两个实体之间的路径";
    }
  }, [mode]);

  // 提交逻辑
  const submit = async () => {
    setError(null);
    setIsLoading(true);
    try {
      let data;

      if (mode === "qa") {
        if (!queryText.trim()) throw new Error("请输入问题");
        data = await qa(queryText.trim());
        setResult({ answer: data.answer, evidence: data.evidence });
      } else if (mode === "rec") {
        const payload = {
          query: queryText.trim() || undefined,
          userId: userId.trim() || undefined,
          topK: Number(topK) || 5,
        };
        data = await recommend(payload);
        setResult({ items: data.items || [] });
      } else if (mode === "query") {
        if (!entityA.trim() || !entityB.trim())
          throw new Error("请填写两个实体名称");
        console.log(entityA.trim(), entityB.trim());
        data = await queryPath({
          entityA: entityA.trim(),
          entityB: entityB.trim(),
        });
        setResult({ path: data.path || [] });
      }

      // 更新子图和焦点节点
      if (data?.subgraph) setGraph(data.subgraph);
      setFocusNodeIds((data?.focusNodeIds || []).map(String));
    } catch (e) {
      setError(e);
    } finally {
      setIsLoading(false);
    }
  };

  const clearAll = () => {
    setError(null);
    setResult(null);
    setFocusNodeIds([]);
    setQueryText("");
    setUserId("");
    setTopK(5);
    setEntityA("");
    setEntityB("");
  };

  return (
    <div className="panel-right">
      <div
        className="panel-header"
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          backgroundColor: MODE_BG[mode] || "#222",
          // borderLeft: `4px solid ${MODE_COLORS[mode] || "#888"}`,
          padding: "4px 8px",
          borderRadius: "4px",
          height: 41,
        }}
      >
        <div className="title" style={{ color: "#fff", fontWeight: 600 }}>
          输入与结果
        </div>
      </div>

      <div className="form">
        {/* 查询模式输入 */}
        {mode === "query" && (
          <div className="row" style={{ gap: 8 }}>
            <div style={{ flex: 1, position: "relative" }}>
              <input
                list="nodes-list-a"
                value={entityA}
                onChange={(e) => setEntityA(e.target.value)}
                placeholder="实体 A"
                className="textarea"
                style={{ minHeight: 44, resize: "none" }}
              />
              <datalist id="nodes-list-a">
                {store.graph.nodes.map((n) => (
                  <option
                    key={n.id}
                    value={n.name}
                    label={`(${n.group || "default"})`}
                  />
                ))}
              </datalist>
            </div>

            <div style={{ flex: 1, position: "relative" }}>
              <input
                list="nodes-list-b"
                value={entityB}
                onChange={(e) => setEntityB(e.target.value)}
                placeholder="实体 B"
                className="textarea"
                style={{ minHeight: 44, resize: "none" }}
              />
              <datalist id="nodes-list-b">
                {store.graph.nodes.map((n) => (
                  <option
                    key={n.id}
                    value={n.name}
                    label={`(${n.group || "default"})`}
                  />
                ))}
              </datalist>
            </div>
          </div>
        )}

        {/* QA 模式输入 */}
        {mode === "qa" && (
          <textarea
            value={queryText}
            onChange={(e) => setQueryText(e.target.value)}
            className="textarea"
            placeholder={placeholder}
          />
        )}

        {/* 推荐模式输入 */}
        {mode === "rec" && (
          <div className="row" style={{ gap: 8 }}>
            <input
              value={userId}
              onChange={(e) => setUserId(e.target.value)}
              placeholder="userId（可选）"
              className="textarea"
              style={{ minHeight: 44, resize: "none" }}
            />
            <input
              type="number"
              value={topK}
              onChange={(e) => setTopK(e.target.value)}
              min={1}
              max={50}
              className="textarea"
              style={{ minHeight: 44, width: 120, resize: "none" }}
            />
          </div>
        )}

        {/* 提交按钮 */}
        <div className="row" style={{ marginTop: 8 }}>
          <button className="primary" onClick={submit} disabled={isLoading}>
            {isLoading ? (
              <span
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 10,
                }}
              >
                <span className="spinner" />
                生成中…
              </span>
            ) : mode === "qa" ? (
              "提问"
            ) : mode === "rec" ? (
              "生成推荐"
            ) : (
              "查询路径"
            )}
          </button>
          <button className="secondary" onClick={clearAll}>
            清空输入
          </button>
        </div>
      </div>

      <hr className="sep" />

      <div className="result">
        <Result mode={mode} store={store} />
      </div>
    </div>
  );
}

function Result({ mode, store }) {
  return <ResultView mode={mode} result={store.result} error={store.error} />;
}
