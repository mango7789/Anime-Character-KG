// src/components/ResultView.jsx

import React from "react";

export default function ResultView({ mode, result, error }) {
  if (error) {
    return (
      <div
        className="result-block"
        style={{ borderColor: "rgba(255,107,107,.35)" }}
      >
        <div style={{ fontWeight: 700, color: "var(--danger)" }}>发生错误</div>
        <div className="notice" style={{ marginTop: 6 }}>
          {String(error.message || error)}
        </div>
      </div>
    );
  }

  if (!result) {
    return (
      <div className="result-block">
        <div style={{ fontWeight: 700 }}>等待输入</div>
        <div className="notice" style={{ marginTop: 6 }}>
          左侧选择模式，在右侧输入并提交。后端返回 subgraph
          后会自动更新左侧图谱并聚焦。
        </div>
      </div>
    );
  }

  if (mode === "qa") {
    return (
      <div className="result-block">
        <div style={{ fontWeight: 700, marginBottom: 8 }}>答案</div>
        <div style={{ whiteSpace: "pre-wrap", lineHeight: 1.55 }}>
          {result.answer}
        </div>
        {result.evidence && (
          <>
            <div style={{ height: 10 }} />
            <div style={{ fontWeight: 700, marginBottom: 6 }}>
              证据 / 解释（可选）
            </div>
            <pre
              style={{
                margin: 0,
                whiteSpace: "pre-wrap",
                color: "var(--muted)",
                fontSize: 12,
              }}
            >
              {JSON.stringify(result.evidence, null, 2)}
            </pre>
          </>
        )}
      </div>
    );
  }

  if (mode === "query") {
    const path = result.path || { nodes: [], links: [] };
    return (
      <div className="result-block">
        <div style={{ fontWeight: 700, marginBottom: 8 }}>路径查询结果</div>
        <div style={{ marginBottom: 6 }}>
          节点数量: {path.nodes.length}，边数量: {path.links.length}
        </div>
      </div>
    );
  }

  // 推荐
  return (
    <div className="result-block">
      <div style={{ fontWeight: 700, marginBottom: 8 }}>推荐结果</div>
      <div style={{ display: "grid", gap: 8 }}>
        {(result.items || []).map((it, idx) => (
          <div
            key={it.id || idx}
            className="result-block"
            style={{ margin: 0 }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                gap: 12,
              }}
            >
              <div style={{ fontWeight: 650 }}>
                {idx + 1}. {it.name || it.id}
              </div>
              <div className="badge">score: {it.score ?? "-"}</div>
            </div>
            {it.reason && (
              <div className="notice" style={{ marginTop: 6 }}>
                {it.reason}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
