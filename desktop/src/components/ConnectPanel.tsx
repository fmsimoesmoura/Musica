import { useEffect, useRef, useState } from "react";
import { openUrl } from "@tauri-apps/plugin-opener";
import { api } from "../api";
import type { LinkLogin } from "../types";

export function ConnectPanel({
  onConnected,
  providerName = "Tidal",
}: {
  onConnected: (name: string | null) => void;
  providerName?: string;
}) {
  const [login, setLogin] = useState<LinkLogin | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const pollRef = useRef<number | null>(null);

  useEffect(() => () => {
    if (pollRef.current) window.clearInterval(pollRef.current);
  }, []);

  async function start() {
    setError(null);
    setBusy(true);
    try {
      const l = await api.authStart();
      setLogin(l);
      try {
        await openUrl(l.verification_uri);
      } catch {
        /* user can click the link manually */
      }
      pollRef.current = window.setInterval(() => poll(l.login_id), 2500);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  async function poll(loginId: string) {
    try {
      const r = await api.authPoll(loginId);
      if (r.status === "authorized") {
        if (pollRef.current) window.clearInterval(pollRef.current);
        onConnected(r.user_name);
      } else if (r.status === "expired" || r.status === "unknown") {
        if (pollRef.current) window.clearInterval(pollRef.current);
        setLogin(null);
        setError("Login expired. Please try again.");
      }
    } catch (e) {
      setError(String(e));
    }
  }

  return (
    <div className="center">
      <div className="card">
        <h1>Tidal Manager</h1>
        <p className="muted">Connect your {providerName} account to manage playlists and discover music.</p>

        {!login ? (
          <button className="primary" disabled={busy} onClick={start}>
            {busy ? "Starting…" : `Connect ${providerName}`}
          </button>
        ) : (
          <div className="login-pending">
            <p>Approve the login in your browser:</p>
            <a className="link" onClick={() => openUrl(login.verification_uri)}>
              {login.verification_uri}
            </a>
            <p className="muted">
              Code: <code>{login.user_code}</code> · waiting for approval…
            </p>
            <div className="spinner" />
          </div>
        )}

        {error && <p className="error">{error}</p>}
      </div>
    </div>
  );
}
