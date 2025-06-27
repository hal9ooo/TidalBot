import tidalapi
import os
import time
import json
from datetime import datetime
import re # For regex operations in search strategies
from difflib import SequenceMatcher
from tqdm import tqdm
import sys
from fuzzywuzzy import fuzz # For fuzzy matching
from fuzzywuzzy import process # For fuzzy matching
import concurrent.futures # For parallel processing

# --- 1. CONFIGURATION ---
DEBUG_MODE = True # Set to True to enable debug output, False to disable
TIDAL_SEARCH_LIMIT = 5 # Number of tracks to retrieve from Tidal API search
DEBUG_CANDIDATE_LIMIT = 3 # Number of top candidates to show in debug output
# Define the name of the Tidal playlist to be created or updated.
NOME_PLAYLIST = "miss monique fuzzy2"

LISTA_CANZONI = """
Pavel Khvaleev - Connect
Cherry - Euphoria 
Armina - Mindstorm 
David Granha  - Mahuru 
Matchy  - Unforgotten 
Double Disco  - Where You Are 
Miss Monique  - Veselka 
ChangedFaces  - False Hope 
Citizen Kain  - Low Blow 
Weekend Heroes  - Dragonfly 
Hidden Empire  - Morjim At Night 
Andrewboy & RAIDON  - Sign 
Brian Don  - Silo 
Miss Monique & P.O.U - Million Miles Away 
Greenjack  - At night
"""

def datetime_serializer(obj):
    """Serializes datetime objects for JSON output."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError('Type not serializable')

def save_session(session, session_file):
    """Saves session tokens to a JSON file."""
    token_data = {
        'token_type': session.token_type,
        'access_token': session.access_token,
        'refresh_token': session.refresh_token,
        'expiry_time': session.expiry_time
    }
    
    with open(session_file, 'w') as f:
        json.dump(token_data, f, default=datetime_serializer)

def load_session(session_file):
    """Loads session tokens from a JSON file."""
    with open(session_file, 'r') as f:
        token_data = json.load(f)
    
    # Convert expiry_time string to datetime if necessary
    if isinstance(token_data['expiry_time'], str):
        try:
            token_data['expiry_time'] = datetime.fromisoformat(token_data['expiry_time'])
        except ValueError:
            pass
    
    return token_data

def get_full_track_title(session, track):
    """Creates a full title for the track, including the artist.
    If track object is incomplete, fetches full track details using session.
    """
    try:
        # Check if essential attributes are missing or if the title is 'Unknown Title' from a previous fallback
        if not hasattr(track, 'name') or not hasattr(track, 'artist') or not hasattr(track.artist, 'name'):
            if DEBUG_MODE: print(f"DEBUG: Incomplete track object. Attempting to fetch full details for ID: {track.id}")
            full_track = session.track(track.id) # Corrected method: session.track
            if full_track:
                track = full_track # Use the complete track object
                if DEBUG_MODE: print(f"DEBUG: Successfully fetched full track details for ID: {track.id}")
                if DEBUG_MODE: print(f"DEBUG: Full track object details: {track.__dict__}") # Added for full response
            else:
                if DEBUG_MODE: print(f"DEBUG: Failed to fetch full track details for ID: {track.id}")
                # Fallback if fetching fails
                artist_name = track.artist.name if hasattr(track, 'artist') and hasattr(track.artist, 'name') else "Unknown Artist"
                return f"{artist_name} - {track.name if hasattr(track, 'name') else f'Unknown Title (ID: {track.id})'}"

        artist_name = track.artist.name if hasattr(track.artist, 'name') else "Unknown Artist"
        return f"{artist_name} - {track.name}"
    except Exception as e:
        if DEBUG_MODE: print(f"DEBUG: Error getting full track title for track ID {track.id if hasattr(track, 'id') else 'N/A'}: {e}")
        if DEBUG_MODE: print(f"DEBUG: Track object details: {track.__dict__ if hasattr(track, '__dict__') else track}")
        return f"{track.name if hasattr(track, 'name') else f'Track ID: {track.id if hasattr(track, 'id') else 'N/A'}'}"

def calculate_similarity_score(query, track_title, track_artist):
    """Calculates a weighted similarity score for a track."""
    query_lower = query.lower()
    title_lower = track_title.lower()
    artist_lower = track_artist.lower()
    
    # Construct the target string for comparison
    target_string = f"{artist_lower} - {title_lower}"
    
    # Use fuzzywuzzy's token_sort_ratio for the main full title similarity
    # This is generally robust to word order and minor differences
    full_match_similarity = fuzz.token_sort_ratio(query_lower, target_string) / 100
    
    # Keep individual title and artist similarities using SequenceMatcher for precision
    title_similarity = SequenceMatcher(None, query_lower, title_lower).ratio()
    artist_similarity = SequenceMatcher(None, query_lower, artist_lower).ratio()
    
    # Adjust weights. Prioritize the full match, then title, then artist.
    # These weights can be fine-tuned based on testing.
    weighted_score = (full_match_similarity * 0.7) + (title_similarity * 0.2) + (artist_similarity * 0.1)
    
    if DEBUG_MODE: print(f"DEBUG: Query: '{query_lower}'")
    if DEBUG_MODE: print(f"DEBUG: Target: '{target_string}'")
    if DEBUG_MODE: print(f"DEBUG: Full Match Similarity (fuzz.token_sort_ratio): {full_match_similarity:.2f}")
    if DEBUG_MODE: print(f"DEBUG: Title Similarity (SequenceMatcher): {title_similarity:.2f}")
    if DEBUG_MODE: print(f"DEBUG: Artist Similarity (SequenceMatcher): {artist_similarity:.2f}")
    if DEBUG_MODE: print(f"DEBUG: Weighted Score: {weighted_score:.2f}")
    
    return weighted_score

# Cache for search results
search_cache = {}

def search_track(session, query):
    """Searches for a track using different available methods."""
    search_methods = [
        lambda: session.search('tracks', query, limit=TIDAL_SEARCH_LIMIT),
        lambda: session.search(query, limit=TIDAL_SEARCH_LIMIT)
    ]
    
    for method in search_methods:
        try:
            result = method()
            # Handle different response formats
            if isinstance(result, dict) and 'tracks' in result:
                return result['tracks']
            elif hasattr(result, '__iter__') and not isinstance(result, str):
                return list(result)
            else:
                return [result] if result else []
        except (ValueError, AttributeError, TypeError):
            continue
    
    return []

def intelligent_search(session, query, max_results=3):
    """Searches with multiple strategies and ranks results."""
    # Check cache first
    cache_key = query.lower().strip()
    if cache_key in search_cache:
        return search_cache[cache_key]

    strategies = [
        query,  # Original query
        query.replace(" - ", " "),  # Without separator
        " ".join(query.split(" - ")[::-1]) if " - " in query else query,  # Inverted
        re.sub(r'\([^)]*\)', '', query).strip(),  # Remove parentheses and their content
        re.sub(r'(?i)(remix|edit|version|mix|remaster|remastered).*$', '', query).strip(),  # Remove common suffixes
        # Simplified strategies to reduce false positives
        # query.split(" - ")[0] if " - " in query else query,  # Removed: Just the artist
        # query.split(" - ")[1] if " - " in query and len(query.split(" - ")) > 1 else query,  # Removed: Just the title
        # re.sub(r'(?i)(\bft\.|\bfeat\.|\bfeatures\b|\bfeaturing\b).*$', '', query).strip()  # Removed: Remove featuring artists
    ]
    
    unique_results = {}
    
    for strategy in strategies:
        tracks = search_track(session, strategy)
        for track in tracks[:max_results]:
            if track.id not in unique_results:
                # Calculate similarity score
                full_title = get_full_track_title(session, track) # Pass session here
                artist_name = track.artist.name if hasattr(track.artist, 'name') else ""
                similarity = calculate_similarity_score(query, full_title, artist_name)
                unique_results[track.id] = (track, similarity)
                
                # Early termination if we find a near-perfect match (above 0.95 similarity)
                if similarity > 0.95:
                    search_cache[cache_key] = ([track], similarity) # Store both track and similarity
                    return [track], similarity
    
    # Sort by similarity score
    sorted_results = sorted(unique_results.values(), key=lambda x: x[1], reverse=True)
    
    # Get the best track and its similarity
    best_track = sorted_results[0][0] if sorted_results else None
    best_similarity = sorted_results[0][1] if sorted_results else 0.0

    results = [track for track, _ in sorted_results]
    search_cache[cache_key] = (results, best_similarity) # Store both tracks and best similarity
    
    # Return the top candidates for debugging based on DEBUG_CANDIDATE_LIMIT
    top_candidates = []
    for track, score in sorted_results[:DEBUG_CANDIDATE_LIMIT]:
        artist_name = track.artist.name if hasattr(track.artist, 'name') else "Unknown Artist"
        album_title = track.album.name if hasattr(track, 'album') and hasattr(track.album, 'name') else "Unknown Album"
        release_year = track.album.release_date.year if hasattr(track, 'album') and hasattr(track.album, 'release_date') else "Unknown Year"
        top_candidates.append({
            'artist': artist_name,
            'title': track.name if hasattr(track, 'name') else f"Track ID: {track.id}",
            'album': album_title,
            'year': release_year,
            'similarity': score
        })
    
    return results, best_similarity, top_candidates

def find_or_create_playlist(session, playlist_name):
    """Searches for a playlist by name. If not found, creates it."""
    try:
        # Retrieve all user playlists
        user_playlists = session.user.playlists()
        for p in user_playlists:
            if p.name == playlist_name:
                print(f"✅ Playlist '{playlist_name}' found.")
                return p
        
        # If the loop finishes, the playlist was not found
        print(f"⚠️ Playlist '{playlist_name}' not found. Creating it now...")
        description = "Playlist automatically created with a Python script."
        new_playlist = session.user.create_playlist(playlist_name, description)
        print(f"✅ Playlist '{playlist_name}' created successfully.")
        return new_playlist

    except Exception as e:
        print(f"❌ Error managing playlist: {e}")
        return None

def process_songs_with_progress(session, playlist_target, songs_to_add, existing_track_ids):
    """Processes songs with a progress bar and statistics."""
    stats = {
        'added': 0,
        'duplicate': 0,
        'not_found': 0,
        'errors': 0
    }
    
    with tqdm(total=len(songs_to_add), desc="Processing songs") as pbar:
        for song_line in songs_to_add:
            search_query = song_line.strip()
            if not search_query:
                pbar.update(1)
                continue
            
            pbar.set_postfix_str(f"Searching: {search_query[:30]}...")
            
            found_tracks, best_similarity, top_candidates = intelligent_search(session, search_query)

            if DEBUG_MODE and top_candidates:
                print("\nDEBUG: Top 3 Search Candidates:")
                for i, candidate in enumerate(top_candidates):
                    print(f"  {i+1}. Artist: {candidate['artist']}, Title: {candidate['title']}, Album: {candidate['album']}, Year: {candidate['year']}, Similarity: {candidate['similarity']:.2f}")
                print("-" * 30)

            if found_tracks:
                found_track = found_tracks[0]
                full_title = get_full_track_title(session, found_track) # Pass session here
                
                # Define a threshold for "good enough" similarity
                SIMILARITY_THRESHOLD = 0.75 # Adjust as needed

                if best_similarity < SIMILARITY_THRESHOLD:
                    print(f"⚠️ LOW SIMILARITY: Found '{full_title}' with similarity {best_similarity:.2f} for query '{search_query}'. Consider reviewing.\n")

                if found_track.id in existing_track_ids:
                    print(f"🟡 ALREADY PRESENT: '{full_title}' is already in the playlist.\n")
                    stats['duplicate'] += 1
                else:
                    try:
                        playlist_target.add([found_track.id])
                        existing_track_ids.add(found_track.id)
                        print(f"🟢 ADDED: '{full_title}' to playlist '{NOME_PLAYLIST}'.\n")
                        stats['added'] += 1
                    except Exception as e:
                        print(f"🔴 ADDITION ERROR: Could not add '{full_title}'. Error: {e}\n")
                        stats['errors'] += 1
            else:
                print(f"🔴 NOT FOUND: No song found for '{search_query}'.\n")
                stats['not_found'] += 1
            
            pbar.update(1)
            time.sleep(1)
    
    print(f"""
📊 Final Statistics:
   ✅ Added: {stats['added']}
   🟡 Duplicate: {stats['duplicate']}
   ❌ Not Found: {stats['not_found']}
   🔴 Errors: {stats['errors']}
    """)

def main():
    """Main function of the script."""
    # --- 2. AUTHENTICATION ---
    # Initialize Tidal session
    session = tidalapi.Session()
    
    session_file = 'tidal_session.json'
    try:
        if os.path.exists(session_file):
            # Load existing session
            token_data = load_session(session_file)
            success = session.load_oauth_session(
                token_data['token_type'],
                token_data['access_token'],
                token_data['refresh_token'],
                token_data['expiry_time']
            )
            
            if success:
                print("✅ Tidal session loaded successfully.")
            else:
                print("⚠️ Session expired, new authentication required...")
                raise Exception("Session expired")
        else:
            raise FileNotFoundError("No session file found")
            
    except (FileNotFoundError, Exception):
        print("➡️ Starting authentication process...")
        # Perform simple OAuth login
        session.login_oauth_simple()
        
        # Save the new session
        save_session(session, session_file)
        print("✅ Authentication completed and session saved.")
    
    # Verify successful login
    if not session.check_login():
        print("❌ Login failed")
        return
        
    print("-" * 40)
    # Display logged-in user information
    try:
        if hasattr(session.user, 'username') and session.user.username:
            print(f"Logged in as: {session.user.username}")
        else:
            print(f"Logged in as user ID: {session.user.id}")
    except Exception as e:
        print(f"Logged in successfully (ID: {session.user.id})")
    print("-" * 40)

    # --- 3. PLAYLIST AND SONG MANAGEMENT ---
    # Find or create the target playlist
    playlist_target = find_or_create_playlist(session, NOME_PLAYLIST)
    if not playlist_target:
        return # Exit if playlist could not be found or created

    # Get IDs of all tracks already in the playlist for quick checking
    try:
        existing_tracks = playlist_target.tracks()
        # Use a 'set' for super fast duplicate checks
        existing_track_ids = {t.id for t in existing_tracks}
        print(f"The playlist already contains {len(existing_track_ids)} tracks.")
        print("-" * 40)
    except Exception as e:
        print(f"❌ Error retrieving tracks from playlist: {e}")
        return

    # Process the list of songs to add
    songs_to_add = LISTA_CANZONI.strip().split('\n')

    # Process songs with progress and statistics
    process_songs_with_progress(session, playlist_target, songs_to_add, existing_track_ids)

    print("✅ Operation completed.")

if __name__ == "__main__":
    main()
