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

def check_chatterbox_server(chatterbox_path: str):
    """
    Chatterbox 서버를 실행하고, 정상 접속 가능한지 확인합니다.
    """
    print("--- Chatterbox 서버 확인 및 실행 ---")
    config_path = os.path.join(chatterbox_path, '.config.yml')
    server_py_path = os.path.join(chatterbox_path, 'server.py')

    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Chatterbox 설정 파일을 찾을 수 없습니다: {config_path}")

    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
        port = config.get('PORT')
        if not port:
            raise ValueError("Chatterbox 설정 파일에 PORT가 설정되지 않았습니다.")

    # 서버가 이미 실행 중인지 확인
    try:
        response = requests.get(f"http://localhost:{port}", timeout=5)
        if response.status_code == 200:
            print(f"Chatterbox 서버가 이미 실행 중입니다. 포트: {port}")
            return port
    except requests.RequestException:
        pass

    # 서버 실행
    print(f"Chatterbox 서버를 실행합니다: {server_py_path}")
    subprocess.Popen([sys.executable, server_py_path], cwd=chatterbox_path)

    # 서버가 시작될 때까지 대기
    for _ in range(30):  # 30초 대기
        try:
            response = requests.get(f"http://localhost:{port}", timeout=5)
            if response.status_code == 200:
                print(f"Chatterbox 서버가 정상적으로 시작되었습니다. 포트: {port}")
                return port
        except requests.RequestException:
            time.sleep(1)

    raise RuntimeError("Chatterbox 서버가 시작되지 않았습니다.")

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

def upload_to_tts(corrected_srt_path: str, chatterbox_port: int):
    """
    교정된 SRT 파일을 Chatterbox TTS 서버에 업로드하여 음성 합성을 수행합니다.
    """
    print("--- Chatterbox TTS 서버에 SRT 파일 업로드 ---")
    url = f"http://localhost:{chatterbox_port}/synthesize"  # 예시 엔드포인트, 실제로 확인 필요

    with open(corrected_srt_path, 'rb') as f:
        files = {'file': f}
        response = requests.post(url, files=files)

    if response.status_code == 200:
        print("음성 합성이 완료되었습니다.")
        # 결과 파일 저장 등 추가 처리 가능
    else:
        print(f"TTS 업로드 실패: {response.status_code} - {response.text}")

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

    # 0. Chatterbox 서버 확인 및 실행
    chatterbox_port = check_chatterbox_server(args.chatterbox_path)

    # 1. SRT 자막 생성
    created_srt_path = create_subtitles(args.video_path, args.subtitles_dir)

    # 2. SRT 교정
    corrected_srt_path = os.path.join(args.corrected_dir, "corrected.srt")
    os.makedirs(args.corrected_dir, exist_ok=True)
    correct_subtitles(created_srt_path, corrected_srt_path)

    # 3. TTS 업로드
    upload_to_tts(corrected_srt_path, chatterbox_port)

if __name__ == "__main__":
    main()