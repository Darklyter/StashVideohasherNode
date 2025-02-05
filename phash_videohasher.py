#!/usr/bin/python

"""
StashVideohasherNode - Video Hash and Preview Generator for Stash

This version is optimized for MacOS with FFmpeg VideoToolbox hardware acceleration.

Requirements:
- Python 3.10+
- FFmpeg with VideoToolbox support (installed via Homebrew)
- Peolic's videohashes utility (darwin-amd64 version)

Installation:
1. Install dependencies:
   pip install requests stashapp-tools tqdm pillow

2. Install FFmpeg via Homebrew:
   brew install ffmpeg

3. Download videohashes:
   - Get darwin-amd64 version from: https://github.com/peolic/videohashes/releases
   - Make it executable: chmod +x videohashes-darwin-amd64

4. Configure Stash paths in the translations section below
"""

import re
import os
import requests
import json
import string
from json.decoder import JSONDecodeError
import subprocess
import random
import base64
from video_sprite_generator import VideoSpriteGenerator
from preview_video_generator import PreviewVideoGenerator

# Stash connection
from stashapi.stashapp import StashInterface
stash = StashInterface({
    "host": "localhost",  # Change to your Stash server IP
    "port": 9999,
    "Apikey": ""  # Add your API key here if required
})

# Path translations - modify these to match your setup
# Example: if Stash sees "/data/videos" but it's mounted as "/Volumes/data/videos" on your Mac
translations = [
    {'orig': '/data/', 'local': '/Volumes/data/'},
    {'orig': '/media/', 'local': '/Volumes/media/'},
]

# System configuration
windows = False  # Set to False for MacOS
binary_windows = r".\videohashes-windows.exe"  # Not used on MacOS
binary_linux = r"./videohashes-darwin-amd64"  # Used for MacOS

# FFmpeg paths (Homebrew default locations)
ffmpeg = r"/opt/homebrew/bin/ffmpeg"
ffprobe = r"/opt/homebrew/bin/ffprobe"

# Stash workflow tags - modify these IDs to match your Stash tags
hashing_tag = 15015        # Tag for scenes being processed
hashing_error_tag = 15018  # Tag for scenes with hashing errors
cover_error_tag = 15019    # Tag for scenes with cover errors

#
# Note about Sprite and Preview options... to generate sprites and previews you must have the appropriate Stash directories available
# and the user running this script has to have write permissions.  Covers can be submitted to Stash via GQL, but Sprites and Previews
# instead have to be written into the generated folders manually (by the script)
#

# Config for Sprite image generation
generate_sprite = True
sprite_path = r"/opt/stash/generated/vtt"  # Change to your Stash VTT directory
# ~ sprite_path = r"/mnt/stash/stash/generated/vtt"

# Config for preview video generation
generate_preview = True
preview_path = r"/opt/stash/generated/screenshots"  # Change to your Stash screenshots directory
# ~ preview_path = r"/mnt/stash/stash/generated/screenshots"
preview_audio = False
preview_clips = 15
preview_clip_length = 1
preview_skip_seconds = 15


def main():

    print("Loading full scene list to 'prime the pump'...  please wait")
    scenelist = stash.find_scenes(f={"phash": {"value": "", "modifier": "IS_NULL"}, "tags": {"value": [hashing_tag, hashing_error_tag, cover_error_tag], "modifier": "EXCLUDES"}}, filter={"per_page": -1}, fragment="id")
    if len(scenelist):
        scenecount = len(scenelist)
        if scenecount > 50:
            page = random.randrange(1, int(scenecount / 25))
            print(f"Found {scenecount} scenes to be processed...  Loading page #{page}")
        else:
            page = False
            print(f"Found {scenecount} scenes to be processed...  Since its less than 50, processing all scenes...")
        scenelist = None
    else:
        print("No scenes found.  Exiting...")
        exit()

    if page:
        scenelist = stash.find_scenes(f={"phash": {"value": "", "modifier": "IS_NULL"}, "tags": {"value": [hashing_tag, hashing_error_tag, cover_error_tag], "modifier": "EXCLUDES"}}, filter={"sort": "created_at", "direction": "DESC", "per_page": 25, "page": page}, fragment="id files{id path fingerprints{value type}} paths{screenshot}")
    else:
        scenelist = stash.find_scenes(f={"phash": {"value": "", "modifier": "IS_NULL"}, "tags": {"value": [hashing_tag, hashing_error_tag, cover_error_tag], "modifier": "EXCLUDES"}}, filter={"sort": "created_at", "direction": "DESC", "per_page": -1}, fragment="id files{id path fingerprints{value type}} paths{screenshot}")

    # First we claim these scenes for this node to work on by appending the "hashing_tag" to the scenes
    for scene in scenelist:
        stash.update_scenes({"ids": scene['id'], "tag_ids": {"ids": hashing_tag, "mode": "ADD"}})

    for scene in scenelist:
        scene_id = scene['id']
        file_id = scene['files'][0]['id']
        filename = scene['files'][0]['path']
        filename_pretty = re.search(r'.*[/\\](.*?)$', filename).group(1)
        for translation in translations:
            filename = filename.replace(translation['orig'], translation['local'], 1)

        filehash = ""
        if scene['files'][0]['fingerprints']:
            for fingerprint in scene['files'][0]['fingerprints']:
                if fingerprint['type'].lower() == "oshash":
                    filehash = fingerprint['value']

        print(f"Working on ID# {scene_id} with Filename: {filename_pretty} ")
        if windows:
            videohash = binary_windows
        else:
            videohash = binary_linux

        result = subprocess.run([videohash, '-json', filename], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=True)
        try:
            results = json.loads(result.stdout.decode("utf-8"))
        except JSONDecodeError as e:
            print(f"Encountered an error:  {e}...  Marking scene ({filename}) with Hashing Error tag.")
            stash.update_scenes({"ids": scene_id, "tag_ids": {"ids": hashing_error_tag, "mode": "ADD"}})
            stash.update_scenes({"ids": scene_id, "tag_ids": {"ids": hashing_tag, "mode": "REMOVE"}})
            print("\n\n")
            continue

        if "phash" in results and results['phash']:
            print(f"Updating hash for '{filename_pretty}' with Phash: {results['phash']}")
            stash.file_set_fingerprints(file_id, [{"type": "phash", "value": results['phash']}])

        # Silly, but need to pre-sanitize filenames for ffmpeg.  It's touchy
        if windows:
            ffmpeg_filename = filename
            ffmpeg_filename = f'"{ffmpeg_filename}"'
        else:
            ffmpeg_filename = filename.replace('"', '\'\\\'"').replace("'", r"'\''")
            ffmpeg_filename = f"'{ffmpeg_filename}'"

        # Lets check for a "default" cover image
        cover_image = scene['paths']['screenshot']
        if cover_image:
            cover_image = requests.get(cover_image)
            cover_image = cover_image.content.decode('latin_1')

            if re.search(r'(<svg)', cover_image.lower()):

                print(f"Extracting Cover image for ID# {scene_id} with Filename: {filename_pretty} ")
                # Create a random filename so as to not interfere with other nodes
                image_filename = ''.join(random.choices(string.ascii_lowercase + string.digits, k=12))
                image_filename = image_filename + ".jpg"

                # Ok, let's pull the screenshot and save it out to the random filename
                ffmpegcmd = ffmpeg + f" -hide_banner -loglevel error -i {ffmpeg_filename} -ss 00:00:30 -vframes 1 {image_filename} -nostdin"
                try:
                    os.system(ffmpegcmd)
                    # Cover image created, now we Base64 it
                    with open(image_filename, "rb") as image_file:
                        cover_data = base64.b64encode(image_file.read()).decode()
                    cover_data = "data:image/jpg;base64," + cover_data

                    # And then send it up to Stash
                    result = stash.update_scene({"id": scene_id, "cover_image": cover_data})
                    if not result:
                        print("Could not submit cover image for scene.  Skipping...")

                except Exception:
                    print("Could not create cover image for scene ({filename}).  Tagging with Cover Error tag and skipping...")
                    stash.update_scenes({"ids": scene_id, "tag_ids": {"ids": cover_error_tag, "mode": "ADD"}})
                    stash.update_scenes({"ids": scene_id, "tag_ids": {"ids": hashing_tag, "mode": "REMOVE"}})

                if os.path.isfile(image_filename):
                    os.remove(image_filename)

        # Processes don't seem to require the sanitizing that direct call does...  still testing
        ffmpeg_filename = filename
        ffmpeg_filename = f'"{ffmpeg_filename}"'

        if generate_sprite:
            # Define input video path and output sprite path
            video_path = ffmpeg_filename
            output_file = f"{sprite_path}/{filehash}_sprite.jpg"
            vtt_file = f"{sprite_path}/{filehash}_thumbs.vtt"

            if not os.path.exists(output_file):
                # Create an instance of the VideoSpriteGenerator class
                print(f"Creating sprite image for {video_path} as \"{output_file}\"")
                generator = VideoSpriteGenerator(video_path, output_file, vtt_file, ffmpeg, ffprobe)

                # Generate the sprite
                generator.generate_sprite()
            else:
                print(f"Sprite already exists for {output_file}, skipping sprite generation...")

        if generate_preview:
            # Define input video path and output preview path
            video_path = ffmpeg_filename
            output_file = f"{preview_path}/{filehash}.mp4"

            if not os.path.exists(output_file):
                # Create an instance of the PreviewVideoGenerator class
                print(f"Creating preview video for {video_path} as \"{output_file}\"")
                generator = PreviewVideoGenerator(video_path, output_file, ffmpeg, ffprobe, preview_clips, preview_clip_length, preview_skip_seconds, preview_audio)

                # Generate the preview
                generator.generate_preview()
            else:
                print(f"Preview video already exists for {output_file}, skipping preview generation...")

        # And finally unflag the scene as being worked on
        stash.update_scenes({"ids": scene['id'], "tag_ids": {"ids": hashing_tag, "mode": "REMOVE"}})
        print(f"Finished with ID# {scene_id} with Filename: {filename_pretty} ")
        print()

    main()


if __name__ == '__main__':
    main()
