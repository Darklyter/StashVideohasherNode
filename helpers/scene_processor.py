# scene_processor.py

import os
import re
import subprocess
import json
import string
import base64
import random
import requests
import shutil
from json.decoder import JSONDecodeError
from datetime import datetime

from helpers.video_sprite_generator import VideoSpriteGenerator
from helpers.preview_video_generator import PreviewVideoGenerator

from config import (
    windows, binary, ffmpeg, ffprobe,
    generate_sprite, generate_preview, sprite_path, preview_path,
    preview_audio, preview_clips, preview_clip_length, preview_skip_seconds,
    translations, dry_run, verbose,
    hashing_tag, hashing_error_tag, cover_error_tag
)

from helpers.stash_utils import (
    claim_scene, release_scene, tag_scene_error,
    update_phash, update_cover, log_scene_failure
)

def process_scene(scene, index=None, total_batch=None):
    scene_id = scene['id']
    file_id = scene['files'][0]['id']
    filename = scene['files'][0]['path']
    filename_pretty = re.search(r'.*[/\\](.*?)$', filename).group(1)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if index and total_batch:
        print(f"[{timestamp}] 📦 Scene #{index} of {total_batch}: ID {scene_id} — {filename_pretty}")
    else:
        print(f"[{timestamp}] 📦 Processing scene: ID {scene_id} — {filename_pretty}")

    for t in translations:
        filename = filename.replace(t['orig'], t['local'], 1)

    filehash = ""
    for fp in scene['files'][0].get('fingerprints', []):
        if fp['type'].lower() == "oshash":
            filehash = fp['value']

    if not filehash or ":" in filehash or "\\" in filehash or "/" in filehash:
        filehash = ''.join(random.choices(string.ascii_lowercase + string.digits, k=12))

    filename = os.path.normpath(filename)
    file_exists = os.path.exists(filename)

    if verbose:
        print(f"🔍 Translated path: {filename}")
        print(f"📂 File exists: {file_exists}")

    if not file_exists:
        log_scene_failure(scene_id, filename_pretty, "file check", "File not found after translation")
        tag_scene_error(scene_id, hashing_error_tag, "File not found after translation")
        return

    claim_scene(scene_id)

    if dry_run:
        print(f"[DRY RUN] Would run videohash on {filename}")
    else:
        try:
            result = subprocess.run([binary, '-json', filename], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=True)
            results = json.loads(result.stdout.decode("utf-8"))
            update_phash(file_id, results['phash'])
        except Exception as e:
            log_scene_failure(scene_id, filename_pretty, "hashing", e)
            tag_scene_error(scene_id, hashing_error_tag, str(e))
            return

    try:
        cover_image = scene['paths'].get('screenshot')
        if cover_image and "<svg" in requests.get(cover_image).content.decode('latin_1').lower():
            temp_dir = os.path.abspath(f"cover_temp_{filehash}")
            os.makedirs(temp_dir, exist_ok=True)
            image_filename = os.path.join(temp_dir, f"{filehash}_cover.jpg")
            ffmpegcmd = [
                ffmpeg, '-hide_banner', '-loglevel', 'error',
                '-i', filename, '-ss', '00:00:30', '-vframes', '1',
                image_filename, '-nostdin'
            ]

            if dry_run:
                print(f"[DRY RUN] Would extract cover image using: {' '.join(ffmpegcmd)}")
            else:
                try:
                    subprocess.run(ffmpegcmd, check=True)
                    if not os.path.exists(image_filename):
                        ffmpegcmd[ffmpegcmd.index('-ss') + 1] = '00:00:05'
                        subprocess.run(ffmpegcmd, check=True)
                    if not os.path.exists(image_filename):
                        raise FileNotFoundError(f"Cover image not created: {image_filename}")
                    with open(image_filename, "rb") as img:
                        encoded = base64.b64encode(img.read()).decode()
                    update_cover(scene_id, "data:image/jpg;base64," + encoded)
                except Exception as e:
                    log_scene_failure(scene_id, filename_pretty, "cover image generation", e)
                    tag_scene_error(scene_id, cover_error_tag, str(e))
                finally:
                    shutil.rmtree(temp_dir, ignore_errors=True)
    except Exception as e:
        log_scene_failure(scene_id, filename_pretty, "cover image setup", e)
        tag_scene_error(scene_id, cover_error_tag, str(e))

    if generate_sprite:
        sprite_file = os.path.join(sprite_path, f"{filehash}_sprite.jpg")
        vtt_file = os.path.join(sprite_path, f"{filehash}_thumbs.vtt")
        if not os.path.exists(sprite_file):
            if dry_run:
                print(f"[DRY RUN] Would generate sprite for {filename_pretty} → {sprite_file}")
            else:
                try:
                    generator = VideoSpriteGenerator(filename, sprite_file, vtt_file, filehash, ffmpeg, ffprobe)
                    generator.generate_sprite()
                except Exception as e:
                    log_scene_failure(scene_id, filename_pretty, "sprite generation", e)
                    tag_scene_error(scene_id, hashing_error_tag, str(e))
                    return

    if generate_preview:
        preview_file = os.path.join(preview_path, f"{filehash}.mp4")
        if not os.path.exists(preview_file):
            if dry_run:
                print(f"[DRY RUN] Would generate preview for {filename_pretty} → {preview_file}")
            else:
                try:
                    generator = PreviewVideoGenerator(
                        filename, preview_file, filehash, ffmpeg, ffprobe,
                        preview_clips, preview_clip_length, preview_skip_seconds, preview_audio,
                        scene_id=scene_id, scene_name=filename_pretty
                    )
                    generator.generate_preview()
                except Exception as e:
                    log_scene_failure(scene_id, filename_pretty, "preview generation", e)
                    tag_scene_error(scene_id, hashing_error_tag, str(e))
                    return

    release_scene(scene_id)
