import os
import sys
import subprocess
import argparse

# --- 경로 설정 ---
# 이 스크립트의 위치를 기준으로 프로젝트 루트 디렉터리를 찾습니다. (scripts -> project_root)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# `scripts` 디렉터리를 sys.path에 추가하여 `common` 모듈을 임포트할 수 있도록 합니다.
sys.path.append(os.path.join(PROJECT_ROOT, 'scripts'))

from common.audio_extractor import extract_audio

EXECUTABLE_PATH = os.path.join("C:", os.sep, "Users", "USER", "dev", "whisper.cpp", "build", "bin", "Release", "whisper-cli.exe")
MODEL_PATH = os.path.join(PROJECT_ROOT, "data", "_models", "ggml-medium.bin")


def transcribe_video(video_path: str, output_dir: str, language: str = "ja"):
    """
    whisper.cpp 실행 파일을 사용하여 비디오 파일의 음성을 텍스트로 변환합니다.
    """
    print(f"--- whisper.cpp 실행을 통한 음성 변환 시작 ---")
    print(f"비디오: {video_path}, 모델: {MODEL_PATH}, 언어: {language}")

    # 필수 파일들이 존재하는지 확인합니다.
    if not os.path.exists(EXECUTABLE_PATH):
        raise FileNotFoundError(f"whisper-cli.exe 파일을 찾을 수 없습니다: {EXECUTABLE_PATH}")
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(f"모델 파일을 찾을 수 없습니다: {MODEL_PATH}")

    # 출력 디렉터리가 없으면 생성합니다.
    os.makedirs(output_dir, exist_ok=True)

    audio_path = None
    try:
        # 1단계: 비디오에서 오디오 추출
        audio_path = extract_audio(video_path, output_dir)
        print(f"임시 오디오 파일이 생성되었습니다: {audio_path}")

        # 2단계: whisper.cpp 실행
        print("whisper.cpp 실행 파일을 실행합니다...")
        
        # 출력 파일 이름을 비디오 파일 이름과 동일하게 설정 (확장자 제외)
        output_filename_no_ext = os.path.splitext(os.path.basename(video_path))[0]
        
        command = [
            EXECUTABLE_PATH,
            "-m", MODEL_PATH,
            "-l", language,
            "-f", os.path.abspath(audio_path),
            "--output-srt",
            "--output-file", os.path.join(os.path.abspath(output_dir), output_filename_no_ext) # 확장자를 제외한 파일명 전달
        ]

        # whisper.cpp의 진행률을 stderr를 통해 직접 표시합니다.
        subprocess.run(command, check=True, stderr=sys.stderr, stdout=subprocess.DEVNULL)
        
        generated_srt_path = os.path.join(output_dir, f"{output_filename_no_ext}.srt")
        print(f"음성 변환 완료. SRT 파일이 저장되었습니다: {generated_srt_path}")

        # 3단계: 생성된 SRT 파일의 이름을 'source.srt'로 변경
        target_srt_path = os.path.join(output_dir, "source.srt")
        if os.path.exists(target_srt_path):
            os.remove(target_srt_path) # 이미 존재하면 덮어쓰기 위해 삭제
        os.rename(generated_srt_path, target_srt_path)
        print(f"파일명을 'source.srt'로 변경했습니다: {target_srt_path}")
        
        return target_srt_path

    except subprocess.CalledProcessError as e:
        print(f"whisper.cpp 실행 중 오류가 발생했습니다: {e}")
        raise
    finally:
        # 4단계: 임시 오디오 파일 정리
        if audio_path and os.path.exists(audio_path):
            print(f"임시 파일을 정리합니다: {audio_path}")
            os.remove(audio_path)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="whisper.cpp를 사용하여 비디오 파일의 음성을 텍스트로 변환합니다.")
    parser.add_argument("video_path", type=str, help="처리할 비디오 파일의 경로입니다.")
    parser.add_argument("--output_dir", type=str, required=True, help="출력 SRT 파일을 저장할 디렉터리입니다.")
    parser.add_argument("--language", type=str, default="ja", help="음성 인식에 사용할 언어입니다. (기본값: ja)")
    
    args = parser.parse_args()
    
    transcribe_video(args.video_path, args.output_dir, args.language)