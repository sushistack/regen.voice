import os
import subprocess
import pytest
import sys

# --- 테스트 경로 설정 ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.append(PROJECT_ROOT)

SCRIPT_PATH = os.path.join(PROJECT_ROOT, 'scripts', 'diarization.py')
EXECUTABLE_PATH = os.path.join("C:", os.sep, "Users", "USER", "dev", "whisper.cpp", "build", "bin", "Release", "whisper-cli.exe")
MODEL_PATH = os.path.join(PROJECT_ROOT, "data", "_models", "ggml-medium.bin")
INPUT_VIDEO_PATH = os.path.join(PROJECT_ROOT, 'data', 'input_videos', 'sample.mp4')
OUTPUT_DIR = os.path.join(PROJECT_ROOT, 'data', 'output', 'diarization')
VENV_PYTHON = os.path.join(PROJECT_ROOT, '.venv', 'Scripts', 'python.exe')

@pytest.fixture(scope="module")
def setup_test_environment():
    """테스트 실행 전 환경을 설정하고 필수 파일들을 확인하는 Fixture"""
    if os.path.exists(OUTPUT_DIR):
        for f in os.listdir(OUTPUT_DIR):
            os.remove(os.path.join(OUTPUT_DIR, f))
    else:
        os.makedirs(OUTPUT_DIR)
        
    if not os.path.exists(EXECUTABLE_PATH):
        pytest.skip(f"whisper-cli.exe를 찾을 수 없습니다. 테스트를 건너뜁니다: {EXECUTABLE_PATH}")

    if not os.path.exists(MODEL_PATH):
        pytest.skip(f"모델 파일을 찾을 수 없습니다. 테스트를 건너뜁니다: {MODEL_PATH}")

    if not os.path.exists(INPUT_VIDEO_PATH):
        pytest.fail(f"테스트 비디오 파일을 찾을 수 없습니다: {INPUT_VIDEO_PATH}")

def test_transcription_script_creates_srt_file(setup_test_environment):
    """
    diarization.py (whisper.cpp 기반) 스크립트가 source.srt 파일을 정상적으로 생성하는지 테스트합니다.
    """
    command = [
        VENV_PYTHON,
        SCRIPT_PATH,
        INPUT_VIDEO_PATH,
        "--output_dir", OUTPUT_DIR,
        "--language", "ja"
    ]
    
    print(f"테스트 명령어 실행: {' '.join(command)}")
    
    try:
        subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
            encoding='utf-8',
            timeout=600
        )
    except subprocess.CalledProcessError as e:
        pytest.fail(f"스크립트 실행 실패 (Exit Code: {e.returncode}):\nSTDOUT:\n{e.stdout}\nSTDERR:\n{e.stderr}")

    expected_srt_file = os.path.join(OUTPUT_DIR, "source.srt")
    assert os.path.exists(expected_srt_file), f"최종 출력 파일 {expected_srt_file}이 생성되지 않았습니다."

    with open(expected_srt_file, 'r', encoding='utf-8') as f:
        content = f.read()
    assert len(content) > 0, f"출력 파일 {expected_srt_file}이 비어있습니다."
    
    assert "-->" in content, "SRT 파일에 타임스탬프 구분자 '-->'가 없습니다."