import type {
  Album,
  Artist,
  ConnectionStatus,
  DiscoveryResult,
  FavoriteType,
  ImportSummary,
  LinkLogin,
  Playlist,
  PollResult,
  ProviderInfo,
  SearchResults,
  SettingsView,
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
  loginCredentials: (username: string, password: string) =>
    req<ConnectionStatus>("/auth/credentials", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    }),

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

  discover: (limit = 12) =>
    req<DiscoveryResult>(`/discover?limit=${limit}`, { method: "POST" }),
  discoverBackend: () => req<{ backend: string }>("/discover/backend"),
  getSettings: () => req<SettingsView>("/settings"),
  putSettings: (values: Record<string, string>) =>
    req<SettingsView>("/settings", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(values),
    }),

  providers: () => req<ProviderInfo[]>("/providers"),
  setProvider: (provider: string) =>
    req<{ active: string }>("/providers/active", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ provider }),
    }),

  saveDiscovery: (name: string, artistIds: string[]) =>
    req<{ playlist_id: string; track_count: number }>("/discover/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, artist_ids: artistIds, tracks_per_artist: 1 }),
    }),

  createPlaylist: (title: string) =>
    req<{ playlist_id: string }>("/playlists", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title }),
    }),
  deletePlaylist: (id: string) =>
    req<{ ok: boolean }>(`/playlists/${encodeURIComponent(id)}`, { method: "DELETE" }),
};
