# Auto File Renamer for qBittorrent

A script to automatically rename files downloaded via qBittorrent and organize them into folders.

## Features

- Renames TV show episodes to a standard format (e.g., "Show Name - S01E01 Episode Title.ext").
- Moves files into season-specific folders (e.g., "/Show Name/Season 01/...").

## How to Use

1. Clone this repository to your local machine.
2. Open qBittorrent and go to `Options` > `Downloads`.
3. In the `Run external program` field, check `Run on torrent finished` and enter the path to `main.py` along with the required arguments:

   ```bash
   python "C:\path\to\main.py" "%N" "%L" "%G" "%F" "%R" "%D" "%C" "%Z" "%T"
   ```

   > **Note:** Replace `C:\path\to\main.py` with the actual path where you cloned the repository. Ensure Python is installed and added to your system's PATH.

4. Apply the settings and start downloading torrents. The script will automatically rename and organize files upon completion.

