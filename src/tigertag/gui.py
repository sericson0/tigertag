from metadata_handler import load_parquet_folder, csv_to_parquet
from helper_functions import subset_entries, parse_years_from_folder
import tag_updater
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext
import threading
import sys
import pandas as pd
from io import StringIO

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


class ToolGUI:
    def __init__(self, root, artists=None, metadata_dict:dict={}):
        self.root = root
        self.root.title("Tool Interface")
        self.root.geometry("700x700")
        
        # Variables
        self.folder_path = tk.StringVar()
        self.start_year = tk.StringVar(value="1935")
        self.end_year = tk.StringVar(value="1945")
        self.input_var = tk.StringVar()
        self.waiting_for_input = False
        self.input_result = None
        
        self.artists = artists
        self.metadata_dict = metadata_dict
        # Create GUI elements
        self.create_widgets()
        
    def create_widgets(self):
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(5, weight=1)
        
        # Folder selection
        ttk.Label(main_frame, text="Folder:").grid(row=0, column=0, sticky=tk.W, pady=5)
        folder_frame = ttk.Frame(main_frame)
        folder_frame.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=5)
        folder_frame.columnconfigure(0, weight=1)
        
        ttk.Entry(folder_frame, textvariable=self.folder_path).grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5))
        ttk.Button(folder_frame, text="Browse", command=self.browse_folder).grid(row=0, column=1)

        # Update metadata button
        ttk.Button(folder_frame, text="Update Metadata", command=self.update_metadata).grid(row=1, column=1, pady=5, sticky=tk.W)
        
        # Start year
        ttk.Label(main_frame, text="Start Year:").grid(row=1, column=0, sticky=tk.W, pady=5)
        ttk.Entry(main_frame, textvariable=self.start_year, width=15).grid(row=1, column=1, sticky=tk.W, pady=5)
        
        # End year
        ttk.Label(main_frame, text="End Year:").grid(row=2, column=0, sticky=tk.W, pady=5)
        ttk.Entry(main_frame, textvariable=self.end_year, width=15).grid(row=2, column=1, sticky=tk.W, pady=5)
        
        # Artist selector
        ttk.Label(main_frame, text="Artists:").grid(row=3, column=0, sticky=(tk.W, tk.N), pady=5)
        self.artist_selector = ArtistSelectorDropdown(main_frame, self.artists)
        self.artist_selector.grid(row=3, column=1, sticky=(tk.W, tk.E), pady=5)
        
        # Run button
        self.run_button = ttk.Button(main_frame, text="Run Tool", command=self.run_tag_updater)
        self.run_button.grid(row=4, column=0, columnspan=2, pady=10, sticky=tk.W)
        
        # Console output area with padding
        console_frame = ttk.LabelFrame(main_frame, text="Console Output", padding="5")
        console_frame.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
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
            padx=10,  # Add horizontal padding inside console
            pady=10   # Add vertical padding inside console
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
        
        # Input area (hidden by default)
        self.input_frame = ttk.Frame(main_frame)
        self.input_frame.grid(row=6, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        self.input_frame.columnconfigure(1, weight=1)
        self.input_frame.grid_remove()  # Hide initially
        
        ttk.Label(self.input_frame, text="Input:").grid(row=0, column=0, sticky=tk.W)
        self.input_entry = ttk.Entry(self.input_frame, textvariable=self.input_var)
        self.input_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)
        ttk.Button(self.input_frame, text="Submit", command=self.submit_input).grid(row=0, column=2)
        
        # Bind Enter key to submit
        self.input_entry.bind('<Return>', lambda e: self.submit_input())
    
    def update_metadata(self):
        print("Updating Metadata")
        csv_to_parquet()

    def browse_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.folder_path.set(folder)
            
            # Try to extract years from folder name
            start_year, end_year = parse_years_from_folder(folder)
            
            if start_year is not None:
                self.start_year.set(str(start_year))
                self.end_year.set(str(end_year))
            
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
        # Validate inputs
        folder = self.folder_path.get()
        if not folder:
            self.console.insert(tk.END, "Error: Please select a folder\n")
            return
            
        try:
            start = int(self.start_year.get())
            end = int(self.end_year.get())
        except ValueError:
            self.console.insert(tk.END, "Error: Years must be valid integers\n")
            return
        
        # Get selected artists
        selected_artists = self.artist_selector.get_selected_artists()
        if not selected_artists:
            self.console.insert(tk.END, "Error: Please select at least one artist\n")
            return
            
        # Clear console and add initial padding
        self.console.delete(1.0, tk.END)
        self.console.insert(tk.END, '\n' * 5)  # Add padding at the end
        self.console.mark_set('padding_start', 'end-6l')  # Mark where padding starts
        
        # Disable run button
        self.run_button.config(state='disabled')
        
        # Run in separate thread to keep GUI responsive
        thread = threading.Thread(target=self.execute_tag_updater, args=(folder, self.metadata_dict, start, end, selected_artists))
        thread.daemon = True
        thread.start()
        
    def execute_tag_updater(self, folder, metadata_dict, start_year, end_year, selected_artists):
        # Redirect stdout to console
        old_stdout = sys.stdout
        old_input = __builtins__.input
        
        try:
            # Create metadata subset
            metadata_sub = subset_entries(
                df = pd.concat([metadata_dict[artist] for artist in selected_artists]),
                start_year = start_year,
                end_year=end_year,
            )
            
            # Redirect after creating the data
            sys.stdout = ConsoleRedirect(self.console)
            __builtins__.input = self.custom_input
            
            # Run the tag updater
            tag_updater.update_tags(folder, metadata_sub)
        
        except Exception as e:
            # Make sure console redirect is active for error messages
            if sys.stdout != ConsoleRedirect(self.console):
                sys.stdout = ConsoleRedirect(self.console)
            print(f"\nError: {str(e)}")
            import traceback
            traceback.print_exc()
            
        finally:
            # Restore stdout and input
            sys.stdout = old_stdout
            __builtins__.input = old_input
            
            # Re-enable run button (must be done in main thread)
            try:
                self.root.after(0, lambda: self.run_button.config(state='normal'))
            except:
                pass

if __name__ == "__main__":
    root = tk.Tk()
    metadata_dict = load_parquet_folder()
    artists = metadata_dict.keys()
    app = ToolGUI(root, artists=artists, metadata_dict=metadata_dict)
    root.mainloop()