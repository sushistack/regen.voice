import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import sys
import threading
import queue

# --- 경로 설정 ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(os.path.join(PROJECT_ROOT, 'scripts'))

from main import create_subtitles, correct_subtitles, synthesize_tts_from_srt

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Regen Voice UI")
        self.geometry("800x700")

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

        self.video_path = tk.StringVar()
        self.subtitles_dir = tk.StringVar(value=os.path.join(PROJECT_ROOT, "data/01_subtitles"))
        self.corrected_dir = tk.StringVar(value=os.path.join(PROJECT_ROOT, "data/02_corrected_subtitles"))
        self.tts_output_dir = tk.StringVar(value=os.path.join(PROJECT_ROOT, "data/03_tts_output"))
        self.reference_audio_path = tk.StringVar()

        ttk.Label(path_frame, text="Video Path:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        ttk.Entry(path_frame, textvariable=self.video_path, width=60).grid(row=0, column=1, padx=5, pady=2)
        ttk.Button(path_frame, text="Browse", command=self.browse_video).grid(row=0, column=2, padx=5, pady=2)

        ttk.Label(path_frame, text="Reference Audio(s):").grid(row=4, column=0, sticky="w", padx=5, pady=2)
        ttk.Entry(path_frame, textvariable=self.reference_audio_path, width=60).grid(row=4, column=1, padx=5, pady=2)
        ttk.Button(path_frame, text="Browse", command=self.browse_reference_audio).grid(row=4, column=2, padx=5, pady=2)

        ttk.Label(path_frame, text="Subtitles Dir:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
        ttk.Entry(path_frame, textvariable=self.subtitles_dir, width=60).grid(row=1, column=1, padx=5, pady=2)
        ttk.Button(path_frame, text="Browse", command=lambda: self.browse_directory(self.subtitles_dir)).grid(row=1, column=2, padx=5, pady=2)

        ttk.Label(path_frame, text="Corrected Dir:").grid(row=2, column=0, sticky="w", padx=5, pady=2)
        ttk.Entry(path_frame, textvariable=self.corrected_dir, width=60).grid(row=2, column=1, padx=5, pady=2)
        ttk.Button(path_frame, text="Browse", command=lambda: self.browse_directory(self.corrected_dir)).grid(row=2, column=2, padx=5, pady=2)

        ttk.Label(path_frame, text="TTS Output Dir:").grid(row=3, column=0, sticky="w", padx=5, pady=2)
        ttk.Entry(path_frame, textvariable=self.tts_output_dir, width=60).grid(row=3, column=1, padx=5, pady=2)
        ttk.Button(path_frame, text="Browse", command=lambda: self.browse_directory(self.tts_output_dir)).grid(row=3, column=2, padx=5, pady=2)

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

        # --- Pipeline Steps to Run ---
        steps_frame = ttk.LabelFrame(frame, text="Pipeline Steps to Run")
        steps_frame.pack(fill="x", padx=10, pady=5)

        self.run_create_subtitles = tk.BooleanVar(value=True)
        self.run_correct_subtitles = tk.BooleanVar(value=True)
        self.run_tts_synthesis = tk.BooleanVar(value=True)

        ttk.Checkbutton(steps_frame, text="Step 1: Create Subtitles from Video", variable=self.run_create_subtitles).pack(anchor="w", padx=5)
        ttk.Checkbutton(steps_frame, text="Step 2: Correct Subtitles with LLM", variable=self.run_correct_subtitles).pack(anchor="w", padx=5)
        ttk.Checkbutton(steps_frame, text="Step 3: Synthesize TTS from Subtitles", variable=self.run_tts_synthesis).pack(anchor="w", padx=5)

        # --- Execution ---
        execution_frame = ttk.Frame(frame)
        execution_frame.pack(pady=20)

        self.run_button = ttk.Button(execution_frame, text="Run Pipeline", command=self.run_pipeline)
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

    def browse_video(self):
        filename = filedialog.askopenfilename(
            title="Select a Video File",
            initialdir="/home/jay-gim/dev/regen.voice/data/00_videos",
            filetypes=(("MP4 files", "*.mp4"), ("All files", "*.*"))
        )
        if filename:
            self.video_path.set(filename)

    def browse_directory(self, var):
        dirname = filedialog.askdirectory(title="Select a Directory")
        if dirname:
            var.set(dirname)

    def run_pipeline(self):
        video_path = self.video_path.get()
        if not video_path:
            messagebox.showerror("Error", "Video path is required.")
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
            video_path = self.video_path.get()

            # This will hold the path to the SRT file to be used by the next step
            current_srt_path = None

            # --- Step 1: Create Subtitles ---
            if self.run_create_subtitles.get():
                self.log_queue.put("--- Step 1: Creating subtitles... ---\n")
                current_srt_path = create_subtitles(video_path, self.subtitles_dir.get())
                if self.stop_requested:
                    self.log_queue.put("--- Pipeline stopped by user. ---\n")
                    return
            else:
                self.log_queue.put("--- Step 1: Skipping subtitle creation. ---\n")
                # If skipping, the next step might need the default created.srt path
                current_srt_path = os.path.join(self.subtitles_dir.get(), "created.srt")

            # --- Step 2: Correct Subtitles ---
            if self.run_correct_subtitles.get():
                self.log_queue.put("--- Step 2: Correcting subtitles... ---\n")
                
                # Before running, check if the input SRT file exists.
                if not os.path.exists(current_srt_path):
                    self.log_queue.put(f"--- ERROR: Subtitle file for correction not found at {current_srt_path}. Please run Step 1 or place the file manually. ---\n")
                    return

                corrected_srt_path = os.path.join(self.corrected_dir.get(), "corrected.srt")
                os.makedirs(self.corrected_dir.get(), exist_ok=True)
                correct_subtitles(current_srt_path, corrected_srt_path)
                current_srt_path = corrected_srt_path # Update current path for the next step
                if self.stop_requested:
                    self.log_queue.put("--- Pipeline stopped by user. ---\n")
                    return
            else:
                self.log_queue.put("--- Step 2: Skipping subtitle correction. ---\n")
                # If skipping, check if a corrected file already exists and prefer it for the next step.
                corrected_srt_path = os.path.join(self.corrected_dir.get(), "corrected.srt")
                if os.path.exists(corrected_srt_path):
                    self.log_queue.put(f"--- Found existing corrected subtitle file, will use it for TTS: {corrected_srt_path} ---\n")
                    current_srt_path = corrected_srt_path
                # Otherwise, current_srt_path (from step 1 or its skip-block) is passed through.

            # --- Step 3: Synthesize TTS ---
            if self.run_tts_synthesis.get():
                self.log_queue.put("--- Step 3: Synthesizing TTS... ---\n")

                # Before running, check if the final input SRT file exists.
                if not os.path.exists(current_srt_path):
                    self.log_queue.put(f"--- ERROR: Subtitle file for TTS not found at {current_srt_path}. Please run previous steps or place the file manually. ---\n")
                    return

                reference_audio_paths = [path.strip() for path in self.reference_audio_path.get().split(';') if path.strip()]

                if not reference_audio_paths:
                    self.log_queue.put("--- No reference audio provides. Running TTS with default voice... ---\n")
                    synthesize_tts_from_srt(
                        current_srt_path,
                        video_path,
                        self.tts_output_dir.get(),
                        self.language.get(),
                        self.temperature.get(),
                        self.exaggeration.get(),
                        self.cfg_weight.get(),
                        self.seed.get(),
                        self.sentence_group_size.get(),
                        reference_audio=None
                    )
                    if self.stop_requested:
                        self.log_queue.put("--- Pipeline stopped by user. ---\n")
                        return
                else:
                    for i, ref_path in enumerate(reference_audio_paths):
                        self.log_queue.put(f"--- [{i+1}/{len(reference_audio_paths)}] Synthesizing with reference: {os.path.basename(ref_path)} ---\n")
                        synthesize_tts_from_srt(
                            current_srt_path,
                            video_path,
                            self.tts_output_dir.get(),
                            self.language.get(),
                            self.temperature.get(),
                            self.exaggeration.get(),
                            self.cfg_weight.get(),
                            self.seed.get(),
                            self.sentence_group_size.get(),
                            reference_audio=ref_path
                        )
                        if self.stop_requested:
                            self.log_queue.put("--- Pipeline stopped by user. ---\n")
                            return
            else:
                self.log_queue.put("--- Step 3: Skipping TTS synthesis. ---\n")

            self.log_queue.put("--- Pipeline Finished ---\n")
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