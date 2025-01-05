# FileSizeTreeChecker

This Python script calculates the total duration of media files (video/audio) in a directory and estimates the total processing time. It was created to help estimate the total duration of daily/rush footage on a hard drive.

## Features

- Supports common media formats: `.mp3`, `.mp4`, `.avi`, `.mkv`, `.mov`, `.wav`, `.flac`
- Recursively scans directories
- Excludes hidden files (those starting with '.')
- Provides:
  - Total number of media files
  - Total size in GB
  - Total duration of all files (and estimation every 10 files)
  - Verbose output with individual file durations
  - Results optionally saved to JSON file

## Requirements

- Python 3.6+ (only tested on 3.11)
- `moviepy` (for media duration extraction)
- `pyclip` (to handle copying and pasting the path)

## Installation

Install required Python packages:
```bash
pip install moviepy
```

Ensure `ffmpeg` is installed on your system.

## Building with PyInstaller

To create a standalone executable on macOS:

```bash
pip install pyinstaller moviepy
pyinstaller --onefile --name FileSizeTreeChecker FileSizeTreeChecker.py --argv-emulation --optimize 2 --target-architecture x86_64 --clean --console --hidden-import=imageio_ffmpeg
```

This will create a single executable file in the `dist` directory.

## Usage

Basic usage:
```bash
python filesize_check.py /path/to/media/files
```

With custom output file:
```bash
python filesize_check.py /path/to/media/files --outpath custom_output.json
```

Verbose mode (shows individual file processing):
```bash
python filesize_check.py /path/to/media/files --verbose
```

All options:
```bash
python filesize_check.py --help
```

## Output Example

```
Found 1234 media files (456.78 GB)
Processing files: 100%|████████████████████| 1234/1234 [12:34<00:00,  1.23it/s]
Current: 12h 34m | Estimated total: 15h 30m

Total duration: 15h 30m
Results saved to media_durations.json
```

## JSON Output Format

The output JSON file contains:
```json
{
  "/path/to/file.mp4": {
    "duration": 3600,  // in seconds
    "size": 1048576   // in bytes
  },
  ...
}
```

## Notes

- The script uses `ffprobe` to get media durations
- Hidden files (starting with '.') are ignored
- Files are processed in random order to provide better time estimates
- The script handles errors gracefully, skipping files it can't process
