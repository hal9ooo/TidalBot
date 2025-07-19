# TidalBot

This Python script automates the process of creating and populating a Tidal playlist from a predefined list of songs. It handles authentication, intelligent song searching, and provides progress updates and statistics.

## Features

* **Tidal API Integration**: Authenticates with Tidal using `tidalapi` to manage sessions and interact with user data.

* **Configuration File**: Easily manage all settings through a `config.json` file.

* **Session Management**: Saves and loads Tidal session tokens to avoid repeated logins.

* **Playlist Management**: Automatically finds an existing playlist by name or creates a new one if it doesn't exist.

* **Enhanced Intelligent Song Search**: Employs multiple strategies, weighted similarity scoring using `fuzzywuzzy`, and caching for faster repeated searches to find the most relevant tracks on Tidal.

* **Progress Bar**: Uses `tqdm` to display a progress bar during song processing.

* **Detailed Statistics**: Provides a summary of added, duplicated, not found, and error tracks at the end of the process.

## Setup

1. **Clone the repository (or download the files):**


git clone https://github.com/your-repo/tidalbot.git
cd tidalbot


2. **Install dependencies:**
This script requires `tidalapi`, `tqdm`, and `python-Levenshtein` (for `fuzzywuzzy`). You can install them using pip:


pip install tidalapi tqdm fuzzywuzzy python-Levenshtein


3. **Configure the `config.json` file:**
This is the central place to manage the script's behavior. Open `config.json` and edit the values.

* `PLAYLIST_NAME`: The desired name for your Tidal playlist.

* `SONG_LIST`: A list of songs you want to add. Each song should be a separate string in the list, ideally in the format `"Artist - Song Title"`.

* `DEBUG_MODE`: Set to `true` to enable detailed debug output during the search process.

* `TIDAL_SEARCH_LIMIT`: The maximum number of tracks to retrieve from the Tidal API for each search strategy. A higher number may improve accuracy but increases processing time.

* `SIMILARITY_THRESHOLD`: A value between 0.0 and 1.0. Matches below this score will be flagged with a "LOW SIMILARITY" warning.

**Example `config.json`:**


{
"DEBUG_MODE": false,
"TIDAL_SEARCH_LIMIT": 5,
"DEBUG_CANDIDATE_LIMIT": 3,
"SIMILARITY_THRESHOLD": 0.75,
"PLAYLIST_NAME": "My Awesome Playlist",
"SONG_LIST": [
"Pavel Khvaleev - Connect",
"Cherry - Euphoria",
"Armina - Mindstorm"
]
}


## Usage

Run the script from your terminal. Make sure `tidalbot.py` and `config.json` are in the same directory.


python tidalbot.py


### Authentication

The first time you run the script, it will guide you through the Tidal authentication process. You will need to open a URL in your browser and log in. The session will be saved to `tidal_session.json` for future use, so you won't have to log in every time.

### Output

The script will display real-time progress and messages indicating:

* Session loading/authentication status.

* Playlist creation/finding status.

* Song search progress.

* Whether a song was added, was already present, or not found.

* Final statistics on the operation.

## How Intelligent Search Works

To find the most accurate match for each song, the script:

1. **Generates Search Variations**: It creates multiple versions of your query (e.g., "Artist Title", "Title Artist", "Artist - Title (Remix)", etc.).

2. **Calculates Similarity**: It compares your query to the search results using a weighted score, giving more importance to the title and artist match.

3. **Ranks and Selects**: It picks the track with the highest similarity score.

4. **Flags Low Confidence Matches**: If the best score is below the `SIMILARITY_THRESHOLD` set in `config.json`, it will print a warning for you to review.

To see this process in action, set `"DEBUG_MODE": true` in your `config.json`.

## Contributing

Feel free to fork this repository, make improvements, and submit pull requests.

## License

This project is open-source and available under the
