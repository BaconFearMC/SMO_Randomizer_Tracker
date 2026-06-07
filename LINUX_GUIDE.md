## How to compile yourself on Linux (Arch/CachyOS)

1. Install Tkinter via your package manager:
   sudo pacman -S tk

2. Set up a virtual environment and install dependencies:
   python -m venv tracker_env
   source tracker_env/bin/activate
   pip install -r requirements.txt
   pip install pyinstaller

3. To compile the standalone Linux binary:
   pyinstaller --onefile --windowed --add-data "assets:assets" --hidden-import="PIL._tkinter_finder" tracker_NEW.py
