#!/usr/bin/env python3
"""Media Duration and Size Analyzer

Repository: https://github.com/thiswillbeyourgithub/FileSizeTreeChecker
Author: thiswillbeyourgithub
License: GPLv3

This script calculates the total duration and size of media files in a directory tree.
It supports common media formats including MP3, MP4, AVI, MKV, MOV, WAV, and FLAC.

Key Features:
- Recursively scans directories for media files
- Calculates total duration in hours and minutes
- Estimates total processing time based on file sizes
- Saves results to a JSON file with individual file details
- Progress tracking with tqdm (if installed)
- Verbose mode for detailed processing information

Usage:
    python FileSizeTreeChecker.py /path/to/media [--outpath output.json] [--verbose]

Arguments:
    filepath    : Path to directory containing media files
    --outpath   : Path to output JSON file (default: media_durations.json)
    --verbose   : Print detailed processing information for each file

Output JSON Format:
{
    "file_path": {
        "duration": seconds,
        "size": bytes
    },
    ...
}

Dependencies:
    moviepy>=1.0.0 - For media file duration extraction
    tqdm>=4.0.0    - For progress bars (optional)

Example:
    python FileSizeTreeChecker.py ~/Videos --outpath video_stats.json --verbose
"""
# /// script
# requires-python = ">=3.8"
# dependencies = [
#     "moviepy>=1.0.0",
#     "tqdm>=4.0.0",
# ]
# ///

from pprint import pprint
import json
import random
from pathlib import Path
from typing import List
import argparse
try:
    from tqdm import tqdm
    has_tqdm = True
except ImportError:
    has_tqdm = False

MEDIA_EXTENSIONS = {'.mp3', '.mp4', '.avi', '.mkv', '.mov', '.wav', '.flac'}

def get_duration(file_path: Path, base_path: Path, verbose: bool = False) -> int:
    """Get duration of a media file in seconds.
    
    Args:
        file_path: Path to media file
        base_path: Base path for relative path calculation
        verbose: Print detailed processing information
    """
    # Using moviepy to get duration
    import warnings
    from moviepy.video.io.VideoFileClip import VideoFileClip
    try:
        # Suppress warnings unless verbose mode
        if not verbose:
            warnings.filterwarnings("ignore", category=UserWarning)
        with VideoFileClip(str(file_path)) as clip:
            val = int(clip.duration)
            if verbose:
                filename = str(file_path.relative_to(base_path))
                print(f"{filename:<50}: {val:>6}s")
            return val
    except Exception as e:
        if verbose:
            filename = str(file_path.relative_to(base_path))
            print(f"E: {filename:<50}: {e}")
        return 0


def main() -> None:
    """Main function to calculate total duration of media files."""
    parser = argparse.ArgumentParser(description='Calculate total duration of media files')
    parser.add_argument('filepath', type=str, help='Path to directory containing media files')
    parser.add_argument('--outpath', type=str, default="media_durations.json",
                       help='Path to output JSON file (default: media_durations.json)')
    parser.add_argument('--verbose', action='store_true',
                       help='Print detailed processing information')
    args = parser.parse_args()

    filepath = args.filepath
    outpath = args.outpath
    verbose = args.verbose
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
    
    if has_tqdm:
        file_iter = tqdm(media_files, desc="Processing files")
    else:
        file_iter = media_files
        print(f"Processing {len(media_files)} files...")
    
    for i, file in enumerate(file_iter):
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
            progress_msg = f"Current: {current_duration//3600}h {(current_duration%3600)//60}m | " \
                         f"Estimated total: {estimated_total//3600:.0f}h {(estimated_total%3600)//60:.0f}m"
            
            if i % 10 == 0:  # Print progress every 10 files
                if has_tqdm:
                    tqdm.write(progress_msg)
                else:
                    print(f"[{i+1}/{len(media_files)}] {progress_msg}")
    
    print(f"\nTotal duration: {current_duration//3600}h {(current_duration%3600)//60}m")
    
    # Write results to JSON file
    with open(outpath, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"Results saved to {outpath}")

if __name__ == '__main__':
    main()
