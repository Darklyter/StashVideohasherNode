import subprocess
import os
from tqdm import tqdm

class PreviewVideoGenerator:
    def __init__(self, filename, output_path, ffmpeg='ffmpeg', ffprobe='fprobe', num_clips=15, clip_length=1, skip_seconds=0, include_audio=True):
        self.filename = filename.strip('"').strip("'")
        self.output_path = output_path
        self.num_clips = num_clips
        self.clip_length = clip_length
        self.skip_seconds = skip_seconds
        self.include_audio = include_audio
        self.ffmpeg = ffmpeg
        self.ffprobe = ffprobe

    def get_video_duration(self):
        # Use ffprobe to get the video duration
        result = subprocess.run([self.ffprobe, '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', self.filename],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT)
        return float(result.stdout)

    def clean_previous_clips(self):
        # Remove any leftover clip files
        for file in os.listdir():
            if file.startswith('clip_') and file.endswith('.mp4'):
                os.remove(file)
                # ~ print(f"Removed leftover clip file: {file}")

    def generate_clips(self):
        video_duration = self.get_video_duration()
        start_times = self.get_start_times(video_duration)
        clips = []

        for i, start_time in tqdm(enumerate(start_times), desc="Generating clips", total=len(start_times)):
            clip_file = f"clip_{i:03d}.mp4"
            command = [
                self.ffmpeg,
                '-ss', str(start_time),
                '-i', self.filename,
                '-t', str(self.clip_length),
                '-s', '640x360',
                '-c:v', 'libx264',
                '-crf', '18',  # High-quality setting
                '-preset', 'slow',  # High-quality preset
                '-loglevel', 'quiet'  # Suppress all ffmpeg output
            ]
            if self.include_audio:
                command.extend(['-c:a', 'aac', '-b:a', '192k', '-strict', 'experimental'])
            else:
                command.append('-an')

            command.append(clip_file)
            subprocess.run(command, check=True)
            clips.append(clip_file)

        return clips

    def get_start_times(self, video_duration):
        if self.num_clips * self.clip_length > (video_duration - self.skip_seconds):
            raise ValueError("Total clip length exceeds video duration after skip")

        start_times = []
        interval = (video_duration - self.skip_seconds - self.clip_length) / (self.num_clips + 1)
        for i in range(1, self.num_clips + 1):
            start_times.append(self.skip_seconds + interval * i)

        return start_times

    def concatenate_clips(self, clips):
        with open('clips.txt', 'w') as f:
            for clip in sorted(clips):
                f.write(f"file '{clip}'\n")

        command = [
            self.ffmpeg,
            '-f', 'concat',
            '-safe', '0',
            '-i', 'clips.txt',
            '-c:v', 'libx264',
            '-crf', '18',  # High-quality setting
            '-preset', 'slow',  # High-quality preset
            '-loglevel', 'quiet'  # Suppress all ffmpeg output
        ]
        if self.include_audio:
            command.extend(['-c:a', 'aac', '-b:a', '192k'])
        else:
            command.append('-an')

        command.append(self.output_path)
        subprocess.run(command, check=True)

        # Cleanup
        os.remove('clips.txt')
        for clip in clips:
            os.remove(clip)

    def generate_preview(self):
        # Clean any leftover clip files before running
        self.clean_previous_clips()

        clips = self.generate_clips()
        print("Concatenating clips...")
        self.concatenate_clips(clips)
        print(f"Preview video created and saved at {self.output_path}")

        # Clean any leftover clip files after running
        self.clean_previous_clips()
