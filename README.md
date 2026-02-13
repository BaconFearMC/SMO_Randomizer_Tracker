# SMO Randomizer Tracker

A live tracker + OBS overlay for Super Mario Odyssey Randomizer speedruns.

> [!TIP]
> If you do not have Python installed or you just want to run the tracker easily, there is a EXE file made through [PyInstaller](https://pyinstaller.org/en/stable/operating-mode.html) that has all the dependencies wrapped in. Double clicking the file will run the program with no issues.

## Requirements for Running through Python
- Python 3.11+  
Download from: https://www.python.org/downloads/
✔ Make sure "Add Python to PATH" is checked

## Installation through Python
1. In the directory of your choosing run: `git clone https://github.com/FireRisingRaging/SMO_Randomizer_Tracker.git`
2. Install dependencies in the project folder: `pip install -r requirements.txt`
3. Run the tracker: `python tracker.py`

> [!NOTE]
> The tracker will make a json file to save progress in the same folder that the program is in

## Getting Started
As mentioned previously, it is very easy to run the tracker! Simply double-clicking on the application titled "tracker" will open it up!

> [!NOTE]
> Your PC may warn you with a Windows security pop-up saying that a security update needs to be installed when opening the tracker. You may also get the blue box that reads "Windows protected your PC." The Python application is NOT malware, and you are safe to run the program. Installing and running the scripts through Python will circumvent this.

After you've opened the tracker, getting started is very easy!
- The lock and peace icons are toggleable buttons to track when you've flown the Odyssey to a kingdom and gotten world peace in a kingdom, respectively.
- The plus and minus buttons will increase or decrease your collected moon count
- Type in the required amount of moons for any given kingdom in the box with the question mark and hit save
- Hit the "Open OBS Overlay" button to open a convenient window to capture into OBS
- Hit "Toggle OBS BG" to turn the background of the window to a bright screen that is for color keying!
> [!TIP]
> Through our testing, the best result is leaving this green screen off and instead color keying the hex code #161616. This color is the color of the gray background.

- Pressing the "Clear" button will reset the tracker
- Hit the "Notes" button to open another window that allows you to freely track sub-area loads and chains (you can also track the moons of each sub-area here too!)

<sub>Made by FireRisingRaging and Just Bag assisted by GMO7</sub>
