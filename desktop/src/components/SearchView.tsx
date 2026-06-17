import { useState } from "react";
import { api } from "../api";
import type { FavoriteType, SearchResults } from "../types";

export function SearchView() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResults | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Optimistic favorite state, keyed by `${type}:${id}`.
  const [faved, setFaved] = useState<Set<string>>(new Set());

  async function run() {
    const q = query.trim();
    if (!q) return;
    setLoading(true);
    setError(null);
    try {
      setResults(await api.search(q));
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  async function toggleFav(type: FavoriteType, id: number | string) {
    const key = `${type}:${id}`;
    const isFaved = faved.has(key);
    // optimistic
    setFaved((prev) => {
      const next = new Set(prev);
      isFaved ? next.delete(key) : next.add(key);
      return next;
    });
    try {
      if (isFaved) await api.removeFavorite(type, String(id));
      else await api.addFavorite(type, String(id));
    } catch (e) {
      // revert on failure
      setFaved((prev) => {
        const next = new Set(prev);
        isFaved ? next.add(key) : next.delete(key);
        return next;
      });
      setError(String(e));
    }
  }

  function Heart({ type, id }: { type: FavoriteType; id: number | string }) {
    const on = faved.has(`${type}:${id}`);
    return (
      <button
        className={on ? "heart on" : "heart"}
        title={on ? "Remove from favorites" : "Add to favorites"}
        onClick={() => toggleFav(type, id)}
      >
        {on ? "♥" : "♡"}
      </button>
    );
  }

  const hasResults =
    results && (results.artists.length || results.albums.length || results.tracks.length);

  return (
    <div className="library">
      <div className="searchbar">
        <input
          autoFocus
          placeholder="Search artists, albums, tracks…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && run()}
        />
        <button className="primary" disabled={loading} onClick={run}>
          {loading ? "Searching…" : "Search"}
        </button>
      </div>

      {error && <p className="error">{error}</p>}
      {results && !hasResults && !loading && <p className="muted">No results.</p>}

      <div className="content search-results">
        {results?.artists.length ? (
          <section>
            <h3>Artists</h3>
            <ul className="list">
              {results.artists.map((a) => (
                <li key={a.id} className="row">
                  <span className="title">{a.name}</span>
                  <Heart type="artist" id={a.id} />
                </li>
              ))}
            </ul>
          </section>
        ) : null}

        {results?.albums.length ? (
          <section>
            <h3>Albums</h3>
            <ul className="list">
              {results.albums.map((a) => (
                <li key={a.id} className="row">
                  <span className="title">
                    {a.title} <span className="muted">— {a.artist_name}</span>
                  </span>
                  <Heart type="album" id={a.id} />
                </li>
              ))}
            </ul>
          </section>
        ) : null}

        {results?.tracks.length ? (
          <section>
            <h3>Tracks</h3>
            <ul className="list">
              {results.tracks.map((t) => (
                <li key={t.id} className="row">
                  <span className="title">
                    {t.title} <span className="muted">— {t.artist_name}</span>
                  </span>
                  <Heart type="track" id={t.id} />
                </li>
              ))}
            </ul>
          </section>
        ) : null}
      </div>
    </div>
  );
}
