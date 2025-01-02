#!/usr/bin/env python3

from pprint import pprint
import json
import random
from pathlib import Path
from typing import List
import fire
from tqdm import tqdm

MEDIA_EXTENSIONS = {'.mp3', '.mp4', '.avi', '.mkv', '.mov', '.wav', '.flac'}

def get_duration(file_path: Path, base_path: Path, verbose: bool = False) -> int:
    """Get duration of a media file in seconds.
    
    Args:
        file_path: Path to media file
        base_path: Base path for relative path calculation
        verbose: Print detailed processing information
    """
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
        val = int(float(result.stdout.decode('utf-8').strip()))
        if verbose:
            filename = str(file_path.relative_to(base_path))
            print(f"{filename:<50}: {val:>6}s")
        return val
    except (subprocess.CalledProcessError, ValueError) as e:
        if verbose:
            filename = str(file_path.relative_to(base_path))
            print(f"E: {filename:<50}: {e}")
        return 0


def main(filepath: str, outpath: str = "media_durations.json", verbose: bool = False) -> None:
    """Main function to calculate total duration of media files.
    
    Args:
        filepath: Path to directory containing media files
        outpath: Path to output JSON file (default: media_durations.json)
        verbose: Print detailed processing information
    """
    path = Path(filepath)
    results = {}
    
    # Get all media files
    media_files = [f for f in path.rglob('*') if f.suffix.lower() in MEDIA_EXTENSIONS and not f.name.startswith('.')]
    if verbose:
        pprint([f.name for f in media_files])
    random.shuffle(media_files)
    
    # Calculate total size
    total_size = sum(f.stat().st_size for f in media_files)
    total_size_gb = total_size / (1024 ** 3)
    
    print(f"Found {len(media_files)} media files ({total_size_gb:.2f} GB)")
    
    # Process files
    current_duration = 0
    processed_size = 0
    
    for file in tqdm(media_files, desc="Processing files"):
        duration = get_duration(file, path, verbose)
        file_size = file.stat().st_size
        current_duration += duration
        processed_size += file_size
        
        # Store results
        results[str(file)] = {
            'duration': duration,
            'size': file_size
        }
        
        # Calculate estimated total duration
        if processed_size > 0:
            estimated_total = (total_size / processed_size) * current_duration
            tqdm.write(f"Current: {current_duration//3600}h {(current_duration%3600)//60}m | "
                      f"Estimated total: {estimated_total//3600:.0f}h {(estimated_total%3600)//60:.0f}m")
    
    print(f"\nTotal duration: {current_duration//3600}h {(current_duration%3600)//60}m")
    
    # Write results to JSON file
    with open(outpath, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"Results saved to {outpath}")

if __name__ == '__main__':
    fire.Fire(main)
