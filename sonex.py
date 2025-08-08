#!/usr/bin/env python3
import os
import shutil
import configparser
from datetime import datetime
import ffmpeg
from tqdm import tqdm
import glob

# Configuration file path
CONFIG_FILE = 'camera_organizer_config.ini'

class MediaOrganizer:
    def __init__(self):
        self.config = configparser.ConfigParser()
        self.load_config()

    def load_config(self):
        """Load previous paths from config file."""
        if os.path.exists(CONFIG_FILE):
            self.config.read(CONFIG_FILE)
            self.camera_path = self.config.get('Paths', 'camera_path', fallback='')
            self.destination_root = self.config.get('Paths', 'destination_root', fallback='')
        else:
            self.camera_path = ''
            self.destination_root = ''

    def save_config(self):
        """Save paths to config file."""
        self.config['Paths'] = {
            'camera_path': self.camera_path,
            'destination_root': self.destination_root
        }
        with open(CONFIG_FILE, 'w') as configfile:
            self.config.write(configfile)

    def get_creation_date(self, file_path):
        """Extract creation date from file metadata."""
        try:
            probe = ffmpeg.probe(file_path)
            for stream in probe['streams']:
                if 'tags' in stream and 'creation_time' in stream['tags']:
                    creation_time = stream['tags']['creation_time']
                    return datetime.strptime(creation_time, '%Y-%m-%dT%H:%M:%S.%fZ').strftime('%m-%d-%Y')
        except Exception:
            pass

        # Fallback to file creation time
        return datetime.fromtimestamp(os.path.getctime(file_path)).strftime('%m-%d-%Y')

    def find_associated_video(self, cpi_file):
        """Find the associated video file for a CPI file."""
        clip_name = os.path.basename(cpi_file).replace('.CPI', '')
        clip_dir = os.path.dirname(os.path.dirname(cpi_file))
        video_files = glob.glob(os.path.join(clip_dir, f"{clip_name}*.MTS"))
        return video_files[0] if video_files else None

    def convert_image_to_jpg(self, input_file, output_file):
        """Convert image to JPG format."""
        if os.path.exists(output_file):
            return False

        try:
            stream = ffmpeg.input(input_file)
            stream = ffmpeg.output(stream, output_file, vcodec='mjpeg', qscale=2)
            ffmpeg.run(stream, quiet=True)
            return True
        except Exception as e:
            print(f"Error converting {input_file} to JPG: {e}")
            return False

    def convert_to_m2ts(self, input_file, output_file):
        """Convert video to M2TS format."""
        if os.path.exists(output_file):
            return False

        try:
            stream = ffmpeg.input(input_file)
            stream = ffmpeg.output(stream, output_file, vcodec='copy', acodec='copy', f='mpegts')
            ffmpeg.run(stream, quiet=True)
            return True
        except Exception as e:
            print(f"Error converting {input_file} to M2TS: {e}")
            return False

    def process_media_files(self):
        """Process all media files."""
        # Get all files from camera
        files = []
        for root, _, filenames in os.walk(self.camera_path):
            for filename in filenames:
                files.append(os.path.join(root, filename))

        processed_count = 0
        skipped_count = 0

        for file_path in tqdm(files, desc="Processing files"):
            date_str = self.get_creation_date(file_path)
            destination_dir = os.path.join(self.destination_root, date_str)
            os.makedirs(destination_dir, exist_ok=True)

            if file_path.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.tiff')):
                # Process image file - convert to JPG
                output_filename = os.path.splitext(os.path.basename(file_path))[0] + '.jpg'
                output_path = os.path.join(destination_dir, output_filename)

                if self.convert_image_to_jpg(file_path, output_path):
                    processed_count += 1
                else:
                    skipped_count += 1

            elif file_path.lower().endswith(('.mts', '.cpi')):
                # Process video file - convert to M2TS
                output_filename = os.path.splitext(os.path.basename(file_path))[0] + '.m2ts'
                output_path = os.path.join(destination_dir, output_filename)

                if file_path.lower().endswith('.cpi'):
                    video_file = self.find_associated_video(file_path)
                    if video_file:
                        if self.convert_to_m2ts(video_file, output_path):
                            processed_count += 1
                        else:
                            skipped_count += 1
                else:
                    if self.convert_to_m2ts(file_path, output_path):
                        processed_count += 1
                    else:
                        skipped_count += 1

        print(f"\nProcessing complete!")
        print(f"Processed {processed_count} files")
        print(f"Skipped {skipped_count} files (already existed or errors)")
        print(f"Media organized in: {self.destination_root}")

    def get_path_input(self, path_type, current_path):
        """Get path input from user."""
        if current_path:
            use_previous = input(f"\nPrevious {path_type} path: {current_path}\nUse previous path? (y/n): ").lower()
            if use_previous == 'y':
                return current_path

        while True:
            path = input(f"\nEnter the {path_type} path: ").strip()
            if path_type == 'camera' and os.path.exists(path):
                return path
            if path_type == 'destination':
                if os.path.exists(path):
                    return path
                confirm = input(f"Folder '{path}' doesn't exist. Create it? (y/n): ").lower()
                if confirm == 'y':
                    os.makedirs(path)
                    return path
            print(f"Error: Invalid {path_type} path. Please try again.")

    def run(self):
        """Main program loop."""
        print("Welcome to Media Organizer")
        print("-------------------------")

        # Get camera path
        self.camera_path = self.get_path_input('camera', self.camera_path)

        # Get destination path
        self.destination_root = self.get_path_input('destination', self.destination_root)

        # Save paths for next time
        self.save_config()

        # Process files
        print("\nStarting file processing...")
        self.process_media_files()

if __name__ == "__main__":
    organizer = MediaOrganizer()
    organizer.run()
