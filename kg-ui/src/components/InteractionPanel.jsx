// src/components/InteractionPanel.jsx

import React, { useMemo, useState } from "react";
import { qa, recommend } from "../api/client";
import ResultView from "./ResultView";

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

  // 统一的输入框：问答用 query；推荐用 userId/query/topK
  const [queryText, setQueryText] = useState("");
  const [userId, setUserId] = useState("");
  const [topK, setTopK] = useState(5);

  const placeholder = useMemo(() => {
    return mode === "qa"
      ? "例如：角色“利威尔·阿克曼”出自哪部作品？他的声优是谁？"
      : "例如：为“利威尔·阿克曼”推荐 5 个相关角色或人物。";
  }, [mode]);

  const submit = async () => {
    setError(null);
    setIsLoading(true);
    try {
      let data;
      if (mode === "qa") {
        if (!queryText.trim()) throw new Error("请输入问题");
        data = await qa(queryText.trim());
        setResult({ answer: data.answer, evidence: data.evidence });
      } else {
        const payload = {
          query: queryText.trim() || undefined,
          userId: userId.trim() || undefined,
          topK: Number(topK) || 5,
        };
        data = await recommend(payload);
        setResult({ items: data.items || [] });
      }

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
    setGraph({ nodes: [], links: [] });
    setFocusNodeIds([]);
  };

  return (
    <div className="panel-right">
      <div className="panel-header">
        <div className="title">输入与结果</div>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          {/* <button className="icon-btn" onClick={clearAll}>
            清空
          </button> */}
        </div>
      </div>

      <div className="form">
        {mode === "rec" && (
          <div className="row">
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

        <textarea
          value={queryText}
          onChange={(e) => setQueryText(e.target.value)}
          className="textarea"
          placeholder={placeholder}
        />

        <div className="row">
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
            ) : (
              "生成推荐"
            )}
          </button>
          <button className="secondary" onClick={() => setQueryText("")}>
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
