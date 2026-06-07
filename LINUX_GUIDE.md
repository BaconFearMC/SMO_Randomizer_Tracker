## How to compile yourself on Linux using bash
## This assumes you already have all your Python Dependencies installed

1. Install Tkinter via your package manager:
## Arch
   sudo pacman -S tk
## Debian
   sudo apt update
   sudo apt install python3-tk
## fedora
   sudo dnf install python3-tkinter

# 1. Create a virtual environment sandbox
python -m venv tracker_env

# 2. Activate the virtual environment
source tracker_env/bin/activate

# 3. Install core project packages and the compiler
pip install -r requirements.txt
pip install pyinstaller

# Clear any old compilation artifacts
rm -rf build dist

# Compile the production binary
pyinstaller --onefile --windowed --add-data "assets:assets" --hidden-import="PIL._tkinter_finder" trackerNEW.py

# 4. Troubleshooting Cross-Platform Quirks
Because this project is often developed on Windows, certain platform differences can break the application when packaged inside a Linux container environment.

Symptom A: ModuleNotFoundError: No module named 'PIL._tkinter_finder'
Cause: PyInstaller failed to map the image rendering pipeline to the UI library dynamically.

Solution: Ensure you are using the exact build command above containing the --hidden-import="PIL._tkinter_finder" flag.

Symptom B: FileNotFoundError or IsADirectoryError regarding specific asset files
If the script fails to launch and running ./dist/trackerNEW manually in your terminal reveals an error like:
FileNotFoundError: [Errno 2] No such file or directory: '/tmp/_MEIxxxx/assets/Capture.png'

Cause: Linux file systems are strictly case-sensitive, whereas Windows file systems are case-insensitive. If a line of Python code looks for Capture.png (capital C), but the physical file inside your /assets folder is named capture.png (lowercase c), Windows will load it seamlessly, but Linux will crash instantly.

The Non-Destructive Fix: You do not need to modify the repository's core code. Navigate to your local assets/ directory, find the file throwing the error, duplicate it, and rename the copy to match the exact casing structure the error code is looking for.

For example: Having both capture.png and Capture.png sitting side-by-side inside your asset folder satisfies both realities simultaneously and allows PyInstaller to compile perfectly.
