# TidalBot

This Python script automates the process of creating and populating a Tidal playlist from a predefined list of songs. It handles authentication, intelligent song searching, and provides progress updates and statistics.

## Features

- **Tidal API Integration**: Authenticates with Tidal using `tidalapi` to manage sessions and interact with user data.
- **Session Management**: Saves and loads Tidal session tokens to avoid repeated logins.
- **Playlist Management**: Automatically finds an existing playlist by name or creates a new one if it doesn't exist.
- **Enhanced Intelligent Song Search**: Employs a wider range of strategies (including handling parentheses, common suffixes, and featuring artists), weighted similarity scoring using `difflib.SequenceMatcher` and `fuzzywuzzy` for improved accuracy, and caching for faster repeated searches to find the most relevant tracks on Tidal.
- **Progress Bar**: Uses `tqdm` to display a progress bar during song processing.
- **Detailed Statistics**: Provides a summary of added, duplicated, not found, and error tracks at the end of the process.

## Intelligent Search and Fuzzy Matching

The script employs an **Enhanced Intelligent Song Search** algorithm to find the most accurate match for each song query on Tidal. This process involves several steps:

1.  **Multiple Search Strategies**: For each song query (e.g., "Artist - Song Title"), the script generates several variations (strategies) of the query. This includes the original query, removing separators like " - ", inverting the artist and title, removing content within parentheses, and removing common suffixes like "Remix" or "Extended Mix". This helps to increase the chances of finding a match even if the original query format doesn't exactly match Tidal's data.
2.  **Tidal API Search**: Each generated strategy is used to search the Tidal API. The `TIDAL_SEARCH_LIMIT` variable (default: 5) controls how many results are requested from the Tidal API for each individual search strategy. Increasing this limit can potentially find more relevant candidates but will also increase the number of API calls and processing time.
3.  **Candidate Collection**: All unique tracks found across all search strategies are collected as potential candidates.
4.  **Similarity Scoring**: For each candidate track, a weighted similarity score is calculated against the original song query. This score uses a combination of `fuzzywuzzy`'s `token_sort_ratio` (which is good for comparing strings with different word orders) and `difflib.SequenceMatcher` (for more precise sequence comparison) on the full artist-title string, as well as individual artist and title components. The weights are currently tuned to prioritize the overall match and title similarity.
5.  **Ranking**: The collected candidates are ranked based on their calculated similarity scores in descending order.
6.  **Best Match Selection**: The track with the highest similarity score is selected as the best match.
7.  **Similarity Threshold**: The `SIMILARITY_THRESHOLD` (default: 0.75) is used to flag potential low-confidence matches. If the best match's similarity score falls below this threshold, a warning is printed to the console, suggesting manual review.
8.  **Caching**: Search results are cached to speed up processing if the same song query is encountered again.

### Debugging Search Results

To gain insight into the search process and the candidates considered, you can enable `DEBUG_MODE` at the top of the `tidalbot.py` script (`DEBUG_MODE = True`). When enabled, the script will print detailed information for each song search, including:

*   The original query and the target string used for comparison.
*   Individual similarity scores (full match, title, artist).
*   The final weighted similarity score.
*   A list of the top potential track candidates found across all strategies, ranked by similarity. The number of candidates shown in this debug list is controlled by the `DEBUG_CANDIDATE_LIMIT` variable (default: 3). This list includes the artist, title, album, year, and similarity score for each candidate.

This debug output is invaluable for understanding why a particular track was matched (or not matched) and for fine-tuning the similarity threshold or search strategies if needed.

## Setup

1.  **Clone the repository (or download the script):**
    ```bash
    git clone https://github.com/your-repo/tidalbot.git
    cd tidalbot
    ```

2.  **Install dependencies:**
    This script requires `tidalapi`, `tqdm`, and `fuzzywuzzy`. You can install them using pip:
    ```bash
    pip install tidalapi tqdm fuzzywuzzy
    ```

3.  **Configure the script:**
    Open `tidalbot.py` and modify the following variables in the `--- 1. CONFIGURATION ---` section:

    -   `DEBUG_MODE`: Set to `True` to enable detailed debug output during the search process. Set to `False` to disable.
    -   `TIDAL_SEARCH_LIMIT`: An integer specifying the maximum number of tracks to retrieve from the Tidal API for each search strategy. A higher number may improve accuracy but increases processing time.
    -   `DEBUG_CANDIDATE_LIMIT`: An integer specifying the number of top search candidates to display in the debug output when `DEBUG_MODE` is enabled.
    -   `NOME_PLAYLIST`: The desired name for your Tidal playlist.
    -   `LISTA_CANZONI`: A multi-line string containing the list of songs you want to add, one song per line. Each line should ideally be in the format "Artist - Song Title".

    Example:
    ```python
    NOME_PLAYLIST = "My Awesome Playlist"

    LISTA_CANZONI = """
    Pavel Khvaleev - Connect
    Cherry - Euphoria
    Armina - Mindstorm
    """
    ```

## Usage

Run the script from your terminal:

```bash
python tidalbot.py
```

### Authentication

The first time you run the script, it will guide you through the Tidal authentication process. You will need to open a URL in your browser and paste the provided URL back into the terminal. The session will be saved to `tidal_session.json` for future use.

### Output

The script will display real-time progress and messages indicating:
- Session loading/authentication status.
- Playlist creation/finding status.
- Song search progress.
- Whether a song was added, was already present, or not found.
- Final statistics on the operation.

## Contributing

Feel free to fork this repository, make improvements, and submit pull requests.

## License

This project is open-source and available under the [MIT License](LICENSE).