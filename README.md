# AutoTyper Pro 🚀

A powerful and user-friendly automated typing tool built with Python. This application allows you to automate text input with customizable typing speed, hotkeys, and window focus detection.

## ✨ Features

- 🎯 Customizable typing speed
- ⌨️ Global hotkey support
- 🪟 Window focus detection
- ⏰ Adjustable start delay
- 🔄 Multi-language support
- 💻 Modern GUI interface

## 🛠️ Installation

1. Clone this repository:
```bash
git clone https://github.com/creator79/AutoTyper.git
cd AutoTyper
```

2. Install the required packages:
```bash
pip install -r requirements.txt
```

Required packages:
- PyQt5
- pynput
- pyautogui
- psutil
- pywin32 (optional, for Windows)
- pyinstaller (for building executable)

## 🚀 Building the Executable

To build the executable file, run the following command:

```powershell
python -m PyInstaller --onefile --noconsole typer.py
```

The executable will be created in the `dist` folder.

## 🎮 Usage

1. Run the application
2. Enter or paste the text you want to auto-type
3. Set your preferred typing speed
4. Configure hotkeys if desired
5. Press the configured hotkey to start/stop typing

## ⚙️ Configuration

- **Typing Speed**: Adjust the delay between keystrokes (0.000 to 2.0 seconds)
- **Start Delay**: Set a delay before typing begins
- **Hotkeys**: Customize your start/stop hotkey combinations
- **Window Focus**: Option to type in any window or specific windows only

## 🤝 Credits

- **Developer**: [Vivek Upadhyay](https://github.com/creator79)
- **Version**: 3.0.0

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## ⚠️ Disclaimer

This tool is intended for legitimate use cases such as testing, automation, and productivity enhancement. Users are responsible for ensuring appropriate and ethical use of this software.

---
Made with ❤️ by [Vivek Upadhyay](https://github.com/creator79)
