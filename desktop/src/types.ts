export interface ConnectionStatus {
  connected: boolean;
  user_name: string | null;
}

export interface LinkLogin {
  login_id: string;
  verification_uri: string;
  user_code: string;
  expires_in: number;
}

export interface PollResult {
  status: "pending" | "authorized" | "expired" | "unknown";
  connected: boolean;
  user_name: string | null;
}

export interface ImportSummary {
  playlists: number;
  playlist_tracks: number;
  fav_tracks: number;
  fav_artists: number;
  fav_albums: number;
}

export interface Playlist {
  id: string;
  title: string;
  description: string | null;
  num_tracks: number;
  creator: string | null;
  picture: string | null;
  last_updated: string | null;
}

export interface Track {
  id: number;
  title: string;
  duration: number | null;
  artist_id: number | null;
  artist_name: string | null;
  album_id: number | null;
  album_title: string | null;
  isrc: string | null;
}

export interface Artist {
  id: number;
  name: string;
  picture: string | null;
}

export interface Album {
  id: number;
  title: string;
  artist_name: string | null;
  num_tracks: number | null;
  release_date: string | null;
}

export type FavoriteType = "track" | "artist" | "album";

export interface SearchResults {
  artists: Artist[];
  albums: Album[];
  tracks: Track[];
}
