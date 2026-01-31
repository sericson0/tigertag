from metadata_handler import load_parquet_folder, csv_to_parquet
from helper_functions import (
    subset_entries, 
    parse_years_from_folder,
    extract_artist_names_from_folder,
    extract_artist_from_file_tags,
    fuzzy_match_artists,
    slugify_filename
)
import tag_updater
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext
import threading
import sys
import pandas as pd
from io import StringIO
from pathlib import Path
import pygame
import time
import os
import config_handler
import vdj_updater
from batch_audio_processor import process_audio_file

class ConsoleRedirect:
    """Redirects stdout to the GUI console"""
    def __init__(self, text_widget):
        self.text_widget = text_widget
        self.buffer = StringIO()
        
    def write(self, string):
        # Insert text at the end
        self.text_widget.insert(tk.END, string)
        
        # Add padding mark at the very end if not already there
        if not hasattr(self, '_padding_added'):
            self.text_widget.insert(tk.END, '\n' * 5)  # Add 5 blank lines as padding
            self._padding_added = True
        
        # Auto-scroll to show the new content with padding visible below
        self.text_widget.see(tk.END)
        
        # Scroll up a bit to show some of the padding below the text
        try:
            self.text_widget.yview_scroll(-3, 'units')
        except:
            pass
            
        self.text_widget.update_idletasks()
        
    def flush(self):
        pass

class MusicPlayer(tk.Frame):
    """A compact, modern music player widget - all controls on one line"""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        
        # Initialize pygame mixer
        pygame.mixer.init()
        
        # Player state
        self.current_file = None
        self.is_playing = False
        self.is_paused = False
        self.volume = 0.7  # Default volume (0.0 to 1.0)
        self.saved_volume = 0.7  # Volume before mute
        self.is_muted = False
        self.position = 0  # Current position in seconds
        self.duration = 0  # Total duration in seconds
        self.update_thread = None
        self.stop_update = False
        
        # Modern color scheme
        self.colors = {
            'bg': '#ffffff',
            'bg_alt': '#f8f9fa',
            'text': '#212529',
            'text_secondary': '#6c757d',
            'primary': '#FF8C42',
            'primary_hover': '#FF6B1A',
            'success': '#198754',
            'success_hover': '#157347',
            'danger': '#dc3545',
            'danger_hover': '#bb2d3b',
            'border': '#dee2e6',
            'slider_bg': '#e9ecef',  # Gray background for slider track
            'slider_normal': '#FF8C42',  # Light orange for slider thumb (not hovered)
            'slider_active': '#FF6B1A',  # Darker orange for slider thumb (hovered/active)
        }
        
        self.configure(bg=self.colors['bg'], height=50)
        self.create_widgets()
        
    def create_widgets(self):
        """Create a compact single-line player UI"""
        # Main container with subtle border
        main_frame = tk.Frame(
            self, 
            bg=self.colors['bg'],
            highlightthickness=1,
            highlightbackground=self.colors['border'],
            relief=tk.FLAT
        )
        main_frame.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        
        # Single horizontal row for all controls
        controls_row = tk.Frame(main_frame, bg=self.colors['bg'])
        controls_row.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)
        
        # Play/Pause button (circular style)
        self.play_button = tk.Button(
            controls_row,
            text="▶",
            command=self.toggle_play_pause,
            bg=self.colors['primary'],
            fg='white',
            font=('Segoe UI', 9, 'bold'),
            relief=tk.FLAT,
            cursor='hand2',
            width=2,
            height=0,
            bd=0,
            padx=2,
            pady=0
        )
        self.play_button.pack(side=tk.LEFT, padx=(0, 8))
        self._add_hover(self.play_button, self.colors['primary'], self.colors['primary_hover'])
        
        self.position_var = tk.DoubleVar(value=0)
        self.position_slider = tk.Scale(
            controls_row,
            from_=0,
            to=100,
            orient=tk.HORIZONTAL,
            variable=self.position_var,
            command=self.on_position_change,
            bg=self.colors['bg'],
            fg=self.colors['text'],
            highlightthickness=0,
            troughcolor=self.colors['slider_bg'],  # Gray background
            background=self.colors['slider_normal'],  # Light orange when not hovered
            activebackground=self.colors['slider_active'],  # Darker orange when hovered/active
            length=100,  
            sliderlength=15, 
            sliderrelief=tk.FLAT,
            borderwidth=0,
            width=12, 
            showvalue=0
        )
        self.position_slider.pack(side=tk.LEFT, padx=(0, 6))
        
        # Time label (compact)
        self.time_label = tk.Label(
            controls_row,
            text="0:00 / 0:00",
            bg=self.colors['bg'],
            fg=self.colors['text_secondary'],
            font=('Segoe UI', 8),
            width=10,
            anchor='w'
        )
        self.time_label.pack(side=tk.LEFT, padx=(0, 10))
        
        # Volume icon and slider (compact)
        volume_container = tk.Frame(controls_row, bg=self.colors['bg'])
        volume_container.pack(side=tk.LEFT, padx=(0, 6))
        
        # Clickable volume icon with mute overlay
        self.volume_icon_frame = tk.Frame(volume_container, bg=self.colors['bg'], cursor='hand2')
        self.volume_icon_frame.pack(side=tk.LEFT, padx=(0, 4))
        
        self.volume_icon = tk.Label(
            self.volume_icon_frame,
            text="🔊",
            bg=self.colors['bg'],
            font=('Segoe UI', 10)
        )
        self.volume_icon.pack()
        
        # Mute overlay (X symbol) - hidden by default
        self.mute_overlay = tk.Label(
            self.volume_icon_frame,
            text="🔇",
            # bg=self.colors['bg'],
            fg=self.colors['danger'],
            font=('Segoe UI', 12, 'bold')
        )
        self.mute_overlay.place(relx=0.5, rely=0.5, anchor='center')
        self.mute_overlay.place_forget()  # Hide initially
        
        # Bind click event to toggle mute
        self.volume_icon_frame.bind('<Button-1>', lambda e: self.toggle_mute())
        self.volume_icon.bind('<Button-1>', lambda e: self.toggle_mute())
        self.mute_overlay.bind('<Button-1>', lambda e: self.toggle_mute())
        
        self.volume_var = tk.DoubleVar(value=self.volume * 100)
        self.volume_slider = tk.Scale(
            volume_container,
            from_=0,
            to=100,
            orient=tk.HORIZONTAL,
            variable=self.volume_var,
            command=self.on_volume_change,
            bg=self.colors['bg'],
            highlightthickness=0,
            troughcolor=self.colors['slider_bg'],  # Gray background
            background=self.colors['slider_normal'],  # Light orange when not hovered
            activebackground=self.colors['slider_active'],  # Darker orange when hovered/active
            length=72,  # 20% longer: 60 * 1.2 = 72
            sliderrelief=tk.FLAT,
            borderwidth=0,
            width=12,  # Increased slider bar width
            sliderlength=15,
            showvalue=0
        )
        self.volume_slider.pack(side=tk.LEFT)
        
        self.volume_label = tk.Label(
            volume_container,
            text="70%",
            bg=self.colors['bg'],
            fg=self.colors['text_secondary'],
            font=('Segoe UI', 8),
            width=4,
            anchor='w'
        )
        self.volume_label.pack(side=tk.LEFT, padx=(4, 0))
        
        # File name label (truncated, on the right)
        self.file_label = tk.Label(
            controls_row,
            text="No file loaded",
            bg=self.colors['bg'],
            fg=self.colors['text'],
            font=('Segoe UI', 8),
            anchor='w',
            width=30
        )
        self.file_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 0))
    
    def _add_hover(self, button, normal_color, hover_color):
        """Add smooth hover effect to button"""
        def on_enter(e):
            button.config(bg=hover_color)
        def on_leave(e):
            button.config(bg=normal_color)
        button.bind('<Enter>', on_enter)
        button.bind('<Leave>', on_leave)
    
    def toggle_mute(self):
        """Toggle mute on/off"""
        if self.is_muted:
            # Unmute: restore saved volume
            self.is_muted = False
            self.volume = self.saved_volume
            pygame.mixer.music.set_volume(self.volume)
            self.volume_var.set(self.volume * 100)
            self.volume_label.config(text=f"{int(self.volume * 100)}%")
            self.mute_overlay.place_forget()
        else:
            # Mute: save current volume and set to 0
            if self.volume > 0:
                self.saved_volume = self.volume
            self.is_muted = True
            pygame.mixer.music.set_volume(0.0)
            self.mute_overlay.place(relx=0.5, rely=0.5, anchor='center')
    
    def unload_file(self):
        """Unload the current file to release file handle"""
        try:
            if self.is_playing or self.is_paused:
                pygame.mixer.music.stop()
            pygame.mixer.music.unload()  # Unload the current music
            self.is_playing = False
            self.is_paused = False
            self.position = 0
            self.position_var.set(0)
            self.play_button.config(text="▶")
            self.stop_update = True
            # Clear the current file reference
            self.current_file = None
            # Force garbage collection to release file handles
            import gc
            gc.collect()
        except Exception as e:
            print(f"Error unloading file: {str(e)}")
    
    def load_file(self, file_path):
        """Load an audio file for playback"""
        if not file_path or not Path(file_path).exists():
            return
        
        # Unload current file first to release file handle
        self.unload_file()
        
        self.current_file = Path(file_path)
        # Truncate filename if too long
        filename = self.current_file.name
        if len(filename) > 35:
            filename = filename[:32] + "..."
        self.file_label.config(text=filename, fg=self.colors['text'])
        
        # Load the file
        try:
            pygame.mixer.music.load(str(self.current_file))
            # Get duration using mutagen
            from mutagen import File as MutagenFile
            audio_file = MutagenFile(self.current_file)
            if audio_file:
                self.duration = audio_file.info.length if hasattr(audio_file.info, 'length') else 0
            else:
                self.duration = 0
            
            # Update position slider max
            self.position_slider.config(to=max(1, int(self.duration)))
            self.position = 0
            self.position_var.set(0)
            self.update_time_label()
        except Exception as e:
            self.file_label.config(text=f"Error: {str(e)[:30]}", fg=self.colors['danger'])
    
    def toggle_play_pause(self):
        """Toggle between play and pause"""
        if not self.current_file:
            return
        
        if not self.is_playing:
            self.play()
        else:
            self.pause()
    
    def play(self):
        """Start or resume playback"""
        if not self.current_file:
            return
        
        try:
            if self.is_paused:
                pygame.mixer.music.unpause()
            else:
                if self.position > 0:
                    pygame.mixer.music.play(start=self.position)
                else:
                    pygame.mixer.music.play()
            
            self.is_playing = True
            self.is_paused = False
            self.play_button.config(text="⏸")
            
            # Start position update thread
            if self.update_thread is None or not self.update_thread.is_alive():
                self.stop_update = False
                self.update_thread = threading.Thread(target=self.update_position, daemon=True)
                self.update_thread.start()
        except Exception as e:
            self.file_label.config(text=f"Error: {str(e)[:30]}", fg=self.colors['danger'])
    
    def pause(self):
        """Pause playback"""
        pygame.mixer.music.pause()
        self.is_playing = False
        self.is_paused = True
        self.play_button.config(text="▶")
    
    def stop(self):
        """Stop playback"""
        pygame.mixer.music.stop()
        self.is_playing = False
        self.is_paused = False
        self.position = 0
        self.position_var.set(0)
        self.play_button.config(text="▶")
        self.update_time_label()
        self.stop_update = True
    
    def on_volume_change(self, value):
        """Handle volume slider change"""
        if not self.is_muted:
            self.volume = float(value) / 100.0
            self.saved_volume = self.volume
            pygame.mixer.music.set_volume(self.volume)
            self.volume_label.config(text=f"{int(self.volume * 100)}%")
        else:
            # If muted, update saved volume but don't change actual volume
            self.saved_volume = float(value) / 100.0
            self.volume_var.set(self.saved_volume * 100)
            self.volume_label.config(text=f"{int(self.saved_volume * 100)}%")
    
    def on_position_change(self, value):
        """Handle position slider change (seeking)"""
        if not self.is_playing and not self.is_paused:
            return
        
        new_position = float(value)
        if abs(new_position - self.position) > 1:  # Only seek if difference is significant
            self.position = new_position
            try:
                pygame.mixer.music.stop()
                pygame.mixer.music.load(str(self.current_file))
                pygame.mixer.music.play(start=self.position)
                self.is_playing = True
                self.is_paused = False
                self.play_button.config(text="⏸")
            except Exception as e:
                print(f"Error seeking: {str(e)}")
    
    def update_position(self):
        """Update position slider and time label while playing"""
        while not self.stop_update and (self.is_playing or self.is_paused):
            if self.is_playing and pygame.mixer.music.get_busy():
                time.sleep(0.1)
                self.position += 0.1
                if self.position > self.duration:
                    self.position = self.duration
                    self.stop()
                    break
                
                # Update UI in main thread
                self.after(0, self._update_ui)
            elif not pygame.mixer.music.get_busy() and self.is_playing:
                # Song ended
                self.after(0, self.stop)
                break
            else:
                time.sleep(0.1)
    
    def _update_ui(self):
        """Update UI elements (called from main thread)"""
        if not self.stop_update:
            self.position_var.set(self.position)
            self.update_time_label()
    
    def update_time_label(self):
        """Update the time display label"""
        current_time = self.format_time(self.position)
        total_time = self.format_time(self.duration)
        self.time_label.config(text=f"{current_time} / {total_time}")
    
    def format_time(self, seconds):
        """Format seconds as MM:SS"""
        if seconds < 0:
            seconds = 0
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins}:{secs:02d}"
    
    def cleanup(self):
        """Clean up resources"""
        self.stop_update = True
        self.unload_file()
        pygame.mixer.quit()

class ArtistSelectorDropdown(tk.Frame):
    """A modern dropdown widget for selecting multiple artists with checkboxes"""
    
    def __init__(self, parent, artists, **kwargs):
        """
        Parameters:
        -----------
        parent : tk widget
            Parent widget
        artists : list or dict
            List of artist names or dict of artist data
        """
        super().__init__(parent, **kwargs)
        
        # Extract artist names if dict is provided
        if isinstance(artists, dict):
            self.artists = list(artists.keys())
        else:
            self.artists = list(artists) if artists else []  # Handle None case

        # Store selection state
        self.artist_vars = {}
        self.is_expanded = False
        
        # Colors
        self.colors = {
            'bg': '#ffffff',
            'border': '#e0e0e0',
            'hover': '#f5f5f5',
            'primary': '#007acc',
            'text': '#333333'
        }
        
        self.configure(bg=self.colors['bg'])
        
        # Only create widgets if we have artists
        if self.artists:
            self.create_widgets()
        
    def create_widgets(self):
        # Main container
        self.main_frame = tk.Frame(self, bg=self.colors['bg'], 
                                   highlightthickness=1,
                                   highlightbackground=self.colors['border'])
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Header (clickable to expand/collapse)
        self.header = tk.Frame(self.main_frame, bg=self.colors['bg'], cursor='hand2')
        self.header.pack(fill=tk.X, padx=5, pady=5)
        
        # Selected count label
        self.count_label = tk.Label(self.header, 
                                    text="Select Artists (0 selected)",
                                    font=('Segoe UI', 10),
                                    bg=self.colors['bg'],
                                    fg=self.colors['text'],
                                    anchor='w')
        self.count_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Dropdown arrow
        self.arrow_label = tk.Label(self.header, text="▼",
                                    font=('Segoe UI', 8),
                                    bg=self.colors['bg'],
                                    fg=self.colors['text'])
        self.arrow_label.pack(side=tk.RIGHT, padx=5)
        
        # Bind click events to header
        self.header.bind('<Button-1>', lambda e: self.toggle_dropdown())
        self.count_label.bind('<Button-1>', lambda e: self.toggle_dropdown())
        self.arrow_label.bind('<Button-1>', lambda e: self.toggle_dropdown())
        
        # Dropdown content (hidden by default)
        self.dropdown_frame = tk.Frame(self.main_frame, bg=self.colors['bg'])
        
        # Control buttons frame
        controls_frame = tk.Frame(self.dropdown_frame, bg=self.colors['bg'])
        controls_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Select All button
        select_all_btn = tk.Button(controls_frame, text="Select All",
                                   command=self.select_all,
                                   bg=self.colors['primary'], fg='white',
                                   font=('Segoe UI', 9),
                                   relief=tk.FLAT, cursor='hand2',
                                   padx=10, pady=5)
        select_all_btn.pack(side=tk.LEFT, padx=(0, 5))
        self._add_hover(select_all_btn, self.colors['primary'], '#005a9e')
        
        # Deselect All button
        deselect_all_btn = tk.Button(controls_frame, text="Deselect All",
                                     command=self.deselect_all,
                                     bg='#6c757d', fg='white',
                                     font=('Segoe UI', 9),
                                     relief=tk.FLAT, cursor='hand2',
                                     padx=10, pady=5)
        deselect_all_btn.pack(side=tk.LEFT)
        self._add_hover(deselect_all_btn, '#6c757d', '#5a6268')
        
        # Scrollable artist list
        canvas_frame = tk.Frame(self.dropdown_frame, bg=self.colors['bg'],
                               highlightthickness=1,
                               highlightbackground=self.colors['border'])
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=(0, 5))
        
        # Canvas and scrollbar
        self.canvas = tk.Canvas(canvas_frame, bg=self.colors['bg'],
                               highlightthickness=0, height=200)
        scrollbar = ttk.Scrollbar(canvas_frame, orient='vertical', 
                                 command=self.canvas.yview)
        
        self.scrollable_frame = tk.Frame(self.canvas, bg=self.colors['bg'])
        self.scrollable_frame.bind(
            '<Configure>',
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox('all'))
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor='nw')
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Add checkboxes for each artist
        for artist in sorted(self.artists):
            self._create_artist_checkbox(artist)
        
        # Enable mouse wheel scrolling
        self.canvas.bind_all('<MouseWheel>', self._on_mousewheel)
        
    def _create_artist_checkbox(self, artist):
        """Create a checkbox for an artist"""
        var = tk.BooleanVar(value=False)
        self.artist_vars[artist] = var
        
        frame = tk.Frame(self.scrollable_frame, bg=self.colors['bg'])
        frame.pack(fill=tk.X, padx=5, pady=2, anchor='w')
        
        # Add hover effect to frame
        frame.bind('<Enter>', lambda e: frame.config(bg=self.colors['hover']))
        frame.bind('<Leave>', lambda e: frame.config(bg=self.colors['bg']))
        
        cb = tk.Checkbutton(frame, text=artist, variable=var,
                           bg=self.colors['bg'], fg=self.colors['text'],
                           font=('Segoe UI', 9),
                           activebackground=self.colors['hover'],
                           selectcolor='white',
                           relief=tk.FLAT,
                           anchor='w',
                           command=self.update_count)
        cb.pack(side=tk.LEFT, padx=5, pady=2)
        
        # Make frame clickable too
        frame.bind('<Button-1>', lambda e, v=var: self._toggle_checkbox(v))
        
    def _toggle_checkbox(self, var):
        """Toggle checkbox value when frame is clicked"""
        var.set(not var.get())
        self.update_count()
        
    def _add_hover(self, button, normal_color, hover_color):
        """Add hover effect to button"""
        button.bind('<Enter>', lambda e: button.config(bg=hover_color))
        button.bind('<Leave>', lambda e: button.config(bg=normal_color))
        
    def _on_mousewheel(self, event):
        """Handle mouse wheel scrolling"""
        if self.is_expanded:
            self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
    def toggle_dropdown(self):
        """Expand or collapse the dropdown"""
        if self.is_expanded:
            self.dropdown_frame.pack_forget()
            self.arrow_label.config(text="▼")
            self.is_expanded = False
        else:
            self.dropdown_frame.pack(fill=tk.BOTH, expand=True)
            self.arrow_label.config(text="▲")
            self.is_expanded = True
            
    def select_all(self):
        """Select all artists"""
        for var in self.artist_vars.values():
            var.set(True)
        self.update_count()
        
    def deselect_all(self):
        """Deselect all artists"""
        for var in self.artist_vars.values():
            var.set(False)
        self.update_count()
        
    def update_count(self):
        """Update the selected count label"""
        selected_count = sum(var.get() for var in self.artist_vars.values())
        total_count = len(self.artist_vars)
        self.count_label.config(text=f"Select Artists ({selected_count}/{total_count} selected)")
        
    def get_selected_artists(self):
        """Return list of selected artist names"""
        return [artist for artist, var in self.artist_vars.items() if var.get()]
    
    def set_selected_artists(self, artist_list):
        """Set which artists are selected"""
        for artist, var in self.artist_vars.items():
            var.set(artist in artist_list)
        self.update_count()


class AudioProcessingDropdown(tk.Frame):
    """A dropdown widget for audio processing options"""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        
        # Store selection state
        self.is_expanded = False
        
        # Colors
        self.colors = {
            'bg': '#ffffff',
            'border': '#e0e0e0',
            'hover': '#f5f5f5',
            'primary': '#007acc',
            'text': '#333333'
        }
        
        self.configure(bg=self.colors['bg'])
        self.create_widgets()
    
    def create_widgets(self):
        # Main container
        self.main_frame = tk.Frame(self, bg=self.colors['bg'], 
                                   highlightthickness=1,
                                   highlightbackground=self.colors['border'])
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Header (clickable to expand/collapse)
        self.header = tk.Frame(self.main_frame, bg=self.colors['bg'], cursor='hand2')
        self.header.pack(fill=tk.X, padx=5, pady=5)
        
        # Title label
        self.title_label = tk.Label(self.header, 
                                    text="Audio Processing Options",
                                    font=('Segoe UI', 10),
                                    bg=self.colors['bg'],
                                    fg=self.colors['text'],
                                    anchor='w')
        self.title_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Dropdown arrow
        self.arrow_label = tk.Label(self.header, text="▼",
                                    font=('Segoe UI', 8),
                                    bg=self.colors['bg'],
                                    fg=self.colors['text'])
        self.arrow_label.pack(side=tk.RIGHT, padx=5)
        
        # Bind click events to header
        self.header.bind('<Button-1>', lambda e: self.toggle_dropdown())
        self.title_label.bind('<Button-1>', lambda e: self.toggle_dropdown())
        self.arrow_label.bind('<Button-1>', lambda e: self.toggle_dropdown())
        
        # Dropdown content (hidden by default)
        self.dropdown_frame = tk.Frame(self.main_frame, bg=self.colors['bg'])
    
    def add_checkbox(self, text, variable, row, column):
        """Add a checkbox to the dropdown frame"""
        cb = ttk.Checkbutton(
            self.dropdown_frame,
            text=text,
            variable=variable
        )
        cb.grid(row=row, column=column, sticky=tk.W, padx=5, pady=2)
        return cb
    
    def add_label_entry(self, text, variable, row):
        """Add a label and entry field to the dropdown frame"""
        label = ttk.Label(self.dropdown_frame, text=text)
        label.grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        
        entry = ttk.Entry(self.dropdown_frame, textvariable=variable, width=10)
        entry.grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)
        return entry
    
    def toggle_dropdown(self):
        """Expand or collapse the dropdown"""
        if self.is_expanded:
            self.dropdown_frame.pack_forget()
            self.arrow_label.config(text="▼")
            self.is_expanded = False
        else:
            self.dropdown_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            self.arrow_label.config(text="▲")
            self.is_expanded = True


class ToolGUI:
    def __init__(self, root, artists=None, metadata_dict:dict={}):
        self.root = root
        self.root.title("Tool Interface")
        self.root.geometry("700x850")  # Increased height for player
        
        # Variables
        self.folder_path = tk.StringVar()
        self.folder_paths = []  # List of folder paths for multiple folder processing
        self.start_year = tk.StringVar(value="1900")
        self.end_year = tk.StringVar(value="2050")
        self.filename_format = tk.StringVar(value="orchestra last - title - singer last - year")  # Default format
        self.input_var = tk.StringVar()
        self.waiting_for_input = False
        self.input_result = None
        
        # Virtual DJ database linking
        self.link_database = tk.BooleanVar()
        self.vdj_database_path = tk.StringVar()
        
        # Audio processing options
        self.convert_aflac_to_flac = tk.BooleanVar(value=False)
        self.convert_to_mono = tk.BooleanVar(value=False)
        self.convert_to_48khz = tk.BooleanVar(value=False)
        self.use_24bit = tk.BooleanVar(value=False)
        self.normalize_audio = tk.BooleanVar(value=False)
        self.aufs_target = tk.StringVar(value="-13.0")  # Default AUFS target
        
        # Output folder for processed audio files
        self.output_folder_path = tk.StringVar()
        self.output_structure = tk.StringVar(value="preserve")  # "preserve" or "by_artist"
        
        # Auto-select option
        self.auto_select = tk.BooleanVar(value=False)
        
        # Undo history - stack of operations that can be undone
        self.undo_history = []  # List of dicts with: original_path, new_path, chosen_idx, catalogue, audio_folder
        
        # Load saved config (will be loaded after widgets are created)
        self.artists = artists
        self.metadata_dict = metadata_dict
        self.current_audio_file = None  # Track current file being processed
        
        # Create GUI elements
        self.create_widgets()
        
        # Load saved settings after widgets are created
        self.load_all_settings()
        
        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
    def on_closing(self):
        """Handle window closing"""
        # Save all settings before closing
        self.save_all_settings()
        if hasattr(self, 'music_player'):
            self.music_player.cleanup()
        self.root.destroy()
        
    def create_widgets(self):
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(6, weight=1)  # Console row
        
        # Top row: Settings and Audio Processing dropdowns
        top_row_frame = ttk.Frame(main_frame)
        top_row_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        top_row_frame.columnconfigure(0, weight=1)
        top_row_frame.columnconfigure(1, weight=1)
        
        # Settings dropdown (left side)
        self.settings_dropdown = AudioProcessingDropdown(top_row_frame)
        self.settings_dropdown.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5))
        self.settings_dropdown.title_label.config(text="Settings")
        
        # Auto-select checkbox in settings dropdown
        ttk.Checkbutton(
            self.settings_dropdown.dropdown_frame,
            text="Auto-select single match",
            variable=self.auto_select
        ).grid(row=0, column=0, columnspan=3, sticky=tk.W, padx=5, pady=2)
        
        # Filename format in settings dropdown
        ttk.Label(self.settings_dropdown.dropdown_frame, text="Filename Format:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        format_options = [
            "title - orchestra last - singer last - year",
            "title - orchestra last - year",
            "title - orchestra - year",
            "orchestra last - title - singer last - year",
            "orchestra last - singer last - title - year",
            "orchestra last - title - year",
            "orchestra - title - singer last - year",
            "orchestra - title - year",
        ]
        format_dropdown = ttk.Combobox(
            self.settings_dropdown.dropdown_frame,
            textvariable=self.filename_format,
            values=format_options,
            state="readonly",
            width=50
        )
        format_dropdown.grid(row=1, column=1, columnspan=2, sticky=(tk.W, tk.E), padx=5, pady=2)
        
        # Update metadata button in settings dropdown
        ttk.Button(
            self.settings_dropdown.dropdown_frame,
            text="Update Metadata",
            command=self.update_metadata
        ).grid(row=2, column=0, columnspan=3, sticky=tk.W, padx=5, pady=5)
        
        # Virtual DJ Database Linking in settings dropdown
        vdj_checkbox = ttk.Checkbutton(
            self.settings_dropdown.dropdown_frame,
            text="Link Virtual DJ Database",
            variable=self.link_database,
            command=self.on_link_database_toggle
        )
        vdj_checkbox.grid(row=3, column=0, columnspan=3, sticky=tk.W, padx=5, pady=2)
        
        # Database path frame in settings dropdown
        db_path_frame = ttk.Frame(self.settings_dropdown.dropdown_frame)
        db_path_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), padx=5, pady=2)
        db_path_frame.columnconfigure(0, weight=1)
        
        ttk.Entry(db_path_frame, textvariable=self.vdj_database_path, state='readonly').grid(
            row=0, column=0, sticky=(tk.W, tk.E), padx=(5, 5)
        )
        ttk.Button(
            db_path_frame,
            text="Browse",
            command=self.browse_vdj_database
        ).grid(row=0, column=1, padx=(0, 5))
        
        
        # Audio Processing dropdown (right side)
        self.audio_processing_dropdown = AudioProcessingDropdown(top_row_frame)
        self.audio_processing_dropdown.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(5, 0))
        self.audio_processing_dropdown.title_label.config(text="Audio Processing Options")
        
        # Add checkboxes to audio processing dropdown
        self.audio_processing_dropdown.add_checkbox(
            "Convert AFLAC to FLAC", self.convert_aflac_to_flac, 0, 0
        )
        self.audio_processing_dropdown.add_checkbox(
            "Sum to Mono", self.convert_to_mono, 0, 1
        )
        self.audio_processing_dropdown.add_checkbox(
            "Convert to 48kHz", self.convert_to_48khz, 1, 0
        )
        self.audio_processing_dropdown.add_checkbox(
            "Use 24-bit Depth", self.use_24bit, 1, 1
        )
        self.audio_processing_dropdown.add_checkbox(
            "Normalize Audio", self.normalize_audio, 2, 0
        )
        
        # AUFS target input in audio processing dropdown
        ttk.Label(self.audio_processing_dropdown.dropdown_frame, text="AUFS Target:").grid(row=2, column=1, sticky=tk.W, padx=(5, 5), pady=2)
        ttk.Entry(self.audio_processing_dropdown.dropdown_frame, textvariable=self.aufs_target, width=10).grid(row=2, column=2, sticky=tk.W, padx=5, pady=2)
        
        # Folder selection with output folder on same row (row 1)
        ttk.Label(main_frame, text="Input Folder:").grid(row=1, column=0, sticky=tk.W, pady=5)
        folder_frame = ttk.Frame(main_frame)
        folder_frame.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=5)
        folder_frame.columnconfigure(0, weight=1)
        folder_frame.columnconfigure(3, weight=1)
        
        # Input folder
        ttk.Entry(folder_frame, textvariable=self.folder_path, width=25).grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5))
        ttk.Button(folder_frame, text="Browse", command=self.browse_folder).grid(row=0, column=1, padx=(0, 10))
        
        # Output folder on same row
        ttk.Label(folder_frame, text="Output:").grid(row=0, column=2, padx=(0, 5))
        ttk.Entry(folder_frame, textvariable=self.output_folder_path, width=25).grid(row=0, column=3, sticky=(tk.W, tk.E), padx=(0, 5))
        ttk.Button(folder_frame, text="Browse", command=self.browse_output_folder).grid(row=0, column=4)
        
        # Output structure option
        ttk.Label(folder_frame, text="Structure:").grid(row=0, column=5, padx=(10, 5))
        structure_dropdown = ttk.Combobox(
            folder_frame,
            textvariable=self.output_structure,
            values=["Preserve Subfolders", "By Artist"],
            state="readonly",
            width=15
        )
        structure_dropdown.grid(row=0, column=6, padx=(0, 5))
        
        # Multiple folders button
        ttk.Button(folder_frame, text="Add Folders", command=self.browse_multiple_folders).grid(row=0, column=7, padx=(0, 5))
        
        # Folder list display
        self.folder_listbox = None  # Will be created if needed
        
        # Start year and End year in main area (row 2)
        ttk.Label(main_frame, text="Start Year:").grid(row=2, column=0, sticky=tk.W, pady=5)
        year_frame = ttk.Frame(main_frame)
        year_frame.grid(row=2, column=1, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Entry(year_frame, textvariable=self.start_year, width=15).grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        ttk.Label(year_frame, text="End Year:").grid(row=0, column=1, sticky=tk.W, padx=(0, 5))
        ttk.Entry(year_frame, textvariable=self.end_year, width=15).grid(row=0, column=2, sticky=tk.W)
        
        # Artist selector (row 3)
        ttk.Label(main_frame, text="Artists:").grid(row=3, column=0, sticky=(tk.W, tk.N), pady=5)
        self.artist_selector = ArtistSelectorDropdown(main_frame, self.artists)
        self.artist_selector.grid(row=3, column=1, sticky=(tk.W, tk.E), pady=5)
        
        player_frame = ttk.LabelFrame(main_frame, text="Music Player", padding="5")
        player_frame.grid(row=4, column=1, sticky=(tk.W, tk.E), pady=5)
        player_frame.columnconfigure(0, weight=1)
        
        self.music_player = MusicPlayer(player_frame)
        self.music_player.pack(fill=tk.BOTH, expand=True)
        
        # Run button and Undo button (row 5) - centered
        run_button_frame = ttk.Frame(main_frame)
        run_button_frame.grid(row=5, column=0, columnspan=2, pady=10, sticky=(tk.W, tk.E))
        run_button_frame.columnconfigure(0, weight=1)
        
        self.run_button = ttk.Button(run_button_frame, text="Run TigerTag", command=self.run_tag_updater)
        self.run_button.grid(row=0, column=0)
        
        # Undo button
        self.undo_button = ttk.Button(run_button_frame, text="Undo Last", command=self.undo_last_operation, state='disabled')
        self.undo_button.grid(row=0, column=1, padx=(10, 0))
        
        # Progress bar and counter - smaller, on same row as buttons
        progress_frame = ttk.Frame(run_button_frame)
        progress_frame.grid(row=0, column=2, sticky=(tk.W, tk.E), padx=(20, 0))
        progress_frame.columnconfigure(0, weight=1)
        
        self.progress_bar = ttk.Progressbar(progress_frame, mode='determinate', length=150)
        self.progress_bar.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5))
        
        self.progress_counter = ttk.Label(progress_frame, text="0/0", font=("", 9))
        self.progress_counter.grid(row=0, column=1, sticky=tk.E)
        
        console_frame = ttk.LabelFrame(main_frame, text="Console Output", padding="5")
        console_frame.grid(row=6, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        console_frame.columnconfigure(0, weight=1)
        console_frame.rowconfigure(0, weight=1)
        
        # Add padding frame around console
        console_padding = ttk.Frame(console_frame, padding="5")
        console_padding.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        console_padding.columnconfigure(0, weight=1)
        console_padding.rowconfigure(0, weight=1)
        
        self.console = scrolledtext.ScrolledText(
            console_padding, 
            wrap=tk.WORD, 
            height=15, 
            bg="#1e1e1e", 
            fg="#d4d4d4", 
            font=("Consolas", 10),
            padx=10,
            pady=10
        )
        self.console.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure color tags for the console
        self.console.tag_config("cyan", foreground="#00FFFF")
        self.console.tag_config("green", foreground="#00FF00")
        self.console.tag_config("yellow", foreground="#FFFF00")
        self.console.tag_config("red", foreground="#FF0000")
        self.console.tag_config("blue", foreground="#5555FF")
        self.console.tag_config("magenta", foreground="#FF00FF")
        self.console.tag_config("bold", font=("Consolas", 10, "bold"))
        
        # Input area (visible by default)
        self.input_frame = ttk.Frame(main_frame)
        self.input_frame.grid(row=7, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        self.input_frame.columnconfigure(1, weight=1)
        
        ttk.Label(self.input_frame, text="Input:").grid(row=0, column=0, sticky=tk.W)
        self.input_entry = ttk.Entry(self.input_frame, textvariable=self.input_var)
        self.input_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)
        ttk.Button(self.input_frame, text="Submit", command=self.submit_input).grid(row=0, column=2)
        
        # Bind Enter key to submit
        self.input_entry.bind('<Return>', lambda e: self.submit_input())
    
    def load_vdj_config(self):
        """Load Virtual DJ database settings from config."""
        self.link_database.set(config_handler.is_link_database_enabled())
        vdj_path = config_handler.get_vdj_database_path()
        if vdj_path:
            self.vdj_database_path.set(vdj_path)
    
    def load_all_settings(self):
        """Load all settings from config file."""
        # Load folder paths
        folder_paths = config_handler.get_folder_paths()
        if folder_paths:
            self.folder_paths = folder_paths
            if len(folder_paths) == 1:
                self.folder_path.set(folder_paths[0])
            elif len(folder_paths) > 1:
                self.folder_path.set(f"{len(folder_paths)} folders selected")
        
        # Load output folder
        output_folder = config_handler.get_output_folder_path()
        if output_folder:
            self.output_folder_path.set(output_folder)
        
        # Load years
        self.start_year.set(config_handler.get_start_year())
        self.end_year.set(config_handler.get_end_year())
        
        # Load filename format
        self.filename_format.set(config_handler.get_filename_format())
        
        # Load audio processing settings
        audio_settings = config_handler.get_audio_processing_settings()
        self.convert_aflac_to_flac.set(audio_settings.get("convert_aflac_to_flac", False))
        self.convert_to_mono.set(audio_settings.get("convert_to_mono", False))
        self.convert_to_48khz.set(audio_settings.get("convert_to_48khz", False))
        self.use_24bit.set(audio_settings.get("use_24bit", False))
        self.normalize_audio.set(audio_settings.get("normalize_audio", False))
        self.aufs_target.set(audio_settings.get("aufs_target", "-13.0"))
        
        # Load output structure (map from config value to combobox value)
        structure = config_handler.get_output_structure()
        if structure == "by_artist":
            self.output_structure.set("By Artist")
        else:
            self.output_structure.set("Preserve Subfolders")
        
        # Load auto-select
        self.auto_select.set(config_handler.get_auto_select())
        
        # Load selected artists - will be applied after widgets are created
        self._saved_selected_artists = config_handler.get_selected_artists()
    
    def save_all_settings(self):
        """Save all current settings to config file."""
        # Save folder paths
        config_handler.set_folder_paths(self.folder_paths)
        
        # Save output folder
        config_handler.set_output_folder_path(self.output_folder_path.get())
        
        # Save years
        config_handler.set_start_year(self.start_year.get())
        config_handler.set_end_year(self.end_year.get())
        
        # Save filename format
        config_handler.set_filename_format(self.filename_format.get())
        
        # Save audio processing settings
        config_handler.set_audio_processing_settings({
            "convert_aflac_to_flac": self.convert_aflac_to_flac.get(),
            "convert_to_mono": self.convert_to_mono.get(),
            "convert_to_48khz": self.convert_to_48khz.get(),
            "use_24bit": self.use_24bit.get(),
            "normalize_audio": self.normalize_audio.get(),
            "aufs_target": self.aufs_target.get(),
        })
        
        # Save output structure (map from combobox value to config value)
        structure_value = self.output_structure.get()
        if structure_value == "By Artist":
            config_handler.set_output_structure("by_artist")
        else:
            config_handler.set_output_structure("preserve")
        
        # Save auto-select
        config_handler.set_auto_select(self.auto_select.get())
        
        # Save selected artists (if artist_selector exists)
        if hasattr(self, 'artist_selector'):
            selected_artists = self.artist_selector.get_selected_artists()
            config_handler.set_selected_artists(selected_artists)
    
    def on_link_database_toggle(self):
        """Handle link database checkbox toggle."""
        config_handler.set_link_database(self.link_database.get())
    
    def browse_vdj_database(self):
        """Browse for Virtual DJ database XML file."""
        file_path = filedialog.askopenfilename(
            title="Select Virtual DJ Database XML File",
            filetypes=[("XML files", "*.xml"), ("All files", "*.*")]
        )
        if file_path:
            self.vdj_database_path.set(file_path)
            config_handler.set_vdj_database_path(file_path)
    
    def browse_output_folder(self):
        """Browse for output folder for processed audio files."""
        folder = filedialog.askdirectory(title="Select Output Folder for Processed Audio Files")
        if folder:
            self.output_folder_path.set(folder)
    
    def update_metadata(self):
        print("Updating Metadata")
        csv_to_parquet()

    def browse_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.folder_path.set(folder)
            self.folder_paths = [folder]  # Initialize with single folder
            
            # Try to extract years from folder name
            start_year, end_year = parse_years_from_folder(folder)
            
            if start_year is not None:
                self.start_year.set(str(start_year))
                self.end_year.set(str(end_year))
            
            self.save_all_settings()
    
    def browse_multiple_folders(self):
        """Browse for multiple folders to process"""
        folder = filedialog.askdirectory(mustexist=True, title="Add Folder to Process")
        if folder:
            if folder not in self.folder_paths:
                self.folder_paths.append(folder)
            # Update display
            if len(self.folder_paths) > 1:
                self.folder_path.set(f"{len(self.folder_paths)} folders selected")
            else:
                self.folder_path.set(folder)
            self.save_all_settings()
            self.save_all_settings()
            
    def submit_input(self):
        if self.waiting_for_input:
            self.input_result = self.input_var.get()
            self.input_var.set("")
            self.input_frame.grid_remove()
            self.waiting_for_input = False
            
    def custom_input(self, prompt=""):
        """Custom input function that works with the GUI"""
        if prompt:
            self.console.insert(tk.END, prompt)
            self.console.see(tk.END)
            
        self.waiting_for_input = True
        self.input_result = None
        self.input_frame.grid()
        self.input_entry.focus()
        
        # Wait for input
        while self.waiting_for_input:
            self.root.update()
            
        return self.input_result
    
    def run_tag_updater(self):
        # Get folders to process
        folders_to_process = []
        if self.folder_paths:
            folders_to_process = self.folder_paths
        else:
            folder = self.folder_path.get()
            if folder:
                folders_to_process = [folder]
        
        if not folders_to_process:
            self.console.insert(tk.END, "Error: Please select at least one folder\n")
            return
        
        # Require output folder to be specified
        output_folder = self.output_folder_path.get().strip()
        if not output_folder:
            self.console.insert(tk.END, "Error: Please specify an output folder. Original files will not be modified.\n")
            return
            
        try:
            default_start = int(self.start_year.get())
            default_end = int(self.end_year.get())
        except ValueError:
            self.console.insert(tk.END, "Error: Years must be valid integers\n")
            return
        
        # Get selected artists (may be empty for fuzzy matching)
        selected_artists = self.artist_selector.get_selected_artists()
            
        # Clear console and add initial padding
        self.console.delete(1.0, tk.END)
        self.console.insert(tk.END, '\n' * 5)  # Add padding at the end
        self.console.mark_set('padding_start', 'end-6l')  # Mark where padding starts
        
        # Reset progress
        self._total_files_counted = False
        self._current_total = 0
        self._current_index = 0
        self._update_progress(0, 0)
        
        # Disable run button
        self.run_button.config(state='disabled')
        
        # Run in separate thread to keep GUI responsive
        thread = threading.Thread(
            target=self.execute_tag_updater, 
            args=(folders_to_process, self.metadata_dict, default_start, default_end, selected_artists)
        )
        thread.daemon = True
        thread.start()
        
    def execute_tag_updater(self, folders, metadata_dict, default_start_year, default_end_year, selected_artists):
        # Redirect stdout to console
        old_stdout = sys.stdout
        old_input = __builtins__.input
        
        try:
            # Redirect after creating the data
            sys.stdout = ConsoleRedirect(self.console)
            __builtins__.input = self.custom_input
            
            # Count total files across all folders FIRST, before processing
            total_files = 0
            for f in folders:
                folder_path = Path(f)
                if folder_path.exists() and folder_path.is_dir():
                    audio_extensions = ('.mp3', '.flac', '.m4a', '.mp4', '.aif', '.aiff', '.aflac')
                    for ext in audio_extensions:
                        files_lower = list(folder_path.rglob(f'*{ext}'))
                        files_upper = list(folder_path.rglob(f'*{ext.upper()}'))
                        # Count unique files (resolve to handle case-insensitive duplicates)
                        all_files = set([f.resolve() for f in files_lower + files_upper])
                        total_files += len([f for f in all_files if Path(f).is_file()])
            
            # Set total files and initialize progress
            self._current_total = total_files
            self._current_index = 0
            # Use a closure with default argument to capture total_files
            self.root.after(0, lambda t=total_files: self._update_progress(0, t))
            print(f"Found {total_files} audio files to process")
            
            # Process each folder
            all_filename_changes = []
            
            for folder_path in folders:
                folder = Path(folder_path)
                if not folder.exists() or not folder.is_dir():
                    print(f"Warning: Skipping invalid folder: {folder_path}")
                    continue
                
                print(f"\n{'='*80}")
                print(f"Processing folder: {folder}")
                print(f"{'='*80}\n")
                
                # Detect years from folder name
                folder_start_year, folder_end_year = parse_years_from_folder(folder)
                if folder_start_year is None:
                    folder_start_year = default_start_year
                    folder_end_year = default_end_year
                    print(f"Using default years: {folder_start_year}-{folder_end_year}")
                else:
                    print(f"Detected years from folder: {folder_start_year}-{folder_end_year}")
                
                # Determine artists for this folder
                folder_artists = selected_artists.copy() if selected_artists else []
                
                # If no artists selected, do fuzzy matching
                if not folder_artists:
                    print("No artists selected, performing fuzzy matching...")
                    
                    # Extract artist names from folder structure
                    candidate_names = extract_artist_names_from_folder(folder)
                    
                    # Extract artist names from file tags
                    audio_extensions = ('.mp3', '.flac', '.m4a', '.mp4', '.aif', '.aiff', '.aflac')
                    for audio_file in folder.rglob('*'):
                        if audio_file.is_file() and audio_file.suffix.lower() in audio_extensions:
                            try:
                                tagged_artist = extract_artist_from_file_tags(audio_file)
                                if tagged_artist:
                                    candidate_names.add(tagged_artist)
                            except:
                                pass
                    
                    # Fuzzy match against available artists
                    available_artists = list(metadata_dict.keys())
                    if candidate_names:
                        folder_artists = fuzzy_match_artists(candidate_names, available_artists, threshold=70)
                        if len(folder_artists) == 1:
                            # Single artist matched - use only that artist
                            print(f"Fuzzy matched single artist: {folder_artists[0]}")
                        elif len(folder_artists) > 1:
                            print(f"Fuzzy matched artists: {', '.join(folder_artists)}")
                        else:
                            # No artists matched - use all artists (larger subset)
                            print("Warning: No artists matched via fuzzy matching. Using all artists.")
                            folder_artists = available_artists
                    else:
                        print("Warning: No candidate artist names found. Using all artists.")
                        folder_artists = available_artists
                
                # Create metadata subset for this folder
                if folder_artists:
                    metadata_sub = subset_entries(
                        df=pd.concat([metadata_dict[artist] for artist in folder_artists]),
                        start_year=folder_start_year,
                        end_year=folder_end_year,
                    )
                else:
                    print("Warning: No artists available. Skipping folder.")
                    continue
                
                # Use the total files count that was calculated at the start
                total_files = self._current_total
                
                # Process files in this folder
                current_index = len(all_filename_changes)
                # Update current index before processing
                self._current_index = current_index
                folder_changes = self.process_folder(folder, metadata_sub, total_files=total_files, current_index=current_index)
                all_filename_changes.extend(folder_changes)
                # Update current index after processing
                self._current_index = len(all_filename_changes)
                # Update progress bar to final count for this folder
                if total_files:
                    final_idx = len(all_filename_changes)
                    self.root.after(0, lambda idx=final_idx, tot=total_files: self._update_progress(idx, tot))
            
            # Update Virtual DJ database if enabled
            if self.link_database.get() and all_filename_changes:
                vdj_path = self.vdj_database_path.get()
                if vdj_path and Path(vdj_path).exists():
                    print("\n" + "=" * 80)
                    print("Updating Virtual DJ Database...")
                    print("=" * 80)
                    # Note: vdj_updater.update_vdj_database may need to be updated for multiple folders
                    # For now, we'll pass the first folder as reference
                    updated_count, error = vdj_updater.update_vdj_database(
                        vdj_path,
                        all_filename_changes,
                        folders[0] if folders else ""
                    )
                    if error:
                        print(f"Error: {error}")
                    else:
                        print(f"Successfully updated {updated_count} entries in Virtual DJ database.")
                    print("=" * 80 + "\n")
            
            print("\n\n >>> Finished processing all folders! <<< \n\n\n")
            
            # Update progress bar to 100% when done
            if hasattr(self, '_current_total') and self._current_total > 0:
                final_total = self._current_total
                self.root.after(0, lambda t=final_total: self._update_progress(t, t))
            
        except Exception as e:
            if sys.stdout != ConsoleRedirect(self.console):
                sys.stdout = ConsoleRedirect(self.console)
            print(f"\nError: {str(e)}")
            import traceback
            traceback.print_exc()
            
        finally:
            sys.stdout = old_stdout
            __builtins__.input = old_input
            try:
                self.root.after(0, lambda: self.run_button.config(state='normal'))
            except:
                pass
    
    def process_folder(self, audio_folder, catalogue, total_files=None, current_index=0):
        """Process a single folder (including subfolders) and return filename changes"""
        filename_changes = []
        audio_extensions = ('.mp3', '.flac', '.m4a', '.mp4', '.aif', '.aiff', '.aflac')
        
        # Get all audio files recursively
        audio_files = []
        for ext in audio_extensions:
            audio_files.extend(list(audio_folder.rglob(f'*{ext}')))
            audio_files.extend(list(audio_folder.rglob(f'*{ext.upper()}')))
        
        # Remove duplicates (case-insensitive filesystems)
        audio_files = list(set([f.resolve() for f in audio_files]))
        audio_files.sort()
        
        # Filter to only files
        audio_files = [f for f in audio_files if f.is_file()]
        
        file_index = current_index
        
        for audio_file in audio_files:
            # Update progress before processing
            file_index += 1
            if total_files:
                # Update the current index and update progress bar
                self._current_index = file_index
                # Use a closure with default arguments to capture current values correctly
                current_idx = file_index
                current_total = total_files
                self.root.after(0, lambda idx=current_idx, tot=current_total: self._update_progress(idx, tot))
            
            # Store original file location for output structure preservation
            original_file_location = audio_file
            
            # Update player with current file
            self.root.after(0, lambda f=audio_file: self.music_player.load_file(str(f)))
            self.current_audio_file = audio_file
            
            audio_metadata = tag_updater.get_audio_metadata(audio_file)
            # Pass auto_select option to ask_choice
            chosen_idx = tag_updater.ask_choice(
                audio_file.name, 
                audio_metadata, 
                catalogue,
                auto_select=self.auto_select.get()
            )
            
            if chosen_idx != 9999:
                new_metadata = tag_updater.get_updated_metadata(catalogue.loc[chosen_idx].to_dict())
                try:
                    old_filename = audio_file.name
                    old_path_resolved = audio_file.resolve()
                    
                    # Store state for undo before making changes
                    undo_entry = {
                        'original_path': Path(old_path_resolved),
                        'new_path': None,  # Will be set after rename/processing
                        'chosen_idx': chosen_idx,
                        'catalogue': catalogue,
                        'audio_folder': audio_folder,
                        'audio_metadata': audio_metadata.copy(),
                        'output_folder': self.output_folder_path.get().strip(),
                        'process_audio': False,  # Will be set if audio processing happens
                    }
                    
                    # Unload file from player before any file operations
                    self.root.after(0, lambda: self.music_player.unload_file())
                    import time
                    import shutil
                    time.sleep(0.3)
                    
                    # Get output folder - required for copying files (original files are never modified)
                    output_folder = self.output_folder_path.get().strip()
                    if not output_folder:
                        print(f"Error: Output folder required. Skipping {audio_file.name}")
                        continue
                    
                    output_folder_path = Path(output_folder)
                    output_folder_path.mkdir(parents=True, exist_ok=True)
                    
                    # Generate new filename based on metadata (without renaming original)
                    format_type = self.filename_format.get()
                    tag_title = (format_type
                        .replace("orchestra last", new_metadata.orchestra_last_name)
                        .replace("orchestra", new_metadata.orchestra)
                        .replace("singer last", new_metadata.singer_last_name)
                        .replace("title", new_metadata.title)
                        .replace("year", new_metadata.year)
                    )
                    safe_title = slugify_filename(tag_title)
                    new_filename = f"{safe_title}{audio_file.suffix.lower()}"
                    
                    # Determine output path based on structure option
                    structure = self.output_structure.get()
                    
                    if structure == "By Artist":
                        # Create folder by artist name (orchestra)
                        artist_folder = output_folder_path / new_metadata.orchestra
                        artist_folder.mkdir(parents=True, exist_ok=True)
                        output_path = artist_folder / new_filename
                    else:
                        # Preserve subfolder structure
                        try:
                            # Get relative path from the original file location to the root folder
                            relative_to_root = original_file_location.relative_to(audio_folder)
                            # Preserve directory structure in output (use parent directory of relative path)
                            output_path = output_folder_path / relative_to_root.parent / new_filename
                            output_path.parent.mkdir(parents=True, exist_ok=True)
                        except (ValueError, AttributeError):
                            # If relative path calculation fails, just use filename
                            output_path = output_folder_path / new_filename
                    
                    # Handle filename conflicts
                    counter = 1
                    original_output_path = output_path
                    while output_path.exists():
                        stem = original_output_path.stem
                        suffix = original_output_path.suffix
                        output_path = original_output_path.parent / f"{stem} ({counter}){suffix}"
                        counter += 1
                    
                    # Copy original file to output folder with new name (original file is never modified)
                    print(f"\nCopying file: {old_filename} → {output_path.name}")
                    shutil.copy2(audio_file, output_path)
                    print(f"Original file preserved: {audio_file.name}")
                    print(f"Updated file created: {output_path.name}")
                    
                    new_path = output_path
                    new_filename = output_path.name
                    new_path_resolved = output_path.resolve()
                    
                    # Update undo entry with new path
                    if 'undo_entry' in locals():
                        undo_entry['new_path'] = Path(new_path_resolved)
                    
                    filename_changes.append((old_filename, new_filename))
                    
                    # Check if any audio processing options are enabled
                    process_audio = (
                        self.convert_aflac_to_flac.get() or
                        self.convert_to_mono.get() or
                        self.convert_to_48khz.get() or
                        self.use_24bit.get() or
                        self.normalize_audio.get()
                    )
                    
                    # Process audio file if any options are enabled (process the copied file)
                    if process_audio:
                        self.root.after(0, lambda: self.music_player.unload_file())
                        time.sleep(0.3)
                        
                        # Handle AFLAC to FLAC conversion in filename
                        audio_output_path = new_path
                        if self.convert_aflac_to_flac.get() and new_path.suffix.lower() == '.aflac':
                            audio_output_path = new_path.with_suffix('.flac')
                            # Handle conflicts
                            counter = 1
                            original_audio_path = audio_output_path
                            while audio_output_path.exists():
                                stem = original_audio_path.stem
                                suffix = original_audio_path.suffix
                                audio_output_path = original_audio_path.parent / f"{stem} ({counter}){suffix}"
                                counter += 1
                        
                        print(f"\nProcessing audio file: {new_filename}")
                        print(f"Output will be saved to: {audio_output_path}")
                        
                        try:
                            try:
                                aufs_target_value = float(self.aufs_target.get())
                            except (ValueError, TypeError):
                                aufs_target_value = -13.0
                                print(f"  - Warning: Invalid AUFS target, using default: {aufs_target_value}")
                            
                            success = process_audio_file(
                                input_path=new_path,
                                output_path=audio_output_path,
                                target_lufs=aufs_target_value,
                                convert_to_flac=self.convert_aflac_to_flac.get(),
                                convert_to_mono=self.convert_to_mono.get(),
                                convert_to_48khz=self.convert_to_48khz.get(),
                                use_24bit=self.use_24bit.get(),
                                normalize=self.normalize_audio.get()
                            )
                            if success:
                                print(f"✓ Audio processing completed for: {audio_output_path.name}\n")
                                # Update paths to point to processed file
                                new_path = audio_output_path
                                new_filename = audio_output_path.name
                                new_path_resolved = audio_output_path.resolve()
                                # Update filename changes
                                for i, (old, new) in enumerate(filename_changes):
                                    if old == old_filename:
                                        filename_changes[i] = (old, new_filename)
                                        break
                                # Update undo entry
                                if 'undo_entry' in locals():
                                    undo_entry['new_path'] = Path(new_path_resolved)
                                    undo_entry['process_audio'] = True
                            else:
                                print(f"⚠ Audio processing failed for: {new_filename}\n")
                        except Exception as audio_error:
                            print(f"Error processing audio for {new_filename}: {str(audio_error)}")
                            import traceback
                            traceback.print_exc()
                    
                    # Write metadata
                    self.root.after(0, lambda: self.music_player.unload_file())
                    time.sleep(0.2)
                    
                    try:
                        tag_updater.write_metadata(new_path, new_metadata)
                        print(f"Updated metadata for: {new_filename}")
                    except PermissionError as pe:
                        print(f"Permission denied writing metadata for {new_filename}: {str(pe)}")
                        print("File may still be locked. Retrying after delay...")
                        time.sleep(0.5)
                        tag_updater.write_metadata(new_path, new_metadata)
                        print(f"Successfully updated metadata for: {new_filename} on retry")
                    except Exception as meta_error:
                        print(f"Error updating metadata for {new_filename}: {str(meta_error)}")
                        import traceback
                        traceback.print_exc()
                    
                    if old_path_resolved != new_path_resolved:
                        self.root.after(0, lambda p=new_path: self.music_player.load_file(str(p)))
                    
                    # Add to undo history after successful processing
                    if 'undo_entry' in locals():
                        undo_entry['new_path'] = Path(new_path_resolved) if 'new_path_resolved' in locals() else undo_entry.get('new_path')
                        self.undo_history.append(undo_entry)
                        # Enable undo button
                        self.root.after(0, lambda: self.undo_button.config(state='normal'))
                    
                except Exception as e:
                    print(f"Error processing {audio_file.name}: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    continue
        
        tag_updater.print_filename_changes_table(filename_changes)
        return filename_changes
    
    def _update_progress(self, current, total):
        """Update progress bar and counter"""
        try:
            if total > 0:
                self.progress_bar['maximum'] = total
                self.progress_bar['value'] = current
                self.progress_counter.config(text=f"{current}/{total}")
            else:
                self.progress_bar['value'] = 0
                self.progress_bar['maximum'] = 100
                self.progress_counter.config(text="0/0")
            # Force GUI update (safe to call from main thread)
            self.root.update_idletasks()
        except Exception:
            # Silently handle any GUI update errors (might happen if window is closed)
            pass
    
    def undo_last_operation(self):
        """Undo the last file operation - delete updated file and restore original, then re-run matching"""
        if not self.undo_history:
            self.console.insert(tk.END, "No operations to undo.\n")
            return
        
        # Get the last operation
        last_op = self.undo_history.pop()
        
        try:
            original_path = last_op['original_path']
            new_path = last_op.get('new_path')
            
            # Redirect stdout to console for undo messages
            old_stdout = sys.stdout
            sys.stdout = ConsoleRedirect(self.console)
            
            print("\n" + "=" * 80)
            print("UNDOING LAST OPERATION")
            print("=" * 80)
            
            # Handle file restoration based on whether it was renamed or moved to output folder
            if new_path and original_path != new_path:
                # Check if file was renamed in place (same directory) or moved to output folder
                if new_path.parent == original_path.parent:
                    # File was renamed in place - restore original filename first (before deleting)
                    if new_path.exists() and not original_path.exists():
                        try:
                            # Unload from player first
                            self.root.after(0, lambda: self.music_player.unload_file())
                            import time
                            time.sleep(0.3)
                            
                            new_path.rename(original_path)
                            print(f"Restored original filename: {original_path.name}")
                        except Exception as e:
                            print(f"Error restoring original filename: {str(e)}")
                    elif original_path.exists():
                        # Original already exists - delete the new one if it exists
                        if new_path.exists():
                            try:
                                self.root.after(0, lambda: self.music_player.unload_file())
                                import time
                                time.sleep(0.3)
                                new_path.unlink()
                                print(f"Deleted duplicate file: {new_path.name}")
                            except Exception as e:
                                print(f"Error deleting duplicate file: {str(e)}")
                else:
                    # File was moved to output folder - original should still exist
                    # Delete the file in output folder
                    if new_path.exists():
                        try:
                            # Unload from player first
                            self.root.after(0, lambda: self.music_player.unload_file())
                            import time
                            time.sleep(0.3)
                            
                            new_path.unlink()
                            print(f"Deleted updated file in output folder: {new_path.name}")
                        except Exception as e:
                            print(f"Error deleting updated file {new_path}: {str(e)}")
                    
                    # Check if original still exists
                    if original_path.exists():
                        print(f"Original file exists: {original_path.name}")
                    else:
                        print(f"Warning: Original file {original_path.name} not found.")
            
            # Re-run matching for the original file
            print(f"\nRe-running matching for: {original_path.name}")
            print("=" * 80 + "\n")
            
            # Get the original file's metadata and catalogue
            audio_metadata = last_op['audio_metadata']
            catalogue = last_op['catalogue']
            
            # Re-run the choice selection
            old_input = __builtins__.input
            __builtins__.input = self.custom_input
            
            chosen_idx = tag_updater.ask_choice(
                original_path.name, 
                audio_metadata, 
                catalogue,
                auto_select=self.auto_select.get()
            )
            
            # Restore input
            __builtins__.input = old_input
            sys.stdout = old_stdout
            
            # If user makes a new choice, we need to process it
            # For now, just inform the user they can process again
            if chosen_idx != 9999:
                print(f"\nYou selected a new match. The file will be processed again.")
                # Note: The file processing would need to be triggered again
                # This is a simplified version - in a full implementation, you might want to
                # automatically process the file again with the new choice
            else:
                print(f"\nFile skipped - no changes will be made.")
            
            # Update undo button state
            if not self.undo_history:
                self.undo_button.config(state='disabled')
            
        except Exception as e:
            if sys.stdout != ConsoleRedirect(self.console):
                sys.stdout = ConsoleRedirect(self.console)
            print(f"Error during undo: {str(e)}")
            import traceback
            traceback.print_exc()
            # Restore the operation to history if undo failed
            self.undo_history.append(last_op)
            sys.stdout = old_stdout

if __name__ == "__main__":
    root = tk.Tk()
    metadata_dict = load_parquet_folder()
    artists = metadata_dict.keys()
    app = ToolGUI(root, artists=artists, metadata_dict=metadata_dict)
    root.mainloop()

    

    