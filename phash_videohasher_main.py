# main.py

import argparse
import re
import os
import shutil
import time
import subprocess
from concurrent.futures import ThreadPoolExecutor

import config
from helpers.scene_discovery import discover_scenes
from helpers.scene_processor import process_scene
from helpers.stash_utils import get_total_scene_count, tag_scene_error, reset_terminal, claim_scene

def apply_cli_args(args):
    config.windows = args.windows
    config.generate_sprite = args.generate_sprite
    config.generate_preview = args.generate_preview
    config.dry_run = args.dry_run
    config.verbose = args.verbose
    config.once = args.once
    if args.batch_size:
        config.per_page = args.batch_size
    if args.max_workers:
        config.max_workers = args.max_workers

def clean_temp_dirs():
    for folder in os.listdir():
        if folder.startswith("preview_temp_") or folder.startswith("screenshots_") or folder.startswith("cover_temp_"):
            try:
                shutil.rmtree(folder)
                if config.verbose:
                    print(f"🧹 Removed leftover temp folder: {folder}")
            except Exception as e:
                if config.verbose:
                    print(f"⚠️ Failed to remove {folder}: {e}")

def main():
    parser = argparse.ArgumentParser(description="Stash Scene Processor CLI")
    parser.add_argument("--windows", action="store_true", help="Use Windows-style paths and binaries")
    parser.add_argument("--generate-sprite", action="store_true", help="Enable sprite image generation")
    parser.add_argument("--generate-preview", action="store_true", help="Enable preview video generation")
    parser.add_argument("--batch-size", type=int, help="Number of scenes to process per run (default: 25)")
    parser.add_argument("--max-workers", type=int, help="Number of threads for parallel processing (default: 4)")
    parser.add_argument("--dry-run", action="store_true", help="Simulate processing without writing changes")
    parser.add_argument("--verbose", action="store_true", help="Enable detailed output and progress bars")
    parser.add_argument("--once", action="store_true", help="Run a single batch and exit")

    args = parser.parse_args()
    apply_cli_args(args)

    while True:
        clean_temp_dirs()

        scenes = discover_scenes()
        if not scenes:
            print("✅ No scenes to process. Exiting.")
            reset_terminal()
            break

        total_batch = len(scenes)
        total_database = get_total_scene_count()
        print(f"🎯 Selected page with {total_batch} scenes (out of {total_database} total)")

        for scene in scenes:
            try:
                claim_scene(scene['id'])
            except Exception as e:
                print(f"⚠️ Failed to tag scene {scene['id']} during batch tagging: {e}")

        try:
            with ThreadPoolExecutor(max_workers=config.max_workers) as executor:
                futures = []
                for index, scene in enumerate(scenes, start=1):
                    filename_pretty = re.search(r'.*[/\\](.*?)$', scene['files'][0]['path']).group(1)
                    futures.append(executor.submit(process_scene, scene, index, total_batch))

                for future in futures:
                    future.result()

        except KeyboardInterrupt:
            print("\n🛑 Interrupted by user. Shutting down gracefully...")
            executor.shutdown(wait=False, cancel_futures=True)
            reset_terminal()
            break

        if config.once:
            print("✅ Finished single batch. Exiting due to --once flag.")
            reset_terminal()
            break

        print("⏳ Waiting 5 seconds before next batch... Press Ctrl+C to cancel.")
        time.sleep(5)

if __name__ == '__main__':
    main()
