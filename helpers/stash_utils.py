# stash_utils.py

from stashapi.stashapp import StashInterface
from config import hashing_tag, hashing_error_tag, cover_error_tag, dry_run, stash_host, stash_port
from datetime import datetime

stash = StashInterface({"host": stash_host, "port": stash_port})

def log_scene_failure(scene_id, filename_pretty, step, error):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"{timestamp} ❌ Scene {scene_id} — {filename_pretty} failed during {step}: {error}")

def reset_terminal():
    import platform
    if platform.system() != "Windows":
        print("\033[0;37m", end="")  # Reset + white text

def get_total_scene_count():
    scenes = stash.find_scenes(
        f={
            "phash": {"value": "", "modifier": "IS_NULL"},
            "tags": {"value": [hashing_tag, hashing_error_tag, cover_error_tag], "modifier": "EXCLUDES"}
        },
        filter={"sort": "created_at", "direction": "DESC", "per_page": -1},
        fragment="id"
    )
    return len(scenes)

def tag_scene_error(scene_id, error_tag, error_msg=None):
    if dry_run:
        print(f"[DRY RUN] Would tag scene {scene_id} with error tag {error_tag}")
        return
    stash.update_scenes({"ids": scene_id, "tag_ids": {"ids": error_tag, "mode": "ADD"}})
    stash.update_scenes({"ids": scene_id, "tag_ids": {"ids": hashing_tag, "mode": "REMOVE"}})
    if error_msg:
        with open("error_log.txt", "a") as log:
            log.write(f"Scene {scene_id}: {error_msg}\n")

def claim_scene(scene_id):
    if dry_run:
        print(f"[DRY RUN] Would claim scene {scene_id}")
        return
    stash.update_scenes({"ids": scene_id, "tag_ids": {"ids": hashing_tag, "mode": "ADD"}})

def release_scene(scene_id):
    if dry_run:
        print(f"[DRY RUN] Would release scene {scene_id}")
        return
    stash.update_scenes({"ids": scene_id, "tag_ids": {"ids": hashing_tag, "mode": "REMOVE"}})

def update_phash(file_id, phash):
    if dry_run:
        print(f"[DRY RUN] Would update phash for file {file_id} to {phash}")
        return
    stash.file_set_fingerprints(file_id, [{"type": "phash", "value": phash}])

def update_cover(scene_id, cover_data):
    if dry_run:
        print(f"[DRY RUN] Would update cover image for scene {scene_id}")
        return True
    return stash.update_scene({"id": scene_id, "cover_image": cover_data})

def get_scenes_to_process():
    return stash.find_scenes(
        f={"phash": {"value": "", "modifier": "IS_NULL"},
           "tags": {"value": [hashing_tag, hashing_error_tag, cover_error_tag], "modifier": "EXCLUDES"}},
        filter={"sort": "created_at", "direction": "DESC", "per_page": -1},
        fragment="id files{id path fingerprints{value type}} paths{screenshot}"
    )

