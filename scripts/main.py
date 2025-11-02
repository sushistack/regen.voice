import os
import sys
import argparse
import subprocess
from datetime import datetime

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

def synthesize_tts_from_srt(corrected_srt_path: str, video_path: str, tts_output_dir: str):
    """
    교정된 SRT 파일을 읽어 30줄씩 묶어 TTS 합성을 수행합니다.
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

    # 숫자와 타임스탬프를 제외한 텍스트 라인만 미리 추출
    processed_subtitle_texts = []
    for block in subtitle_blocks:
        text_lines = [line.strip() for line in block if not line.strip().isdigit() and '-->' not in line]
        processed_subtitle_texts.append(" ".join(text_lines).strip())

    video_file_name = os.path.splitext(os.path.basename(video_path))[0]
    today_str = datetime.now().strftime('%Y_%m_%d')
    classify_size = 5

    for i in range(0, len(processed_subtitle_texts), classify_size):
        chunk_texts = processed_subtitle_texts[i:i+classify_size]
        loop_index = (i // classify_size) + 1
        
        text_to_speak = "\nー".join(chunk_texts)

        if not text_to_speak.strip():
            continue

        output_filename = f"{video_file_name}_{today_str}_{loop_index}.wav"
        output_path = os.path.join(tts_output_dir, output_filename)
        
        # TTS 명령어 생성
        tts_command = [
            "/home/jay-gim/dev/Chatterbox-TTS-Server/venv/bin/python",
            "/home/jay-gim/dev/Chatterbox-TTS-Server/command.py", text_to_speak.strip(),
            "--voice-mode", "clone",
            "--reference-audio", "/home/jay-gim/dev/Chatterbox-TTS-Server/reference_audio/normal_man.wav",
            "--output", output_path,
            "--language", "ja",
            "--speed-factor", "1.0",
            "--temperature", "0.8",
            "--exaggeration", "1.1",
            "--cfg_weight", "0.6",
            "--seed", "41"
        ]
        
        print(f"--- TTS 명령어 실행 ({loop_index}/{len(processed_subtitle_texts)//classify_size + 1}) ---")
        subprocess.run(tts_command)

def main():
    parser = argparse.ArgumentParser(description="비디오에서 자막 생성, 교정, TTS 합성 파이프라인을 실행합니다.")
    parser.add_argument("--video_path", type=str, default=os.path.join(PROJECT_ROOT, "data/00_videos/sample.mp4"),
                        help="처리할 비디오 파일 경로입니다. (기본값: data/00_videos/sample.mp4)")
    parser.add_argument("--subtitles_dir", type=str, default=os.path.join(PROJECT_ROOT, "data/01_subtitles"),
                        help="자막 파일 출력 디렉터리입니다. (기본값: data/01_subtitles)")
    parser.add_argument("--corrected_dir", type=str, default=os.path.join(PROJECT_ROOT, "data/02_corrected_subtitles"),
                        help="교정된 자막 파일 출력 디렉터리입니다. (기본값: data/02_corrected_subtitles)")
    parser.add_argument("--tts_output_dir", type=str, default=os.path.join(PROJECT_ROOT, "data/03_tts_output"),
                        help="TTS 합성 오디오 파일 출력 디렉터리입니다. (기본값: data/03_tts_output)")

    args = parser.parse_args()

    # 1. SRT 자막 생성
    # created_srt_path = create_subtitles(args.video_path, args.subtitles_dir)

    # 2. SRT 교정
    corrected_srt_path = os.path.join(args.corrected_dir, "corrected.srt")
    # os.makedirs(args.corrected_dir, exist_ok=True)
    # correct_subtitles(created_srt_path, corrected_srt_path)

    # 3. TTS 합성
    synthesize_tts_from_srt(corrected_srt_path, args.video_path, args.tts_output_dir)

if __name__ == "__main__":
    main()