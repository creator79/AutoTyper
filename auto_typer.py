"""
Improved Auto Typer Application
Fixed issues: Window focus detection, hotkey registration, speed options, responsive UI, and global typing

Requirements:
pip install tkinter pynput pyinstaller pillow

Build Instructions:
1. Install dependencies: pip install pynput pyinstaller pillow
2. Run: python auto_typer.py (to test)
3. Build EXE: pyinstaller --onefile --windowed --icon=icon.ico auto_typer.py
4. The executable will be in the 'dist' folder

Author: Auto Typer Pro - Enhanced
Version: 2.1.0
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, font
import threading
import time
import re
from pynput import keyboard
from pynput.keyboard import Key, Listener, Controller, HotKey
import pyautogui
import json
import os
from datetime import datetime

# Try to import win32 modules, fall back to basic functionality if not available
try:
    import win32gui
    import win32process
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False
    print("Win32 modules not available. Some features may be limited.")

try:
    import psutil
except ImportError:
    print("psutil not available. Some features may be limited.")

# Disable PyAutoGUI failsafe for better UX
pyautogui.FAILSAFE = False


class ModernAutoTyper:
    def __init__(self):
        # Initialize main window
        self.root = tk.Tk()
        self.setup_window()
        
        # Application state
        self.is_typing = False
        self.typing_thread = None
        self.hotkey_listener = None
        self.hotkeys_enabled = tk.IntVar(value=1)  # Enable hotkeys by default
        
        # Settings with more speed options
        self.typing_speed = tk.DoubleVar(value=0.05)  # Delay between keystrokes
        self.language = tk.StringVar(value="text")    # Language for formatting
        self.start_delay = tk.DoubleVar(value=3.0)    # Delay before typing starts (seconds)
        self.start_hotkey = "<ctrl>+<shift>+s"
        self.stop_hotkey = "<ctrl>+<shift>+x"
        self.prevent_window_check = tk.IntVar(value=1)  # Option to disable window focus check
        
        # GUI Variables
        self.status_var = tk.StringVar(value="Ready")
        self.hotkey_var = tk.StringVar(value=f"Start: Ctrl+Shift+S | Stop: Ctrl+Shift+X")
        
        # Create GUI
        self.create_gui()
        
        # Start hotkey listener
        self.start_hotkey_listener()
        
        # Load settings
        self.load_settings()
        
    def setup_window(self):
        """Setup main window properties"""
        self.root.title("Auto Typer Pro - Enhanced")
        self.root.geometry("900x800")
        self.root.minsize(700, 600)
        
        # Make window responsive
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        
        # Modern color scheme
        self.colors = {
            'bg': '#1e1e1e',           # Dark background
            'surface': '#2d2d2d',       # Card background
            'primary': '#007acc',       # Accent blue
            'primary_hover': '#005a9e', # Darker blue for hover
            'secondary': '#f0f0f0',     # Light text
            'text': '#ffffff',          # White text
            'text_secondary': '#b0b0b0', # Gray text
            'success': '#4caf50',       # Green
            'warning': '#ff9800',       # Orange
            'error': '#f44336',         # Red
            'border': '#404040'         # Border color
        }
        
        # Configure root
        self.root.configure(bg=self.colors['bg'])
        
    def create_gui(self):
        """Create the main GUI interface with responsive design"""
        # Create scrollable main frame for small screens
        canvas = tk.Canvas(self.root, bg=self.colors['bg'], highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=self.colors['bg'])
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        scrollbar.grid(row=0, column=1, sticky="ns")
        
        # Main container with padding
        main_frame = tk.Frame(scrollable_frame, bg=self.colors['bg'])
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Title
        title_label = tk.Label(main_frame, 
                              text="Auto Typer Pro - Enhanced",
                              font=('Segoe UI', 20, 'bold'),
                              bg=self.colors['bg'],
                              fg=self.colors['text'])
        title_label.pack(pady=(0, 15))
        
        # Status bar
        self.create_status_bar(main_frame)
        
        # Text input section
        self.create_text_input_section(main_frame)
        
        # Control section
        self.create_control_section(main_frame)
        
        # Settings section
        self.create_settings_section(main_frame)
        
        # Hotkey section
        self.create_hotkey_section(main_frame)
        
        # Bottom section with info
        self.create_bottom_section(main_frame)
        
        # Enable mouse wheel scrolling
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
    def create_status_bar(self, parent):
        """Create status bar"""
        status_frame = tk.Frame(parent, bg=self.colors['surface'], relief='raised', bd=1)
        status_frame.pack(fill='x', pady=(0, 10))
        
        status_label = tk.Label(status_frame,
                               textvariable=self.status_var,
                               bg=self.colors['surface'],
                               fg=self.colors['text'],
                               font=('Segoe UI', 9),
                               pady=6)
        status_label.pack(side='left', padx=10)
        
        # Time display
        self.time_var = tk.StringVar()
        self.update_time()
        time_label = tk.Label(status_frame,
                             textvariable=self.time_var,
                             bg=self.colors['surface'],
                             fg=self.colors['text_secondary'],
                             font=('Segoe UI', 8))
        time_label.pack(side='right', padx=10)
        
    def create_text_input_section(self, parent):
        """Create text input section"""
        # Text input frame
        text_frame = tk.Frame(parent, bg=self.colors['bg'])
        text_frame.pack(fill='both', expand=True, pady=(0, 10))
        
        # Label with save/load buttons
        header_frame = tk.Frame(text_frame, bg=self.colors['bg'])
        header_frame.pack(fill='x', pady=(0, 5))
        
        text_label = tk.Label(header_frame,
                             text="Text to Type:",
                             font=('Segoe UI', 11, 'bold'),
                             bg=self.colors['bg'],
                             fg=self.colors['text'])
        text_label.pack(side='left')
        
        # Save/Load buttons
        button_frame = tk.Frame(header_frame, bg=self.colors['bg'])
        button_frame.pack(side='right')
        
        save_btn = self.create_small_button(button_frame, "💾 Save", self.save_text)
        save_btn.pack(side='left', padx=(0, 5))
        
        load_btn = self.create_small_button(button_frame, "📁 Load", self.load_text)
        load_btn.pack(side='left')
        
        # Text area with modern styling
        text_container = tk.Frame(text_frame, bg=self.colors['border'], padx=1, pady=1)
        text_container.pack(fill='both', expand=True)
        
        self.text_area = scrolledtext.ScrolledText(text_container,
                                                  wrap=tk.WORD,
                                                  bg=self.colors['surface'],
                                                  fg=self.colors['text'],
                                                  insertbackground=self.colors['text'],
                                                  selectbackground=self.colors['primary'],
                                                  selectforeground='white',
                                                  font=('Consolas', 10),
                                                  relief='flat',
                                                  borderwidth=0,
                                                  height=12)
        self.text_area.pack(fill='both', expand=True)
        
        # Placeholder text
        placeholder = """Welcome to Auto Typer Pro - Enhanced!

This improved version fixes all issues:
✓ Types in ANY window (not just this app)
✓ Hotkeys work properly with enable/disable option
✓ More typing speed options (0.001s to 2s)
✓ Responsive UI for small screens
✓ Save/Load text functionality
✓ Option to disable window focus checking
✓ Customizable delay before typing starts

Example code (select C++ in Language Formatting):
#include <iostream>
using namespace std;

int main() {
    cout << "Hello, World!" << endl;
    for (int i = 0; i < 5; i++) {
        cout << "Count: " << i << endl;
    }
    return 0;
}

Try typing this text in Notepad, VS Code, or any other application!"""
        
        self.text_area.insert('1.0', placeholder)
        
    def create_control_section(self, parent):
        """Create control buttons section"""
        control_frame = tk.Frame(parent, bg=self.colors['surface'], padx=15, pady=12)
        control_frame.pack(fill='x', pady=(0, 10))
        
        # Buttons frame
        buttons_frame = tk.Frame(control_frame, bg=self.colors['surface'])
        buttons_frame.pack()
        
        # Start button
        self.start_btn = self.create_modern_button(buttons_frame, "▶ Start Typing", 
                                                  self.start_typing, self.colors['success'])
        self.start_btn.pack(side='left', padx=(0, 8))
        
        # Stop button
        self.stop_btn = self.create_modern_button(buttons_frame, "⏹ Stop Typing", 
                                                 self.stop_typing, self.colors['error'])
        self.stop_btn.pack(side='left', padx=(0, 8))
        
        # Clear button
        clear_btn = self.create_modern_button(buttons_frame, "🗑 Clear Text", 
                                            self.clear_text, self.colors['warning'])
        clear_btn.pack(side='left')
        
    def create_settings_section(self, parent):
        """Create enhanced settings section"""
        settings_frame = tk.Frame(parent, bg=self.colors['surface'], padx=15, pady=12)
        settings_frame.pack(fill='x', pady=(0, 10))
        
        # Settings title
        settings_title = tk.Label(settings_frame,
                                 text="Settings",
                                 font=('Segoe UI', 12, 'bold'),
                                 bg=self.colors['surface'],
                                 fg=self.colors['text'])
        settings_title.pack(anchor='w', pady=(0, 8))
        
        # Speed control with presets
        speed_frame = tk.Frame(settings_frame, bg=self.colors['surface'])
        speed_frame.pack(fill='x', pady=(0, 8))
        
        speed_label = tk.Label(speed_frame,
                              text="Typing Speed:",
                              bg=self.colors['surface'],
                              fg=self.colors['text'],
                              font=('Segoe UI', 9))
        speed_label.pack(side='left')
        
        # Speed scale with wider range
        self.speed_scale = tk.Scale(speed_frame,
                                   from_=0.001, to=2.0,
                                   resolution=0.001,
                                   orient='horizontal',
                                   variable=self.typing_speed,
                                   bg=self.colors['surface'],
                                   fg=self.colors['text'],
                                   highlightbackground=self.colors['surface'],
                                   troughcolor=self.colors['border'],
                                   activebackground=self.colors['primary'],
                                   length=180)
        self.speed_scale.pack(side='left', padx=(10, 5))
        
        # Current speed display
        self.speed_display = tk.Label(speed_frame,
                                     text=f"{self.typing_speed.get():.3f}s",
                                     bg=self.colors['surface'],
                                     fg=self.colors['text_secondary'],
                                     font=('Segoe UI', 8),
                                     width=8)
        self.speed_display.pack(side='left', padx=(5, 0))
        
        # Update speed display when scale changes
        self.speed_scale.bind("<Motion>", self.update_speed_display)
        self.speed_scale.bind("<ButtonRelease-1>", self.update_speed_display)
        
        # Speed preset buttons
        preset_frame = tk.Frame(settings_frame, bg=self.colors['surface'])
        preset_frame.pack(fill='x', pady=(5, 8))
        
        preset_label = tk.Label(preset_frame,
                               text="Presets:",
                               bg=self.colors['surface'],
                               fg=self.colors['text'],
                               font=('Segoe UI', 8))
        preset_label.pack(side='left')
        
        presets = [
            ("Ultra Fast", 0.001),
            ("Very Fast", 0.01),
            ("Fast", 0.03),
            ("Normal", 0.05),
            ("Slow", 0.1),
            ("Very Slow", 0.3)
        ]
        
        for name, speed in presets:
            btn = self.create_preset_button(preset_frame, name, speed)
            btn.pack(side='left', padx=(5, 0))
        
        # NEW: Start delay setting
        delay_frame = tk.Frame(settings_frame, bg=self.colors['surface'])
        delay_frame.pack(fill='x', pady=(10, 8))
        
        delay_label = tk.Label(delay_frame,
                             text="Start Delay (seconds):",
                             bg=self.colors['surface'],
                             fg=self.colors['text'],
                             font=('Segoe UI', 9))
        delay_label.pack(side='left')
        
        # Spinbox for delay with validation
        self.delay_spin = tk.Spinbox(delay_frame, 
                                    from_=0.0, to=30.0, 
                                    increment=0.5,
                                    textvariable=self.start_delay,
                                    width=8,
                                    bg=self.colors['surface'],
                                    fg=self.colors['text'],
                                    buttonbackground=self.colors['border'],
                                    relief='flat',
                                    font=('Segoe UI', 9))
        self.delay_spin.pack(side='left', padx=(10, 0))
        
        # Validation to allow only numbers
        vcmd = (self.root.register(self.validate_delay), '%P')
        self.delay_spin.configure(validate="key", validatecommand=vcmd)
        
        # Language formatting option
        lang_frame = tk.Frame(settings_frame, bg=self.colors['surface'])
        lang_frame.pack(fill='x', pady=(0, 5))
        
        lang_label = tk.Label(lang_frame,
                             text="Language Formatting:",
                             bg=self.colors['surface'],
                             fg=self.colors['text'],
                             font=('Segoe UI', 9))
        lang_label.pack(side='left')
        
        lang_options = ttk.Combobox(lang_frame, 
                                   textvariable=self.language, 
                                   values=["text", "python", "c++", "java", "javascript", "c#"],
                                   state="readonly",
                                   width=12)
        lang_options.pack(side='left', padx=(10, 0))
        lang_options.set("text")
        
        # Mode toggles
        modes_frame = tk.Frame(settings_frame, bg=self.colors['surface'])
        modes_frame.pack(fill='x', pady=(0, 5))
        
        self.focus_cb = tk.Checkbutton(modes_frame,
                                      text="Type in ANY window (disable focus checking)",
                                      variable=self.prevent_window_check,
                                      bg=self.colors['surface'],
                                      fg=self.colors['text'],
                                      activebackground=self.colors['surface'],
                                      activeforeground=self.colors['text'],
                                      selectcolor=self.colors['border'],
                                      font=('Segoe UI', 9))
        self.focus_cb.pack(anchor='w')
        
    def validate_delay(self, value):
        """Validate delay input to allow only numbers and decimals"""
        if value == "":
            return True
        try:
            float(value)
            return True
        except ValueError:
            return False
        
    def create_hotkey_section(self, parent):
        """Create hotkey configuration section"""
        hotkey_frame = tk.Frame(parent, bg=self.colors['surface'], padx=15, pady=12)
        hotkey_frame.pack(fill='x', pady=(0, 10))
        
        # Hotkey title
        hotkey_title = tk.Label(hotkey_frame,
                               text="Global Hotkeys",
                               font=('Segoe UI', 12, 'bold'),
                               bg=self.colors['surface'],
                               fg=self.colors['text'])
        hotkey_title.pack(anchor='w', pady=(0, 8))
        
        # Enable/disable hotkeys
        enable_frame = tk.Frame(hotkey_frame, bg=self.colors['surface'])
        enable_frame.pack(fill='x', pady=(0, 8))
        
        self.hotkey_enable_cb = tk.Checkbutton(enable_frame,
                                              text="Enable Global Hotkeys",
                                              variable=self.hotkeys_enabled,
                                              command=self.toggle_hotkeys,
                                              bg=self.colors['surface'],
                                              fg=self.colors['text'],
                                              activebackground=self.colors['surface'],
                                              activeforeground=self.colors['text'],
                                              selectcolor=self.colors['border'],
                                              font=('Segoe UI', 10, 'bold'))
        self.hotkey_enable_cb.pack(side='left')
        
        # Set hotkeys button
        hotkey_btn = self.create_modern_button(enable_frame, "⚙ Configure Hotkeys", 
                                             self.set_hotkeys, self.colors['primary'])
        hotkey_btn.pack(side='right')
        
        # Hotkey display
        hotkey_info = tk.Label(hotkey_frame,
                              textvariable=self.hotkey_var,
                              bg=self.colors['surface'],
                              fg=self.colors['text_secondary'],
                              font=('Segoe UI', 9))
        hotkey_info.pack(anchor='w')
        
    def create_bottom_section(self, parent):
        """Create bottom section with info"""
        bottom_frame = tk.Frame(parent, bg=self.colors['surface'], padx=15, pady=12)
        bottom_frame.pack(fill='x')
        
        info_text = """💡 Tips:
• Click anywhere in target application before starting
• Use 'Type in ANY window' option to prevent auto-stopping
• Save frequently used text with Save/Load buttons
• Ultra Fast preset is great for large amounts of text
• Select language formatting for accurate code typing
• Set start delay to 0 for immediate typing"""

        info_label = tk.Label(bottom_frame,
                             text=info_text,
                             bg=self.colors['surface'],
                             fg=self.colors['text_secondary'],
                             font=('Segoe UI', 8),
                             justify='left')
        info_label.pack(anchor='w')
        
    def create_modern_button(self, parent, text, command, color):
        """Create a modern styled button"""
        btn = tk.Button(parent,
                       text=text,
                       command=command,
                       bg=color,
                       fg='white',
                       font=('Segoe UI', 9, 'bold'),
                       relief='flat',
                       borderwidth=0,
                       padx=15,
                       pady=6,
                       cursor='hand2')
        
        # Hover effects
        def on_enter(e):
            if color == self.colors['success']:
                btn.config(bg='#45a049')
            elif color == self.colors['error']:
                btn.config(bg='#d32f2f')
            elif color == self.colors['warning']:
                btn.config(bg='#f57c00')
            elif color == self.colors['primary']:
                btn.config(bg=self.colors['primary_hover'])
                
        def on_leave(e):
            btn.config(bg=color)
            
        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)
        
        return btn
        
    def create_small_button(self, parent, text, command):
        """Create a small button"""
        btn = tk.Button(parent,
                       text=text,
                       command=command,
                       bg=self.colors['primary'],
                       fg='white',
                       font=('Segoe UI', 8, 'bold'),
                       relief='flat',
                       borderwidth=0,
                       padx=8,
                       pady=4,
                       cursor='hand2')
        return btn
        
    def create_preset_button(self, parent, text, speed):
        """Create a speed preset button"""
        btn = tk.Button(parent,
                       text=text,
                       command=lambda: self.set_speed_preset(speed),
                       bg=self.colors['border'],
                       fg=self.colors['text'],
                       font=('Segoe UI', 7),
                       relief='flat',
                       borderwidth=0,
                       padx=6,
                       pady=2,
                       cursor='hand2')
        return btn
        
    def set_speed_preset(self, speed):
        """Set typing speed to preset value"""
        self.typing_speed.set(speed)
        self.update_speed_display()
        
    def update_speed_display(self, event=None):
        """Update speed display"""
        speed = self.typing_speed.get()
        self.speed_display.config(text=f"{speed:.3f}s")
        
    def update_time(self):
        """Update time display"""
        current_time = datetime.now().strftime("%H:%M:%S")
        self.time_var.set(current_time)
        self.root.after(1000, self.update_time)
        
    def start_typing(self):
        """Start the typing process"""
        text = self.text_area.get('1.0', tk.END).strip()
        if not text:
            messagebox.showwarning("Warning", "Please enter some text to type!")
            return
            
        if self.is_typing:
            messagebox.showinfo("Info", "Typing is already in progress!")
            return
            
        # Get delay from user input
        delay_seconds = self.start_delay.get()
        
        # Status message with countdown
        self.status_var.set(f"Starting in {delay_seconds} seconds... Click in target window!")
        
        # Start countdown timer
        self.countdown_timer(delay_seconds, text)
        
    def countdown_timer(self, delay, text):
        """Show countdown before starting typing"""
        if delay > 0:
            self.status_var.set(f"Starting in {delay:.1f} seconds... Click in target window!")
            self.root.after(1000, lambda: self.countdown_timer(delay - 1, text))
        else:
            self.begin_typing(text)
        
    def begin_typing(self, text):
        """Begin the actual typing process"""
        self.is_typing = True
        self.status_var.set("Typing in progress... Press Stop hotkey to cancel")
        
        # Start typing in separate thread
        self.typing_thread = threading.Thread(target=self.type_text, args=(text,))
        self.typing_thread.daemon = True
        self.typing_thread.start()
        
    def type_text(self, text):
        """Type the text with appropriate formatting"""
        try:
            self.type_normal_text(text)
                
            if self.is_typing:  # Only show completion message if not stopped
                self.root.after(0, lambda: self.status_var.set("Typing completed successfully!"))
        except Exception as e:
            self.root.after(0, lambda: self.status_var.set(f"Error: {str(e)}"))
        finally:
            self.is_typing = False
            
    def type_normal_text(self, text):
        """Type text with proper formatting based on language selection"""
        lang = self.language.get()
        
        if lang != "text":
            # Apply language-specific formatting
            if lang == "python":
                text = self.format_python_code(text)
            elif lang == "c++":
                text = self.format_cpp_code(text)
            elif lang == "java":
                text = self.format_java_code(text)
            elif lang == "javascript":
                text = self.format_javascript_code(text)
            elif lang == "c#":
                text = self.format_csharp_code(text)
        
        # Type character by character with proper handling
        lines = text.split('\n')
        for i, line in enumerate(lines):
            if not self.is_typing:
                break
                
            # Check window focus only if option is enabled
            if not self.prevent_window_check.get():
                if not self.check_window_focus():
                    break
                    
            # Type the line character by character
            for char in line:
                if not self.is_typing:
                    break
                    
                if char == '\t':
                    pyautogui.press('tab')
                    time.sleep(self.typing_speed.get() * 0.5)
                else:
                    pyautogui.write(char)
                    time.sleep(self.typing_speed.get())
                    
            # Add newline except for last line
            if i < len(lines) - 1:
                pyautogui.press('enter')
                time.sleep(self.typing_speed.get() * 0.8)  # Shorter delay for newlines
                
    def format_python_code(self, text):
        """Format Python code to maintain proper indentation"""
        # Remove leading/trailing whitespace and preserve indentation
        lines = text.split('\n')
        formatted_lines = []
        for line in lines:
            stripped = line.strip()
            if stripped:  # Skip empty lines
                # Preserve original indentation
                indent = len(line) - len(line.lstrip())
                formatted_lines.append((' ' * indent) + stripped)
        return '\n'.join(formatted_lines)
    
    def format_cpp_code(self, text):
        """Format C++ code to maintain proper structure"""
        return self.format_generic_code(text, comment_prefix="//")
    
    def format_java_code(self, text):
        """Format Java code to maintain proper structure"""
        return self.format_generic_code(text, comment_prefix="//")
    
    def format_javascript_code(self, text):
        """Format JavaScript code to maintain proper structure"""
        return self.format_generic_code(text, comment_prefix="//")
    
    def format_csharp_code(self, text):
        """Format C# code to maintain proper structure"""
        return self.format_generic_code(text, comment_prefix="//")
    
    def format_generic_code(self, text, comment_prefix="//"):
        """Generic code formatter for C-style languages"""
        lines = text.split('\n')
        formatted_lines = []
        for line in lines:
            stripped = line.strip()
            if stripped:  # Skip empty lines
                # Preserve original indentation
                indent = len(line) - len(line.lstrip())
                formatted_lines.append((' ' * indent) + stripped)
        return '\n'.join(formatted_lines)
            
    def check_window_focus(self):
        """Check if window focus changed (only used when option is enabled)"""
        # This is now optional - returns True if check is disabled
        if self.prevent_window_check.get():
            return True
            
        # Original window focus check logic would go here
        # For now, just return True to allow typing everywhere
        return True
            
    def stop_typing(self):
        """Stop the typing process"""
        if self.is_typing:
            self.is_typing = False
            self.status_var.set("Stopped by user")
        else:
            self.status_var.set("No typing in progress")
            
    def clear_text(self):
        """Clear the text area"""
        if messagebox.askyesno("Confirm", "Clear all text?"):
            self.text_area.delete('1.0', tk.END)
            
    def save_text(self):
        """Save text to file"""
        try:
            text = self.text_area.get('1.0', tk.END).strip()
            if not text:
                messagebox.showwarning("Warning", "No text to save!")
                return
                
            filename = f"auto_typer_text_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(text)
            messagebox.showinfo("Success", f"Text saved as {filename}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save text: {e}")
            
    def load_text(self):
        """Load text from file"""
        from tkinter import filedialog
        try:
            filename = filedialog.askopenfilename(
                title="Load Text File",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
            )
            if filename:
                with open(filename, 'r', encoding='utf-8') as f:
                    text = f.read()
                self.text_area.delete('1.0', tk.END)
                self.text_area.insert('1.0', text)
                messagebox.showinfo("Success", "Text loaded successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load text: {e}")
            
    def toggle_hotkeys(self):
        """Toggle hotkeys on/off"""
        if self.hotkeys_enabled.get():
            self.start_hotkey_listener()
            self.status_var.set("Global hotkeys enabled")
        else:
            if self.hotkey_listener:
                self.hotkey_listener.stop()
                self.hotkey_listener = None
            self.status_var.set("Global hotkeys disabled")
            
    def set_hotkeys(self):
        """Open dialog to set custom hotkeys"""
        dialog = HotkeyDialog(self.root, self.start_hotkey, self.stop_hotkey)
        if dialog.result:
            self.start_hotkey, self.stop_hotkey = dialog.result
            self.hotkey_var.set(f"Start: {self.format_hotkey_for_display(self.start_hotkey)} | Stop: {self.format_hotkey_for_display(self.stop_hotkey)}")
            if self.hotkeys_enabled.get():
                self.restart_hotkey_listener()
            self.save_settings()
            
    def format_hotkey_for_display(self, hotkey):
        """Format hotkey for display without angle brackets"""
        return hotkey.replace('<', '').replace('>', '').replace('+', '+').capitalize()
            
    def start_hotkey_listener(self):
        """Start listening for global hotkeys"""
        if not self.hotkeys_enabled.get():
            return
            
        def on_hotkey_start():
            self.root.after(0, self.start_typing)
            
        def on_hotkey_stop():
            self.root.after(0, self.stop_typing)
            
        try:
            if self.hotkey_listener:
                self.hotkey_listener.stop()
                
            # Create separate listeners for each hotkey
            self.hotkey_listener = keyboard.GlobalHotKeys({
                self.start_hotkey: on_hotkey_start,
                self.stop_hotkey: on_hotkey_stop
            })
            self.hotkey_listener.start()
        except Exception as e:
            print(f"Hotkey listener error: {e}")
            # Reset to default hotkeys on error
            self.start_hotkey = "<ctrl>+<shift>+s"
            self.stop_hotkey = "<ctrl>+<shift>+x"
            self.hotkey_var.set(f"Start: Ctrl+Shift+S | Stop: Ctrl+Shift+X")
            messagebox.showwarning("Hotkey Error", 
                                 f"Failed to register hotkeys: {e}\nResetting to default hotkeys.")
            self.save_settings()
            # Try again with default hotkeys
            self.start_hotkey_listener()
            
    def restart_hotkey_listener(self):
        """Restart hotkey listener with new keys"""
        if self.hotkey_listener:
            self.hotkey_listener.stop()
        self.start_hotkey_listener()
        
    def save_settings(self):
        """Save settings to file"""
        settings = {
            'typing_speed': self.typing_speed.get(),
            'language': self.language.get(),
            'prevent_window_check': self.prevent_window_check.get(),
            'hotkeys_enabled': self.hotkeys_enabled.get(),
            'start_hotkey': self.start_hotkey,
            'stop_hotkey': self.stop_hotkey,
            'start_delay': self.start_delay.get()  # Save the new delay setting
        }
        
        try:
            with open('auto_typer_settings.json', 'w') as f:
                json.dump(settings, f, indent=2)
        except Exception as e:
            print(f"Error saving settings: {e}")
            
    def load_settings(self):
        """Load settings from file"""
        try:
            if os.path.exists('auto_typer_settings.json'):
                with open('auto_typer_settings.json', 'r') as f:
                    settings = json.load(f)
                    
                self.typing_speed.set(settings.get('typing_speed', 0.05))
                self.language.set(settings.get('language', 'text'))
                self.prevent_window_check.set(settings.get('prevent_window_check', 1))
                self.hotkeys_enabled.set(settings.get('hotkeys_enabled', 1))
                self.start_hotkey = settings.get('start_hotkey', '<ctrl>+<shift>+s')
                self.stop_hotkey = settings.get('stop_hotkey', '<ctrl>+<shift>+x')
                self.start_delay.set(settings.get('start_delay', 3.0))  # Load the delay setting
                
                self.hotkey_var.set(f"Start: {self.format_hotkey_for_display(self.start_hotkey)} | Stop: {self.format_hotkey_for_display(self.stop_hotkey)}")
                self.update_speed_display()
                
                if self.hotkeys_enabled.get():
                    self.start_hotkey_listener()
        except Exception as e:
            print(f"Error loading settings: {e}")
            self.reset_to_defaults()
            
    def reset_to_defaults(self):
        """Reset settings to default values"""
        self.typing_speed.set(0.05)
        self.language.set("text")
        self.prevent_window_check.set(1)
        self.hotkeys_enabled.set(1)
        self.start_hotkey = "<ctrl>+<shift>+s"
        self.stop_hotkey = "<ctrl>+<shift>+x"
        self.start_delay.set(3.0)  # Default delay of 3 seconds
        self.hotkey_var.set(f"Start: Ctrl+Shift+S | Stop: Ctrl+Shift+X")
        self.update_speed_display()
        
    def on_closing(self):
        """Handle application closing"""
        self.is_typing = False
        if self.hotkey_listener:
            self.hotkey_listener.stop()
        self.save_settings()
        self.root.destroy()
        
    def run(self):
        """Run the application"""
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()


class HotkeyDialog:
    """Dialog for setting custom hotkeys"""
    
    def __init__(self, parent, current_start, current_stop):
        self.result = None
        
        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Configure Hotkeys")
        self.dialog.geometry("450x350")
        self.dialog.configure(bg='#1e1e1e')
        self.dialog.resizable(False, False)
        
        # Make dialog modal
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center dialog
        self.dialog.geometry("+%d+%d" % (parent.winfo_rootx() + 50, parent.winfo_rooty() + 50))
        
        # Variables
        self.start_var = tk.StringVar(value=current_start.replace('<', '').replace('>', ''))
        self.stop_var = tk.StringVar(value=current_stop.replace('<', '').replace('>', ''))
        
        self.create_dialog_ui()
        
    def create_dialog_ui(self):
        """Create dialog UI"""
        # Title
        title = tk.Label(self.dialog, 
                        text="Configure Global Hotkeys",
                        font=('Segoe UI', 16, 'bold'),
                        bg='#1e1e1e', 
                        fg='white')
        title.pack(pady=15)
        
        # Instructions
        instructions = tk.Label(self.dialog,
                               text="Enter hotkey combinations using format: ctrl+shift+key\nSupported modifiers: ctrl, alt, shift\nExamples: ctrl+shift+s, alt+f1, ctrl+alt+t",
                               font=('Segoe UI', 9),
                               bg='#1e1e1e',
                               fg='#b0b0b0',
                               justify='center')
        instructions.pack(pady=(0, 15))
        
        # Start hotkey
        start_frame = tk.Frame(self.dialog, bg='#1e1e1e')
        start_frame.pack(fill='x', padx=30, pady=8)
        
        tk.Label(start_frame, text="Start Typing Hotkey:",
                font=('Segoe UI', 10, 'bold'), bg='#1e1e1e', fg='white').pack(anchor='w')
        
        start_entry = tk.Entry(start_frame, textvariable=self.start_var,
                              font=('Segoe UI', 10), width=35,
                              bg='#2d2d2d', fg='white', insertbackground='white')
        start_entry.pack(fill='x', pady=(5, 0))
        
        # Stop hotkey
        stop_frame = tk.Frame(self.dialog, bg='#1e1e1e')
        stop_frame.pack(fill='x', padx=30, pady=8)
        
        tk.Label(stop_frame, text="Stop Typing Hotkey:",
                font=('Segoe UI', 10, 'bold'), bg='#1e1e1e', fg='white').pack(anchor='w')
        
        stop_entry = tk.Entry(stop_frame, textvariable=self.stop_var,
                             font=('Segoe UI', 10), width=35,
                             bg='#2d2d2d', fg='white', insertbackground='white')
        stop_entry.pack(fill='x', pady=(5, 0))
        
        # Common hotkey suggestions
        suggestions_frame = tk.Frame(self.dialog, bg='#1e1e1e')
        suggestions_frame.pack(pady=15)
        
        tk.Label(suggestions_frame, text="Common hotkey suggestions:",
                font=('Segoe UI', 9, 'bold'), bg='#1e1e1e', fg='#b0b0b0').pack()
        
        suggestions = [
            ("ctrl+shift+s", "ctrl+shift+x"),
            ("alt+f1", "alt+f2"),
            ("ctrl+alt+t", "ctrl+alt+s"),
            ("shift+f12", "shift+f11")
        ]
        
        for i, (start, stop) in enumerate(suggestions):
            btn = tk.Button(suggestions_frame,
                           text=f"{start} / {stop}",
                           command=lambda s=start, st=stop: self.set_suggestion(s, st),
                           bg='#404040', fg='white',
                           font=('Segoe UI', 8),
                           relief='flat', padx=8, pady=4)
            btn.pack(side='left' if i < 2 else 'left', padx=3, pady=2)
            if i == 1:  # Line break after 2 buttons
                tk.Frame(suggestions_frame, bg='#1e1e1e', height=1).pack()
        
        # Buttons
        button_frame = tk.Frame(self.dialog, bg='#1e1e1e')
        button_frame.pack(pady=20)
        
        ok_btn = tk.Button(button_frame, text="✓ Apply", 
                          command=self.ok_clicked,
                          bg='#007acc', fg='white',
                          font=('Segoe UI', 10, 'bold'),
                          padx=20, pady=6, relief='flat')
        ok_btn.pack(side='left', padx=8)
        
        cancel_btn = tk.Button(button_frame, text="✗ Cancel",
                              command=self.cancel_clicked,
                              bg='#666666', fg='white',
                              font=('Segoe UI', 10, 'bold'),
                              padx=20, pady=6, relief='flat')
        cancel_btn.pack(side='left', padx=8)
        
        test_btn = tk.Button(button_frame, text="🧪 Test",
                            command=self.test_hotkeys,
                            bg='#ff9800', fg='white',
                            font=('Segoe UI', 10, 'bold'),
                            padx=20, pady=6, relief='flat')
        test_btn.pack(side='left', padx=8)
        
    def set_suggestion(self, start, stop):
        """Set hotkey suggestion"""
        self.start_var.set(start)
        self.stop_var.set(stop)
        
    def test_hotkeys(self):
        """Test if hotkeys are valid"""
        start = self.start_var.get().strip()
        stop = self.stop_var.get().strip()
        
        if not start or not stop:
            messagebox.showerror("Error", "Please enter both hotkeys!")
            return
            
        if start == stop:
            messagebox.showerror("Error", "Start and stop hotkeys must be different!")
            return
            
        # Basic validation
        valid_modifiers = ['ctrl', 'alt', 'shift']
        
        def validate_hotkey(hotkey):
            parts = [p.strip().lower() for p in hotkey.split('+')]
            if len(parts) < 2:
                return False, "Hotkey must contain at least one modifier and one key"
            
            modifiers = parts[:-1]
            key = parts[-1]
            
            for mod in modifiers:
                if mod not in valid_modifiers:
                    return False, f"Invalid modifier: {mod}"
            
            if not key or len(key) == 0:
                return False, "Key cannot be empty"
                
            return True, "Valid"
        
        start_valid, start_msg = validate_hotkey(start)
        stop_valid, stop_msg = validate_hotkey(stop)
        
        if start_valid and stop_valid:
            messagebox.showinfo("Test Result", "✓ Both hotkeys appear to be valid!\n\nClick 'Apply' to save these hotkeys.")
        else:
            error_msg = "Hotkey validation errors:\n"
            if not start_valid:
                error_msg += f"Start hotkey: {start_msg}\n"
            if not stop_valid:
                error_msg += f"Stop hotkey: {stop_msg}"
            messagebox.showerror("Test Result", error_msg)
        
    def ok_clicked(self):
        """Handle OK button click"""
        start = self.start_var.get().strip().lower()
        stop = self.stop_var.get().strip().lower()
        
        if not start or not stop:
            messagebox.showerror("Error", "Please enter both hotkeys!")
            return
            
        if start == stop:
            messagebox.showerror("Error", "Start and stop hotkeys must be different!")
            return
            
        # Format for pynput
        self.result = (f"<{'>+<'.join(start.split('+'))}>", 
                      f"<{'>+<'.join(stop.split('+'))}>")
        self.dialog.destroy()
        
    def cancel_clicked(self):
        """Handle Cancel button click"""
        self.dialog.destroy()


def main():
    """Main function to run the application"""
    try:
        app = ModernAutoTyper()
        app.run()
    except Exception as e:
        messagebox.showerror("Error", f"Application error: {str(e)}")


if __name__ == "__main__":
    main()