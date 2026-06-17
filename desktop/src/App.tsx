import { useEffect, useState } from "react";
import { api } from "./api";
import { ConnectPanel } from "./components/ConnectPanel";
import { LibraryView } from "./components/LibraryView";
import "./App.css";

type Phase = "starting" | "disconnected" | "connected";

export default function App() {
  const [phase, setPhase] = useState<Phase>("starting");
  const [userName, setUserName] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      // Wait for the Python sidecar to come up, then check connection.
      for (let i = 0; i < 40 && !cancelled; i++) {
        if (await api.health()) break;
        await new Promise((r) => setTimeout(r, 500));
      }
      if (cancelled) return;
      try {
        const s = await api.authStatus();
        setUserName(s.user_name);
        setPhase(s.connected ? "connected" : "disconnected");
      } catch {
        setPhase("disconnected");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  async function logout() {
    await api.logout();
    setUserName(null);
    setPhase("disconnected");
  }

  if (phase === "starting") {
    return (
      <div className="center">
        <div className="card">
          <h1>Tidal Manager</h1>
          <p className="muted">Starting…</p>
          <div className="spinner" />
        </div>
      </div>
    );
  }

  if (phase === "disconnected") {
    return (
      <ConnectPanel
        onConnected={(name) => {
          setUserName(name);
          setPhase("connected");
        }}
      />
    );
  }

  return (
    <div className="app">
      <header className="appbar">
        <strong>Tidal Manager</strong>
        <div className="appbar-right">
          <span className="muted">{userName}</span>
          <button className="ghost" onClick={logout}>
            Log out
          </button>
        </div>
      </header>
      <LibraryView />
    </div>
  );
}
