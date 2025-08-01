# TidalBot

This Python script automates the process of creating and populating a Tidal playlist from a predefined list of songs. It handles authentication, intelligent song searching, and provides progress updates and statistics.

## Features

* **Tidal API Integration**: Authenticates with Tidal using `tidalapi` to manage sessions and interact with user data.
* **Serverless Web Config Editor**: A user-friendly, browser-based editor (`tidalbot-config-editor.html`) to create and modify your `config.json` file without any manual coding.
* **Configuration File**: All settings are managed via an external `config.json` file, making it easy to change parameters without editing the script.
* **Session Management**: Saves and loads Tidal session tokens to avoid repeated logins.
* **Playlist Management**: Automatically finds an existing playlist by name or creates a new one if it doesn't exist.
* **Enhanced Intelligent Song Search**: Employs a wider range of strategies (including handling parentheses, common suffixes, and featuring artists), weighted similarity scoring using `difflib.SequenceMatcher` and `fuzzywuzzy` for improved accuracy, and caching for faster repeated searches to find the most relevant tracks on Tidal.
* **Progress Bar**: Uses `tqdm` to display a progress bar during song processing.
* **Detailed Statistics**: Provides a summary of added, duplicated, not found, and error tracks at the end of the process.

## Setup

1.  **Clone the repository (or download the files):**
    ```bash
    git clone [https://github.com/your-repo/tidalbot.git](https://github.com/your-repo/tidalbot.git)
    cd tidalbot
    ```

2.  **Install dependencies:**
    This script requires `tidalapi`, `tqdm`, and `fuzzywuzzy`. You can install them using pip:
    ```bash
    pip install tidalapi tqdm "fuzzywuzzy[speedup]"
    ```

3.  **Create the configuration file:**
    You have two options:
    * **Recommended**: Use the **Web Config Editor**. Simply open the `tidalbot-config-editor.html` file in your web browser. This provides a user-friendly interface to configure everything and download the `config.json` file.
    * **Manual**: Create a file named `config.json` yourself. See the manual configuration section for details.

## Web-Based Config Editor (Serverless)

To make configuration easy and avoid syntax errors, this project includes a serverless web-based editor.

**How to use it:**

1.  Open the `tidalbot-config-editor.html` file in any modern web browser (like Chrome, Firefox, or Edge).
2.  Use the graphical interface to fill in your playlist name, song list, and adjust settings.
3.  You can:
    * **Load an existing `config.json`** by clicking "Upload Config".
    * **Load an example** to see how it works.
    * **See a live preview** of the JSON output.
4.  Once you're done, click **"Download Config"**.
5.  Save the downloaded `config.json` file in the same directory as the `tidalbot.py` script.

!(https://i.imgur.com/gY3v2Yk.png)

## Manual Configuration (`config.json`)

If you prefer to create the configuration file manually, create a file named `config.json` in the script's directory. Below is an explanation of each option.

* `DEBUG_MODE`: (boolean) Set to `true` to enable detailed debug output during the search process. Default is `false`.
* `TIDAL_SEARCH_LIMIT`: (integer) The maximum number of tracks to retrieve from the Tidal API for each search strategy. A higher number may improve accuracy but increases processing time. Default is `3`.
* `DEBUG_CANDIDATE_LIMIT`: (integer) The number of top search candidates to display in the debug output when `DEBUG_MODE` is enabled. Default is `3`.
* `SIMILARITY_THRESHOLD`: (float) The minimum similarity score (from 0.0 to 1.0) to consider a track a match. If the best match's score is below this, a warning is shown. Default is `0.75`.
* `PLAYLIST_NAME`: (string) The desired name for your Tidal playlist.
* `SONG_LIST`: (array of strings) A list of the songs you want to add. Each string in the array represents one song, ideally in the format `"Artist - Song Title"`.

**Example `config.json`:**
```json
{
    "DEBUG_MODE": false,
    "TIDAL_SEARCH_LIMIT": 3,
    "DEBUG_CANDIDATE_LIMIT": 3,
    "SIMILARITY_THRESHOLD": 0.75,
    "PLAYLIST_NAME": "My Awesome Playlist",
    "SONG_LIST": [
        "Pavel Khvaleev - Connect",
        "Cherry - Euphoria",
        "Armina - Mindstorm",
        "Led Zeppelin - Stairway to Heaven",
        "Queen - Bohemian Rhapsody"
    ]
}
```

## Usage

Run the script from your terminal:

```bash
python tidalbot.py
```

### Authentication

The first time you run the script, it will guide you through the Tidal authentication process. You will need to open a URL in your browser and log in. The session will be saved to `tidal_session.json` for future use, so you won't have to log in every time.

### Output

The script will display real-time progress and messages indicating:

* Session loading/authentication status.
* Playlist creation/finding status.
* Song search progress.
* Whether a song was added, was already present, or not found.
* Final statistics on the operation.

## Intelligent Search and Fuzzy Matching

The script employs an **Enhanced Intelligent Song Search** algorithm to find the most accurate match for each song query on Tidal. This process involves several steps:

1.  **Multiple Search Strategies**: For each song query, the script generates several variations to increase the chances of finding a match.
2.  **Tidal API Search**: Each variation is used to search the Tidal API.
3.  **Candidate Collection**: All unique tracks found are collected as potential candidates.
4.  **Similarity Scoring**: Each candidate is scored against the original query using a weighted combination of `fuzzywuzzy` and `difflib`.
5.  **Ranking and Selection**: Candidates are ranked, and the one with the highest score is chosen.
6.  **Similarity Threshold**: The `SIMILARITY_THRESHOLD` is used to flag potential low-confidence matches.
7.  **Caching**: Search results are cached to speed up processing.

### Debugging Search Results

To gain insight into the search process, enable `DEBUG_MODE` in your `config.json`. This will print detailed information for each song search, including the similarity scores and a list of the top potential candidates found.

## Contributing

Feel free to fork this repository, make improvements, and submit pull requests.

## License

This project is open-source and available under the [MIT License](LICENSE).
