# config.py

import platform
import os

# 🌐 Stash API connection
stash_scheme = "http"
stash_host = "localhost"
stash_port = 9999
stash_api_key = ""  # Set your Stash API key here (Settings → Security → API Key)

windows = platform.system() == "Windows"

# 📁 External tool paths
binary_windows = r".\bin\videohashes-windows.exe"
binary_linux = r"./videohashes-linux-amd64"
binary = binary_windows if windows else binary_linux

ffmpeg = r"c:\mediatools\ffmpeg.exe" if windows else "/usr/bin/ffmpeg"
ffprobe = r"c:\mediatools\ffprobe.exe" if windows else "/usr/bin/ffprobe"

sprite_path = r"Y:/stash/generated/vtt" if windows else "/mnt/stash/generated/vtt"
preview_path = r"Y:/stash/generated/screenshots" if windows else "/mnt/stash/generated/screenshots"

# 🏷️ Stash tag IDs
hashing_tag = 0      # Stash tag ID for "In Process" — create tag and set ID here
hashing_error_tag = 0  # Stash tag ID for "Hashing Error"
cover_error_tag = 0    # Stash tag ID for "Cover Error"

# 🔢 Batch size for scene processing
per_page = 25  # --batch-size: Number of scenes to process per run (default: 25)

# ⚙️ Parallelism settings
max_workers = 4  # --max-workers: Number of threads for parallel processing

# 🖼️ Sprite generation settings
generate_sprite = True  # --generate-sprite: Enable sprite image generation

# 🎞️ Preview video settings
generate_preview = True  # --generate-preview: Enable preview video generation
preview_audio = False
preview_clips = 15
preview_clip_length = 1
preview_skip_seconds = 15

# 🧪 Various flags, with their cli equivalents
dry_run = False  # --dry-run: Simulate processing without writing changes
once = False     # --once: Run one batch then exit
verbose = False  # --verbose: Display additional information including progress bars for generation tasks
nvenc = True     # Use NVIDIA NVENC hardware encoder for preview video generation

# 🚫 Stash paths to exclude from processing (matched with EXCLUDES filter)
excluded_paths = [
    # "/data/my-folder",  # Add Stash paths to exclude from processing
]

# 🔁 Path translations.  The path that Stash access is the Orig, the path on the local machine is obviously Local
translations = (
    [
        {'orig': '/data/', 'local': 'S:/'},
        {'orig': '/data2/', 'local': 'P:/'},
        {'orig': '/data3/', 'local': 'R:/'},
    ] if windows else [
        {'orig': '/data/', 'local': '/mnt/datadrive/'},
    ]
)
