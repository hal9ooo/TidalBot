# TidalBot

This Python script automates the process of creating and populating a Tidal playlist from a predefined list of songs. It handles authentication, intelligent song searching, and provides progress updates and statistics.

## Features

- **Tidal API Integration**: Authenticates with Tidal using `tidalapi` to manage sessions and interact with user data.
- **Session Management**: Saves and loads Tidal session tokens to avoid repeated logins.
- **Playlist Management**: Automatically finds an existing playlist by name or creates a new one if it doesn't exist.
- **Intelligent Song Search**: Employs multiple strategies (original query, query without separators, inverted query) and similarity ranking to find the most relevant tracks on Tidal.
- **Progress Bar**: Uses `tqdm` to display a progress bar during song processing.
- **Detailed Statistics**: Provides a summary of added, duplicated, not found, and error tracks at the end of the process.

## Setup

1.  **Clone the repository (or download the script):**
    ```bash
    git clone https://github.com/your-repo/tidalbot.git
    cd tidalbot
    ```

2.  **Install dependencies:**
    This script requires `tidalapi` and `tqdm`. You can install them using pip:
    ```bash
    pip install tidalapi tqdm
    ```

3.  **Configure the script:**
    Open `tidalbot.py` and modify the following variables in the `--- 1. CONFIGURAZIONE ---` section:

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