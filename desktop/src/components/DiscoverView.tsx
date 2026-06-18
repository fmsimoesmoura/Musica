import { useEffect, useState } from "react";
import { api } from "../api";
import type { DiscoveryResult } from "../types";

const BACKEND_LABEL: Record<string, string> = {
  anthropic: "Claude (API)",
  ollama: "local LLM (Ollama)",
  none: "Tidal similarity (no LLM)",
};

export function DiscoverView() {
  const [result, setResult] = useState<DiscoveryResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [faved, setFaved] = useState<Set<number>>(new Set());
  const [backend, setBackend] = useState<string | null>(null);

  useEffect(() => {
    api.discoverBackend().then((b) => setBackend(b.backend)).catch(() => {});
  }, []);

  async function generate() {
    setLoading(true);
    setError(null);
    try {
      setResult(await api.discover(12));
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState<string | null>(null);

  async function saveAsPlaylist() {
    if (!result || result.recommendations.length === 0) return;
    const name = window.prompt("Playlist name:", "Discoveries");
    if (!name) return;
    setSaving(true);
    setError(null);
    setSaved(null);
    try {
      const r = await api.saveDiscovery(
        name,
        result.recommendations.map((x) => x.artist_id),
      );
      setSaved(`Saved “${name}” — ${r.track_count} tracks added to Tidal.`);
    } catch (e) {
      setError(String(e));
    } finally {
      setSaving(false);
    }
  }

  async function favorite(artistId: number) {
    setFaved((prev) => new Set(prev).add(artistId));
    try {
      await api.addFavorite("artist", String(artistId));
    } catch (e) {
      setFaved((prev) => {
        const next = new Set(prev);
        next.delete(artistId);
        return next;
      });
      setError(String(e));
    }
  }

  return (
    <div className="library">
      <div className="toolbar">
        <div>
          <h2 className="discover-title">Discover new artists</h2>
          <p className="muted small">
            Seeds from your favorites → Tidal's similar artists → ranked &amp; explained.
            {backend && <> Curated by: <strong>{BACKEND_LABEL[backend] ?? backend}</strong>.</>}
          </p>
        </div>
        <div className="toolbar-actions">
          {result && result.recommendations.length > 0 && (
            <button disabled={saving} onClick={saveAsPlaylist}>
              {saving ? "Saving…" : "Save as playlist"}
            </button>
          )}
          <button className="primary" disabled={loading} onClick={generate}>
            {loading ? "Curating…" : "Generate"}
          </button>
        </div>
      </div>

      {error && <p className="error">{error}</p>}
      {saved && <p className="muted small">{saved}</p>}
      {result?.note && <p className="muted">{result.note}</p>}

      {result && result.based_on.length > 0 && (
        <p className="muted small">Based on: {result.based_on.slice(0, 10).join(", ")}</p>
      )}

      <div className="content discover-list">
        {result?.recommendations.map((r) => (
          <div key={r.artist_id} className="rec-card">
            <div className="rec-head">
              <span className="rec-name">{r.name}</span>
              <button
                className={faved.has(r.artist_id) ? "heart on" : "heart"}
                title="Add to favorites"
                disabled={faved.has(r.artist_id)}
                onClick={() => favorite(r.artist_id)}
              >
                {faved.has(r.artist_id) ? "♥" : "♡"}
              </button>
            </div>
            <p className="rec-reason">{r.reason}</p>
          </div>
        ))}
      </div>

      {!result && !loading && (
        <p className="muted">Click “Generate” to discover artists that fit your taste.</p>
      )}
    </div>
  );
}
