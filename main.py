import re
import logging
import shutil
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
WINDOWS_INVALID_CHARS = r'[<>:"/\\|?*]'
VIDEO_EXTENSIONS = {
    ".mkv", ".mp4", ".avi", ".mov", ".wmv", ".m4v", ".ts", ".m2ts"
}


def clean_name(name: str) -> str:
    cleaned = re.sub(pattern, "", name, flags=re.IGNORECASE)
    cleaned = cleaned.replace(".", " ")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def sanitize_path_component(name: str) -> str:
    sanitized = re.sub(WINDOWS_INVALID_CHARS, "", name)
    sanitized = sanitized.strip().rstrip(".")
    return sanitized or "Unknown"


def extract_episode_info(name: str):
    match = re.search(r"(.*?)\s*S(\d+)E(\d+)(?:\s+(.+?))?$", name, re.IGNORECASE)
    if not match:
        return None

    show_name = sanitize_path_component(match.group(1).strip())
    season_num = int(match.group(2))
    episode_num = int(match.group(3))
    episode_name = match.group(4).strip() if match.group(4) else None

    return {
        "show_name": show_name,
        "season_num": season_num,
        "episode_num": episode_num,
        "episode_name": episode_name,
    }


def extract_season_pack_info(name: str):
    # Match names like "Show Name Season 5 Complete".
    match = re.search(r"^(.*?)\s+Season\s+(\d+)\b", name, re.IGNORECASE)
    if match:
        return {
            "show_name": sanitize_path_component(match.group(1).strip()),
            "season_num": int(match.group(2)),
        }

    # Also support common "S05" season pack naming.
    match = re.search(r"^(.*?)\s+S(\d+)(?!\s*E\d+)\b", name, re.IGNORECASE)
    if not match:
        return None

    return {
        "show_name": sanitize_path_component(match.group(1).strip()),
        "season_num": int(match.group(2)),
    }


def find_primary_episode_file(folder: Path):
    candidates = []
    for child in folder.iterdir():
        if child.is_file() and child.suffix.lower() in VIDEO_EXTENSIONS:
            episode_token = re.search(r"S\d+E\d+", child.stem, re.IGNORECASE) is not None
            try:
                size = child.stat().st_size
            except OSError:
                size = 0
            candidates.append((episode_token, size, child))

    if not candidates:
        return None

    # Prefer files that contain SxxExx; break ties by file size.
    candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return candidates[0][2]


def get_video_files(folder: Path):
    return [
        child for child in folder.iterdir()
        if child.is_file() and child.suffix.lower() in VIDEO_EXTENSIONS
    ]


def cleanup_redundant_folder_items(folder: Path):
    removed_count = 0
    for child in folder.iterdir():
        try:
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()
            removed_count += 1
        except OSError as error:
            logging.warning(f"Could not remove redundant item {child}: {error}")

    try:
        folder.rmdir()
        logging.info(f"Removed wrapper folder after cleanup: {folder}")
    except OSError as error:
        logging.warning(f"Could not remove wrapper folder {folder}: {error}")

    if removed_count > 0:
        logging.info(f"Removed {removed_count} redundant item(s) from {folder}")


def build_episode_target_path(source_path: Path, save_path: str, episode_info: dict, clean_base_name: str) -> Path:
    show_name = episode_info["show_name"]
    season_num = episode_info["season_num"]
    episode_num = episode_info["episode_num"]
    episode_name = episode_info.get("episode_name")
    
    dest_dir = Path(save_path) / show_name / f"Season {season_num}"
    
    # Build filename with show name, episode number and name if available
    if episode_name:
        filename = f"{show_name} S{season_num:02d}E{episode_num:02d} - {sanitize_path_component(episode_name)}"
    else:
        filename = sanitize_path_component(clean_base_name)
    
    if source_path.is_dir():
        return dest_dir / filename
    return dest_dir / f"{filename}{source_path.suffix}"


def build_season_target_path(save_path: str, season_info: dict) -> Path:
    show_name = season_info["show_name"]
    season_num = season_info["season_num"]
    return Path(save_path) / show_name / f"Season {season_num}"


def move_with_collision_handling(source_path: Path, target_path: Path) -> Path:
    if source_path == target_path:
        return source_path

    target_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        source_path.rename(target_path)
        return target_path
    except FileExistsError:
        stem = target_path.stem
        suffix = target_path.suffix
        counter = 1
        while True:
            candidate = target_path.with_name(f"{stem} ({counter}){suffix}")
            try:
                source_path.rename(candidate)
                return candidate
            except FileExistsError:
                counter += 1

def main():
    try:
        logging.info(f"-------- Script started for {sys.argv[TORRENT_NAME]} --------")
        save_path = sys.argv[TORRENT_SAVE_PATH]
        content_path = sys.argv[TORRENT_CONTENT_PATH]
        torrent_num_files = int(sys.argv[TORRENT_NUM_FILES])

        original_path = Path(content_path)
        is_dir = original_path.is_dir()

        source_path = original_path
        clean_base_name = clean_name(original_path.name if is_dir else original_path.stem)
        episode_info = extract_episode_info(clean_base_name)
        season_info = None
        wrapper_folder_for_cleanup = None

        if is_dir:
            video_files = get_video_files(original_path)
            if len(video_files) == 1:
                primary_episode_file = video_files[0]
                source_path = primary_episode_file
                clean_base_name = clean_name(primary_episode_file.stem)
                episode_info = extract_episode_info(clean_base_name)
                wrapper_folder_for_cleanup = original_path
                logging.info(f"Episode folder detected; selected primary media file: {primary_episode_file.name}")
            else:
                season_info = extract_season_pack_info(clean_name(original_path.name))

        if torrent_num_files > 1 and episode_info is None and season_info is None:
            logging.info("Skipping multifile torrent because no episode or season-pack pattern was detected.")
            return

        if episode_info:
            target_path = build_episode_target_path(source_path, save_path, episode_info, clean_base_name)
        elif season_info and original_path.is_dir():
            source_path = original_path
            target_path = build_season_target_path(save_path, season_info)
            logging.info(
                f"Season pack detected; organizing folder as {season_info['show_name']} / Season {season_info['season_num']}"
            )
        else:
            # No episode pattern detected, rename in place.
            target_stem = sanitize_path_component(clean_base_name)
            if source_path.is_dir():
                target_path = source_path.with_name(target_stem)
            else:
                target_path = source_path.with_name(f"{target_stem}{source_path.suffix}")

        final_path = move_with_collision_handling(source_path, target_path)
        if source_path == final_path:
            logging.info("No renaming needed, original and new paths are the same.")
        else:
            logging.info(f"SUCCESS: {source_path} -> {final_path}")

        if wrapper_folder_for_cleanup and wrapper_folder_for_cleanup.exists():
            cleanup_redundant_folder_items(wrapper_folder_for_cleanup)

    except Exception as e:
        logging.error(f"Script failed: {str(e)}")
    
    

if __name__ == "__main__":
    main()