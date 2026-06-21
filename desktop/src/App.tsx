import { useEffect, useState } from "react";
import { api } from "./api";
import { ConnectPanel } from "./components/ConnectPanel";
import { LibraryView } from "./components/LibraryView";
import { SearchView } from "./components/SearchView";
import { DiscoverView } from "./components/DiscoverView";
import type { ProviderInfo } from "./types";
import "./App.css";

type Phase = "starting" | "disconnected" | "connected";
type View = "library" | "search" | "discover";

const PROVIDER_LABELS: Record<string, string> = {
  tidal: "Tidal",
  spotify: "Spotify",
  qobuz: "Qobuz",
};
const IMPLEMENTED = new Set(["tidal", "spotify", "qobuz"]);
const CREDENTIALS_PROVIDERS = new Set(["qobuz"]);

export default function App() {
  const [phase, setPhase] = useState<Phase>("starting");
  const [userName, setUserName] = useState<string | null>(null);
  const [view, setView] = useState<View>("library");
  const [providers, setProviders] = useState<ProviderInfo[]>([]);
  const [active, setActive] = useState<string>("tidal");

  async function checkStatus() {
    try {
      const s = await api.authStatus();
      setUserName(s.user_name);
      setPhase(s.connected ? "connected" : "disconnected");
    } catch {
      setPhase("disconnected");
    }
    api.providers().then(setProviders).catch(() => {});
  }

  useEffect(() => {
    let cancelled = false;
    (async () => {
      for (let i = 0; i < 40 && !cancelled; i++) {
        if (await api.health()) break;
        await new Promise((r) => setTimeout(r, 500));
      }
      if (cancelled) return;
      try {
        const list = await api.providers();
        setProviders(list);
        setActive(list.find((p) => p.active)?.provider ?? "tidal");
      } catch {
        /* ignore */
      }
      await checkStatus();
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  async function switchProvider(name: string) {
    if (name === active || !IMPLEMENTED.has(name)) return;
    setPhase("starting");
    setView("library");
    try {
      await api.setProvider(name);
      setActive(name);
      await checkStatus();
    } catch {
      await checkStatus();
    }
  }

  async function logout() {
    await api.logout();
    setUserName(null);
    setPhase("disconnected");
  }

  const providerBar = (
    <div className="provider-bar">
      {(providers.length ? providers : [{ provider: "tidal", active: true, connected: false }]).map((p) => (
        <button
          key={p.provider}
          className={p.provider === active ? "prov active" : "prov"}
          disabled={!IMPLEMENTED.has(p.provider)}
          title={IMPLEMENTED.has(p.provider) ? "" : "Coming soon"}
          onClick={() => switchProvider(p.provider)}
        >
          {PROVIDER_LABELS[p.provider] ?? p.provider}
          {p.connected && <span className="dot" />}
        </button>
      ))}
    </div>
  );

  return (
    <div className="app">
      <header className="appbar">
        <div className="appbar-left">
          <strong>Tidal Manager</strong>
          {providerBar}
          {phase === "connected" && (
            <nav className="nav">
              <button className={view === "library" ? "active" : ""} onClick={() => setView("library")}>
                Library
              </button>
              <button className={view === "search" ? "active" : ""} onClick={() => setView("search")}>
                Search
              </button>
              <button className={view === "discover" ? "active" : ""} onClick={() => setView("discover")}>
                Discover
              </button>
            </nav>
          )}
        </div>
        <div className="appbar-right">
          {phase === "connected" && <span className="muted">{userName}</span>}
          {phase === "connected" && (
            <button className="ghost" onClick={logout}>
              Log out
            </button>
          )}
        </div>
      </header>

      {phase === "starting" && (
        <div className="center">
          <div className="card">
            <p className="muted">Starting…</p>
            <div className="spinner" />
          </div>
        </div>
      )}

      {phase === "disconnected" && (
        <ConnectPanel
          providerName={PROVIDER_LABELS[active] ?? active}
          mode={CREDENTIALS_PROVIDERS.has(active) ? "credentials" : "oauth"}
          onConnected={(name) => {
            setUserName(name);
            setPhase("connected");
          }}
        />
      )}

      {phase === "connected" && (
        <div key={active} className="body">
          {view === "library" && <LibraryView />}
          {view === "search" && <SearchView />}
          {view === "discover" && <DiscoverView />}
        </div>
      )}
    </div>
  );
}
