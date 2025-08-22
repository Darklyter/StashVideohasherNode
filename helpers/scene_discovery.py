# scene_discovery.py

import random
from helpers.stash_utils import stash
import config

def discover_scenes():
    # Use the current value of config.config.per_page, which may be overridden by CLI
    """
    Discovers a random batch of scenes to process.
    - Filters scenes that do not yet have a phash
    - Excludes scenes already tagged with hashing_tag, hashing_error_tag, or cover_error_tag
    - Randomly selects one page of scenes to avoid overlap across multiple systems
    """

    # Step 1: Query all matching scene IDs (lightweight query, only returns 'id')
    # This helps determine how many total scenes are available for processing
    all_scenes = stash.find_scenes(
        f={
            "phash": {"value": "", "modifier": "IS_NULL"},
            "tags": {"value": [config.hashing_tag, config.hashing_error_tag, config.cover_error_tag], "modifier": "EXCLUDES"}
        },
        filter={"per_page": -1},  # Retrieve all matching scene IDs
        fragment="id"
    )

    # Step 2: Count total matching scenes
    total_count = len(all_scenes)
    if total_count == 0:
        print("🚫 No scenes found to process.")
        return []

    # Step 3: Calculate total number of pages based on configured batch size
    total_pages = max(1, (total_count + config.per_page - 1) // config.per_page)

    # Step 4: Randomly select one page to process
    # This helps distribute work across multiple systems without overlap
    selected_page = random.randint(1, total_pages)
    print(f"🎯 Selected page {selected_page} of {total_pages} (batch size: {config.per_page}, total: {total_count})")

    # Step 5: Fetch the selected page of scenes with full metadata
    # These scenes will be claimed and processed by this node
    batch_scenes = stash.find_scenes(
        f={
            "phash": {"value": "", "modifier": "IS_NULL"},
            "tags": {"value": [config.hashing_tag, config.hashing_error_tag, config.cover_error_tag], "modifier": "EXCLUDES"}
        },
        filter={
            "sort": "created_at",           # Sort by creation date (newest first)
            "direction": "DESC",
            "per_page": config.per_page,           # Limit to configured batch size
            "page": selected_page           # Use randomly selected page
        },
        fragment="id files{id path fingerprints{value type}} paths{screenshot}"
    )

    # Step 6: Return the batch of scenes to be processed
    return batch_scenes
