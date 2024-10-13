#!/usr/bin/python

# Modules needed:
# pip install stashapp-tools

import re
import os
import requests
import json
import string
from json.decoder import JSONDecodeError
import subprocess
import random
import base64

# Stash import and settings
from stashapi.stashapp import StashInterface
stash = StashInterface({"host": "192.168.1.71", "port": 9999})
config = stash.get_configuration()["plugins"]

# Stash very likely has different mount paths than the node, so any translations should be listed here.
# It's a simple find and replace.  Btw for Windows systems, please use unix style forward slashes, for example "C:/Media/Path/"
# The two entries are 'orig' for the path that is in the Stash database, and 'local' for what the local system sees the path as

# Example for Windows:
#translations = [
#    {'orig': '/data/', 'local': 'S:/'},
#    {'orig': '/xerxes/', 'local': 'P:/'},
#    {'orig': '/data_stranghouse/', 'local': 'R:/'},
#    {'orig': '/mnt/gomorrah/', 'local': 'G:/'},
#]

# Example for Linux
# translations = [
#    {'orig': '/data/', 'local': '/mnt/strangyr/'},
#    {'orig': '/xerxes/', 'local': '/mnt/xerxes/'},
#    {'orig': '/data_stranghouse/', 'local': '/mnt/Stranghouse/'},
#]

# This is silly, and there's probably a workaround but I had to use double quotes (") around filenames in Windows
# and single quotes (') around filenames in Linux for FFMPEG to work correctly.  For Windows, use regular backslashes here
#
# This script uses the videohashes binary written by Peolic, which you can get here: https://github.com/peolic/videohashes

windows = True
binary_windows = r".\videohashes-windows.exe"
binary_linux = r"./videohashes-linux"

# You can use Python's static_ffmpeg or binaries you already have
# ~ ffmpeg = "static_ffmpeg"
ffmpeg = r"c:\mediatools\ffmpeg.exe"

# Simply tags in Stash that identifies "This scene is being worked on", or has an error.
# I called mine 'Work_Hashing', "Work_Hash_Error" and "Work_Cover_Error", but they can be anything.  Just need the numeric ids here
hashing_tag = 15015
hashing_error_tag = 15018
cover_error_tag = 15019


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
        scenelist = stash.find_scenes(f={"phash": {"value": "", "modifier": "IS_NULL"}, "tags": {"value": [hashing_tag, hashing_error_tag, cover_error_tag], "modifier": "EXCLUDES"}}, filter={"sort": "created_at", "direction": "DESC", "per_page": 25, "page": page}, fragment="id files{id path} paths{screenshot}")
    else:
        scenelist = stash.find_scenes(f={"phash": {"value": "", "modifier": "IS_NULL"}, "tags": {"value": [hashing_tag, hashing_error_tag, cover_error_tag], "modifier": "EXCLUDES"}}, filter={"sort": "created_at", "direction": "DESC", "per_page": -1}, fragment="id files{id path} paths{screenshot}")

    # First we claim these scenes for this node to work on by appending the "hashing_tag" to the scenes
    for scene in scenelist:
        stash.update_scenes({"ids": scene['id'], "tag_ids": {"ids": hashing_tag, "mode": "ADD"}})

    for scene in scenelist:
        # ~ print(scene)
        scene_id = scene['id']
        file_id = scene['files'][0]['id']
        filename = scene['files'][0]['path']
        filename_pretty = re.search(r'.*[/\\](.*?)$', filename).group(1)
        for translation in translations:
            filename = filename.replace(translation['orig'], translation['local'])

        print(f"Working on ID# {scene_id} with Filename: {filename_pretty} ")
        if windows:
            videohash = binary_windows
        else:
            videohash = binary_linux

        result = subprocess.run([videohash, '-json', filename],
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=True)
        try:
            results = json.loads(result.stdout.decode("utf-8"))
        except JSONDecodeError as e:
            print(f"Encountered an error:  {e}...  Marking scene with Hashing Error tag.")
            stash.update_scenes({"ids": scene_id, "tag_ids": {"ids": hashing_error_tag, "mode": "ADD"}})
            stash.update_scenes({"ids": scene_id, "tag_ids": {"ids": hashing_tag, "mode": "REMOVE"}})
            print("\n\n")
            continue

        if "phash" in results and results['phash']:
            print(f"Updating hash for '{filename_pretty}' with Phash: {results['phash']}")
            stash.file_set_fingerprints(file_id, [{"type": "phash", "value": results['phash']}])

        # Lets check for a "default" cover image
        cover_image = scene['paths']['screenshot']
        if cover_image:
            cover_image = requests.get(cover_image)
            cover_image = cover_image.content.decode('latin_1')
            if re.search(r'(<svg)', cover_image.lower()):

                # Silly, but need to pre-sanitize filenames for ffmpeg.  It's touchy
                if not windows:
                    ffmpeg_filename = filename.replace('"', '\'\\\'"').replace("'", r"'\''")
                else:
                    ffmpeg_filename = filename

                if windows:
                    ffmpeg_filename = f'"{ffmpeg_filename}"'
                else:
                    ffmpeg_filename = f"'{ffmpeg_filename}'"

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
                    print("Could not create cover image for scene.  Tagging with Cover Error tag and skipping...")
                    stash.update_scenes({"ids": scene_id, "tag_ids": {"ids": cover_error_tag, "mode": "ADD"}})
                    stash.update_scenes({"ids": scene_id, "tag_ids": {"ids": hashing_tag, "mode": "REMOVE"}})

                if os.path.isfile(image_filename):
                    os.remove(image_filename)

        # And finally unflag the scene as being worked on
        stash.update_scenes({"ids": scene['id'], "tag_ids": {"ids": hashing_tag, "mode": "REMOVE"}})
        print()

    main()


if __name__ == '__main__':
    main()
