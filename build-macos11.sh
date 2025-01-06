#!/bin/zsh

# Build the Docker image
sudo docker build -t macos11-builder .

# Run the container and build the app
sudo docker run --rm -v $(pwd)/dist:/home/builder/app/dist macos11-builder zsh -c "
    # Create hook file for Tkinter
    echo \"from PyInstaller.utils.hooks import collect_data_files\" > hook-tkinter.py
    echo \"datas = collect_data_files('tkinter')\" >> hook-tkinter.py
    
    # Build for macOS 11 (Intel)
    pyinstaller --onedir --windowed --name FileSizeTreeChecker-macos11.app FileSizeTreeChecker.py \
        --target-architecture x86_64 \
        --hidden-import='tkinter' \
        --clean
"

echo "Build complete! Check the dist/ directory for your macOS 11 compatible build."
