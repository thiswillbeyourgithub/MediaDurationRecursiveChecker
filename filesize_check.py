#!/usr/bin/env python3

import random
from pathlib import Path
from typing import List
import fire
from tqdm import tqdm

MEDIA_EXTENSIONS = {'.mp3', '.mp4', '.avi', '.mkv', '.mov', '.wav', '.flac'}

def get_duration(file_path: Path) -> int:
    """Get duration of a media file in seconds."""
    # Using ffprobe to get duration
    import subprocess
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'error', '-show_entries', 
             'format=duration', '-of', 
             'default=noprint_wrappers=1:nokey=1', str(file_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )
        return int(float(result.stdout.decode('utf-8').strip()))
    except (subprocess.CalledProcessError, ValueError):
        return 0

def main(filepath: str) -> None:
    """Main function to calculate total duration of media files."""
    path = Path(filepath)
    
    # Get all media files
    media_files = [f for f in path.rglob('*') if f.suffix.lower() in MEDIA_EXTENSIONS]
    random.shuffle(media_files)
    
    # Calculate total size
    total_size = sum(f.stat().st_size for f in media_files)
    total_size_gb = total_size / (1024 ** 3)
    
    print(f"Found {len(media_files)} media files ({total_size_gb:.2f} GB)")
    
    # Process files
    current_duration = 0
    processed_size = 0
    
    for file in tqdm(media_files, desc="Processing files"):
        duration = get_duration(file)
        current_duration += duration
        processed_size += file.stat().st_size
        
        # Calculate estimated total duration
        if processed_size > 0:
            estimated_total = (total_size / processed_size) * current_duration
            tqdm.write(f"Current: {current_duration//3600}h {(current_duration%3600)//60}m | "
                      f"Estimated total: {estimated_total//3600:.0f}h {(estimated_total%3600)//60:.0f}m")
    
    print(f"\nTotal duration: {current_duration//3600}h {(current_duration%3600)//60}m")

if __name__ == '__main__':
    fire.Fire(main)
