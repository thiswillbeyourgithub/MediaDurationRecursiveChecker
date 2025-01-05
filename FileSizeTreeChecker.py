#!/usr/bin/env python3
"""Media Duration Calculator GUI Application

Repository: https://github.com/thiswillbeyourgithub/FileSizeTreeChecker
Author: thiswillbeyourgithub
License: GPLv3

This application provides a graphical interface for calculating the total duration
of media files in a directory tree. It supports various media formats and provides
detailed progress reporting and results saving.

Features:
- Supports multiple media formats: MP3, MP4, AVI, MKV, MOV, WAV, FLAC
- Recursively scans directories for media files
- Calculates total duration in hours and minutes
- Estimates total processing time during calculation
- Provides verbose output mode for detailed processing information
- Saves results to JSON file with duration and size for each file
- Progress reporting with current and estimated total duration
- Threaded processing to keep UI responsive
- Cross-platform support (Windows, macOS, Linux)

Dependencies:
- moviepy: For media file duration extraction

Usage:
1. Launch the application
2. Select a folder containing media files
3. Choose options (verbose mode, JSON output)
4. Click "Start Processing"
5. View progress in the output window
6. Results will be displayed and optionally saved to JSON

The application handles large media collections efficiently by:
- Processing files in random order to prevent media type bias
- Providing real-time progress updates
- Using threading to maintain responsive UI
- Implementing error handling for problematic files

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
"""
# /// script
# requires-python = ">=3.8"
# dependencies = [
#     "numpy>=1.25.0",
#     "moviepy>=1.0.0",
#     "pyperclip>=1.9.0",
# ]
# ///

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pyperclip
from pprint import pprint
import json
import random
from pathlib import Path
from typing import List, Optional
import threading
import os
import warnings
from moviepy.video.io.VideoFileClip import VideoFileClip

MEDIA_EXTENSIONS = {'.mp3', '.mp4', '.avi', '.mkv', '.mov', '.wav', '.flac'}

def get_duration(file_path: Path, base_path: Path, verbose: bool = False) -> int:
    """Get duration of a media file in seconds.
    
    Args:
        file_path: Path to media file
        base_path: Base path for relative path calculation
        verbose: Print detailed processing information
    """
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


class FileSizeTreeChecker:
    def __init__(self, root):
        self.root = root
        self.root.title("Media Duration Calculator")
        self.root.geometry("500x400")
        self.root.minsize(400, 300)  # Set minimum window size
        
        # Try to load last used path
        last_path = self._load_last_path()
        self.folder_path = tk.StringVar(value=last_path if last_path else "")
        
        # Set initial window position based on last path
        if last_path:
            self.root.geometry("500x300+100+100")  # Default position
        else:
            # Center window if no last path
            self.root.geometry("500x300")
            self.root.eval('tk::PlaceWindow . center')
        
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
            foreground="blue"
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
            pady=5
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
        self.folder_entry.bind("<Control-a>", lambda e: self.folder_entry.selection_range(0, 'end'))
        self.folder_entry.bind("<Command-a>", lambda e: self.folder_entry.selection_range(0, 'end'))
        self.folder_entry.bind("<Control-c>", lambda e: pyperclip.copy(self.folder_entry.get()))
        self.folder_entry.bind("<Command-c>", lambda e: pyperclip.copy(self.folder_entry.get()))
        self.folder_entry.bind("<Control-v>", lambda e: self.folder_entry.insert(0, pyperclip.paste()))
        self.folder_entry.bind("<Command-v>", lambda e: self.folder_entry.insert(0, pyperclip.paste()))
        
        self.browse_button = ttk.Button(self.folder_frame, text="Browse", command=self.select_folder)
        self.browse_button.pack(side="right", padx=5, pady=5)
        
        # Options
        self.options_frame = ttk.LabelFrame(self.main_container, text="Options")
        self.options_frame.grid(row=2, column=0, sticky="ew", padx=5, pady=2)
        
        # Output path
        self.output_frame = ttk.Frame(self.options_frame)
        self.output_frame.pack(fill="x", padx=5, pady=2)
        
        self.save_json = tk.BooleanVar(value=False)
        self.json_check = ttk.Checkbutton(self.output_frame, text="Save results to JSON", 
                                        variable=self.save_json, command=self.toggle_output_path)
        self.json_check.pack(side="left", padx=(0,5))
        
        self.output_path = tk.StringVar()
        self.output_entry = ttk.Entry(self.output_frame, textvariable=self.output_path, state="disabled")
        self.output_entry.pack(side="left", fill="x", expand=True, padx=(0,5))
        # Add clipboard and select-all shortcuts
        self.output_entry.bind("<Control-a>", lambda e: self.output_entry.selection_range(0, 'end'))
        self.output_entry.bind("<Command-a>", lambda e: self.output_entry.selection_range(0, 'end'))
        self.output_entry.bind("<Control-c>", lambda e: pyperclip.copy(self.output_entry.get()))
        self.output_entry.bind("<Command-c>", lambda e: pyperclip.copy(self.output_entry.get()))
        self.output_entry.bind("<Control-v>", lambda e: self.output_entry.insert(0, pyperclip.paste()))
        self.output_entry.bind("<Command-v>", lambda e: self.output_entry.insert(0, pyperclip.paste()))
        
        self.output_browse_button = ttk.Button(self.output_frame, text="Browse", 
                                             command=self.select_output_file, state="disabled")
        self.output_browse_button.pack(side="right")
        
        self.verbose_mode = tk.BooleanVar(value=False)
        self.verbose_check = ttk.Checkbutton(self.options_frame, text="Verbose output", 
                                           variable=self.verbose_mode)
        self.verbose_check.pack(anchor="w", padx=5, pady=2)
        
        # Progress
        self.progress_frame = ttk.LabelFrame(self.main_container, text="Progress")
        self.progress_frame.grid(row=3, column=0, sticky="nsew", padx=5, pady=2)
        
        # Add scrollbar to progress text
        self.progress_text = tk.Text(self.progress_frame, height=8, state="disabled")
        scrollbar = ttk.Scrollbar(self.progress_frame, command=self.progress_text.yview)
        self.progress_text.configure(yscrollcommand=scrollbar.set)
        
        # Grid layout for progress area
        self.progress_text.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        
        # Configure grid weights for progress frame
        self.progress_frame.grid_rowconfigure(0, weight=1)
        self.progress_frame.grid_columnconfigure(0, weight=1)
        
        # Configure grid weights for main container
        self.main_container.grid_rowconfigure(3, weight=1)  # Progress area gets extra space
        self.main_container.grid_columnconfigure(0, weight=1)
        
        # Make text widget expand to fill space
        self.progress_text.config(wrap="none")
        
        # Control buttons
        self.button_frame = ttk.Frame(self.main_container)
        self.button_frame.grid(row=4, column=0, sticky="ew", padx=5, pady=5)
        
        self.start_button = ttk.Button(
            self.button_frame, 
            text="Start Processing", 
            command=self.start_processing,
            style='Accent.TButton'
        )
        self.start_button.pack(side="left", expand=True, fill="x")
        
        self.cancel_button = ttk.Button(
            self.button_frame,
            text="Cancel",
            command=self.cancel_processing,
            state="disabled"
        )
        self.cancel_button.pack(side="right", expand=True, fill="x")
        
        # Thread control
        self.processing_thread = None
        self.cancel_requested = False
        
        # Message queue for progress updates
        self.message_queue = []
        self.update_timer = None
        
        # Configure styles
        style = ttk.Style()
        style.configure('Accent.TButton', 
                       font=('Helvetica', 12, 'bold'),
                       padding=10,
                       foreground='white',
                       background='#0078d7')
        
        # Add GitHub link
        self.footer_frame = ttk.Frame(self.main_container)
        self.footer_frame.grid(row=5, column=0, sticky="ew", padx=5, pady=2)
        
        self.github_link = ttk.Label(
            self.footer_frame,
            text="View source code, documentation, or request features on GitHub",
            foreground="blue",
            cursor="hand2",
            font=('Helvetica', 9)
        )
        self.github_link.pack(side="right")
        self.github_link.bind("<Button-1>", lambda e: self.open_github())
        
    def _get_last_path_file(self) -> Path:
        """Get the path to the last path file in system temp directory."""
        import tempfile
        temp_dir = Path(tempfile.gettempdir())
        return temp_dir / "FileSizeTreeChecker_latest_path.txt"

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
        folder = filedialog.askdirectory()
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
                    "Please select a valid directory."
                )
            
    def select_output_file(self):
        output_file = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
            initialfile="media_durations.json"
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
                "Please check the path and try again."
            )
            return
            
        # Check if it's actually a directory
        if not os.path.isdir(folder):
            messagebox.showerror(
                "Error", 
                f"The selected path is not a directory:\n{folder}\n\n"
                "Please select a valid directory."
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
            target=self.process_folder,
            args=(folder,),
            daemon=True
        )
        self.processing_thread.start()
        
    def process_folder(self, folder):
        try:
            path = Path(folder)
            results = {}
    
            # Get all media files
            media_files = [f for f in path.rglob('*') if f.suffix.lower() in MEDIA_EXTENSIONS and not f.name.startswith('.')]
            
            random.shuffle(media_files)
            
            # Calculate total size
            total_size = sum(f.stat().st_size for f in media_files)
            total_size_gb = total_size / (1024 ** 3)
    
            self.log_message(f"Found {len(media_files)} media files ({total_size_gb:.2f} GB)")
            
            # Process files
            current_duration = 0
            processed_size = 0
            estimated_total = 0  # Initialize with 0
            
            for i, file in enumerate(media_files):
                # Calculate estimated total duration
                if processed_size > 0:
                    estimated_total = (total_size / processed_size) * current_duration
                if self.cancel_requested:
                    self.log_message("\nProcessing cancelled by user")
                    self.log_message(f"Duration of all files seen so far: {current_duration//3600}h {(current_duration%3600)//60}m")
                    self.log_message(f"Estimated duration for all the files (seen and unseen): {estimated_total//3600:.0f}h {(estimated_total%3600)//60:.0f}m")
                    break
                duration = get_duration(file, path, self.verbose_mode.get())
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
                    percent_done = (i+1)/len(media_files)*100
                    progress_msg = f"[{i+1}/{len(media_files)} ({percent_done:.1f}%)] Sum of durations so far: {current_duration//3600}h {(current_duration%3600)//60}m | " \
                                 f"Estimated total for all files: {estimated_total//3600:.0f}h {(estimated_total%3600)//60:.0f}m"
                    
                    if i % 10 == 0:  # Update progress every 10 files
                        self.queue_message(progress_msg)
            
            self.log_message(f"\nTotal duration: {current_duration//3600}h {(current_duration%3600)//60}m")
            
            # Write results to JSON file if enabled
            if self.save_json.get():
                outpath = Path(self.output_path.get())
                with open(outpath, 'w', encoding='utf-8') as f:
                    json.dump(results, f, indent=2)
                self.log_message(f"Results saved to {outpath}")
            
            messagebox.showinfo("Processing Complete", "Media duration calculation finished!")
            
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
            self.log_message("\nCancelling... Please wait for current file to finish.")
            self.cancel_button.config(state="disabled")
            
    def open_github(self):
        """Open the GitHub repository in the default web browser."""
        import webbrowser
        webbrowser.open("https://github.com/thiswillbeyourgithub/FileSizeTreeChecker")
        
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

if __name__ == '__main__':
    try:
        root = tk.Tk()
        app = FileSizeTreeChecker(root)
        root.mainloop()
    except KeyboardInterrupt:
        print("\nKeyboard interrupt received. Exiting gracefully...")
        try:
            if app.processing_thread and app.processing_thread.is_alive():
                app.cancel_processing()
                app.processing_thread.join(timeout=2)
        except Exception:
            pass
        root.destroy()
