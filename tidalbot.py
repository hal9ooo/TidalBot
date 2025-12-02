import tidalapi
import os
import time
import json
import logging
import re
import sys
from datetime import datetime
from difflib import SequenceMatcher
from typing import List, Dict, Any, Optional, Tuple, Set, Union

from tqdm import tqdm
from fuzzywuzzy import fuzz

# Configure stdout to use UTF-8
sys.stdout.reconfigure(encoding='utf-8')

class TidalBot:
    """
    A bot to automate playlist creation on Tidal based on a list of songs.
    """

    def __init__(self, config_file: str = 'config.json', session_file: str = 'tidal_session.json'):
        self.config_file = config_file
        self.session_file = session_file
        self.config = self.load_configuration()
        self.session = tidalapi.Session()
        self.search_cache: Dict[str, Any] = {}
        
        # Load configuration values
        self.debug_mode = self.config.get('DEBUG_MODE', False)
        self.tidal_search_limit = self.config.get('TIDAL_SEARCH_LIMIT', 3)
        self.debug_candidate_limit = self.config.get('DEBUG_CANDIDATE_LIMIT', 3)
        self.playlist_name = self.config.get('PLAYLIST_NAME', "My TidalBot Playlist")
        self.song_list = self.config.get('SONG_LIST', [])
        self.raw_tracklist = self.config.get('RAW_TRACKLIST', [])
        self.similarity_threshold = self.config.get('SIMILARITY_THRESHOLD', 0.75)

        # Parse raw tracklist and append to song_list
        if self.raw_tracklist:
            lines = []
            # Check if it's a file path
            if isinstance(self.raw_tracklist, str) and os.path.exists(self.raw_tracklist):
                try:
                    with open(self.raw_tracklist, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                    logging.info(f"Loaded tracklist from file: {self.raw_tracklist}")
                except Exception as e:
                    logging.error(f"Error reading tracklist file: {e}")
            
            # Fallback: Handle if RAW_TRACKLIST is a single string (raw text)
            elif isinstance(self.raw_tracklist, str):
                lines = self.raw_tracklist.split('\n')
            
            # Handle if it's already a list
            elif isinstance(self.raw_tracklist, list):
                lines = self.raw_tracklist

            # Process lines
            lines = [line.strip() for line in lines if line.strip()]
            
            if lines:
                # The first line is the playlist name
                self.playlist_name = lines[0]
                logging.info(f"Extracted Playlist Name from RAW_TRACKLIST: {self.playlist_name}")
                
                # The rest are tracks
                self.raw_tracklist = lines[1:]
                
                parsed_songs = self.parse_raw_tracklist(self.raw_tracklist)
                if parsed_songs:
                    logging.info(f"Parsed {len(parsed_songs)} songs from RAW_TRACKLIST.")
                    self.song_list.extend(parsed_songs)
            else:
                self.raw_tracklist = []

        self.setup_logging()

    def parse_raw_tracklist(self, raw_lines: List[str]) -> List[str]:
        """
        Parses a list of raw strings from 1001tracklists format.
        Format example: [00:00] Artist - Title [LABEL]
        """
        parsed_songs = []
        for line in raw_lines:
            line = line.strip()
            if not line:
                continue
            
            # Regex to match: [Timestamp] Artist - Title [Label] (Label is optional)
            # We want to capture 'Artist - Title'
            # Pattern:
            # ^\[[\d:]+\]\s+  -> Starts with [digits:digits] and whitespace
            # (.*?)           -> Capture group for Artist - Title (non-greedy)
            # (?:\s*\[.*?\])? -> Optional non-capturing group for [Label] at the end
            # $               -> End of string
            
            match = re.match(r'^\[[\d:]+\]\s+(.*?)(?:\s*\[.*?\])?$', line)
            if match:
                song_info = match.group(1).strip()
                parsed_songs.append(song_info)
            else:
                # If it doesn't match the timestamp format, check if it looks like a song line anyway
                # but ignore header lines like "Artist @ Venue"
                if " - " in line and not line.startswith("http"):
                     parsed_songs.append(line)

        return parsed_songs

    def setup_logging(self):
        """Configures the logging module."""
        level = logging.DEBUG if self.debug_mode else logging.INFO
        logging.basicConfig(
            level=level,
            format='%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            handlers=[
                logging.StreamHandler(sys.stdout)
            ]
        )

    def load_configuration(self) -> Dict[str, Any]:
        """Loads configuration from a JSON file."""
        if not os.path.exists(self.config_file):
            print(f"ERROR: Configuration file '{self.config_file}' not found.")
            sys.exit(1)
        with open(self.config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config

    def _datetime_serializer(self, obj: Any) -> str:
        """Serializes datetime objects for JSON output."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError('Type not serializable')

    def save_session(self):
        """Saves session tokens to a JSON file."""
        token_data = {
            'token_type': self.session.token_type,
            'access_token': self.session.access_token,
            'refresh_token': self.session.refresh_token,
            'expiry_time': self.session.expiry_time
        }
        
        with open(self.session_file, 'w') as f:
            json.dump(token_data, f, default=self._datetime_serializer)
        logging.info(f"Session saved to '{self.session_file}'.")

    def load_session(self) -> Dict[str, Any]:
        """Loads session tokens from a JSON file."""
        with open(self.session_file, 'r') as f:
            token_data = json.load(f)
        
        # Convert expiry_time string to datetime if necessary
        if isinstance(token_data['expiry_time'], str):
            try:
                token_data['expiry_time'] = datetime.fromisoformat(token_data['expiry_time'])
            except ValueError:
                pass
        
        return token_data

    def authenticate(self):
        """Authenticates with Tidal using OAuth."""
        try:
            if os.path.exists(self.session_file):
                token_data = self.load_session()
                success = self.session.load_oauth_session(
                    token_data['token_type'],
                    token_data['access_token'],
                    token_data['refresh_token'],
                    token_data['expiry_time']
                )
                
                if success:
                    logging.info("Tidal session loaded successfully.")
                else:
                    logging.warning("Session expired, new authentication required...")
                    raise Exception("Session expired")
            else:
                raise FileNotFoundError("No session file found")
                
        except (FileNotFoundError, Exception):
            logging.info("Starting authentication process...")
            self.session.login_oauth_simple()
            self.save_session()
            logging.info("Authentication completed.")
        
        if not self.session.check_login():
            logging.error("Login failed.")
            sys.exit(1)

        try:
            user_id = self.session.user.id
            username = getattr(self.session.user, 'username', None)
            logging.info(f"Logged in as: {username if username else user_id}")
        except Exception:
            logging.info("Logged in successfully.")

    def get_full_track_title(self, track: Any) -> str:
        """Creates a full title for the track, including the artist."""
        try:
            if not hasattr(track, 'name') or not hasattr(track, 'artist') or not hasattr(track.artist, 'name'):
                logging.debug(f"Incomplete track object. Fetching full details for ID: {track.id}")
                full_track = self.session.track(track.id)
                if full_track:
                    track = full_track
                else:
                    artist_name = track.artist.name if hasattr(track, 'artist') and hasattr(track.artist, 'name') else "Unknown Artist"
                    return f"{artist_name} - {track.name if hasattr(track, 'name') else f'Unknown Title (ID: {track.id})'}"

            artist_name = track.artist.name if hasattr(track.artist, 'name') else "Unknown Artist"
            return f"{artist_name} - {track.name}"
        except Exception as e:
            logging.debug(f"Error getting full track title: {e}")
            return f"{track.name if hasattr(track, 'name') else f'Track ID: {track.id if hasattr(track, 'id') else 'N/A'}'}"

    def calculate_similarity_score(self, query: str, track_title: str, track_artist: str) -> float:
        """Calculates a weighted similarity score for a track."""
        query_lower = query.lower()
        title_lower = track_title.lower()
        artist_lower = track_artist.lower()
        
        target_string = f"{artist_lower} - {title_lower}"
        
        full_match_similarity = fuzz.token_sort_ratio(query_lower, target_string) / 100
        title_similarity = SequenceMatcher(None, query_lower, title_lower).ratio()
        artist_similarity = SequenceMatcher(None, query_lower, artist_lower).ratio()
        
        weighted_score = (full_match_similarity * 0.7) + (title_similarity * 0.2) + (artist_similarity * 0.1)
        
        return weighted_score

    def search_track(self, query: str) -> List[Any]:
        """Searches for a track using different available methods."""
        search_methods = [
            lambda: self.session.search('tracks', query, limit=self.tidal_search_limit),
            lambda: self.session.search(query, limit=self.tidal_search_limit)
        ]
        
        for method in search_methods:
            try:
                result = method()
                if isinstance(result, dict) and 'tracks' in result:
                    return result['tracks']
                elif hasattr(result, '__iter__') and not isinstance(result, str):
                    return list(result)
                else:
                    return [result] if result else []
            except (ValueError, AttributeError, TypeError):
                continue
        
        return []

    def intelligent_search(self, query: str, max_results: int = 3) -> Tuple[List[Any], float, List[Dict]]:
        """Searches with multiple strategies and ranks results."""
        cache_key = query.lower().strip()
        if cache_key in self.search_cache:
            return self.search_cache[cache_key]

        # Enhanced cleaning strategies
        cleaned_query = query
        # Remove "Number. Timestamp - " pattern (e.g., "23. 1:31:14 - ")
        cleaned_query = re.sub(r'^\d+\.\s*\d+:\d+:\d+\s*[–-]\s*', '', cleaned_query)
        # Remove just "Number. " prefix if present
        cleaned_query = re.sub(r'^\d+\.\s*', '', cleaned_query)
        
        strategies = [
            cleaned_query,
            cleaned_query.replace(" - ", " "),
            " ".join(cleaned_query.split(" - ")[::-1]) if " - " in cleaned_query else cleaned_query,
            re.sub(r'\([^)]*\)', '', cleaned_query).strip(),
            re.sub(r'(?i)(remix|edit|version|mix|remaster|remastered).*$', '', cleaned_query).strip(),
            re.sub(r'(?i)\s*(ft\.|feat\.|featuring)\s*.*$', '', cleaned_query).strip(),
        ]
        
        unique_results = {}
        top_candidates = []

        for strategy in strategies:
            if not strategy: continue
            
            tracks = self.search_track(strategy)
            for track in tracks[:max_results]:
                if track.id not in unique_results:
                    full_title = self.get_full_track_title(track)
                    artist_name = track.artist.name if hasattr(track.artist, 'name') else ""
                    similarity = self.calculate_similarity_score(cleaned_query, full_title, artist_name)
                    unique_results[track.id] = (track, similarity)
                    
                    if similarity > 0.95:
                        # Perfect match found
                        artist_name = track.artist.name if hasattr(track.artist, 'name') else "Unknown Artist"
                        album_title = track.album.name if hasattr(track, 'album') and hasattr(track.album, 'name') else "Unknown Album"
                        release_year = track.album.release_date.year if hasattr(track, 'album') and hasattr(track.album, 'release_date') else "Unknown Year"
                        
                        candidate_info = {
                            'artist': artist_name,
                            'title': track.name if hasattr(track, 'name') else f"Track ID: {track.id}",
                            'album': album_title,
                            'year': release_year,
                            'similarity': similarity
                        }
                        self.search_cache[cache_key] = ([track], similarity, [candidate_info])
                        return [track], similarity, [candidate_info]
        
        sorted_results = sorted(unique_results.values(), key=lambda x: x[1], reverse=True)
        
        best_similarity = sorted_results[0][1] if sorted_results else 0.0
        results = [track for track, _ in sorted_results]
        
        for track, score in sorted_results[:self.debug_candidate_limit]:
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
        
        self.search_cache[cache_key] = (results, best_similarity, top_candidates)
        return results, best_similarity, top_candidates

    def find_or_create_playlist(self) -> Optional[Any]:
        """Searches for a playlist by name. If not found, creates it."""
        try:
            user_playlists = self.session.user.playlists()
            for p in user_playlists:
                if p.name == self.playlist_name:
                    logging.info(f"Playlist '{self.playlist_name}' found.")
                    return p
            
            logging.warning(f"Playlist '{self.playlist_name}' not found. Creating it now...")
            description = "Playlist automatically created with a Python script, see https://github.com/hal9ooo/TidalBot"
            new_playlist = self.session.user.create_playlist(self.playlist_name, description)
            logging.info(f"Playlist '{self.playlist_name}' created successfully.")
            return new_playlist

        except Exception as e:
            logging.error(f"Error managing the playlist: {e}")
            return None

    def process_songs(self, playlist_target: Any):
        """Processes songs with a progress bar and statistics."""
        try:
            existing_tracks = playlist_target.tracks()
            existing_track_ids = {t.id for t in existing_tracks}
            logging.info(f"The playlist already contains {len(existing_track_ids)} tracks.")
        except Exception as e:
            logging.error(f"Error retrieving tracks from the playlist: {e}")
            return

        stats = {'added': 0, 'duplicate': 0, 'not_found': 0, 'errors': 0}
        low_similarity_warnings = []
        not_found_warnings = []

        with tqdm(total=len(self.song_list), desc="Processing songs") as pbar:
            for song_line in self.song_list:
                search_query = song_line.strip()
                if not search_query:
                    pbar.update(1)
                    continue
                
                pbar.set_postfix_str(f"Searching: {search_query[:30]}...")
                
                found_tracks, best_similarity, top_candidates = self.intelligent_search(search_query)

                if self.debug_mode and top_candidates:
                    logging.debug("\nTop Search Candidates:")
                    for i, candidate in enumerate(top_candidates):
                        logging.debug(f"  {i+1}. {candidate['artist']} - {candidate['title']} ({candidate['similarity']:.2f})")

                if found_tracks:
                    found_track = found_tracks[0]
                    full_title = self.get_full_track_title(found_track)
                    
                    if best_similarity < self.similarity_threshold:
                        logging.warning(f"LOW SIMILARITY: Found '{full_title}' ({best_similarity:.2f}) for '{search_query}'")
                        
                        found_artist = found_track.artist.name if hasattr(found_track.artist, 'name') else "Unknown"
                        found_title_txt = found_track.name if hasattr(found_track, 'name') else f"ID: {found_track.id}"
                        
                        low_similarity_warnings.append({
                            'query': search_query,
                            'found_title': full_title,
                            'found_artist': found_artist,
                            'found_track_title': found_title_txt,
                            'similarity': best_similarity,
                            'candidates': top_candidates
                        })

                    if found_track.id in existing_track_ids:
                        logging.info(f"[SKIP] '{full_title}' already in playlist.")
                        stats['duplicate'] += 1
                    else:
                        try:
                            playlist_target.add([found_track.id])
                            existing_track_ids.add(found_track.id)
                            logging.info(f"[ADD] Added '{full_title}' to playlist.")
                            stats['added'] += 1
                        except Exception as e:
                            logging.error(f"Could not add '{full_title}': {e}")
                            stats['errors'] += 1
                else:
                    logging.warning(f"NOT FOUND: '{search_query}'")
                    stats['not_found'] += 1
                    not_found_warnings.append(search_query)
                 
                pbar.update(1)
                time.sleep(1) # Rate limiting
        
        self.print_summary(stats, low_similarity_warnings, not_found_warnings)

    def print_summary(self, stats: Dict, low_sim: List[Dict], not_found: List[str]):
        """Prints the final summary of the operation."""
        print("\n" + "="*40)
        print("--- Final Statistics ---")
        print(f"   ADDED: {stats['added']}")
        print(f"   DUPLICATE: {stats['duplicate']}")
        print(f"   NOT FOUND: {stats['not_found']}")
        print(f"   ERRORS: {stats['errors']}")
        print("="*40)

        if low_sim:
            print("\n--- Low Similarity Warnings ---")
            for w in low_sim:
                print(f"\nQuery: '{w['query']}'")
                print(f"Found: '{w['found_title']}' (Similarity: {w['similarity']:.2f})")
                print("Candidates:")
                for i, c in enumerate(w['candidates']):
                    print(f"  {i+1}. {c['artist']} - {c['title']} ({c['similarity']:.2f})")

        if not_found:
            print("\n--- Not Found Songs ---")
            for i, q in enumerate(not_found):
                print(f"{i+1}. {q}")

    def run(self):
        """Main execution method."""
        self.authenticate()
        
        playlist_target = self.find_or_create_playlist()
        if not playlist_target:
            return

        self.process_songs(playlist_target)
        logging.info("Operation completed.")

if __name__ == "__main__":
    bot = TidalBot()
    bot.run()
