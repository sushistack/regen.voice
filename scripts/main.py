import os
import sys
import argparse
import subprocess
from datetime import datetime
from pydub import AudioSegment

# --- 경로 설정 ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(os.path.join(PROJECT_ROOT, 'scripts'))

from create_subtitles import transcribe_video
from llm_correction import correct_srt_with_gemini

def create_subtitles(video_path: str, output_dir: str):
    """
    create_subtitles.py를 사용하여 SRT 자막 파일을 생성합니다.
    """
    print("--- SRT 자막 파일 생성 ---")
    transcribe_video(video_path, output_dir)

    # 파일명을 created.srt로 변경
    source_srt_path = os.path.join(output_dir, "source.srt")
    created_srt_path = os.path.join(output_dir, "created.srt")
    if os.path.exists(source_srt_path):
        os.rename(source_srt_path, created_srt_path)
        print(f"파일명을 'created.srt'로 변경했습니다: {created_srt_path}")
    return created_srt_path

def correct_subtitles(input_srt_path: str, output_srt_path: str):
    """
    llm_correction.py를 사용하여 SRT 파일을 Gemini API로 교정합니다.
    """
    print("--- SRT 파일 Gemini API 교정 ---")
    correct_srt_with_gemini(input_srt_path, output_srt_path)
    return output_srt_path

def synthesize_tts_from_srt(corrected_srt_path: str, video_path: str, tts_output_dir: str, language: str, temperature: float, exaggeration: float, cfg_weight: float, seed: int, sentence_group_size: int, reference_audio: str):
    """
    교정된 SRT 파일을 읽어 30줄씩 묶어 TTS 합성을 수행하고, 생성된 오디오 파일들을 병합합니다.
    """
    print("--- SRT 파일 기반 TTS 합성 시작 ---")
    os.makedirs(tts_output_dir, exist_ok=True)

    with open(corrected_srt_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    subtitle_blocks = []
    current_block = []
    for line in lines:
        if line.strip() == '':
            if current_block:
                subtitle_blocks.append(current_block)
                current_block = []
        else:
            current_block.append(line)
    if current_block:
        subtitle_blocks.append(current_block)

    processed_subtitle_texts = []
    for block in subtitle_blocks:
        text_lines = [line.strip() for line in block if not line.strip().isdigit() and '-->' not in line]
        processed_subtitle_texts.append(" ".join(text_lines).strip())

    video_file_name = os.path.splitext(os.path.basename(video_path))[0]
    today_str = datetime.now().strftime('%Y_%m_%d')
    classify_size = sentence_group_size
    for i in range(0, len(processed_subtitle_texts), classify_size):
        chunk_texts = processed_subtitle_texts[i:i+classify_size]
        loop_index = (i // classify_size) + 1
        
        text_to_speak = "\nー".join(chunk_texts)

        if not text_to_speak.strip():
            continue

        output_filename = f"{video_file_name}_{today_str}_{loop_index}.wav"
        output_path = os.path.join(tts_output_dir, output_filename)
        
        tts_command = [
            "/home/jay-gim/dev/Chatterbox-TTS-Server/venv/bin/python",
            "/home/jay-gim/dev/Chatterbox-TTS-Server/command.py", text_to_speak.strip(),
            "--voice-mode", "clone",
            "--reference-audio", reference_audio,
            "--output", output_path,
            "--language", language,
            "--speed-factor", "1.0",
            "--temperature", str(temperature),
            "--exaggeration", str(exaggeration),
            "--cfg_weight", str(cfg_weight),
            "--seed", str(seed)
        ]
        
        print(f"--- TTS 명령어 실행 ({loop_index}/{len(processed_subtitle_texts)//classify_size + 1}) ---")
        subprocess.run(tts_command)

    print("--- 모든 TTS 파일 생성 완료 ---")
    merged_output_path = merge_audio_files(tts_output_dir, silence_duration_ms=200)
    
    print(f"--- 모든 오디오 파일 병합 완료 ---")
    print(f"병합된 파일이 다음 경로에 저장되었습니다: {merged_output_path}")

def merge_audio_files(tts_output_dir: str, silence_duration_ms: int = 200):
    """
    생성된 오디오 파일들을 병합하고, 파일들 사이에 묵음을 추가합니다.
    """
    print("--- 생성된 오디오 파일 병합 시작 ---")
    
    # tts_output_dir에서 .wav 파일들을 찾아 리스트에 추가
    generated_files = [os.path.join(tts_output_dir, f) for f in os.listdir(tts_output_dir) if f.endswith('.wav')]

    silence = AudioSegment.silent(duration=silence_duration_ms)
    combined = AudioSegment.empty()
    
    def get_filenumber(path):
        try:
            # 파일 이름에서 숫자 부분을 추출하여 정렬
            return int(os.path.splitext(os.path.basename(path))[0].split('_')[-1])
        except:
            return -1

    generated_files.sort(key=get_filenumber)

    for i, file_path in enumerate(generated_files):
        if os.path.exists(file_path):
            audio = AudioSegment.from_wav(file_path)
            combined += audio
            if i < len(generated_files) - 1:
                combined += silence
            print(f"병합 완료: {os.path.basename(file_path)}")

    merged_output_path = os.path.join(tts_output_dir, "merged_output.wav")
    combined.export(merged_output_path, format="wav")
    
    return merged_output_path

def main():
    parser = argparse.ArgumentParser(description="비디오에서 자막 생성, 교정, TTS 합성 파이프라인을 실행합니다.")
    
    # UI 실행 옵션
    parser.add_argument("--ui", action="store_true", help="GUI를 실행합니다.")

    # 파일 시스템 경로 관련
    parser.add_argument("--video_path", type=str, help="처리할 비디오 파일 경로입니다.")
    parser.add_argument("--subtitles_dir", type=str, default=os.path.join(PROJECT_ROOT, "data/01_subtitles"),
                        help="자막 파일 출력 디렉터리입니다. (기본값: data/01_subtitles)")
    parser.add_argument("--corrected_dir", type=str, default=os.path.join(PROJECT_ROOT, "data/02_corrected_subtitles"),
                        help="교정된 자막 파일 출력 디렉터리입니다. (기본값: data/02_corrected_subtitles)")
    parser.add_argument("--tts_output_dir", type=str, default=os.path.join(PROJECT_ROOT, "data/03_tts_output"),
                        help="TTS 합성 오디오 파일 출력 디렉터리입니다. (기본값: data/03_tts_output)")

    # 옵션 관련
    parser.add_argument("--language", type=str, default="ja", help="TTS 언어입니다.")
    parser.add_argument("--temperature", type=float, default=0.8, help="TTS temperature입니다. (0 ~ 1.0)")
    parser.add_argument("--exaggeration", type=float, default=1.0, help="TTS exaggeration입니다. (0 ~ 2.0)")
    parser.add_argument("--cfg_weight", type=float, default=0.6, help="TTS cfg_weight입니다. (0 ~ 1.0)")
    parser.add_argument("--seed", type=int, default=40, help="TTS seed입니다. (0 ~ 65,536)")
    parser.add_argument("--sentence_group_size", type=int, default=1, help="TTS 문장 그룹 크기입니다. (0 ~ 10)")
    parser.add_argument("--reference_audio", type=str, default=None, help="TTS 클론을 위한 참조 오디오 파일 경로입니다.")

    args = parser.parse_args()

    if args.ui:
        from ui import App
        app = App()
        app.mainloop()
    else:
        if not args.video_path:
            parser.error("--video_path is required when not running in UI mode.")
        
        # 1. SRT 자막 생성
        created_srt_path = create_subtitles(args.video_path, args.subtitles_dir)

        # 2. SRT 교정
        corrected_srt_path = os.path.join(args.corrected_dir, "corrected.srt")
        os.makedirs(args.corrected_dir, exist_ok=True)
        correct_subtitles(created_srt_path, corrected_srt_path)

        # 3. TTS 합성
        synthesize_tts_from_srt(
            corrected_srt_path, 
            args.video_path,
            args.tts_output_dir,
            args.language,
            args.temperature,
            args.exaggeration,
            args.cfg_weight,
            args.seed,
            args.sentence_group_size,
            reference_audio=args.reference_audio
        )
if __name__ == "__main__":
    main()