// src/App.jsx

import React, { useEffect } from "react";
import Sidebar from "./components/Sidebar";
import TopBar from "./components/TopBar";
import GraphPanel from "./components/GraphPanel";
import InteractionPanel from "./components/InteractionPanel";
import { useAppStore, Modes } from "./state/useAppStore";

export default function App() {
  const store = useAppStore();

  // 切换模式时：建议清空 result，但保留 graph（你也可以选择全部清空）
  useEffect(() => {
    store.setError(null);
    store.setResult(null);
    store.setFocusNodeIds([]);
  }, [store.mode]);

  return (
    <div className="app">
      <Sidebar mode={store.mode} setMode={store.setMode} />

      <div className="main">
        {/* <TopBar mode={store.mode} /> */}

        {/* <div className="content"> */}
          <div className="card">
            <div
              className="split"
              style={{
                display: "flex",
                flexDirection: "row",
                width: "100%",
                height: "100vh"
              }}
            >
              <div
                style={{
                  flexBasis: "70%", 
                  flexGrow: 0,
                  flexShrink: 0,
                  height: "100%",
                  overflow: "hidden",
                }}
              >
                <GraphPanel
                  graph={store.graph}
                  store={store}
                  focusNodeIds={store.focusNodeIds}
                />
              </div>

              <div
                style={{
                  flexBasis: "30%",
                  flexGrow: 0,
                  flexShrink: 0,
                  height: "100%",
                  overflow: "hidden",
                }}
              >
                <InteractionPanel mode={store.mode} store={store} />
              </div>
            </div>
          {/* </div> */}
        </div>
      </div>
    </div>
  );
}
