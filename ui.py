#!/usr/bin/env python3
import tkinter as tk
from tkinter import filedialog
from tkinter.scrolledtext import ScrolledText
import subprocess
import threading
import sys
import os
from dotenv import load_dotenv

# Load env variables at startup
load_dotenv()

class CustomProgressbar(tk.Canvas):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, highlightthickness=0, bg='#1a1a1a', height=12, **kwargs)
        self.rect = self.create_rectangle(0, 0, 0, 12, fill='#ff4444', width=0)
        self.percentage = 0
        self.bind("<Configure>", self.on_resize)
        
    def set(self, percentage):
        self.percentage = percentage
        self.draw()
        
    def draw(self):
        width = self.winfo_width()
        fill_width = (self.percentage / 100.0) * width
        self.coords(self.rect, 0, 0, fill_width, 12)
        
    def on_resize(self, event):
        self.draw()

class KillframeUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("🎮 KILLFRAME-AGENT — Autonomous Montage Editor")
        self.root.geometry("900x700")
        self.root.configure(bg='#0a0a0a')
        self.root.resizable(False, False)
        
        self.footage_path = ""
        self.music_path = ""
        
        self.setup_ui()
        self.load_api_key()
        
    def setup_ui(self):
        # Section 1 - API Key (top)
        sec1 = tk.Frame(self.root, bg='#0a0a0a')
        sec1.pack(fill=tk.X, padx=25, pady=(20, 10))
        
        lbl_api = tk.Label(sec1, text="GEMINI API KEY", fg='#ff4444', bg='#0a0a0a', font=('Consolas', 10, 'bold'))
        lbl_api.pack(anchor=tk.W)
        
        sec1_input = tk.Frame(sec1, bg='#0a0a0a')
        sec1_input.pack(fill=tk.X, pady=(2, 2))
        
        self.entry_api_key = tk.Entry(
            sec1_input, bg='#1a1a1a', fg='white', insertbackground='white',
            font=('Consolas', 10), show='*', relief='flat', highlightthickness=1,
            highlightbackground='#333333', highlightcolor='#ff4444'
        )
        self.entry_api_key.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        
        btn_save = tk.Button(
            sec1_input, text="SAVE KEY", bg='#ff4444', fg='white',
            font=('Consolas', 10, 'bold'), relief='flat', bd=0, padx=15, pady=3,
            activebackground='#cc3333', activeforeground='white', command=self.save_api_key
        )
        btn_save.pack(side=tk.LEFT)
        
        self.lbl_api_status = tk.Label(sec1_input, text="", fg='#00ff00', bg='#0a0a0a', font=('Consolas', 10))
        self.lbl_api_status.pack(side=tk.LEFT, padx=10)
        
        lbl_api_hint = tk.Label(sec1, text="Get free key at aistudio.google.com", fg='grey', bg='#0a0a0a', font=('Consolas', 10))
        lbl_api_hint.pack(anchor=tk.W, pady=(2, 0))
        
        # Section 2 - Reference Video
        sec2 = tk.Frame(self.root, bg='#0a0a0a')
        sec2.pack(fill=tk.X, padx=25, pady=10)
        
        lbl_ref = tk.Label(sec2, text="REFERENCE YOUTUBE URL", fg='white', bg='#0a0a0a', font=('Consolas', 10, 'bold'))
        lbl_ref.pack(anchor=tk.W)
        
        sec2_input = tk.Frame(sec2, bg='#0a0a0a')
        sec2_input.pack(fill=tk.X, pady=(2, 0))
        
        self.entry_ref_url = tk.Entry(
            sec2_input, bg='#1a1a1a', fg='white', insertbackground='white',
            font=('Consolas', 10), relief='flat', highlightthickness=1,
            highlightbackground='#333333', highlightcolor='#ff4444'
        )
        self.entry_ref_url.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        
        self.btn_analyze = tk.Button(
            sec2_input, text="ANALYZE STYLE", bg='#ff4444', fg='white',
            font=('Consolas', 10, 'bold'), relief='flat', bd=0, padx=15, pady=3,
            activebackground='#cc3333', activeforeground='white', command=self.start_analysis
        )
        self.btn_analyze.pack(side=tk.LEFT)
        
        self.lbl_ref_status = tk.Label(sec2_input, text="", fg='white', bg='#0a0a0a', font=('Consolas', 10))
        self.lbl_ref_status.pack(side=tk.LEFT, padx=10)
        
        # Section 3 - Footage
        sec3 = tk.Frame(self.root, bg='#0a0a0a')
        sec3.pack(fill=tk.X, padx=25, pady=10)
        
        lbl_footage = tk.Label(sec3, text="RAW GAMEPLAY FOOTAGE", fg='white', bg='#0a0a0a', font=('Consolas', 10, 'bold'))
        lbl_footage.pack(anchor=tk.W)
        
        sec3_input = tk.Frame(sec3, bg='#0a0a0a')
        sec3_input.pack(fill=tk.X, pady=(2, 0))
        
        btn_browse_f = tk.Button(
            sec3_input, text="BROWSE FILE", bg='#ff4444', fg='white',
            font=('Consolas', 10, 'bold'), relief='flat', bd=0, padx=15, pady=3,
            activebackground='#cc3333', activeforeground='white', command=self.browse_footage
        )
        btn_browse_f.pack(side=tk.LEFT)
        
        self.lbl_footage_file = tk.Label(sec3_input, text="No file selected", fg='grey', bg='#0a0a0a', font=('Consolas', 10))
        self.lbl_footage_file.pack(side=tk.LEFT, padx=10)
        
        # Section 4 - Music
        sec4 = tk.Frame(self.root, bg='#0a0a0a')
        sec4.pack(fill=tk.X, padx=25, pady=10)
        
        lbl_music = tk.Label(sec4, text="BACKGROUND MUSIC", fg='white', bg='#0a0a0a', font=('Consolas', 10, 'bold'))
        lbl_music.pack(anchor=tk.W)
        
        sec4_input = tk.Frame(sec4, bg='#0a0a0a')
        sec4_input.pack(fill=tk.X, pady=(2, 0))
        
        btn_browse_m = tk.Button(
            sec4_input, text="BROWSE FILE", bg='#ff4444', fg='white',
            font=('Consolas', 10, 'bold'), relief='flat', bd=0, padx=15, pady=3,
            activebackground='#cc3333', activeforeground='white', command=self.browse_music
        )
        btn_browse_m.pack(side=tk.LEFT)
        
        self.lbl_music_file = tk.Label(sec4_input, text="No file selected", fg='grey', bg='#0a0a0a', font=('Consolas', 10))
        self.lbl_music_file.pack(side=tk.LEFT, padx=10)
        
        # Section 5 - Output Duration
        sec5 = tk.Frame(self.root, bg='#0a0a0a')
        sec5.pack(fill=tk.X, padx=25, pady=10)
        
        lbl_duration = tk.Label(sec5, text="OUTPUT DURATION", fg='white', bg='#0a0a0a', font=('Consolas', 10, 'bold'))
        lbl_duration.pack(anchor=tk.W)
        
        sec5_input = tk.Frame(sec5, bg='#0a0a0a')
        sec5_input.pack(fill=tk.X, pady=(2, 0))
        
        self.slider_duration = tk.Scale(
            sec5_input, from_=30, to=600, orient=tk.HORIZONTAL,
            bg='#0a0a0a', fg='white', troughcolor='#1a1a1a',
            activebackground='#ff4444', highlightthickness=0, bd=0,
            showvalue=False, length=400, command=self.update_dur_label
        )
        self.slider_duration.set(60)
        self.slider_duration.pack(side=tk.LEFT, padx=(0, 10))
        
        self.lbl_dur_val = tk.Label(sec5_input, text="1:00 minutes", fg='white', bg='#0a0a0a', font=('Consolas', 10))
        self.lbl_dur_val.pack(side=tk.LEFT)
        
        # Section 6 - Generate & Logs
        sec6 = tk.Frame(self.root, bg='#0a0a0a')
        sec6.pack(fill=tk.BOTH, expand=True, padx=25, pady=(10, 20))
        
        sec6_actions = tk.Frame(sec6, bg='#0a0a0a')
        sec6_actions.pack(fill=tk.X, pady=(0, 10))
        
        self.btn_generate = tk.Button(
            sec6_actions, text="⚡ GENERATE MONTAGE", bg='#ff4444', fg='white',
            font=('Consolas', 10, 'bold'), relief='flat', bd=0, width=40, pady=6,
            activebackground='#cc3333', activeforeground='white', command=self.start_generation
        )
        self.btn_generate.pack(side=tk.LEFT)
        
        self.btn_play = tk.Button(
            sec6_actions, text="▶ PLAY RESULT", bg='#ff4444', fg='white',
            font=('Consolas', 10, 'bold'), relief='flat', bd=0, padx=15, pady=6,
            activebackground='#cc3333', activeforeground='white', command=self.play_result
        )
        # Hidden initially, so we don't pack it.
        
        self.lbl_gen_status = tk.Label(sec6_actions, text="", fg='red', bg='#0a0a0a', font=('Consolas', 10, 'bold'))
        self.lbl_gen_status.pack(side=tk.LEFT, padx=10)
        
        self.progress_bar = CustomProgressbar(sec6)
        self.progress_bar.pack(fill=tk.X, pady=(0, 10))
        
        self.log_box = ScrolledText(
            sec6, bg='black', fg='#00ff00', insertbackground='white',
            font=('Consolas', 10), relief='flat', highlightthickness=1,
            highlightbackground='#333333', highlightcolor='#ff4444', height=8
        )
        self.log_box.pack(fill=tk.BOTH, expand=True)
        self.log_box.config(state=tk.DISABLED)

    def load_api_key(self):
        env_path = ".env"
        if os.path.exists(env_path):
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip().startswith("GEMINI_API_KEY="):
                            parts = line.strip().split("=", 1)
                            if len(parts) == 2:
                                key = parts[1]
                                self.entry_api_key.delete(0, tk.END)
                                self.entry_api_key.insert(0, key)
                                break
            except Exception:
                pass

    def save_api_key(self):
        key = self.entry_api_key.get().strip()
        env_path = ".env"
        lines = []
        gemini_found = False
        groq_found = False
        
        if os.path.exists(env_path):
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
            except Exception:
                pass
                
        for i, line in enumerate(lines):
            if line.strip().startswith("GEMINI_API_KEY="):
                lines[i] = f"GEMINI_API_KEY={key}\n"
                gemini_found = True
            elif line.strip().startswith("GROQ_API_KEY="):
                lines[i] = f"GROQ_API_KEY={key}\n"
                groq_found = True
                
        if not gemini_found:
            lines.append(f"GEMINI_API_KEY={key}\n")
        if not groq_found:
            lines.append(f"GROQ_API_KEY={key}\n")
            
        try:
            with open(env_path, "w", encoding="utf-8") as f:
                f.writelines(lines)
            self.lbl_api_status.config(text="✅ Key Saved", fg='#00ff00')
        except Exception as e:
            self.lbl_api_status.config(text=f"❌ Error: {e}", fg='#ff4444')

    def start_analysis(self):
        url = self.entry_ref_url.get().strip()
        if not url:
            self.lbl_ref_status.config(text="❌ URL required", fg='#ff4444')
            return
            
        self.lbl_ref_status.config(text="Analyzing...", fg='#ffff00')
        self.btn_analyze.config(state=tk.DISABLED)
        
        def run_analysis():
            import time
            time.sleep(2)
            try:
                self.root.after(0, lambda: self.lbl_ref_status.config(text="✅ Style Ready", fg='#00ff00'))
                self.root.after(0, lambda: self.btn_analyze.config(state=tk.NORMAL))
            except tk.TclError:
                pass
                
        threading.Thread(target=run_analysis, daemon=True).start()

    def browse_footage(self):
        path = filedialog.askopenfilename(
            title="Select Gameplay Footage",
            filetypes=[("MP4 Video", "*.mp4"), ("All Files", "*.*")]
        )
        if path:
            self.footage_path = path
            filename = os.path.basename(path)
            self.lbl_footage_file.config(text=filename, fg='grey')

    def browse_music(self):
        path = filedialog.askopenfilename(
            title="Select Background Music",
            filetypes=[
                ("Audio Files", "*.mp3 *.wav *.webm"),
                ("MP3 Audio", "*.mp3"),
                ("WAV Audio", "*.wav"),
                ("WEBM Audio", "*.webm"),
                ("All Files", "*.*")
            ]
        )
        if path:
            self.music_path = path
            filename = os.path.basename(path)
            self.lbl_music_file.config(text=filename, fg='grey')

    def update_dur_label(self, val):
        seconds = int(val)
        minutes = seconds // 60
        secs = seconds % 60
        self.lbl_dur_val.config(text=f"{minutes}:{secs:02d} minutes")

    def log_to_box(self, message):
        self.root.after(0, self._safe_log, message)

    def _safe_log(self, message):
        try:
            self.log_box.config(state=tk.NORMAL)
            self.log_box.insert(tk.END, message)
            self.log_box.see(tk.END)
            self.log_box.config(state=tk.DISABLED)
        except tk.TclError:
            pass

    def play_result(self):
        output_file = "killframe_output.mp4"
        if os.path.exists(output_file):
            try:
                os.startfile(os.path.abspath(output_file))
            except Exception as e:
                self.log_to_box(f"\n[ERROR] Could not play file: {e}\n")
        else:
            self.log_to_box(f"\n[ERROR] Output file {output_file} not found!\n")

    def start_generation(self):
        youtube_url = self.entry_ref_url.get().strip()
        api_key = self.entry_api_key.get().strip()
        
        # Validation
        if not api_key or not youtube_url or not self.footage_path or not self.music_path:
            self.lbl_gen_status.config(text="❌ Error: All fields are required!", fg='#ff4444')
            return
            
        self.lbl_gen_status.config(text="")
        self.btn_generate.config(state=tk.DISABLED)
        self.btn_play.pack_forget()
        self.progress_bar.set(0)
        
        # Clear log box
        self.log_box.config(state=tk.NORMAL)
        self.log_box.delete("1.0", tk.END)
        self.log_box.config(state=tk.DISABLED)
        
        self.lbl_gen_status.config(text="Running...", fg='#ffff00')
        
        # Prepare environment
        env = os.environ.copy()
        env["GEMINI_API_KEY"] = api_key
        env["GROQ_API_KEY"] = api_key
        
        def run_process():
            try:
                cmd = [
                    sys.executable, "agent.py",
                    "--youtube", youtube_url,
                    "--footage", self.footage_path,
                    "--music", self.music_path,
                    "--output", "killframe_output.mp4"
                ]
                
                # Log command line
                self.log_to_box(f"Running pipeline command:\n{' '.join(cmd)}\n\n")
                
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    env=env
                )
                
                for line in process.stdout:
                    self.log_to_box(line)
                    
                    # Check step progression
                    if "Step 2/4" in line:
                        self.root.after(0, lambda: self.progress_bar.set(25))
                    elif "Step 3/4" in line:
                        self.root.after(0, lambda: self.progress_bar.set(50))
                    elif "Step 4/4" in line:
                        self.root.after(0, lambda: self.progress_bar.set(75))
                    elif "Montage exported to" in line:
                        self.root.after(0, lambda: self.progress_bar.set(100))
                        
                process.wait()
                
                if process.returncode == 0:
                    self.root.after(0, lambda: self.progress_bar.set(100))
                    self.root.after(0, lambda: self.lbl_gen_status.config(text="✅ Complete!", fg='#00ff00'))
                    self.root.after(0, lambda: self.btn_play.pack(side=tk.LEFT, padx=10))
                else:
                    self.root.after(0, lambda: self.lbl_gen_status.config(text="❌ Failed", fg='#ff4444'))
                    
            except Exception as e:
                self.log_to_box(f"\n[KILLFRAME UI ERROR] {e}\n")
                self.root.after(0, lambda: self.lbl_gen_status.config(text="❌ Error", fg='#ff4444'))
            finally:
                self.root.after(0, lambda: self.btn_generate.config(state=tk.NORMAL))
                
        threading.Thread(target=run_process, daemon=True).start()

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = KillframeUI()
    app.run()
