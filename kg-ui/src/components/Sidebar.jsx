// src/components/Sidebar.jsx
import React from "react";
import { Modes } from "../state/useAppStore";
import { MODE_BG, MODE_COLORS } from "./Constant";
import characterImg from "../assets/skele.jpeg";

export default function Sidebar({ mode, setMode }) {
  return (
    <aside className="sidebar">
      <div className="brand">
        <img
          src={characterImg}
          alt="角色图标"
          className="brand-badge"
          style={{ width: 40, height: 40, borderRadius: "50%" }}
        />
        <div>
          <div className="brand-title">Anime Character KG</div>
          <div className="brand-sub" style={{ fontSize: 11 }}>
            基于热门动画角色的知识图谱系统
          </div>
        </div>
      </div>

      <hr className="sidebar-divider" />

      <div className="mode-group">
        {[Modes.QUERY, Modes.QA, Modes.REC].map((m) => {
          const isActive = mode === m;
          const titleMap = {
            [Modes.QUERY]: "查询模式",
            [Modes.QA]: "问答模式",
            [Modes.REC]: "推荐模式",
          };
          const descMap = {
            [Modes.QUERY]: "选择两个实体，查询并展示它们之间的关系路径",
            [Modes.QA]: "输入自然语言问题，返回结构化答案及相关知识子图",
            [Modes.REC]: "输入用户或约束条件，返回推荐结果及可解释子图",
          };

          // 如果是推荐模式按钮，不可点击
          const disabled = m === Modes.REC;

          return (
            <button
              key={m}
              className={`mode-btn ${isActive ? "active" : ""}`}
              onClick={() => !disabled && setMode(m)}
              disabled={disabled}
              style={{
                borderLeft: `4px solid ${MODE_COLORS[m]}`,
                backgroundColor: isActive ? MODE_BG[m] : "transparent",
                cursor: disabled ? "not-allowed" : "pointer",
                opacity: disabled ? 0.5 : 1, // 灰掉不可点击的按钮
              }}
            >
              <div style={{ fontWeight: 650, color: MODE_COLORS[m] }}>
                {titleMap[m]}
              </div>
              <div className="small">{descMap[m]}</div>
            </button>
          );
        })}
      </div>
    </aside>
  );
}
