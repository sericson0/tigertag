import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext
import threading
import sys
from io import StringIO

class ConsoleRedirect:
    """Redirects stdout to the GUI console"""
    def __init__(self, text_widget):
        self.text_widget = text_widget
        self.buffer = StringIO()
        
    def write(self, string):
        self.text_widget.insert(tk.END, string)
        self.text_widget.see(tk.END)
        self.text_widget.update_idletasks()
        
    def flush(self):
        pass

class ModernButton(tk.Canvas):
    """Custom modern button with hover effects"""
    def __init__(self, parent, text, command, bg="#007acc", fg="white", hover_bg="#005a9e", **kwargs):
        super().__init__(parent, height=40, bg=parent['bg'], highlightthickness=0, **kwargs)
        self.command = command
        self.bg = bg
        self.hover_bg = hover_bg
        self.fg = fg
        self.text = text
        self.disabled = False
        
        self.bind('<Button-1>', self._on_click)
        self.bind('<Enter>', self._on_enter)
        self.bind('<Leave>', self._on_leave)
        self.bind('<Configure>', self._on_configure)
        
        self._draw()
        
    def _draw(self):
        self.delete('all')
        w = self.winfo_width() or 200
        h = self.winfo_height() or 40
        
        color = self.hover_bg if hasattr(self, '_hovered') and self._hovered else self.bg
        if self.disabled:
            color = "#cccccc"
            
        self.create_rectangle(0, 0, w, h, fill=color, outline='', tags='bg')
        self.create_text(w/2, h/2, text=self.text, fill=self.fg if not self.disabled else "#666666", 
                        font=('Segoe UI', 10, 'bold'), tags='text')
        
    def _on_click(self, event):
        if not self.disabled and self.command:
            self.command()
            
    def _on_enter(self, event):
        if not self.disabled:
            self._hovered = True
            self._draw()
            
    def _on_leave(self, event):
        self._hovered = False
        self._draw()
        
    def _on_configure(self, event):
        self._draw()
        
    def config_state(self, state):
        self.disabled = (state == 'disabled')
        self._draw()

class ToolGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Tool Interface")
        self.root.geometry("850x700")
        
        # Modern color scheme
        self.colors = {
            'bg': '#f5f5f5',
            'card_bg': 'white',
            'primary': '#007acc',
            'primary_hover': '#005a9e',
            'text': '#333333',
            'text_light': '#666666',
            'border': '#e0e0e0',
            'console_bg': '#1e1e1e',
            'console_fg': '#d4d4d4',
            'success': '#28a745',
            'input_bg': '#ffffff'
        }
        
        self.root.configure(bg=self.colors['bg'])
        
        # Variables
        self.folder_path = tk.StringVar()
        self.start_year = tk.StringVar(value="2020")
        self.end_year = tk.StringVar(value="2024")
        self.input_var = tk.StringVar()
        self.waiting_for_input = False
        self.input_result = None
        
        # Create GUI elements
        self.create_widgets()
        
    def create_widgets(self):
        # Main container with padding
        main_frame = tk.Frame(self.root, bg=self.colors['bg'])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Header
        header = tk.Label(main_frame, text="Tool Configuration", 
                         font=('Segoe UI', 20, 'bold'),
                         bg=self.colors['bg'], fg=self.colors['text'])
        header.pack(pady=(0, 20))
        
        # Configuration card
        config_card = tk.Frame(main_frame, bg=self.colors['card_bg'], relief=tk.FLAT)
        config_card.pack(fill=tk.X, pady=(0, 20))
        self._add_shadow(config_card)
        
        config_inner = tk.Frame(config_card, bg=self.colors['card_bg'])
        config_inner.pack(fill=tk.BOTH, padx=30, pady=25)
        
        # Folder selection
        self._create_input_section(config_inner, "Folder Path", 0)
        folder_frame = tk.Frame(config_inner, bg=self.colors['card_bg'])
        folder_frame.grid(row=1, column=0, sticky='ew', pady=(5, 20))
        folder_frame.columnconfigure(0, weight=1)
        
        self.folder_entry = self._create_modern_entry(folder_frame, self.folder_path)
        self.folder_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        
        browse_btn = tk.Button(folder_frame, text="📁 Browse", command=self.browse_folder,
                              bg=self.colors['border'], fg=self.colors['text'],
                              font=('Segoe UI', 9), relief=tk.FLAT, cursor='hand2',
                              padx=15, pady=8)
        browse_btn.pack(side=tk.RIGHT)
        self._add_hover_effect(browse_btn, self.colors['border'], '#d0d0d0')
        
        # Year inputs
        years_frame = tk.Frame(config_inner, bg=self.colors['card_bg'])
        years_frame.grid(row=2, column=0, sticky='ew')
        years_frame.columnconfigure(0, weight=1)
        years_frame.columnconfigure(1, weight=1)
        
        # Start year
        start_frame = tk.Frame(years_frame, bg=self.colors['card_bg'])
        start_frame.grid(row=0, column=0, sticky='ew', padx=(0, 10))
        self._create_input_section(start_frame, "Start Year", 0, parent_bg=self.colors['card_bg'])
        self.start_entry = self._create_modern_entry(start_frame, self.start_year)
        self.start_entry.pack(fill=tk.X, pady=(5, 0))
        
        # End year
        end_frame = tk.Frame(years_frame, bg=self.colors['card_bg'])
        end_frame.grid(row=0, column=1, sticky='ew')
        self._create_input_section(end_frame, "End Year", 0, parent_bg=self.colors['card_bg'])
        self.end_entry = self._create_modern_entry(end_frame, self.end_year)
        self.end_entry.pack(fill=tk.X, pady=(5, 0))
        
        # Run button
        btn_frame = tk.Frame(main_frame, bg=self.colors['bg'])
        btn_frame.pack(fill=tk.X, pady=(0, 20))
        
        self.run_button = ModernButton(btn_frame, text="▶ Run Tool", command=self.run_tool,
                                       bg=self.colors['primary'], hover_bg=self.colors['primary_hover'])
        self.run_button.pack(fill=tk.X)
        
        # Console card
        console_card = tk.Frame(main_frame, bg=self.colors['card_bg'], relief=tk.FLAT)
        console_card.pack(fill=tk.BOTH, expand=True)
        self._add_shadow(console_card)
        
        # Console header
        console_header = tk.Frame(console_card, bg=self.colors['card_bg'])
        console_header.pack(fill=tk.X, padx=30, pady=(20, 10))
        
        tk.Label(console_header, text="Console Output", 
                font=('Segoe UI', 12, 'bold'),
                bg=self.colors['card_bg'], fg=self.colors['text']).pack(side=tk.LEFT)
        
        # Console output area
        console_frame = tk.Frame(console_card, bg=self.colors['card_bg'])
        console_frame.pack(fill=tk.BOTH, expand=True, padx=30, pady=(0, 20))
        
        self.console = scrolledtext.ScrolledText(
            console_frame, wrap=tk.WORD,
            bg=self.colors['console_bg'], 
            fg=self.colors['console_fg'],
            font=('Consolas', 10),
            relief=tk.FLAT,
            padx=15, pady=15,
            insertbackground=self.colors['console_fg']
        )
        self.console.pack(fill=tk.BOTH, expand=True)
        
        # Input area (hidden by default)
        self.input_card = tk.Frame(main_frame, bg=self.colors['card_bg'], relief=tk.FLAT)
        self._add_shadow(self.input_card)
        
        input_inner = tk.Frame(self.input_card, bg=self.colors['card_bg'])
        input_inner.pack(fill=tk.X, padx=30, pady=20)
        input_inner.columnconfigure(0, weight=1)
        
        tk.Label(input_inner, text="Input Required", 
                font=('Segoe UI', 10, 'bold'),
                bg=self.colors['card_bg'], fg=self.colors['text']).grid(row=0, column=0, sticky='w', pady=(0, 10))
        
        input_row = tk.Frame(input_inner, bg=self.colors['card_bg'])
        input_row.grid(row=1, column=0, sticky='ew')
        input_row.columnconfigure(0, weight=1)
        
        self.input_entry = self._create_modern_entry(input_row, self.input_var)
        self.input_entry.grid(row=0, column=0, sticky='ew', padx=(0, 10))
        
        submit_btn = tk.Button(input_row, text="Submit", command=self.submit_input,
                              bg=self.colors['success'], fg='white',
                              font=('Segoe UI', 9, 'bold'), relief=tk.FLAT, 
                              cursor='hand2', padx=20, pady=8)
        submit_btn.grid(row=0, column=1)
        self._add_hover_effect(submit_btn, self.colors['success'], '#218838')
        
        self.input_entry.bind('<Return>', lambda e: self.submit_input())
        
    def _create_input_section(self, parent, label_text, row, parent_bg=None):
        bg = parent_bg if parent_bg else self.colors['card_bg']
        label = tk.Label(parent, text=label_text, 
                        font=('Segoe UI', 10, 'bold'),
                        bg=bg, fg=self.colors['text'])
        label.grid(row=row, column=0, sticky='w')
        
    def _create_modern_entry(self, parent, textvariable):
        entry = tk.Entry(parent, textvariable=textvariable,
                        font=('Segoe UI', 10),
                        bg=self.colors['input_bg'],
                        fg=self.colors['text'],
                        relief=tk.FLAT,
                        highlightthickness=1,
                        highlightbackground=self.colors['border'],
                        highlightcolor=self.colors['primary'])
        entry.config(insertbackground=self.colors['text'])
        
        # Add padding
        style_frame = tk.Frame(parent, bg=self.colors['input_bg'], 
                              highlightthickness=1,
                              highlightbackground=self.colors['border'])
        entry.pack(in_=style_frame, padx=10, pady=8)
        
        return entry
        
    def _add_shadow(self, widget):
        """Add subtle shadow effect to widgets"""
        widget.config(highlightbackground='#d0d0d0', highlightthickness=1)
        
    def _add_hover_effect(self, button, normal_color, hover_color):
        """Add hover effect to regular buttons"""
        button.bind('<Enter>', lambda e: button.config(bg=hover_color))
        button.bind('<Leave>', lambda e: button.config(bg=normal_color))
        
    def browse_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.folder_path.set(folder)
            
    def submit_input(self):
        if self.waiting_for_input:
            self.input_result = self.input_var.get()
            self.input_var.set("")
            self.input_card.pack_forget()
            self.waiting_for_input = False
            
    def custom_input(self, prompt=""):
        """Custom input function that works with the GUI"""
        if prompt:
            self.console.insert(tk.END, prompt)
            self.console.see(tk.END)
            
        self.waiting_for_input = True
        self.input_result = None
        self.input_card.pack(fill=tk.X, pady=(20, 0))
        self.input_entry.focus()
        
        while self.waiting_for_input:
            self.root.update()
            
        return self.input_result
    
    def run_tool(self):
        folder = self.folder_path.get()
        if not folder:
            self.console.insert(tk.END, "❌ Error: Please select a folder\n")
            return
            
        try:
            start = int(self.start_year.get())
            end = int(self.end_year.get())
        except ValueError:
            self.console.insert(tk.END, "❌ Error: Years must be valid integers\n")
            return
            
        self.console.delete(1.0, tk.END)
        self.run_button.config_state('disabled')
        
        thread = threading.Thread(target=self.execute_tool, args=(folder, start, end))
        thread.daemon = True
        thread.start()
        
    def execute_tool(self, folder, start_year, end_year):
        old_stdout = sys.stdout
        sys.stdout = ConsoleRedirect(self.console)
        
        old_input = __builtins__.input
        __builtins__.input = self.custom_input
        
        try:
            # Import and run your function here
            # Example: from your_package import your_function
            # your_function(folder, start_year, end_year)
            
            print("🚀 Starting tool execution...")
            print(f"📁 Folder: {folder}")
            print(f"📅 Start Year: {start_year}")
            print(f"📅 End Year: {end_year}\n")
            
            for year in range(start_year, end_year + 1):
                print(f"⚙️  Processing year {year}...")
                
            name = input("👤 Enter your name: ")
            print(f"👋 Hello, {name}!")
            
            print("\n✅ Tool execution completed successfully!")
            
        except Exception as e:
            print(f"\n❌ Error: {str(e)}")
        finally:
            sys.stdout = old_stdout
            __builtins__.input = old_input
            self.root.after(0, lambda: self.run_button.config_state('normal'))

if __name__ == "__main__":
    root = tk.Tk()
    app = ToolGUI(root)
    root.mainloop()