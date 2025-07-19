import tidalapi
import os
import time
import json
import sys
import re
from datetime import datetime
from difflib import SequenceMatcher
from tqdm import tqdm
from fuzzywuzzy import fuzz

# --- CONSTANTS ---
CONFIG_FILE = 'config.json'
SESSION_FILE = 'tidal_session.json'

# --- CONFIGURATION ---
def load_config(config_file):
    """Loads configuration from a JSON file."""
    if not os.path.exists(config_file):
        print(f"ERROR: Configuration file '{config_file}' not found.")
        sys.exit(1)
    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)
    print(f"[OK] Configuration loaded from '{config_file}'.")
    return config

# Load configuration at startup
config = load_config(CONFIG_FILE)
DEBUG_MODE = config.get('DEBUG_MODE', False)
TIDAL_SEARCH_LIMIT = config.get('TIDAL_SEARCH_LIMIT', 3)
DEBUG_CANDIDATE_LIMIT = config.get('DEBUG_CANDIDATE_LIMIT', 3)
PLAYLIST_NAME = config.get('PLAYLIST_NAME', "Default Playlist Name")
SONG_LIST = config.get('SONG_LIST', [])
SIMILARITY_THRESHOLD = config.get('SIMILARITY_THRESHOLD', 0.75)

# --- SESSION MANAGEMENT ---
def datetime_serializer(obj):
    """Serializes datetime objects for JSON output."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError('Type not serializable')

def save_session(session, session_file):
    """
    Saves session tokens to a JSON file.
    WARNING: This file contains sensitive access tokens.
    Ensure it is stored in a secure location.
    """
    token_data = {
        'token_type': session.token_type,
        'access_token': session.access_token,
        'refresh_token': session.refresh_token,
        'expiry_time': session.expiry_time
    }
    with open(session_file, 'w') as f:
        json.dump(token_data, f, default=datetime_serializer)

def load_session_from_file(session_file):
    """Loads session tokens from a JSON file."""
    with open(session_file, 'r') as f:
        token_data = json.load(f)
    
    if isinstance(token_data.get('expiry_time'), str):
        try:
            token_data['expiry_time'] = datetime.fromisoformat(token_data['expiry_time'])
        except ValueError:
            pass # Keep it as a string if parsing fails
    return token_data

def authenticate_session():
    """Handles the Tidal authentication process, loading or creating a session."""
    session = tidalapi.Session()
    
    if os.path.exists(SESSION_FILE):
        try:
            token_data = load_session_from_file(SESSION_FILE)
            is_loaded = session.load_oauth_session(
                token_data['token_type'],
                token_data['access_token'],
                token_data['refresh_token'],
                token_data['expiry_time']
            )
            if is_loaded and session.check_login():
                print("[OK] Tidal session loaded successfully.")
                return session
            print("[WARN] Session expired or invalid. New authentication required.")
        except (json.JSONDecodeError, KeyError) as e:
            print(f"[WARN] Could not load session file due to error: {e}. Re-authenticating.")

    print("--- Starting new authentication process ---")
    session.login_oauth_simple()
    if session.check_login():
        save_session(session, SESSION_FILE)
        print("[OK] Authentication successful and session saved.")
        return session
    
    print("[ERROR] Login failed.")
    sys.exit(1)


# --- TRACK & PLAYLIST HELPERS ---
def get_full_track_title(track):
    """Creates a standardized full title for a track (Artist - Title)."""
    artist_name = getattr(track.artist, 'name', "Unknown Artist")
    track_name = getattr(track, 'name', f"Unknown Title (ID: {track.id})")
    return f"{artist_name} - {track_name}"

def find_or_create_playlist(session, playlist_name):
    """Searches for a playlist by name. If not found, creates it."""
    try:
        user_playlists = session.user.playlists()
        for p in user_playlists:
            if p.name == playlist_name:
                print(f"[OK] Playlist '{playlist_name}' found.")
                return p
        
        print(f"[INFO] Playlist '{playlist_name}' not found. Creating it...")
        description = "Playlist automatically created by TidalBot script."
        new_playlist = session.user.create_playlist(playlist_name, description)
        print(f"[OK] Playlist '{playlist_name}' created successfully.")
        return new_playlist
    except Exception as e:
        print(f"❌ ERROR: Could not manage playlist: {e}")
        return None

# --- SEARCH & SIMILARITY LOGIC ---
search_cache = {}

def calculate_similarity_score(query, track_title, track_artist):
    """Calculates a weighted similarity score for a track."""
    query_lower = query.lower()
    title_lower = track_title.lower()
    artist_lower = track_artist.lower()
    
    target_string = f"{artist_lower} - {title_lower}"
    
    # Use fuzzywuzzy's token_sort_ratio for robustness to word order.
    full_match_similarity = fuzz.token_sort_ratio(query_lower, target_string) / 100.0
    
    # Use SequenceMatcher for more direct title and artist comparison.
    title_similarity = SequenceMatcher(None, query_lower, title_lower).ratio()
    artist_similarity = SequenceMatcher(None, query_lower, artist_lower).ratio()
    
    # Weighted average. The full match is most important.
    weighted_score = (full_match_similarity * 0.7) + (title_similarity * 0.2) + (artist_similarity * 0.1)
    
    if DEBUG_MODE:
        print(f"\nDEBUG: Query: '{query_lower}'")
        print(f"DEBUG: Target: '{target_string}'")
        print(f"DEBUG: Full Match (fuzz): {full_match_similarity:.2f}, Title: {title_similarity:.2f}, Artist: {artist_similarity:.2f}")
        print(f"DEBUG: Weighted Score: {weighted_score:.2f}")
    
    return weighted_score

def intelligent_search(session, query):
    """Searches with multiple strategies and ranks results by similarity."""
    cache_key = query.lower().strip()
    if cache_key in search_cache:
        return search_cache[cache_key]

    strategies = [
        query,
        query.replace(" - ", " "),
        " ".join(query.split(" - ")[::-1]) if " - " in query else query,
        re.sub(r'\([^)]*\)', '', query).strip(),
        re.sub(r'(?i)(remix|edit|version|mix|remaster|remastered).*$', '', query).strip(),
        re.sub(r'(?i)\s*(ft\.|feat\.|featuring)\s*.*$', '', query).strip(),
    ]
    
    unique_results = {}
    for strategy in set(strategies): # Use set to avoid duplicate searches
        if not strategy: continue
        try:
            tracks = session.search('track', strategy, limit=TIDAL_SEARCH_LIMIT).get('tracks', [])
            for track in tracks:
                if track.id not in unique_results:
                    full_title = get_full_track_title(track)
                    artist_name = getattr(track.artist, 'name', "")
                    similarity = calculate_similarity_score(query, full_title, artist_name)
                    unique_results[track.id] = (track, similarity)
        except Exception as e:
            if DEBUG_MODE: print(f"DEBUG: Search strategy '{strategy}' failed: {e}")

    if not unique_results:
        return [], 0.0, []

    sorted_results = sorted(unique_results.values(), key=lambda x: x[1], reverse=True)
    
    best_similarity = sorted_results[0][1]
    top_tracks = [track for track, _ in sorted_results]
    
    top_candidates = []
    for track, score in sorted_results[:DEBUG_CANDIDATE_LIMIT]:
        top_candidates.append({
            'artist': getattr(track.artist, 'name', "N/A"),
            'title': getattr(track, 'name', "N/A"),
            'album': getattr(track.album, 'name', "N/A"),
            'year': getattr(track.album, 'release_date', "N/A"),
            'similarity': score
        })
    
    search_cache[cache_key] = (top_tracks, best_similarity, top_candidates)
    return top_tracks, best_similarity, top_candidates

# --- SONG PROCESSING ---
def process_song(session, query, playlist, existing_track_ids, stats, warnings):
    """Finds a single song and adds it to the playlist if appropriate."""
    found_tracks, best_similarity, top_candidates = intelligent_search(session, query)

    if DEBUG_MODE and top_candidates:
        print("\nDEBUG: Top Search Candidates:")
        for i, c in enumerate(top_candidates):
            print(f"  {i+1}. {c['artist']} - {c['title']} (Album: {c['album']}, Sim: {c['similarity']:.2f})")
        print("-" * 30)

    if not found_tracks:
        print(f"[FAIL] NOT FOUND: No song found for '{query}'.\n")
        stats['not_found'] += 1
        warnings['not_found'].append(query)
        return

    best_track = found_tracks[0]
    full_title = get_full_track_title(best_track)

    if best_similarity < SIMILARITY_THRESHOLD:
        print(f"⚠️ LOW SIMILARITY: Found '{full_title}' with score {best_similarity:.2f} for query '{query}'.\n")
        warnings['low_similarity'].append({
            'query': query,
            'found_title': full_title,
            'similarity': best_similarity,
            'candidates': top_candidates
        })

    if best_track.id in existing_track_ids:
        print(f"[SKIP] DUPLICATE: '{full_title}' is already in the playlist.\n")
        stats['duplicate'] += 1
    else:
        try:
            playlist.add([best_track.id])
            existing_track_ids.add(best_track.id)
            print(f"[OK] ADDED: '{full_title}' to playlist '{PLAYLIST_NAME}'.\n")
            stats['added'] += 1
        except Exception as e:
            print(f"[FAIL] ADD ERROR: Could not add '{full_title}'. Error: {e}\n")
            stats['errors'] += 1

def print_summary(stats, warnings):
    """Prints a final summary of the operations."""
    print("\n" + "--- Final Statistics ---")
    print(f"   ADDED: {stats['added']}")
    print(f"   DUPLICATES (SKIPPED): {stats['duplicate']}")
    print(f"   NOT FOUND: {stats['not_found']}")
    print(f"   ERRORS: {stats['errors']}")
    print("-" * 24)

    if warnings['low_similarity']:
        print("\n--- Summary of Low Similarity Warnings ---")
        for warn in warnings['low_similarity']:
            print(f"\nQuery: '{warn['query']}'")
            print(f"  -> Found: '{warn['found_title']}' (Similarity: {warn['similarity']:.2f})")
            for i, c in enumerate(warn['candidates']):
                print(f"     {i+1}. {c['artist']} - {c['title']} (Sim: {c['similarity']:.2f})")

    if warnings['not_found']:
        print("\n--- Summary of Not Found Songs ---")
        for i, query in enumerate(warnings['not_found']):
            print(f"{i+1}. {query}")

# --- MAIN EXECUTION ---
def main():
    """Main function of the script."""
    sys.stdout.reconfigure(encoding='utf-8')
    search_cache.clear()

    session = authenticate_session()
    
    print("-" * 40)
    print(f"Logged in as: {getattr(session.user, 'username', f'User ID: {session.user.id}')}")
    print("-" * 40)

    playlist = find_or_create_playlist(session, PLAYLIST_NAME)
    if not playlist:
        sys.exit(1)

    try:
        existing_track_ids = {t.id for t in playlist.tracks()}
        print(f"Playlist currently contains {len(existing_track_ids)} tracks.")
    except Exception as e:
        print(f"❌ ERROR: Could not retrieve tracks from playlist: {e}")
        sys.exit(1)
    
    print("-" * 40)

    stats = {'added': 0, 'duplicate': 0, 'not_found': 0, 'errors': 0}
    warnings = {'low_similarity': [], 'not_found': []}

    with tqdm(total=len(SONG_LIST), desc="Processing songs") as pbar:
        for song_query in SONG_LIST:
            if not song_query.strip():
                pbar.update(1)
                continue
            
            pbar.set_postfix_str(f"Searching: {song_query[:30]}...")
            process_song(session, song_query.strip(), playlist, existing_track_ids, stats, warnings)
            pbar.update(1)
            time.sleep(1) # Be respectful to the API

    print_summary(stats, warnings)
    print("\n[OK] Operation completed.")

if __name__ == "__main__":
    main()
