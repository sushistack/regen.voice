import os
import sys
import argparse
import subprocess
import requests
import yaml
import time

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

def main():
    parser = argparse.ArgumentParser(description="비디오에서 자막 생성, 교정, TTS 합성 파이프라인을 실행합니다.")
    parser.add_argument("chatterbox_path", type=str, help="Chatterbox 설치 경로입니다.")
    parser.add_argument("--video_path", type=str, default=os.path.join(PROJECT_ROOT, "data/00_videos/sample.mp4"),
                        help="처리할 비디오 파일 경로입니다. (기본값: data/00_videos/sample.mp4)")
    parser.add_argument("--subtitles_dir", type=str, default=os.path.join(PROJECT_ROOT, "data/01_subtitles"),
                        help="자막 파일 출력 디렉터리입니다. (기본값: data/01_subtitles)")
    parser.add_argument("--corrected_dir", type=str, default=os.path.join(PROJECT_ROOT, "data/02_corrected_subtitles"),
                        help="교정된 자막 파일 출력 디렉터리입니다. (기본값: data/02_corrected_subtitles)")

    args = parser.parse_args()

    # 1. SRT 자막 생성
    created_srt_path = create_subtitles(args.video_path, args.subtitles_dir)

    # 2. SRT 교정
    corrected_srt_path = os.path.join(args.corrected_dir, "corrected.srt")
    os.makedirs(args.corrected_dir, exist_ok=True)
    correct_subtitles(created_srt_path, corrected_srt_path)

if __name__ == "__main__":
    main()