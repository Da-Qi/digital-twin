"use client";

import { Component } from "react";

interface Props { children: React.ReactNode; }
interface State { hasError: boolean; error: Error | null; }

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error("ErrorBoundary caught:", error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: 20, textAlign: "center" }}>
          <p style={{ fontSize: 13, color: "#999", margin: 0 }}>消息渲染出错</p>
          <button
            onClick={() => this.setState({ hasError: false, error: null })}
            style={{ marginTop: 8, padding: "4px 12px", fontSize: 12, borderRadius: 6, border: "0.5px solid #ddd", background: "#fff", cursor: "pointer" }}
          >
            重试
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
