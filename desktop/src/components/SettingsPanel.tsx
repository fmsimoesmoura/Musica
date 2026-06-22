import { useEffect, useState } from "react";
import { api } from "../api";
import type { SettingsView } from "../types";

// Display order + labels. `select` renders a dropdown.
const FIELDS: { key: string; label: string; hint?: string; select?: string[] }[] = [
  { key: "SPOTIFY_CLIENT_ID", label: "Spotify Client ID", hint: "developer.spotify.com → your app" },
  { key: "QOBUZ_APP_ID", label: "Qobuz App ID", hint: "from the Qobuz web player bundle" },
  { key: "LASTFM_API_KEY", label: "Last.fm API Key", hint: "powers Spotify/Qobuz discovery — last.fm/api" },
  { key: "ANTHROPIC_API_KEY", label: "Anthropic API Key", hint: "optional — Claude for discovery" },
  { key: "CURATOR_BACKEND", label: "Discovery AI", hint: "auto picks Claude→Ollama→none", select: ["auto", "anthropic", "ollama", "none"] },
  { key: "OLLAMA_HOST", label: "Ollama host", hint: "local LLM server" },
  { key: "OLLAMA_MODEL", label: "Ollama model" },
  { key: "DISCOVERY_MODEL", label: "Claude model" },
  { key: "SPOTIFY_REDIRECT_URI", label: "Spotify redirect URI", hint: "must match your Spotify app" },
];

export function SettingsPanel({ onClose }: { onClose: () => void }) {
  const [view, setView] = useState<SettingsView | null>(null);
  const [inputs, setInputs] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    api.getSettings().then((v) => {
      setView(v);
      const init: Record<string, string> = {};
      for (const [k, f] of Object.entries(v)) if (!f.secret) init[k] = f.value ?? "";
      setInputs(init);
    }).catch((e) => setError(String(e)));
  }, []);

  async function save() {
    setSaving(true);
    setError(null);
    setSaved(false);
    try {
      // Send non-secret values verbatim; secrets only if the user typed something.
      const payload: Record<string, string> = {};
      for (const f of FIELDS) {
        const isSecret = view?.[f.key]?.secret;
        const val = inputs[f.key];
        if (val === undefined) continue;
        if (isSecret && val === "") continue; // leave existing secret unchanged
        payload[f.key] = val;
      }
      const updated = await api.putSettings(payload);
      setView(updated);
      setSaved(true);
    } catch (e) {
      setError(String(e));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <h2>Settings</h2>
          <button className="ghost" onClick={onClose}>✕</button>
        </div>
        <p className="muted small">
          Keys are stored locally on this machine. Tidal needs none; Spotify/Qobuz/AI need the relevant keys.
        </p>

        <div className="settings-grid">
          {FIELDS.map((f) => {
            const field = view?.[f.key];
            const secretSet = field?.secret && field.configured;
            return (
              <label key={f.key} className="setting">
                <span className="setting-label">{f.label}</span>
                {f.select ? (
                  <select
                    value={inputs[f.key] ?? ""}
                    onChange={(e) => setInputs((s) => ({ ...s, [f.key]: e.target.value }))}
                  >
                    <option value="">(default)</option>
                    {f.select.map((o) => <option key={o} value={o}>{o}</option>)}
                  </select>
                ) : (
                  <input
                    type={field?.secret ? "password" : "text"}
                    value={inputs[f.key] ?? ""}
                    placeholder={secretSet ? "•••••••• (saved — leave blank to keep)" : ""}
                    onChange={(e) => setInputs((s) => ({ ...s, [f.key]: e.target.value }))}
                  />
                )}
                {f.hint && <span className="setting-hint">{f.hint}</span>}
              </label>
            );
          })}
        </div>

        {error && <p className="error">{error}</p>}
        <div className="modal-foot">
          {saved && <span className="muted small">Saved ✓</span>}
          <button className="primary" disabled={saving} onClick={save}>
            {saving ? "Saving…" : "Save"}
          </button>
        </div>
      </div>
    </div>
  );
}
