# preview_video_generator.py

import subprocess
import os
import shutil
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor
from config import verbose  # ✅ Import verbose flag

class PreviewVideoGenerator:
    def __init__(self, filename, output_path, filehash, ffmpeg='ffmpeg', ffprobe='ffprobe',
                 num_clips=15, clip_length=1, skip_seconds=0, include_audio=True,
                 scene_id=None, scene_name=None):
        self.filename = os.path.abspath(filename.strip('"').strip("'"))
        self.output_path = os.path.abspath(output_path)
        self.temp_dir = os.path.abspath(os.path.join(".", f"preview_temp_{filehash}"))
        self.num_clips = num_clips
        self.clip_length = clip_length
        self.skip_seconds = skip_seconds
        self.include_audio = include_audio
        self.ffmpeg = ffmpeg
        self.ffprobe = ffprobe
        self.scene_id = scene_id
        self.scene_name = scene_name

    def get_video_duration(self):
        result = subprocess.run(
            [self.ffprobe, '-v', 'error', '-show_entries', 'format=duration',
             '-of', 'default=noprint_wrappers=1:nokey=1', self.filename],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )
        return float(result.stdout)

    def clean_previous_clips(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def generate_clips(self):
        os.makedirs(self.temp_dir, exist_ok=True)
        video_duration = self.get_video_duration()
        start_times = self.get_start_times(video_duration)

        def extract_clip(i, start_time):
            clip_file = os.path.join(self.temp_dir, f"clip_{i:03d}.mp4")
            command = [
                self.ffmpeg,
                '-ss', str(start_time),
                '-i', self.filename,
                '-t', str(self.clip_length),
                '-s', '640x360',
                '-c:v', 'libx264',
                '-crf', '18',
                '-preset', 'slow',
                '-loglevel', 'quiet'
            ]
            if self.include_audio:
                command.extend(['-c:a', 'aac', '-b:a', '192k', '-strict', 'experimental'])
            else:
                command.append('-an')
            command.append(clip_file)
            try:
                subprocess.run(command, check=True)
            except subprocess.CalledProcessError as e:
                print(f"❌ Failed to generate clip {i} for scene {self.scene_id} — {self.scene_name}: {e}")
                return None
            return clip_file

        clips = []
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(extract_clip, i, start_time) for i, start_time in enumerate(start_times)]
            iterator = tqdm(futures, desc="🎞️ Generating Preview Clips", unit="clip") if verbose else futures
            for future in iterator:
                clip = future.result()
                if clip:
                    clips.append(clip)

        return clips

    def get_start_times(self, video_duration):
        interval = (video_duration - self.skip_seconds - self.clip_length) / (self.num_clips + 1)
        return [self.skip_seconds + interval * i for i in range(1, self.num_clips + 1)]

    def concatenate_clips(self, clips):
        missing = [clip for clip in clips if not os.path.exists(clip)]
        if missing:
            raise FileNotFoundError(f"Missing clips: {missing}")

        concat_file = os.path.join(self.temp_dir, "clips.txt")
        with open(concat_file, 'w') as f:
            for clip in sorted(clips):
                safe_path = os.path.normpath(clip).replace("\\", "/")
                f.write(f"file '{safe_path}'\n")

        command = [
            self.ffmpeg,
            '-f', 'concat',
            '-safe', '0',
            '-i', concat_file,
            '-c:v', 'libx264',
            '-crf', '18',
            '-preset', 'slow',
            '-loglevel', 'quiet'
        ]
        if self.include_audio:
            command.extend(['-c:a', 'aac', '-b:a', '192k'])
        else:
            command.append('-an')

        command.append(self.output_path)

        try:
            subprocess.run(command, check=True)
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to concatenate preview for scene {self.scene_id} — {self.scene_name}: {e}")
            raise RuntimeError(f"FFmpeg failed to concatenate clips: {e}")

    def generate_preview(self):
        self.clean_previous_clips()
        clips = self.generate_clips()
        if not clips:
            print(f"❌ No clips generated for scene {self.scene_id} — {self.scene_name}")
            return
        try:
            self.concatenate_clips(clips)
            if os.path.exists(self.output_path):
                if verbose:
                    print(f"🎞️ Preview video created for ID {self.scene_id} — {self.scene_name} → {self.output_path}")
            else:
                print(f"❌ Preview video not created for ID {self.scene_id} — {self.scene_name}")
        except Exception as e:
            print(f"❌ Preview generation failed for scene {self.scene_id} — {self.scene_name}: {e}")
        finally:
            self.clean_previous_clips()
