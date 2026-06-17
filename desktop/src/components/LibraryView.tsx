import { useEffect, useState } from "react";
import { api } from "../api";
import type { Artist, ImportSummary, Playlist, Track } from "../types";

type Tab = "playlists" | "artists" | "tracks";

export function LibraryView() {
  const [tab, setTab] = useState<Tab>("playlists");
  const [playlists, setPlaylists] = useState<Playlist[]>([]);
  const [artists, setArtists] = useState<Artist[]>([]);
  const [tracks, setTracks] = useState<Track[]>([]);
  const [selected, setSelected] = useState<Playlist | null>(null);
  const [plTracks, setPlTracks] = useState<Track[]>([]);
  const [importing, setImporting] = useState(false);
  const [summary, setSummary] = useState<ImportSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    setError(null);
    try {
      const [p, a, t] = await Promise.all([
        api.playlists(),
        api.favoriteArtists(),
        api.favoriteTracks(),
      ]);
      setPlaylists(p);
      setArtists(a);
      setTracks(t);
    } catch (e) {
      setError(String(e));
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  async function runImport() {
    setImporting(true);
    setError(null);
    try {
      const s = await api.importLibrary();
      setSummary(s);
      await refresh();
    } catch (e) {
      setError(String(e));
    } finally {
      setImporting(false);
    }
  }

  async function openPlaylist(pl: Playlist) {
    setSelected(pl);
    setPlTracks([]);
    try {
      setPlTracks(await api.playlistTracks(pl.id));
    } catch (e) {
      setError(String(e));
    }
  }

  const empty = playlists.length === 0 && artists.length === 0 && tracks.length === 0;

  return (
    <div className="library">
      <div className="toolbar">
        <div className="tabs">
          <button className={tab === "playlists" ? "active" : ""} onClick={() => setTab("playlists")}>
            Playlists ({playlists.length})
          </button>
          <button className={tab === "artists" ? "active" : ""} onClick={() => setTab("artists")}>
            Artists ({artists.length})
          </button>
          <button className={tab === "tracks" ? "active" : ""} onClick={() => setTab("tracks")}>
            Tracks ({tracks.length})
          </button>
        </div>
        <button className="primary" disabled={importing} onClick={runImport}>
          {importing ? "Importing…" : empty ? "Import library" : "Re-sync"}
        </button>
      </div>

      {summary && (
        <p className="muted small">
          Imported {summary.playlists} playlists · {summary.playlist_tracks} playlist tracks ·{" "}
          {summary.fav_artists} artists · {summary.fav_tracks} tracks · {summary.fav_albums} albums
        </p>
      )}
      {error && <p className="error">{error}</p>}
      {empty && !importing && (
        <p className="muted">Your library is empty here. Click “Import library” to pull it from Tidal.</p>
      )}

      <div className="content">
        {tab === "playlists" && (
          <div className="split">
            <ul className="list">
              {playlists.map((p) => (
                <li
                  key={p.id}
                  className={selected?.id === p.id ? "row selected" : "row"}
                  onClick={() => openPlaylist(p)}
                >
                  <span className="title">{p.title || "(untitled)"}</span>
                  <span className="badge">{p.num_tracks}</span>
                </li>
              ))}
            </ul>
            <div className="detail">
              {selected ? (
                <>
                  <h3>{selected.title || "(untitled)"}</h3>
                  <ol className="tracklist">
                    {plTracks.map((t) => (
                      <li key={t.id}>
                        <span className="title">{t.title}</span>
                        <span className="muted"> — {t.artist_name}</span>
                      </li>
                    ))}
                  </ol>
                </>
              ) : (
                <p className="muted">Select a playlist to see its tracks.</p>
              )}
            </div>
          </div>
        )}

        {tab === "artists" && (
          <ul className="list">
            {artists.map((a) => (
              <li key={a.id} className="row">
                <span className="title">{a.name}</span>
              </li>
            ))}
          </ul>
        )}

        {tab === "tracks" && (
          <ul className="list">
            {tracks.map((t) => (
              <li key={t.id} className="row">
                <span className="title">{t.title}</span>
                <span className="muted"> — {t.artist_name}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
