// src/components/ResultView.jsx

import React from "react";

const styles = {
  block: {
    lineHeight: 1.6,
    fontSize: 13,
  },
  title: {
    fontSize: 14,
    fontWeight: 650,
    marginBottom: 8,
  },
  meta: {
    fontSize: 12,
    color: "var(--muted)",
    marginBottom: 6,
  },
  body: {
    whiteSpace: "pre-wrap",
  },
  note: {
    fontSize: 12,
    color: "var(--muted)",
    marginTop: 6,
    whiteSpace: "pre-wrap",
  },
};

export default function ResultView({ mode, result, error }) {
  // ===== 错误 =====
  if (error) {
    return (
      <div
        className="result-block"
        style={{
          ...styles.block,
          borderColor: "rgba(255,107,107,.35)",
          height: "100%",
          overflowY: "auto",
        }}
      >
        <div style={{ ...styles.title, color: "var(--danger)" }}>发生错误</div>
        <div style={styles.note}>{String(error.message || error)}</div>
      </div>
    );
  }

  // ===== 空状态 =====
  if (!result) {
    return (
      <div className="result-block" style={styles.block}>
        <div style={styles.title}>等待输入</div>
        <div style={styles.note}>
          左侧选择模式，在右侧输入并提交。后端返回 subgraph
          后会自动更新左侧图谱并聚焦。
        </div>
      </div>
    );
  }

  // ===== QA 模式 =====
  if (mode === "qa") {
    return (
      <div
        className="result-block"
        style={{
          ...styles.block,
          height: "100%",
          overflowY: "auto",
        }}
      >
        <div style={styles.title}>答案</div>

        <div style={styles.body}>{result.answer}</div>

        {result.evidence && (
          <>
            <div style={{ height: 10 }} />
            <div style={styles.meta}>证据 / 解释</div>
            <div style={styles.note}>
              {JSON.stringify(result.evidence, null, 2)}
            </div>
          </>
        )}
      </div>
    );
  }

  // ===== 路径查询模式 =====
  if (mode === "query") {
    const path = result.path || { nodes: [], links: [] };
    const shortest = result.shortest || null;
    // console.log(result);

    return (
      <div
        className="result-block"
        style={{
          ...styles.block,
          height: "100%",
          overflowY: "auto",
        }}
      >
        <div style={styles.title}>路径查询结果</div>

        <div style={styles.meta}>
          节点数量 {path.nodes.length} · 边数量 {path.links.length}
        </div>

        {path.nodes.length === 0 && (
          <div style={styles.note}>未找到连接路径</div>
        )}

        {shortest && (
          <div style={{ marginTop: 8 }}>
            <div style={styles.note}>
              最短路径（长度 {result.shortest.length}）
            </div>
            <div style={styles.note}>
              {result.shortest.node_names.join(" → ")}
            </div>
          </div>
        )}
      </div>
    );
  }

  // ===== 推荐模式 =====
  return (
    <div className="result-block" style={styles.block}>
      <div style={styles.title}>推荐结果</div>

      <div style={{ display: "grid", gap: 8 }}>
        {(result.items || []).map((it, idx) => (
          <div
            key={it.id || idx}
            className="result-block"
            style={{ margin: 0, padding: 10 }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "baseline",
                gap: 12,
              }}
            >
              <div style={{ fontWeight: 600 }}>
                {idx + 1}. {it.name || it.id}
              </div>
              <div className="badge" style={{ fontSize: 12 }}>
                score: {it.score ?? "-"}
              </div>
            </div>

            {it.reason && <div style={styles.note}>{it.reason}</div>}
          </div>
        ))}
      </div>
    </div>
  );
}
