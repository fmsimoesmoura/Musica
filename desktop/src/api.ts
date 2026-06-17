import type {
  Album,
  Artist,
  ConnectionStatus,
  FavoriteType,
  ImportSummary,
  LinkLogin,
  Playlist,
  PollResult,
  SearchResults,
  Track,
} from "./types";

// The Python sidecar binds to this fixed local port (see backend config).
const BASE = "http://127.0.0.1:8765";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(BASE + path, init);
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new Error(`${res.status} ${res.statusText} ${detail}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  async health(): Promise<boolean> {
    try {
      await req("/health");
      return true;
    } catch {
      return false;
    }
  },
  authStatus: () => req<ConnectionStatus>("/auth/status"),
  authStart: () => req<LinkLogin>("/auth/start", { method: "POST" }),
  authPoll: (loginId: string) =>
    req<PollResult>(`/auth/poll?login_id=${encodeURIComponent(loginId)}`),
  logout: () => req<{ connected: boolean }>("/auth/logout", { method: "POST" }),

  importLibrary: () => req<ImportSummary>("/library/import", { method: "POST" }),
  playlists: () => req<Playlist[]>("/playlists"),
  playlistTracks: (id: string) =>
    req<Track[]>(`/playlists/${encodeURIComponent(id)}/tracks`),
  favoriteArtists: () => req<Artist[]>("/favorites?type=artists"),
  favoriteTracks: () => req<Track[]>("/favorites?type=tracks"),
  favoriteAlbums: () => req<Album[]>("/favorites?type=albums"),

  search: (q: string, include = "artists,albums,tracks") =>
    req<SearchResults>(`/search?q=${encodeURIComponent(q)}&include=${include}`),
  addFavorite: (type: FavoriteType, id: string) =>
    req<{ ok: boolean }>(`/favorites/${type}/${encodeURIComponent(id)}`, { method: "POST" }),
  removeFavorite: (type: FavoriteType, id: string) =>
    req<{ ok: boolean }>(`/favorites/${type}/${encodeURIComponent(id)}`, { method: "DELETE" }),
};
