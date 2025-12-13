import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import sys
import threading
import queue

# --- 경로 설정 ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(os.path.join(PROJECT_ROOT, 'scripts'))

from main import synthesize_tts_from_srt

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Regen Voice - Synthesize Only")
        self.geometry("800x600")

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(pady=10, padx=10, fill="both", expand=True)

        self.main_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.main_frame, text='Main')

        self.log_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.log_frame, text='Logs')

        self.create_widgets()
        self.create_log_viewer()

        self.thread = None
        self.stop_requested = False

    def browse_reference_audio(self):
        filenames = filedialog.askopenfilenames(
            title="Select Reference Audio Files",
            initialdir="/home/jay-gim/dev/regen.voice/reference_audio",
            filetypes=(("Audio files", "*.wav *.mp3 *.flac"), ("All files", "*.*"))
        )
        if filenames:
            self.reference_audio_path.set(";".join(filenames))
            
    def browse_srt_file(self):
        filename = filedialog.askopenfilename(
            title="Select a Subtitle File",
            initialdir=os.path.join(PROJECT_ROOT, "data/02_corrected_subtitles"),
            filetypes=(("SRT files", "*.srt"), ("All files", "*.*"))
        )
        if filename:
            self.srt_path.set(filename)

    def stop_pipeline(self):
        if self.thread and self.thread.is_alive():
            self.stop_requested = True
            self.log_queue.put("--- Stop requested by user. Finishing current step... ---\n")
            self.stop_button.config(state="disabled")

    def create_widgets(self):
        frame = self.main_frame
        
        # --- File Paths ---
        path_frame = ttk.LabelFrame(frame, text="File Paths")
        path_frame.pack(fill="x", padx=10, pady=5)

        self.srt_path = tk.StringVar()
        self.tts_output_dir = tk.StringVar(value=os.path.join(PROJECT_ROOT, "data/03_tts_output"))
        self.reference_audio_path = tk.StringVar()

        ttk.Label(path_frame, text="Subtitle Path (.srt):").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        ttk.Entry(path_frame, textvariable=self.srt_path, width=60).grid(row=0, column=1, padx=5, pady=2)
        ttk.Button(path_frame, text="Browse", command=self.browse_srt_file).grid(row=0, column=2, padx=5, pady=2)
        
        ttk.Label(path_frame, text="TTS Output Dir:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
        ttk.Entry(path_frame, textvariable=self.tts_output_dir, width=60).grid(row=1, column=1, padx=5, pady=2)
        ttk.Button(path_frame, text="Browse", command=lambda: self.browse_directory(self.tts_output_dir)).grid(row=1, column=2, padx=5, pady=2)

        ttk.Label(path_frame, text="Reference Audio(s):").grid(row=2, column=0, sticky="w", padx=5, pady=2)
        ttk.Entry(path_frame, textvariable=self.reference_audio_path, width=60).grid(row=2, column=1, padx=5, pady=2)
        ttk.Button(path_frame, text="Browse", command=self.browse_reference_audio).grid(row=2, column=2, padx=5, pady=2)

        # --- Options ---
        options_frame = ttk.LabelFrame(frame, text="Options")
        options_frame.pack(fill="x", padx=10, pady=5)

        self.language = tk.StringVar(value="ja")
        self.temperature = tk.DoubleVar(value=0.8)
        self.exaggeration = tk.DoubleVar(value=1.0)
        self.cfg_weight = tk.DoubleVar(value=0.6)
        self.seed = tk.IntVar(value=40)
        self.sentence_group_size = tk.IntVar(value=2)

        self.temperature_str = tk.StringVar(value=f"{self.temperature.get():.2f}")
        self.exaggeration_str = tk.StringVar(value=f"{self.exaggeration.get():.2f}")
        self.cfg_weight_str = tk.StringVar(value=f"{self.cfg_weight.get():.2f}")

        self.temperature.trace_add('write', self.update_temperature_label)
        self.exaggeration.trace_add('write', self.update_exaggeration_label)
        self.cfg_weight.trace_add('write', self.update_cfg_weight_label)

        ttk.Label(options_frame, text="Language:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        ttk.Combobox(options_frame, textvariable=self.language, values=["en", "ja", "ko", "zh"]).grid(row=0, column=1, sticky="w", padx=5, pady=2)

        ttk.Label(options_frame, text="Temperature (0.0-1.0):").grid(row=1, column=0, sticky="w", padx=5, pady=2)
        ttk.Scale(options_frame, from_=0.0, to=1.0, orient="horizontal", variable=self.temperature).grid(row=1, column=1, sticky="ew", padx=5, pady=2)
        ttk.Label(options_frame, textvariable=self.temperature_str).grid(row=1, column=2, sticky="w", padx=5, pady=2)

        ttk.Label(options_frame, text="Exaggeration (0.0-2.0):").grid(row=2, column=0, sticky="w", padx=5, pady=2)
        ttk.Scale(options_frame, from_=0.0, to=2.0, orient="horizontal", variable=self.exaggeration).grid(row=2, column=1, sticky="ew", padx=5, pady=2)
        ttk.Label(options_frame, textvariable=self.exaggeration_str).grid(row=2, column=2, sticky="w", padx=5, pady=2)

        ttk.Label(options_frame, text="CFG Weight (0.0-1.0):").grid(row=3, column=0, sticky="w", padx=5, pady=2)
        ttk.Scale(options_frame, from_=0.0, to=1.0, orient="horizontal", variable=self.cfg_weight).grid(row=3, column=1, sticky="ew", padx=5, pady=2)
        ttk.Label(options_frame, textvariable=self.cfg_weight_str).grid(row=3, column=2, sticky="w", padx=5, pady=2)

        ttk.Label(options_frame, text="Seed (0-65536):").grid(row=4, column=0, sticky="w", padx=5, pady=2)
        ttk.Entry(options_frame, textvariable=self.seed).grid(row=4, column=1, sticky="w", padx=5, pady=2)

        ttk.Label(options_frame, text="Sentence Group Size (0-10):").grid(row=5, column=0, sticky="w", padx=5, pady=2)
        ttk.Entry(options_frame, textvariable=self.sentence_group_size).grid(row=5, column=1, sticky="w", padx=5, pady=2)
        
        options_frame.columnconfigure(1, weight=1)

        # --- Execution ---
        execution_frame = ttk.Frame(frame)
        execution_frame.pack(pady=20)

        self.run_button = ttk.Button(execution_frame, text="Run Synthesis", command=self.run_pipeline)
        self.run_button.pack(side="left", padx=5)

        self.stop_button = ttk.Button(execution_frame, text="Force Stop", command=self.stop_pipeline, state="disabled")
        self.stop_button.pack(side="left", padx=5)

        self.progress = ttk.Progressbar(frame, orient="horizontal", length=400, mode="indeterminate")
        self.progress.pack(pady=5)

    def update_temperature_label(self, *args):
        self.temperature_str.set(f"{self.temperature.get():.2f}")

    def update_exaggeration_label(self, *args):
        self.exaggeration_str.set(f"{self.exaggeration.get():.2f}")

    def update_cfg_weight_label(self, *args):
        self.cfg_weight_str.set(f"{self.cfg_weight.get():.2f}")

    def create_log_viewer(self):
        self.log_text = tk.Text(self.log_frame, wrap="word", state="disabled")
        self.log_text.pack(fill="both", expand=True, padx=5, pady=5)
        
        scrollbar = ttk.Scrollbar(self.log_frame, command=self.log_text.yview)
        scrollbar.pack(side="right", fill="y")
        self.log_text.config(yscrollcommand=scrollbar.set)

    def browse_directory(self, var):
        dirname = filedialog.askdirectory(title="Select a Directory")
        if dirname:
            var.set(dirname)

    def run_pipeline(self):
        srt_path = self.srt_path.get()
        if not srt_path:
            messagebox.showerror("Error", "Subtitle file path is required.")
            return

        self.run_button.config(state="disabled")
        self.stop_button.config(state="normal")
        self.progress.start()
        self.notebook.select(self.log_frame)

        self.stop_requested = False

        self.log_queue = queue.Queue()
        self.log_text.config(state="normal")
        self.log_text.delete(1.0, "end")
        self.log_text.config(state="disabled")

        self.thread = threading.Thread(target=self.pipeline_worker, daemon=True)
        self.thread.start()
        self.after(100, self.process_log_queue)

    def pipeline_worker(self):
        class StdoutRedirector:
            def __init__(self, queue):
                self.queue = queue
            def write(self, text):
                self.queue.put(text)
            def flush(self):
                pass

        sys.stdout = StdoutRedirector(self.log_queue)
        sys.stderr = StdoutRedirector(self.log_queue)

        try:
            srt_path = self.srt_path.get()
            tts_output_dir = self.tts_output_dir.get()
            reference_audio_paths = [path.strip() for path in self.reference_audio_path.get().split(';') if path.strip()]

            self.log_queue.put(f"--- Starting TTS Synthesis ---\n")
            self.log_queue.put(f"--- Input Subtitle File: {srt_path} ---\n")
            self.log_queue.put(f"--- Output Directory: {tts_output_dir} ---\n")

            if not os.path.exists(srt_path):
                self.log_queue.put(f"--- ERROR: Subtitle file not found at {srt_path}. Please select a valid file. ---\n")
                messagebox.showerror("Error", f"Subtitle file not found at {srt_path}. Please select a valid file.")
                return

            if not reference_audio_paths:
                self.log_queue.put("--- No reference audio provided. Running TTS with default voice. ---\n")
                synthesize_tts_from_srt(
                    srt_path,
                    srt_path, # Pass srt_path for video_path to handle output naming
                    tts_output_dir,
                    self.language.get(),
                    self.temperature.get(),
                    self.exaggeration.get(),
                    self.cfg_weight.get(),
                    self.seed.get(),
                    self.sentence_group_size.get(),
                    reference_audio=None
                )
                if self.stop_requested:
                    self.log_queue.put("--- Synthesis pipeline stopped by user. ---\n")
                    return
            else:
                self.log_queue.put(f"--- Using {len(reference_audio_paths)} reference audio(s) for synthesis. ---\n")
                valid_reference_audios = []
                for ref_path in reference_audio_paths:
                    if not os.path.exists(ref_path):
                        self.log_queue.put(f"--- WARNING: Reference audio file not found at {ref_path}. Skipping this reference. ---\n")
                    else:
                        valid_reference_audios.append(ref_path)
                
                if not valid_reference_audios:
                    self.log_queue.put("--- No valid reference audio files found. Running TTS with default voice. ---\n")
                    synthesize_tts_from_srt(
                        srt_path,
                        srt_path, # Pass srt_path for video_path to handle output naming
                        tts_output_dir,
                        self.language.get(),
                        self.temperature.get(),
                        self.exaggeration.get(),
                        self.cfg_weight.get(),
                        self.seed.get(),
                        self.sentence_group_size.get(),
                        reference_audio=None
                    )
                else:
                    for i, ref_path in enumerate(valid_reference_audios):
                        self.log_queue.put(f"--- [{i+1}/{len(valid_reference_audios)}] Synthesizing with reference: {os.path.basename(ref_path)} ---\n")
                        synthesize_tts_from_srt(
                            srt_path,
                            srt_path, # Pass srt_path for video_path to handle output naming
                            tts_output_dir,
                            self.language.get(),
                            self.temperature.get(),
                            self.exaggeration.get(),
                            self.cfg_weight.get(),
                            self.seed.get(),
                            self.sentence_group_size.get(),
                            reference_audio=ref_path
                        )
                        if self.stop_requested:
                            self.log_queue.put("--- Synthesis pipeline stopped by user. ---\n")
                            return

            self.log_queue.put("--- TTS Synthesis Finished Successfully ---\n")
        except Exception as e:
            self.log_queue.put(f"An error occurred: {e}\n")
        finally:
            sys.stdout = sys.__stdout__
            sys.stderr = sys.__stderr__
            self.log_queue.put(None) # Signal that the process is done

    def process_log_queue(self):
        try:
            while True:
                line = self.log_queue.get_nowait()
                if line is None:
                    self.run_button.config(state="normal")
                    self.stop_button.config(state="disabled")
                    self.progress.stop()
                    self.thread = None
                    return
                self.log_text.config(state="normal")
                self.log_text.insert("end", line)
                self.log_text.see("end")
                self.log_text.config(state="disabled")
        except queue.Empty:
            self.after(100, self.process_log_queue)

if __name__ == "__main__":
    app = App()
    app.mainloop()
