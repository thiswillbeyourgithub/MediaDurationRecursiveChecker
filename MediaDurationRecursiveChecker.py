#!/usr/bin/env python3
"""MediaDurationRecursiveChecker - Media Duration and Size Calculator

Repository: https://github.com/thiswillbeyourgithub/MediaDurationRecursiveChecker
Author: thiswillbeyourgithub
License: GPLv3

This application calculates the total duration and size of media files in a directory tree.
It's particularly useful for estimating total duration of video/audio collections.

Key Features:
- Supports common media formats: .mp3, .mp4, .avi, .mkv, .mov, .wav, .flac, .mxf, .raw
  (case-insensitive matching, e.g., .MP3 and .mp3 are both supported)
- Recursively scans directories
- Excludes hidden files (those starting with '.')
- Provides:
  - Total number of media files
  - Total size in GB
  - Total duration of all files
  - Real-time duration estimation
  - Verbose output with individual file durations
  - Results optionally saved to JSON file

Requirements:
- Python 3.8+
- moviepy (for media duration extraction)
- pymediainfo (fallback for problematic files)
- pyperclip (for clipboard integration)

Usage:
1. Launch the application
2. Select a folder containing media files
3. Choose options (verbose mode, JSON output)
4. Click "Start Processing"
5. View progress in the output window
6. Results will be displayed and optionally saved to JSON

The application handles large collections efficiently by:
- Processing files in random order for better time estimates
- Providing real-time progress updates
- Using threading to maintain responsive UI
- Gracefully handling problematic files

JSON Output Format:
{
    "path/to/file1.mp4": {
        "duration": 3600,  // in seconds
        "size": 1048576    // in bytes
    },
    ...
}

Note: Some media files may not report accurate durations due to encoding issues.
The application will skip these files and continue processing others.

For more information, see the README at:
https://github.com/thiswillbeyourgithub/MediaDurationRecursiveChecker
"""
# /// script
# requires-python = ">=3.8"
# dependencies = [
#     "numpy>=1.25.0",
#     "moviepy>=1.0.0",
#     "pyperclip>=1.9.0",
#     "pymediainfo>=6.0.0",
# ]
# ///

__version__ = "2.5.0"

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pyperclip
from pprint import pprint
import json
import random
from pathlib import Path
from typing import List, Optional, Union, Dict
import threading
import os
import warnings
import hashlib
import platform
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from moviepy.video.io.VideoFileClip import VideoFileClip
from loguru import logger

try:
    from pymediainfo import MediaInfo

    PYMEDIAINFO_AVAILABLE = True
except ImportError:
    PYMEDIAINFO_AVAILABLE = False

try:
    from moviepy.config import FFMPEG_BINARY
    import subprocess

    # Test if ffprobe is available by checking if we can construct the path
    FFMPEG_BINARY_PATH = FFMPEG_BINARY.replace("ffmpeg", "ffprobe")
    FFMPEG_BINARY_AVAILABLE = True
except (ImportError, AttributeError):
    FFMPEG_BINARY_AVAILABLE = False
    FFMPEG_BINARY_PATH = None


# Configure loguru to save logs to logs.txt next to the script
script_dir = Path(__file__).parent
log_file = script_dir / "logs.txt"
logger.add(log_file, rotation="10 MB", retention="10 files", level="INFO")


def calculate_file_hash(file_path: Path, chunk_size: int = 8192) -> str:
    """Calculate SHA256 hash of a file.

    Args:
        file_path: Path to the file
        chunk_size: Size of chunks to read at a time for memory efficiency

    Returns:
        Hexadecimal string representation of the file's SHA256 hash
    """
    hash_sha256 = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(chunk_size), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    except Exception as e:
        raise Exception(f"Failed to calculate hash for {file_path}: {str(e)}")


def get_duration(
    file_path: Path, base_path: Path, verbose: bool = False
) -> Union[int, str]:
    """Get duration of a media file in seconds.

    Args:
        file_path: Path to media file
        base_path: Base path for relative path calculation
        verbose: Print detailed processing information
    Returns:
        Duration in seconds, or error message if failed to parse
    """
    filename = str(file_path.relative_to(base_path))

    # Determine total number of methods available
    method_count = 1  # moviepy is always available
    if PYMEDIAINFO_AVAILABLE:
        method_count += 1
    if FFMPEG_BINARY_AVAILABLE:
        method_count += 1
    total_methods = method_count

    if verbose:
        logger.info(f"Processing {filename} - trying {total_methods} methods...")

    # Store errors from each method for final error message
    pymediainfo_error = None
    moviepy_error = None
    ffprobe_error = None

    # Method 1/3: Try pymediainfo first if available
    if PYMEDIAINFO_AVAILABLE:
        try:
            if verbose:
                logger.info(
                    f"  Method 1/{total_methods} for {filename}: pymediainfo..."
                )

            media_info = MediaInfo.parse(str(file_path))
            # Look for duration in video or audio tracks
            duration_ms = None
            for track in media_info.tracks:
                if track.track_type in ["Video", "Audio"] and track.duration:
                    duration_ms = track.duration
                    break

            if duration_ms:
                val = int(duration_ms / 1000)  # Convert milliseconds to seconds
                if verbose:
                    logger.info(
                        f"  ✓ Method 1/{total_methods} SUCCESS for {filename}: {val}s (pymediainfo)"
                    )
                else:
                    logger.info(f"{filename:<50}: {val:>6}s (pymediainfo)")
                return val
            else:
                raise Exception("No duration information found in media tracks")

        except Exception as e:
            pymediainfo_error = e
            if verbose:
                logger.info(
                    f"  ✗ Method 1/{total_methods} FAILED for {filename}: {str(e)}"
                )

    # Method 2/3 (or 1/2 if pymediainfo unavailable): Try moviepy
    try:
        method_num = 2 if PYMEDIAINFO_AVAILABLE else 1
        if verbose:
            logger.info(
                f"  Method {method_num}/{total_methods} for {filename}: moviepy..."
            )
        # Suppress warnings unless verbose mode
        if not verbose:
            warnings.filterwarnings("ignore", category=UserWarning)
        with VideoFileClip(str(file_path)) as clip:
            val = int(clip.duration)
            if verbose:
                logger.info(
                    f"  ✓ Method {method_num}/{total_methods} SUCCESS for {filename}: {val}s (moviepy)"
                )
            else:
                logger.info(f"{filename:<50}: {val:>6}s (moviepy)")
            return val
    except Exception as e:
        moviepy_error = e
        method_num = 2 if PYMEDIAINFO_AVAILABLE else 1
        if verbose:
            logger.info(
                f"  ✗ Method {method_num}/{total_methods} FAILED for {filename}: {str(e)}"
            )

    # Method 3/3 (or 2/2 if pymediainfo unavailable): Try ffprobe directly
    if FFMPEG_BINARY_AVAILABLE:
        try:
            method_num = total_methods  # This will be the last method
            if verbose:
                logger.info(
                    f"  Method {method_num}/{total_methods} for {filename}: ffprobe..."
                )

            # Use ffprobe to get duration directly
            cmd = [
                FFMPEG_BINARY_PATH,
                "-v",
                "quiet",
                "-print_format",
                "json",
                "-show_format",
                str(file_path),
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                import json as json_module

                probe_data = json_module.loads(result.stdout)
                if "format" in probe_data and "duration" in probe_data["format"]:
                    val = int(float(probe_data["format"]["duration"]))
                    if verbose:
                        logger.info(
                            f"  ✓ Method {method_num}/{total_methods} SUCCESS for {filename}: {val}s (ffprobe)"
                        )
                    else:
                        logger.info(f"{filename:<50}: {val:>6}s (ffprobe)")
                    return val
                else:
                    raise Exception("Duration not found in ffprobe output")
            else:
                raise Exception(f"ffprobe failed with return code {result.returncode}")

        except Exception as e:
            ffprobe_error = e
            method_num = total_methods
            if verbose:
                logger.info(
                    f"  ✗ Method {method_num}/{total_methods} FAILED for {filename}: {str(e)}"
                )

    # All methods failed, construct comprehensive error message
    error_parts = []
    if PYMEDIAINFO_AVAILABLE and pymediainfo_error:
        error_parts.append(f"pymediainfo failed ({str(pymediainfo_error)})")
    if moviepy_error:
        error_parts.append(f"moviepy failed ({str(moviepy_error)})")
    if FFMPEG_BINARY_AVAILABLE and ffprobe_error:
        error_parts.append(f"ffprobe failed ({str(ffprobe_error)})")

    # Add unavailable method notices
    if not PYMEDIAINFO_AVAILABLE:
        error_parts.append("(pymediainfo not available)")
    if not FFMPEG_BINARY_AVAILABLE:
        error_parts.append("(ffprobe not available)")

    error_msg = f"Error processing {file_path.name}: {', '.join(error_parts)}"

    if verbose:
        logger.info(f"  ✗ ALL METHODS FAILED for {filename}")
        logger.info(f"E: {filename:<50}: {error_msg}")
    return error_msg


def process_single_file(
    file_path: Path,
    base_path: Path,
    verbose: bool,
    debug: bool,
    min_size_bytes: int = 0,
) -> dict:
    """Process a single media file to extract duration and hash.

    Args:
        file_path: Path to the media file
        base_path: Base path for relative path calculation
        verbose: Whether to print verbose output
        debug: Whether to enable debug mode
        min_size_bytes: Minimum file size in bytes to process (files smaller will be skipped)

    Returns:
        Dictionary containing file info: duration, size, hash, error status, skipped flag
    """
    try:
        file_size = file_path.stat().st_size

        # Check if file is too small to process
        if file_size < min_size_bytes:
            if verbose:
                relative_path = str(file_path.relative_to(base_path))
                logger.info(
                    f"SKIPPED (too small): {relative_path:<50}: {file_size} bytes"
                )

            return {
                "file_path": str(file_path),
                "relative_path": str(file_path.relative_to(base_path)),
                "duration": 0,
                "size": file_size,
                "hash": None,
                "error": None,
                "skipped": True,
                "skip_reason": "File too small",
            }

        # Calculate file hash for duplicate detection
        try:
            file_hash = calculate_file_hash(file_path)
        except Exception as e:
            if verbose:
                error_msg = f"Failed to calculate hash for {file_path.name}: {str(e)}"
                logger.info(error_msg)
            file_hash = None

        # Get duration
        duration = get_duration(file_path, base_path, verbose)

        # Check if duration extraction failed
        duration_error = None
        if isinstance(duration, str):  # Error message
            duration_error = duration
            duration = 0

        # Debug mode: check for zero duration on large files
        if debug and duration == 0 and file_size > min_size_bytes:
            debug_msg = f"DEBUG: Zero duration detected for large file: {file_path.relative_to(base_path)} ({file_size / (1024*1024):.1f} MB)"
            logger.info(debug_msg)
            breakpoint()

        return {
            "file_path": str(file_path),
            "relative_path": str(file_path.relative_to(base_path)),
            "duration": duration,
            "size": file_size,
            "hash": file_hash,
            "error": duration_error,
            "skipped": False,
        }

    except Exception as e:
        return {
            "file_path": str(file_path),
            "relative_path": str(file_path.relative_to(base_path)),
            "duration": 0,
            "size": 0,
            "hash": None,
            "error": f"Failed to process file: {str(e)}",
            "skipped": False,
        }


class FileSizeTreeChecker:
    def __init__(self, root):
        self.root = root
        self.root.title("MediaDurationRecursiveChecker")
        self.root.geometry("625x500")
        self.root.minsize(
            400, 450
        )  # Set minimum window size to ensure progress area is visible

        # Try to load last used path
        last_path = self._load_last_path()
        self.folder_path = tk.StringVar(value=last_path if last_path else "")

        # Set initial window position based on last path
        if last_path:
            self.root.geometry("625x375+100+100")  # Default position
        else:
            # Center window if no last path
            self.root.geometry("625x375")
            self.root.eval("tk::PlaceWindow . center")

        # Main container using grid
        self.main_container = ttk.Frame(root)
        self.main_container.pack(fill="both", expand=True, padx=5, pady=5)

        # Documentation section
        self.doc_frame = ttk.Frame(self.main_container)
        self.doc_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=2)

        # Clickable label to show/hide docs
        self.doc_label = ttk.Label(
            self.doc_frame,
            text="▲ Documentation (click to expand)",
            cursor="hand2",
            foreground="blue",
        )
        self.doc_label.pack(fill="x")
        self.doc_label.bind("<Button-1>", self.toggle_documentation)

        # Text widget for documentation
        self.doc_text = tk.Text(
            self.doc_frame,
            height=5,  # Reduced initial height
            wrap="word",
            state="disabled",
            padx=5,
            pady=5,
        )

        # Insert the docstring
        self.doc_text.config(state="normal")
        self.doc_text.insert("1.0", __doc__)
        self.doc_text.config(state="disabled")

        # Start with documentation hidden
        self.docs_visible = False

        # Folder selection
        self.folder_frame = ttk.LabelFrame(self.main_container, text="Select Folder")
        self.folder_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=2)

        # Set default path if last_path exists
        if last_path:
            self.folder_path.set(last_path)

        self.folder_entry = ttk.Entry(self.folder_frame, textvariable=self.folder_path)
        self.folder_entry.pack(side="left", fill="x", expand=True, padx=5, pady=5)
        # Add clipboard and select-all shortcuts
        self.folder_entry.bind(
            "<Control-a>", lambda e: self.folder_entry.selection_range(0, "end")
        )
        self.folder_entry.bind(
            "<Command-a>", lambda e: self.folder_entry.selection_range(0, "end")
        )
        self.folder_entry.bind(
            "<Control-c>", lambda e: pyperclip.copy(self.folder_entry.get())
        )
        self.folder_entry.bind(
            "<Command-c>", lambda e: pyperclip.copy(self.folder_entry.get())
        )
        self.folder_entry.bind(
            "<Control-v>", lambda e: self.folder_entry.insert(0, pyperclip.paste())
        )
        self.folder_entry.bind(
            "<Command-v>", lambda e: self.folder_entry.insert(0, pyperclip.paste())
        )

        self.browse_button = ttk.Button(
            self.folder_frame, text="Browse", command=self.select_folder
        )
        self.browse_button.pack(side="right", padx=5, pady=5)

        # Extensions
        self.extensions_frame = ttk.LabelFrame(
            self.main_container, text="Media Extensions"
        )
        self.extensions_frame.grid(row=2, column=0, sticky="ew", padx=5, pady=2)

        self.extensions_var = tk.StringVar(value="mp3,mp4,avi,mkv,mov,wav,flac,mxf,raw")
        self.extensions_entry = ttk.Entry(
            self.extensions_frame, textvariable=self.extensions_var
        )
        self.extensions_entry.pack(fill="x", expand=True, padx=5, pady=5)

        # Backend Status
        self.backend_frame = ttk.LabelFrame(self.main_container, text="Backend Status")
        self.backend_frame.grid(row=3, column=0, sticky="ew", padx=5, pady=2)

        # Create backend status display
        self.backend_status_frame = ttk.Frame(self.backend_frame)
        self.backend_status_frame.pack(fill="x", padx=5, pady=5)

        # PyMediaInfo status
        pymediainfo_status = "✓ Available" if PYMEDIAINFO_AVAILABLE else "✗ Not Available"
        pymediainfo_color = "green" if PYMEDIAINFO_AVAILABLE else "red"
        self.pymediainfo_label = ttk.Label(
            self.backend_status_frame, 
            text=f"PyMediaInfo: {pymediainfo_status}",
            foreground=pymediainfo_color
        )
        self.pymediainfo_label.pack(anchor="w")

        # FFmpeg/ffprobe status  
        ffmpeg_status = "✓ Available" if FFMPEG_BINARY_AVAILABLE else "✗ Not Available"
        ffmpeg_color = "green" if FFMPEG_BINARY_AVAILABLE else "red"
        self.ffmpeg_label = ttk.Label(
            self.backend_status_frame,
            text=f"FFprobe: {ffmpeg_status}",
            foreground=ffmpeg_color
        )
        self.ffmpeg_label.pack(anchor="w")

        # MoviePy is always available (it's a required dependency)
        self.moviepy_label = ttk.Label(
            self.backend_status_frame,
            text="MoviePy: ✓ Available",
            foreground="green"
        )
        self.moviepy_label.pack(anchor="w")

        # Add explanation
        backend_info = "Multiple backends provide redundancy - if one fails, others will be tried automatically."
        self.backend_info_label = ttk.Label(
            self.backend_status_frame,
            text=backend_info,
            font=("Helvetica", 8),
            foreground="gray"
        )
        self.backend_info_label.pack(anchor="w", pady=(5, 0))

        # Options
        self.options_frame = ttk.LabelFrame(self.main_container, text="Options")
        self.options_frame.grid(row=4, column=0, sticky="ew", padx=5, pady=2)

        # Output path
        self.output_frame = ttk.Frame(self.options_frame)
        self.output_frame.pack(fill="x", padx=5, pady=2)

        self.save_json = tk.BooleanVar(value=False)
        self.json_check = ttk.Checkbutton(
            self.output_frame,
            text="Save results to JSON",
            variable=self.save_json,
            command=self.toggle_output_path,
        )
        self.json_check.pack(side="left", padx=(0, 5))

        self.output_path = tk.StringVar()
        self.output_entry = ttk.Entry(
            self.output_frame, textvariable=self.output_path, state="disabled"
        )
        self.output_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        # Add clipboard and select-all shortcuts
        self.output_entry.bind(
            "<Control-a>", lambda e: self.output_entry.selection_range(0, "end")
        )
        self.output_entry.bind(
            "<Command-a>", lambda e: self.output_entry.selection_range(0, "end")
        )
        self.output_entry.bind(
            "<Control-c>", lambda e: pyperclip.copy(self.output_entry.get())
        )
        self.output_entry.bind(
            "<Command-c>", lambda e: pyperclip.copy(self.output_entry.get())
        )
        self.output_entry.bind(
            "<Control-v>", lambda e: self.output_entry.insert(0, pyperclip.paste())
        )
        self.output_entry.bind(
            "<Command-v>", lambda e: self.output_entry.insert(0, pyperclip.paste())
        )

        self.output_browse_button = ttk.Button(
            self.output_frame,
            text="Browse",
            command=self.select_output_file,
            state="disabled",
        )
        self.output_browse_button.pack(side="right")

        self.verbose_mode = tk.BooleanVar(value=False)
        self.verbose_check = ttk.Checkbutton(
            self.options_frame, text="Verbose output", variable=self.verbose_mode
        )
        self.verbose_check.pack(anchor="w", padx=5, pady=2)

        self.debug_mode = tk.BooleanVar(value=False)
        self.debug_check = ttk.Checkbutton(
            self.options_frame,
            text="Debug mode (breakpoint on 0 duration for large files)",
            variable=self.debug_mode,
        )
        self.debug_check.pack(anchor="w", padx=5, pady=2)

        self.stop_on_error = tk.BooleanVar(value=False)
        self.stop_on_error_check = ttk.Checkbutton(
            self.options_frame,
            text="Stop processing on first file error",
            variable=self.stop_on_error,
        )
        self.stop_on_error_check.pack(anchor="w", padx=5, pady=2)

        # Thread count option
        self.thread_frame = ttk.Frame(self.options_frame)
        self.thread_frame.pack(fill="x", padx=5, pady=2)

        ttk.Label(self.thread_frame, text="Number of processing threads:").pack(
            side="left"
        )

        self.thread_count = tk.IntVar(value=4)
        self.thread_spinbox = ttk.Spinbox(
            self.thread_frame, from_=1, to=16, width=5, textvariable=self.thread_count
        )
        self.thread_spinbox.pack(side="left", padx=(5, 0))

        # Minimum file size option
        self.min_size_frame = ttk.Frame(self.options_frame)
        self.min_size_frame.pack(fill="x", padx=5, pady=2)

        ttk.Label(self.min_size_frame, text="Minimum file size (KB):").pack(side="left")

        self.min_file_size_kb = tk.IntVar(value=100)  # Default 100KB minimum
        self.min_size_spinbox = ttk.Spinbox(
            self.min_size_frame,
            from_=0,
            to=10000,
            width=8,
            textvariable=self.min_file_size_kb,
        )
        self.min_size_spinbox.pack(side="left", padx=(5, 0))

        ttk.Label(
            self.min_size_frame, text="(files smaller than this will be skipped)"
        ).pack(side="left", padx=(5, 0))

        # Progress
        self.progress_frame = ttk.LabelFrame(self.main_container, text="Progress")
        self.progress_frame.grid(row=5, column=0, sticky="nsew", padx=5, pady=2)

        # Add scrollbar to progress text with minimum height enforcement
        self.progress_text = tk.Text(self.progress_frame, height=8, state="disabled")
        # Ensure minimum height is maintained when resizing
        self.progress_text.config(height=8)  # This enforces minimum visible lines
        scrollbar = ttk.Scrollbar(self.progress_frame, command=self.progress_text.yview)
        self.progress_text.configure(yscrollcommand=scrollbar.set)

        # Grid layout for progress area
        self.progress_text.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        # Configure grid weights for progress frame with minimum size
        self.progress_frame.grid_rowconfigure(
            0, weight=1, minsize=120
        )  # Minimum 120px height for progress area
        self.progress_frame.grid_columnconfigure(0, weight=1)

        # Configure grid weights for main container
        self.main_container.grid_rowconfigure(
            5, weight=1
        )  # Progress area gets extra space
        self.main_container.grid_columnconfigure(0, weight=1)

        # Make text widget expand to fill space
        self.progress_text.config(wrap="none")

        # Control buttons
        self.button_frame = ttk.Frame(self.main_container)
        self.button_frame.grid(row=6, column=0, sticky="ew", padx=5, pady=5)

        # Use custom styling only on non-macOS platforms to avoid visibility issues
        button_style = None if platform.system() == "Darwin" else "Accent.TButton"
        self.start_button = ttk.Button(
            self.button_frame,
            text="Start Processing",
            command=self.start_processing,
            style=button_style,
        )
        self.start_button.pack(side="left", expand=True, fill="x")

        self.cancel_button = ttk.Button(
            self.button_frame,
            text="Cancel",
            command=self.cancel_processing,
            state="disabled",
        )
        self.cancel_button.pack(side="right", expand=True, fill="x")

        # Thread control
        self.processing_thread = None
        self.cancel_requested = False
        self.executor = None

        # Message queue for progress updates
        self.message_queue = []
        self.update_timer = None

        # Configure styles (only on non-macOS platforms to avoid visibility issues)
        if platform.system() != "Darwin":
            style = ttk.Style()
            style.configure(
                "Accent.TButton",
                font=("Helvetica", 12, "bold"),
                padding=10,
                foreground="white",
                background="#800080",
            )
            style.map(
                "Accent.TButton",
                background=[("active", "#800080"), ("!active", "#800080")],
            )

        # Add GitHub link
        self.footer_frame = ttk.Frame(self.main_container)
        self.footer_frame.grid(row=7, column=0, sticky="ew", padx=5, pady=2)

        self.github_link = ttk.Label(
            self.footer_frame,
            text="View source code, documentation, or request features on GitHub",
            foreground="blue",
            cursor="hand2",
            font=("Helvetica", 9),
        )
        self.github_link.pack(side="right")
        self.github_link.bind("<Button-1>", lambda e: self.open_github())

    def _get_last_path_file(self) -> Path:
        """Get the path to the last path file in system temp directory."""
        import tempfile

        temp_dir = Path(tempfile.gettempdir())
        return temp_dir / "MediaDurationRecursiveChecker_latest_path.txt"

    def _is_valid_path(self, path: str) -> bool:
        """Check if a path is valid and accessible."""
        try:
            return os.path.exists(path) and os.path.isdir(path)
        except Exception:
            return False

    def _save_last_path(self, path: str) -> None:
        """Save the last selected path to a temporary file only if valid."""
        try:
            if self._is_valid_path(path):
                last_path_file = self._get_last_path_file()
                with open(last_path_file, "w") as f:
                    f.write(path)
        except Exception:
            pass  # Silently ignore any errors

    def get_media_extensions(self):
        """Get media extensions from input field as a set."""
        extensions = self.extensions_var.get().strip()
        if not extensions:
            return set()  # Empty set if no extensions provided
        return set([ext.lower() for ext in extensions.split(",")])

    def _load_last_path(self) -> Optional[str]:
        """Load the last selected path from temporary file if it exists and is valid."""
        try:
            last_path_file = self._get_last_path_file()
            if last_path_file.exists():
                with open(last_path_file, "r") as f:
                    path = f.read().strip()
                    if path and self._is_valid_path(path):
                        return path
                    # Clean up invalid path file
                    os.remove(last_path_file)
        except Exception:
            pass  # Silently ignore any errors
        return None

    def select_folder(self):
        initialdir = self.folder_path.get() if self.folder_path.get() else None
        folder = filedialog.askdirectory(initialdir=initialdir)
        if folder:
            if self._is_valid_path(folder):
                self.folder_path.set(folder)
                self._save_last_path(folder)
                # Set default output path
                self.output_path.set(str(Path(folder) / "media_durations.json"))
            else:
                messagebox.showerror(
                    "Invalid Path",
                    f"The selected path is not accessible:\n{folder}\n\n"
                    "Please select a valid directory.",
                )

    def select_output_file(self):
        output_file = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
            initialfile="media_durations.json",
        )
        if output_file:
            self.output_path.set(output_file)

    def toggle_output_path(self):
        if self.save_json.get():
            self.output_entry.config(state="normal")
            self.output_browse_button.config(state="normal")
        else:
            self.output_entry.config(state="disabled")
            self.output_browse_button.config(state="disabled")

    def queue_message(self, message):
        """Add message to queue and schedule update"""
        self.message_queue.append(message)
        if not self.update_timer:
            self.update_timer = self.root.after(100, self.process_message_queue)

    def process_message_queue(self):
        """Process all queued messages at once"""
        if self.message_queue:
            self.progress_text.config(state="normal")
            # Join all messages with newlines
            text = "\n".join(self.message_queue) + "\n"
            self.progress_text.insert("end", text)
            self.progress_text.see("end")
            self.progress_text.config(state="disabled")
            self.message_queue.clear()
        self.update_timer = None

    def log_message(self, message):
        """Immediate logging for important messages"""
        self.progress_text.config(state="normal")
        self.progress_text.insert("end", message + "\n")
        self.progress_text.see("end")
        self.progress_text.config(state="disabled")

    def start_processing(self):
        folder = self.folder_path.get()
        if not folder:
            messagebox.showerror("Error", "Please select a folder first")
            return

        # Check if path exists
        if not os.path.exists(folder):
            messagebox.showerror(
                "Error",
                f"The selected path does not exist:\n{folder}\n\n"
                "Please check the path and try again.",
            )
            return

        # Check if it's actually a directory
        if not os.path.isdir(folder):
            messagebox.showerror(
                "Error",
                f"The selected path is not a directory:\n{folder}\n\n"
                "Please select a valid directory.",
            )
            return

        # Reset cancel flag
        self.cancel_requested = False

        # Disable UI during processing
        self.browse_button.config(state="disabled")
        self.start_button.config(state="disabled")
        self.cancel_button.config(state="normal")

        # Run processing in separate thread
        self.processing_thread = threading.Thread(
            target=self.process_folder, args=(folder,), daemon=True
        )
        self.processing_thread.start()

    def process_folder(self, folder):
        try:
            path = Path(folder)
            results = {}
            failed_files = []  # Track failed files
            file_hashes = {}  # Track files by hash for duplicate detection
            duplicate_groups = []  # List of lists of duplicate files

            # Get all media files (case-insensitive extension matching)
            # f.suffix.lower() ensures .MP4, .mp4, .Mp4 all match "mp4" in extensions
            media_files = [
                f
                for f in path.rglob("*")
                if f.suffix.lower().lstrip(".") in self.get_media_extensions()
                and not f.name.startswith(".")
            ]

            random.shuffle(media_files)

            # Calculate total size
            total_size = sum(f.stat().st_size for f in media_files)
            total_size_gb = total_size / (1024**3)

            self.log_message(
                f"Found {len(media_files)} media files ({total_size_gb:.2f} GB)"
            )

            # Get processing parameters
            num_threads = self.thread_count.get()
            verbose = self.verbose_mode.get()
            debug = self.debug_mode.get()
            stop_on_error = self.stop_on_error.get()
            min_size_bytes = self.min_file_size_kb.get() * 1024  # Convert KB to bytes

            self.log_message(f"Starting processing with {num_threads} threads...")
            self.log_message(f"Minimum file size: {self.min_file_size_kb.get()} KB")

            # Initialize processing variables
            current_duration = 0
            processed_size = 0
            estimated_total = 0
            failed_size = 0
            completed_files = 0
            skipped_files = 0
            start_time = time.time()

            # Use different processing paths depending on thread count to avoid threading overhead when not needed
            if num_threads == 1:
                # Single-threaded processing - avoid threading infrastructure entirely
                self.log_message(
                    "Using single-threaded processing (no threading overhead)"
                )

                for file in media_files:
                    if self.cancel_requested:
                        self.log_message("\nProcessing cancelled by user")
                        break

                    try:
                        file_result = process_single_file(
                            file, path, verbose, debug, min_size_bytes
                        )
                        completed_files += 1

                        # Extract results
                        duration = file_result["duration"]
                        file_size = file_result["size"]
                        file_hash = file_result["hash"]
                        error = file_result["error"]
                        skipped = file_result.get("skipped", False)

                        # Handle skipped files
                        if skipped:
                            skipped_files += 1
                            # Don't include skipped files in main processing stats
                            continue

                        current_duration += duration
                        processed_size += file_size

                        # Handle errors
                        if error:
                            failed_files.append(file_result["relative_path"])
                            failed_size += file_size
                            if verbose:
                                self.queue_message(error)

                            # Stop processing if stop_on_error is enabled
                            if stop_on_error:
                                self.log_message(
                                    f"\nStopping processing due to error in file: {file_result['relative_path']}"
                                )
                                self.log_message(f"Error: {error}")
                                break

                        # Track duplicates by hash
                        if file_hash:
                            if file_hash in file_hashes:
                                file_hashes[file_hash].append(
                                    file_result["relative_path"]
                                )
                            else:
                                file_hashes[file_hash] = [file_result["relative_path"]]

                        # Store results
                        results[file_result["file_path"]] = {
                            "duration": duration,
                            "size": file_size,
                            "hash": file_hash,
                        }

                        # Calculate progress and estimated total
                        if processed_size > 0:
                            estimated_total = (
                                total_size / processed_size
                            ) * current_duration
                            percent_done = completed_files / len(media_files) * 100
                            progress_msg = (
                                f"[{completed_files}/{len(media_files)} ({percent_done:.1f}%)] "
                                f"Sum of durations so far: {current_duration//3600}h {(current_duration%3600)//60}m | "
                                f"Estimated total for all files: {estimated_total//3600:.0f}h {(estimated_total%3600)//60:.0f}m"
                            )
                            if skipped_files > 0:
                                progress_msg += f" | Skipped: {skipped_files}"

                            if (
                                completed_files % 10 == 0
                            ):  # Update progress every 10 files
                                self.queue_message(progress_msg)

                    except Exception as e:
                        self.queue_message(f"Error processing file: {str(e)}")

            else:
                # Multi-threaded processing using ThreadPoolExecutor
                self.log_message(
                    f"Using multi-threaded processing with {num_threads} threads"
                )

                with ThreadPoolExecutor(max_workers=num_threads) as executor:
                    self.executor = executor  # Store reference for cancellation

                    # Submit all files for processing
                    future_to_file = {
                        executor.submit(
                            process_single_file,
                            file,
                            path,
                            verbose,
                            debug,
                            min_size_bytes,
                        ): file
                        for file in media_files
                    }

                    # Process results as they complete
                    for future in as_completed(future_to_file):
                        if self.cancel_requested:
                            self.log_message("\nProcessing cancelled by user")
                            # Cancel all pending futures
                            for f in future_to_file:
                                f.cancel()
                            # Shutdown executor with cancellation (Python 3.9+) or fallback
                            try:
                                executor.shutdown(wait=False, cancel_futures=True)
                            except TypeError:
                                # Python < 3.9 fallback
                                executor.shutdown(wait=False)
                            break

                        try:
                            file_result = future.result()
                            completed_files += 1

                            # Extract results
                            duration = file_result["duration"]
                            file_size = file_result["size"]
                            file_hash = file_result["hash"]
                            error = file_result["error"]
                            skipped = file_result.get("skipped", False)

                            # Handle skipped files
                            if skipped:
                                skipped_files += 1
                                # Don't include skipped files in main processing stats
                                continue

                            current_duration += duration
                            processed_size += file_size

                            # Handle errors
                            if error:
                                failed_files.append(file_result["relative_path"])
                                failed_size += file_size
                                if verbose:
                                    self.queue_message(error)

                                # Stop processing if stop_on_error is enabled
                                if stop_on_error:
                                    self.log_message(
                                        f"\nStopping processing due to error in file: {file_result['relative_path']}"
                                    )
                                    self.log_message(f"Error: {error}")
                                    # Cancel all pending futures
                                    for f in future_to_file:
                                        f.cancel()
                                    # Shutdown executor with cancellation (Python 3.9+) or fallback
                                    try:
                                        executor.shutdown(
                                            wait=False, cancel_futures=True
                                        )
                                    except TypeError:
                                        # Python < 3.9 fallback
                                        executor.shutdown(wait=False)
                                    break

                            # Track duplicates by hash
                            if file_hash:
                                if file_hash in file_hashes:
                                    file_hashes[file_hash].append(
                                        file_result["relative_path"]
                                    )
                                else:
                                    file_hashes[file_hash] = [
                                        file_result["relative_path"]
                                    ]

                            # Store results
                            results[file_result["file_path"]] = {
                                "duration": duration,
                                "size": file_size,
                                "hash": file_hash,
                            }

                            # Calculate progress and estimated total
                            if processed_size > 0:
                                estimated_total = (
                                    total_size / processed_size
                                ) * current_duration
                                percent_done = completed_files / len(media_files) * 100
                                progress_msg = (
                                    f"[{completed_files}/{len(media_files)} ({percent_done:.1f}%)] "
                                    f"Sum of durations so far: {current_duration//3600}h {(current_duration%3600)//60}m | "
                                    f"Estimated total for all files: {estimated_total//3600:.0f}h {(estimated_total%3600)//60:.0f}m"
                                )
                                if skipped_files > 0:
                                    progress_msg += f" | Skipped: {skipped_files}"

                                if (
                                    completed_files % 10 == 0
                                ):  # Update progress every 10 files
                                    self.queue_message(progress_msg)

                        except Exception as e:
                            self.queue_message(f"Error processing file: {str(e)}")

                    self.executor = None  # Clear reference

            # Calculate processing time
            processing_time = time.time() - start_time

            # Identify duplicate groups (groups with more than one file)
            duplicate_groups = [
                files for files in file_hashes.values() if len(files) > 1
            ]
            total_duplicates = sum(
                len(group) - 1 for group in duplicate_groups
            )  # Don't count the original

            if not self.cancel_requested:
                self.log_message(
                    f"\nProcessing completed in {processing_time:.2f} seconds using {num_threads} threads"
                )
                self.log_message(
                    f"Total duration: {current_duration//3600}h {(current_duration%3600)//60}m"
                )
                if skipped_files > 0:
                    self.log_message(
                        f"Skipped {skipped_files} files (smaller than {self.min_file_size_kb.get()} KB)"
                    )
            else:
                self.log_message(
                    f"Duration of all files seen so far: {current_duration//3600}h {(current_duration%3600)//60}m"
                )
                if estimated_total > 0:
                    self.log_message(
                        f"Estimated duration for all the files (seen and unseen): {estimated_total//3600:.0f}h {(estimated_total%3600)//60:.0f}m"
                    )
                if skipped_files > 0:
                    self.log_message(
                        f"Skipped {skipped_files} files so far (smaller than {self.min_file_size_kb.get()} KB)"
                    )

            # Report duplicate files
            if duplicate_groups:
                self.log_message(
                    f"\nFound {len(duplicate_groups)} groups of duplicate files ({total_duplicates} duplicate files total):"
                )
                if self.verbose_mode.get():
                    for i, group in enumerate(duplicate_groups, 1):
                        self.log_message(f"  Group {i}: {len(group)} identical files")
                        for file_path in group:
                            self.log_message(f"    - {file_path}")
                else:
                    self.log_message(
                        "  (Enable verbose mode to see detailed duplicate file listing)"
                    )
            else:
                self.log_message("\nNo duplicate files found")

            # Add extra information if there were failed files
            if failed_files:
                self.log_message(f"\nFailed to parse {len(failed_files)} files:")
                for failed_file in failed_files:
                    self.log_message(f" - {failed_file}")

                # Calculate extrapolated duration if we have failed files
                if processed_size > 0 and processed_size < total_size:
                    extrapolated_duration = (
                        total_size / processed_size
                    ) * current_duration
                    self.log_message(
                        f"\nExtrapolated total duration (including failed files): {extrapolated_duration//3600:.0f}h {(extrapolated_duration%3600)//60:.0f}m"
                    )

            # Write results to JSON file if enabled
            if self.save_json.get():
                outpath = Path(self.output_path.get())

                # Prepare comprehensive output data
                output_data = {
                    "summary": {
                        "total_files": len(media_files),
                        "processed_files": len(media_files) - skipped_files,
                        "skipped_files": skipped_files,
                        "min_file_size_kb": self.min_file_size_kb.get(),
                        "total_size_gb": total_size_gb,
                        "total_duration_seconds": current_duration,
                        "total_duration_readable": f"{current_duration//3600}h {(current_duration%3600)//60}m",
                        "failed_files_count": len(failed_files),
                        "duplicate_groups_count": len(duplicate_groups),
                        "total_duplicate_files": total_duplicates,
                    },
                    "files": results,
                }

                # Add duplicate groups if any exist
                if duplicate_groups:
                    output_data["duplicate_groups"] = duplicate_groups

                # Add failed files list if any exist
                if failed_files:
                    output_data["failed_files"] = failed_files

                with open(outpath, "w", encoding="utf-8") as f:
                    json.dump(output_data, f, indent=2)
                self.log_message(f"Results saved to {outpath}")

            if self.cancel_requested:
                messagebox.showinfo(
                    "Processing Cancelled",
                    "Media duration calculation was cancelled by user.",
                )
            else:
                messagebox.showinfo(
                    "Processing Complete", "Media duration calculation finished!"
                )

        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {str(e)}")
        finally:
            # Re-enable UI
            self.browse_button.config(state="normal")
            self.start_button.config(state="normal")
            self.cancel_button.config(state="disabled")
            self.processing_thread = None

    def cancel_processing(self):
        """Cancel the current processing operation."""
        if self.processing_thread and self.processing_thread.is_alive():
            self.cancel_requested = True
            self.log_message("\nCancelling... Please wait for current files to finish.")
            self.cancel_button.config(state="disabled")

            # Also shutdown the executor if it exists
            if self.executor:
                try:
                    self.executor.shutdown(wait=False, cancel_futures=True)
                except TypeError:
                    # Python < 3.9 fallback
                    self.executor.shutdown(wait=False)

    def open_github(self):
        """Open the GitHub repository in the default web browser."""
        import webbrowser

        webbrowser.open(
            "https://github.com/thiswillbeyourgithub/MediaDurationRecursiveChecker"
        )

    def toggle_documentation(self, event=None):
        """Toggle visibility of documentation section."""
        if self.docs_visible:
            self.doc_text.pack_forget()
            self.doc_label.config(text="▲ Documentation (click to expand)")
            self.docs_visible = False
        else:
            self.doc_text.pack(fill="x", padx=5, pady=5)
            self.doc_label.config(text="▼ Documentation (click to collapse)")
            self.docs_visible = True


if __name__ == "__main__":
    try:
        root = tk.Tk()
        app = FileSizeTreeChecker(root)
        root.mainloop()
    except KeyboardInterrupt:
        logger.info("\nKeyboard interrupt received. Exiting gracefully...")
        try:
            if app.processing_thread and app.processing_thread.is_alive():
                app.cancel_processing()
                app.processing_thread.join(timeout=2)
        except Exception:
            pass
        root.destroy()
