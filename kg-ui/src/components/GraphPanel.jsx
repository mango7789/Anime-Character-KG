// src/components/GraphPanel.jsx
import React, {
  useEffect,
  useRef,
  useState,
  useLayoutEffect,
  useMemo,
} from "react";
import ForceGraph2D from "react-force-graph-2d";
import { MODE_BG, MODE_COLORS } from "./Constant";

// 可选调色板
const COLOR_PALETTE = [
  "#1f77b4",
  "#ff7f0e",
  "#2ca02c",
  "#d62728",
  "#9467bd",
  "#8c564b",
  "#e377c2",
  "#7f7f7f",
  "#bcbd22",
  "#17becf",
];

function GraphPanel({ graph, store, focusNodeIds }) {
  const fgRef = useRef(null);
  const panelRef = useRef(null);

  const [hoverNode, setHoverNode] = useState(null);
  const [hoverPos, setHoverPos] = useState({ x: 0, y: 0 });
  const [selectedNode, setSelectedNode] = useState(null);
  const [dimensions, setDimensions] = useState({ width: 400, height: 700 });
  const [searchValue, setSearchValue] = useState("");
  const [originalGraph, setOriginalGraph] = useState(graph);

  const { setGraph, setFocusNodeIds } = store;

  // 根据 graph.nodes 自动生成 group -> color 映射
  const groupColorMap = useMemo(() => {
    const groups = Array.from(
      new Set((graph.nodes || []).map((n) => n.group || "default"))
    );
    const map = {};
    groups.forEach((g, idx) => {
      map[g] = COLOR_PALETTE[idx % COLOR_PALETTE.length];
    });
    return map;
  }, [graph.nodes]);

  // 第一次加载时记录 originalGraph
  useEffect(() => {
    if (!originalGraph || originalGraph.nodes.length === 0) {
      setOriginalGraph(graph);
    }

    setSelectedNode(null);

    const fg = fgRef.current;
    if (fg && graph.nodes.length > 0) {
      const center = getGraphCenter(graph);
      fg.centerAt(center.x, center.y, 0);
      fg.zoom(0.3, 0);
    }
  }, [graph, originalGraph]);

  // 监听 div 尺寸变化
  useLayoutEffect(() => {
    const updateDimensions = () => {
      if (panelRef.current) {
        setDimensions({
          width: panelRef.current.clientWidth,
          height: panelRef.current.clientHeight,
        });
      }
    };
    updateDimensions();
    window.addEventListener("resize", updateDimensions);
    return () => window.removeEventListener("resize", updateDimensions);
  }, []);

  // 计算图中心
  const getGraphCenter = (g = graph) => {
    if (!g?.nodes || g.nodes.length === 0) return { x: 0, y: 0 };
    const avgX =
      g.nodes.reduce((sum, n) => sum + (n.x ?? 0), 0) / g.nodes.length;
    const avgY =
      g.nodes.reduce((sum, n) => sum + (n.y ?? 0), 0) / g.nodes.length;
    return { x: avgX, y: avgY };
  };

  // 重置视图
  const resetGraphView = () => {
    const fg = fgRef.current;
    if (!fg || !originalGraph) return;

    setGraph(originalGraph);
    setSelectedNode(null);
    setFocusNodeIds([]);
    setSearchValue("");

    const center = getGraphCenter(originalGraph);
    fg.centerAt(center.x, center.y, 500);
    fg.zoom(0.3, 500);
  };

  const handleSearchEnter = (e) => {
    if (e.key === "Enter" && searchValue.trim() !== "") {
      const node = graph.nodes.find(
        (n) =>
          n.name.toLowerCase() === searchValue.trim().toLowerCase() ||
          n.id.toString() === searchValue.trim()
      );
      if (node && fgRef.current) {
        setSelectedNode(node);
        fgRef.current.centerAt(node.x, node.y, 500);
      }
    }
  };

  // 绘制节点
  const paintNode = (node, ctx, globalScale) => {
    const r = 5;
    ctx.beginPath();
    ctx.arc(node.x, node.y, r, 0, 2 * Math.PI);

    const fillColor = groupColorMap[node.group || "default"] || "#888";

    // 判断是否高亮
    const hasFocus = focusNodeIds?.length > 0 || selectedNode;
    const isFocused =
      !hasFocus || // 如果没有焦点节点，全部高亮
      (selectedNode && node.id === selectedNode.id) ||
      (focusNodeIds && focusNodeIds.includes(String(node.id)));

    // 设置填充颜色
    ctx.fillStyle = isFocused ? fillColor : `${fillColor}66`;
    ctx.fill();

    // 绘制 label
    const label = node.name || node.id;
    const fontSize = Math.max(8, 10 / globalScale);
    ctx.font = `${fontSize}px sans-serif`;

    let showLabel = isFocused;

    if (!showLabel && selectedNode) {
      const isNeighbor = graph.links.some(
        (l) =>
          (l.source.id === selectedNode.id && l.target.id === node.id) ||
          (l.target.id === selectedNode.id && l.source.id === node.id)
      );
      showLabel = isNeighbor;
    }

    if (showLabel) {
      const textWidth = ctx.measureText(label).width;
      const pad = 2;
      ctx.fillStyle = "rgba(0,0,0,0.4)";
      ctx.fillRect(
        node.x + r + 4,
        node.y - fontSize / 2 - pad,
        textWidth + pad * 2,
        fontSize + pad * 2
      );
      ctx.fillStyle = "#e8eeff";
      ctx.fillText(label, node.x + r + 4 + pad, node.y + fontSize / 2);
    }
  };

  return (
    <div
      ref={panelRef}
      className="panel"
      onMouseMove={(e) => setHoverPos({ x: e.clientX, y: e.clientY })}
      style={{
        display: "flex",
        flexDirection: "column",
        flex: 1,
        minWidth: 0,
        minHeight: 0,
        position: "relative",
      }}
    >
      <div
        className="panel-header"
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          backgroundColor: MODE_BG[store.mode] || "#222",
          // borderLeft: `4px solid ${MODE_COLORS[store.mode] || "#888"}`,
          padding: "4px 8px",
          borderRadius: "4px",
        }}
      >
        <div className="title" style={{ color: "#fff", fontWeight: 600 }}>
          节点数量：{graph.nodes.length}，边数量：{graph.links.length}
        </div>

        {/* 下载按钮 */}
        <button
          className="icon-btn"
          onClick={() => {
            const dataStr =
              "data:text/json;charset=utf-8," +
              encodeURIComponent(JSON.stringify(graph, null, 2));
            const dlAnchor = document.createElement("a");
            dlAnchor.setAttribute("href", dataStr);
            dlAnchor.setAttribute("download", "graph.json");
            dlAnchor.click();
          }}
          style={{
            marginLeft: 8,
            borderRadius: 4,
            height: 32,
            padding: "0 12px",
            fontSize: 14,
          }}
        >
          下载图谱
        </button>

        {/* 搜索 + Reset 包裹 */}
        <div style={{ display: "flex", alignItems: "center", height: 32 }}>
          {/* Reset 按钮 */}
          <button
            className="icon-btn"
            onClick={() => {
              resetGraphView();
              setSearchValue("");
            }}
            style={{
              margin: 0,
              borderRadius: "4px 0 0 4px",
              height: "100%",
              padding: "0 12px",
              fontSize: 14,
            }}
          >
            重置
          </button>

          {/* 搜索框 */}
          <div style={{ position: "relative", height: "100%" }}>
            <input
              type="text"
              list="nodes-list"
              placeholder="搜索节点..."
              value={searchValue}
              onChange={(e) => setSearchValue(e.target.value)}
              onKeyDown={handleSearchEnter}
              style={{
                padding: "0 24px 0 6px",
                fontSize: 14,
                borderRadius: "0 4px 4px 0",
                border: "1px solid #ccc",
                backgroundColor: "#2c2c2c",
                color: "#fff",
                height: "100%",
              }}
            />
            {/* 清空按钮 */}
            {searchValue && (
              <span
                onClick={() => setSearchValue("")}
                style={{
                  position: "absolute",
                  right: 4,
                  top: "50%",
                  transform: "translateY(-50%)",
                  cursor: "pointer",
                  color: "#aaa",
                  fontWeight: "bold",
                  userSelect: "none",
                }}
              >
                ×
              </span>
            )}
          </div>

          <datalist id="nodes-list">
            {graph.nodes.map((n) => (
              <option
                key={n.id}
                value={n.name}
                label={`(${n.group || "default"})`}
              />
            ))}
          </datalist>
        </div>
      </div>

      {/* Legend */}
      <div
        style={{
          marginTop: 8,
          marginBottom: 4,
          display: "flex",
          flexWrap: "wrap",
          gap: 8,
          paddingLeft: 8,
          paddingRight: 8,
        }}
      >
        {Object.entries(groupColorMap).map(([group, color]) => {
          const count = graph.nodes.filter(
            (n) => (n.group || "default") === group
          ).length;
          return (
            <div
              key={group}
              style={{ display: "flex", alignItems: "center", gap: 4 }}
            >
              <span
                style={{
                  width: 12,
                  height: 12,
                  backgroundColor: color,
                  display: "inline-block",
                }}
              />
              <span>
                {group} ({count})
              </span>
            </div>
          );
        })}
      </div>

      {/* HTML Tooltip */}
      {hoverNode && (
        <div
          style={{
            position: "fixed",
            left: hoverPos.x + 12,
            top: hoverPos.y + 12,
            background: "rgba(0,0,0,0.85)",
            color: "#fff",
            padding: "6px 8px",
            fontSize: 14,
            borderRadius: 5,
            pointerEvents: "none",
            whiteSpace: "pre-line",
            zIndex: 1000,
            maxWidth: 250,
            lineHeight: 1.4,
          }}
        >
          <div
            style={{
              fontWeight: 700,
              fontSize: 15,
              marginBottom: 4,
              color: groupColorMap[hoverNode.group || "default"] || "#fff",
            }}
          >
            {hoverNode.name || hoverNode.id} ({hoverNode.group || ""})
          </div>
          {hoverNode.properties && (
            <div>
              {Object.entries(hoverNode.properties).map(([k, v]) => (
                <div key={k}>
                  <strong>{k}</strong>: {Array.isArray(v) ? v.join("、") : v}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      <ForceGraph2D
        ref={fgRef}
        width={dimensions.width}
        height={dimensions.height}
        graphData={graph}
        enableNodeDrag
        cooldownTime={1000}
        linkWidth={2}
        linkColor={(link) => {
          if (!selectedNode) return "rgba(255,255,255,0.6)";
          if (
            link.source.id === selectedNode.id ||
            link.target.id === selectedNode.id
          ) {
            return "rgba(255,255,255,0.8)";
          }
          return "rgba(255,255,255,0.1)";
        }}
        linkDirectionalArrowLength={6}
        linkDirectionalArrowRelPos={1}
        linkCurvature={0.08}
        linkLabel={(l) => l.type || ""}
        onNodeHover={(node) => setHoverNode(node || null)}
        onNodeClick={(n) => {
          if (!fgRef.current || !n) return;
          setSelectedNode(n);
          fgRef.current.centerAt(n.x, n.y, 500);
        }}
        nodeCanvasObject={paintNode}
        nodePointerAreaPaint={(node, color, ctx) => {
          ctx.fillStyle = color;
          ctx.beginPath();
          ctx.arc(node.x, node.y, 10, 0, 2 * Math.PI);
          ctx.fill();
        }}
        nodeLabel={null}
      />
    </div>
  );
}

export default GraphPanel;
