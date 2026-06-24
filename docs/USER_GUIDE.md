# Music Manager — User Guide

A desktop app to manage your music library and discover new artists across
**Tidal**, **Spotify**, and **Qobuz** — all in one place.

This guide is for using the app. (Developers: see the [README](../README.md).)

---

## Contents
1. [Install](#1-install)
2. [Connect a music service](#2-connect-a-music-service)
3. [Settings — entering keys](#3-settings--entering-keys)
4. [Using the app](#4-using-the-app)
5. [Where your data lives & privacy](#5-where-your-data-lives--privacy)
6. [Troubleshooting](#6-troubleshooting)
7. [Good to know / limits](#7-good-to-know--limits)

---

## 1. Install

Download the installer for your computer from the
**[latest release](../../releases/latest)**.

### macOS (Apple Silicon — M1/M2/M3…)
1. Download `Music Manager_<version>_aarch64.dmg`.
2. Double-click it, then drag **Music Manager** into your **Applications** folder.
3. The first time you open it, macOS may say it's from an unidentified developer
   (the app isn't paid-signed). To open it: **right-click the app → Open → Open**.
   You only need to do this once.
4. macOS will ask permission to use your **keychain** — enter your Mac login
   password and click **Always Allow**. This is where your music logins are stored
   securely.

> Intel Macs aren't covered by the prebuilt installer — ask the developer for an
> Intel build, or build from source (see the README).

### Windows (10/11, 64-bit)
1. Download `Music Manager_<version>_x64-setup.exe` and run it.
2. Windows SmartScreen may warn that it's unrecognized (unsigned). Click
   **More info → Run anyway**.
3. If prompted, allow the **WebView2** component to install (Windows 11 already has it).
4. Launch **Music Manager** from the Start menu.

### Windows — portable (no installation / no admin rights)
For locked-down work computers where you can't install software:
1. Download **`Music-Manager-portable-windows.zip`** from the
   [latest release](../../releases/latest).
2. **Right-click → Extract All** to any folder you can write to (Desktop, Documents,
   or a USB stick).
3. Open the extracted **Music Manager** folder and double-click **`Music Manager.exe`**.

No installer, no admin password. Your data and logins are saved under your own user
account. (It needs Microsoft **WebView2**, which is already installed on virtually
all Windows 10/11 machines — including most company ones.)

---

## 2. Connect a music service

At the top of the window there's a **provider switch**: **Tidal · Spotify · Qobuz**.
Pick the service you want, then connect. Each service has its own library and login.

### Tidal — works immediately, no setup
1. Select **Tidal** → click **Connect Tidal**.
2. Your browser opens a Tidal page — log in and approve.
3. Back in the app, you're connected. Click **Import library**.

### Spotify — needs a one-time key (see [Settings](#3-settings--entering-keys))
1. Make sure **Spotify Client ID** and **Last.fm API Key** are set in Settings.
2. Select **Spotify** → **Connect Spotify** → approve in the browser.

### Qobuz — needs an App ID, then your login
1. Make sure **Qobuz App ID** is set in Settings.
2. Select **Qobuz** → enter your Qobuz **email and password** → **Connect**.

You stay logged in between launches — connect once per service. **Log out** is in
the top-right.

---

## 3. Settings — entering keys

Click the **⚙ (gear)** icon at the top-right to open **Settings**. Keys are saved
locally on your computer (you don't need to reinstall or edit files).

| Setting | What it's for | How to get it |
|---|---|---|
| **Spotify Client ID** | Lets the app talk to Spotify | Create an app at [developer.spotify.com](https://developer.spotify.com/dashboard) (no secret needed). Add the redirect URI `http://127.0.0.1:8765/auth/spotify/callback` to it. |
| **Qobuz App ID** | Lets the app talk to Qobuz | From the Qobuz web player (ask the developer if unsure). |
| **Last.fm API Key** | Powers "Discover" for Spotify & Qobuz | Free at [last.fm/api](https://www.last.fm/api/account/create). |
| **Anthropic API Key** | *Optional* — use Claude to write smarter discovery picks | [console.anthropic.com](https://console.anthropic.com/) (paid per use). |
| **Discovery AI** | Which engine writes "why it fits" | `auto` is fine — see [Discover](#discover-new-artists). |

You only need the keys for the services you actually use. **Tidal needs none.**

---

## 4. Using the app

### Import your library
Click **Import library** (or **Re-sync** later). This pulls your **playlists** and
**favorites** (tracks, artists, albums) from the service into the app so browsing is
fast. Re-syncing updates everything in place — it never creates duplicates.

### Browse
Three tabs:
- **Playlists** — your playlists with track counts. Click one to see its tracks.
- **Artists** — your favorite artists.
- **Tracks** — your favorite tracks.

### Search
Open the **Search** tab, type an artist, album, or track, and press Enter. Results
come from the **whole catalog** of the connected service. Tap the **♡ heart** on any
result to add it to your favorites (tap again to remove) — this saves straight to
your account.

### Discover new artists
Open the **Discover** tab and click **Generate**. The app:
1. Looks at your favorite artists,
2. Finds similar artists you don't already have,
3. Ranks them and writes a short reason each one fits your taste.

Then you can:
- **♡** an artist to add them to your favorites, or
- **Save as playlist** — creates a new playlist seeded with a top track from each pick.

**How the "why it fits" text is written** (shown as "Curated by…"):
- **No setup** → ranked by similarity with a simple reason (free, instant).
- **Free + smarter** → install [Ollama](https://ollama.com) and run a local model
  (`ollama pull llama3.1:8b`); the app uses it automatically.
- **Best quality** → set an **Anthropic API Key** in Settings to use Claude.

### Create & delete playlists
On the **Playlists** tab: **New playlist** creates one; hover a playlist and click the
**×** to delete it. Both changes are written to your music service.

### Switch services
Use the provider switch at the top any time. Each service keeps its own library and
stays logged in.

---

## 5. Where your data lives & privacy

- Everything runs **on your computer** — there's no Music Manager server.
- Your imported library is a local database; logins/keys are stored in your
  **operating system's secure credential store** (macOS Keychain / Windows
  Credential Manager), with a restricted local file as fallback.
- The app talks only to the music services you connect (and Last.fm / your chosen AI
  if you enable Discover).

---

## 6. Troubleshooting

**"App can't be opened / unidentified developer" (macOS).** Right-click the app →
**Open** → **Open**. One-time.

**"Windows protected your PC" (SmartScreen).** Click **More info → Run anyway**.

**It keeps asking for keychain access (macOS).** Click **Always Allow** once. (This
can re-appear after an app update — that's expected for an unsigned app.)

**"Not connected" / can't import.** Make sure the right provider is selected at the
top and you've connected it. For Spotify/Qobuz, check the keys in **Settings**.

**Spotify won't connect.** You need a **Spotify Client ID** in Settings, the redirect
URI added to your Spotify app, and — because new Spotify apps are limited — your
Spotify account must be allow-listed on that app (ask whoever set it up).

**Discover says it couldn't find anything.** Import your library first (it needs your
favorite artists to work from), and make sure a **Last.fm API Key** is set for
Spotify/Qobuz.

**Nothing loads at all.** Quit and reopen the app; it needs a moment to start its
background engine on first launch.

---

## 7. Good to know / limits

- **Tidal** and **Qobuz** use each service's internal API (not an official public
  one), so they can occasionally break if the service changes things. For personal
  use this is normally fine.
- **Spotify** discovery uses **Last.fm** for "similar artists" (Spotify retired its
  own version), so it needs a free Last.fm key.
- Search shows the top matches per category, not every possible result.
- The app manages your library — it doesn't play audio.
