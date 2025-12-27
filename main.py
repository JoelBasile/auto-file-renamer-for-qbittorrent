import re
import logging
import datetime
from pathlib import Path
import sys

log_path = Path(__file__).parent / "torrent_log.txt"
logging.basicConfig(
    filename=str(log_path),
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Command line arguments indices
TORRENT_NAME=1          # Torrent name
TORRENT_CATEGORY=2      # Category
TORRENT_TAGS=3          # Tags (separated by comma)
TORRENT_CONTENT_PATH=4  # Content path (same as root path for multifile torrent)
TORRENT_ROOT_PATH=5     # Root path (first torrent subdirectory path)
TORRENT_SAVE_PATH=6     # Save path
TORRENT_NUM_FILES=7     # Number of files
TORRENT_SIZE=8          # Torrent size (bytes)
TORRENT_TRACKER=9       # Current tracker

pattern = r"[ .](?:1080p|2160p|720p|480p|WEB|HDTV|HSBS).*$"

def main():
    try:
        logging.info(f"-------- Script started for {sys.argv[TORRENT_NAME]} --------")
        torrent_name = sys.argv[TORRENT_NAME]
        save_path = sys.argv[TORRENT_SAVE_PATH]
        content_path = sys.argv[TORRENT_CONTENT_PATH]

        original_path = Path(content_path)
        is_dir = original_path.is_dir()

        # For directories, use full name. For files, use stem (to preserve extension later)
        name_to_process = original_path.name if is_dir else original_path.stem

        # Calculate new name
        clean_name = re.sub(pattern, "", name_to_process, flags=re.IGNORECASE)
        clean_name = clean_name.replace(".", " ").strip()

        # Check for Show/Season pattern to organize into folders
        # 1. Check for Episode pattern SxxExx
        episode_match = re.search(r"(.*?)\s*S(\d+)E\d+", clean_name, re.IGNORECASE)

        # 2. Check for Season pack pattern Sxx (only if not episode)
        # Look for Sxx NOT followed by Exx
        season_pack_match = re.search(r"(.*?)\s*S(\d+)(?!\s*E\d+)", clean_name, re.IGNORECASE)

        if episode_match and episode_match.group(1).strip():
            show_name = episode_match.group(1).strip()
            season_num = int(episode_match.group(2))
            
            # Construct absolute destination path based on the save path
            # This prevents nesting issues by always anchoring to the base directory
            dest_dir = Path(save_path) / show_name / f"Season {season_num}"
            new_path = dest_dir / f"{clean_name}{original_path.suffix}"

        elif is_dir and season_pack_match and season_pack_match.group(1).strip():
            # It's a Season Pack folder (e.g. "Show Name S01")
            logging.info(f"TODO Detected season pack folder: {clean_name}")
            # show_name = season_pack_match.group(1).strip()
            # season_num = int(season_pack_match.group(2))
            
            # # We want to move this folder to: Show Name / Season X
            # # The folder ITSELF becomes "Season X"
            # dest_dir = Path(save_path) / show_name
            # new_path = dest_dir / f"Season {season_num}"
            
        else:
            # No special patterns detected, just rename in place
            new_path = original_path.with_name(f"{clean_name}{original_path.suffix}")

        if original_path == new_path:
            logging.info("No renaming needed, original and new paths are the same.")
            return
        
        new_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            original_path.rename(new_path)
            logging.info(f"SUCCESS: {original_path.name} -> {new_path.name}")
            return # Thread finishes successfully
        except FileExistsError:
            # Target exists, try to find a unique name
            stem = new_path.stem
            suffix = new_path.suffix
            counter = 1
            while True:
                candidate = new_path.with_name(f"{stem} ({counter}){suffix}")
                try:
                    original_path.rename(candidate)
                    logging.info(f"SUCCESS (renamed duplicate): {original_path.name} -> {candidate.name}")
                    return
                except FileExistsError:
                    counter += 1

    except Exception as e:
        logging.error(f"Script failed: {str(e)}")
    

if __name__ == "__main__":
    main()