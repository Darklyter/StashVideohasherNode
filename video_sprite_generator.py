import subprocess
from PIL import Image
import os
import shutil
from tqdm import tqdm

class VideoSpriteGenerator:
    def __init__(self, video_path, sprite_path, vtt_path, ffmpeg='ffmpeg', ffprobe='ffprobe', total_shots=81, max_width=160, max_height=90, columns=9, rows=9):
        self.video_path = video_path.strip('"').strip("'")
        self.output_dir = 'screenshots'
        self.sprite_path = sprite_path
        self.vtt_path = vtt_path
        self.total_shots = total_shots
        self.max_width = max_width
        self.max_height = max_height
        self.columns = columns
        self.rows = rows
        self.ffmpeg = ffmpeg
        self.ffprobe = ffprobe

    def get_video_duration(self):
        # Use ffprobe to get the video duration
        result = subprocess.run([self.ffprobe, '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', self.video_path], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        return float(result.stdout)

    def clean_previous_files(self):
        # Remove the screenshots directory if it exists
        if os.path.exists(self.output_dir):
            shutil.rmtree(self.output_dir)

        # Remove the VTT file if it exists
        if os.path.exists(self.vtt_path):
            os.remove(self.vtt_path)

    def take_screenshots(self):
        # Pre-emptively clean any leftover files
        self.clean_previous_files()

        # Create the output directory if it doesn't exist
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

        video_duration = self.get_video_duration()
        start_time = 0
        interval = video_duration / self.total_shots

        with open(self.vtt_path, 'w') as vtt_file:
            vtt_file.write("WEBVTT\n\n")

            print(f"Creating sprite frames for {os.path.basename(self.sprite_path)}...")
            
            for i in tqdm(range(self.total_shots), desc="Progress", total=self.total_shots):
                time = start_time + i * interval
                output_file = os.path.join(self.output_dir, f'frame_{i:03d}.jpg')
                command = [
                    self.ffmpeg,
                    '-ss', str(time),
                    '-i', self.video_path,
                    '-frames:v', '1',
                    '-q:v', '2',
                    '-vf', 'scale=160:90',
                    '-y',  # Overwrite output files without asking
                    '-update', '1',  # Add update flag to handle single image output
                    output_file,
                    '-loglevel', 'error'  # Change to error to only show important issues
                ]
                
                subprocess.run(command, check=True)

                # Resize the image
                with Image.open(output_file) as img:
                    img = img.resize((self.max_width, self.max_height), Image.Resampling.LANCZOS)
                    img.save(output_file)

                # Calculate end time
                end_time = time + interval

                # Format start and end times
                start_time_str = self.format_time(time)
                end_time_str = self.format_time(end_time)

                # Calculate xywh values
                x = (i % self.columns) * self.max_width
                y = (i // self.columns) * self.max_height

                # Write VTT entry with the sprite filename
                vtt_file.write(f"{start_time_str} --> {end_time_str}\n")
                vtt_file.write(f"{os.path.basename(self.sprite_path)}#xywh={x},{y},{self.max_width},{self.max_height}\n\n")

    def format_time(self, seconds):
        millisec = int((seconds % 1) * 1000)
        seconds = int(seconds)
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        return f"{hours:02}:{minutes:02}:{seconds:02}.{millisec:03}"

    def create_sprite(self):
        # Get list of image files
        images = [Image.open(os.path.join(self.output_dir, img)) for img in sorted(os.listdir(self.output_dir)) if img.endswith('.jpg')]
        if not images:
            raise ValueError("Something went wrong, no images found to create sprite")

        # Determine sprite size
        sprite_width = self.max_width * self.columns
        sprite_height = self.max_height * self.rows
        sprite = Image.new('RGB', (sprite_width, sprite_height))

        # Paste images into the sprite
        for idx, img in enumerate(images):
            x = (idx % self.columns) * self.max_width
            y = (idx // self.columns) * self.max_height
            sprite.paste(img, (x, y))

        sprite.save(self.sprite_path)
        # ~ print(f"Sprite image created and saved at {self.sprite_path}")

        # ~ # Remove all screenshot images from the drive
        for img in images:
            os.remove(img.filename)

    def clean_up(self):
        # Remove the screenshots directory
        if os.path.exists(self.output_dir):
            shutil.rmtree(self.output_dir)

    def generate_sprite(self):
        self.take_screenshots()
        self.create_sprite()
        self.clean_up()
