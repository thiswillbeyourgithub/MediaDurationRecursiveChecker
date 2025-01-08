# MediaDurationRecursiveChecker

> Une version française de ce fichier README est disponible : [README_fr.md](README_fr.md)  
> A French version of this README is available: [README_fr.md](README_fr.md)

# MediaDurationRecursiveChecker

This Python script calculates the total duration of media files (video/audio) in a directory and estimates the total processing time. It was created to help estimate the total duration of daily/rush footage on a hard drive. The project was renamed from FileSizeTreeChecker to MediaDurationRecursiveChecker to better reflect its purpose.

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

- Python 3.6+ (only tested on 3.8 and 3.11)
- `moviepy` (for media duration extraction)
- `pyperclip` (to handle copying and pasting the path)

## Installation and Usage

You have three options to run MediaDurationRecursiveChecker:

### 1. Run from Source (GUI)
1. Install required Python packages:
```bash
# On macOS:
sudo python3 -m pip install moviepy pyperclip

# On other platforms:
pip install moviepy pyperclip
```
2. Ensure `ffmpeg` is installed on your system
3. Run the script:
```bash
python MediaDurationRecursiveChecker.py
```
4. Use the graphical interface to select folders and process files

### 2. Build Your Own Executable
If you prefer to build it yourself:
1. Install PyInstaller:
```bash
pip install pyinstaller
```
2. Build the executable:
```bash
pyinstaller --onefile --name MediaDurationRecursiveChecker MediaDurationRecursiveChecker.py --noconsole --hidden-import=imageio_ffmpeg
```
3. The executable will be in the `dist` directory

Note: This has been tested to work on macOS 11 when using the command:
```bash
sudo pyinstaller --onefile --windowed --name MediaDurationRecursiveChecker MediaDurationRecursiveChecker.py --clean
```

A pre-compiled .app for macOS is available in the 1.0.1 release.

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

- Files are processed in random order to provide better time estimates
- The script handles errors gracefully, skipping files it can't process
