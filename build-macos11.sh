#!/bin/zsh

# Build the Docker image
sudo docker build -t macos11-builder .

# Run the container and build the app
sudo docker run --rm -v $(pwd)/dist:/home/builder/app/dist macos11-builder zsh -c "
    # Create hook file for Tkinter
    echo \"from PyInstaller.utils.hooks import collect_data_files\" > hook-tkinter.py
    echo \"datas = collect_data_files('tkinter')\" >> hook-tkinter.py
    
    # Build for macOS 11 (Intel)
    pyinstaller --windowed --name FileSizeTreeChecker-macos11.app FileSizeTreeChecker.py \
        --target-architecture x86_64 \
        --hidden-import='tkinter' \
        --add-data='/home/builder/venv/lib/python3.11/site-packages/moviepy:moviepy' \
        --add-data='/home/builder/venv/lib/python3.11/site-packages/imageio:imageio' \
        --add-data='/home/builder/venv/lib/python3.11/site-packages/decorator:decorator' \
        --add-data='/home/builder/venv/lib/python3.11/site-packages/tqdm:tqdm' \
        --add-data='/home/builder/venv/lib/python3.11/site-packages/numpy:numpy' \
        --clean \
        --noconfirm
    
    # Fix macOS app bundle structure
    cd dist/FileSizeTreeChecker-macos11.app/Contents/MacOS
    mkdir -p Frameworks
    mkdir -p Resources
    cd ..
    
    # Create proper Info.plist
    cat > Info.plist <<EOF
<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<!DOCTYPE plist PUBLIC \"-//Apple//DTD PLIST 1.0//EN\" \"http://www.apple.com/DTDs/PropertyList-1.0.dtd\">
<plist version=\"1.0\">
<dict>
    <key>CFBundleExecutable</key>
    <string>FileSizeTreeChecker-macos11</string>
    <key>CFBundleIconFile</key>
    <string></string>
    <key>CFBundleIdentifier</key>
    <string>com.yourcompany.FileSizeTreeChecker</string>
    <key>CFBundleInfoDictionaryVersion</key>
    <string>6.0</string>
    <key>CFBundleName</key>
    <string>FileSizeTreeChecker</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0</string>
    <key>CFBundleVersion</key>
    <string>1</string>
    <key>LSMinimumSystemVersion</key>
    <string>11.0</string>
    <key>NSHighResolutionCapable</key>
    <true/>
</dict>
</plist>
EOF
"

# Fix permissions on the app bundle
sudo chmod -R 755 dist/FileSizeTreeChecker-macos11.app

echo "Build complete! Check the dist/ directory for your macOS 11 compatible build."
echo "You may need to codesign the app before distribution:"
echo "  codesign --deep --force --verify --verbose --sign \"Developer ID Application: Your Name (TEAMID)\" dist/FileSizeTreeChecker-macos11.app"
