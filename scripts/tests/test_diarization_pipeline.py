# -*- coding: utf-8 -*-
import os
import subprocess
import pytest
import sys

# --- 테스트 경로 설정 ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.append(PROJECT_ROOT)

SCRIPT_PATH = os.path.join(PROJECT_ROOT, 'scripts', 'run_diarization_pipeline.py')
INPUT_VIDEO_PATH = os.path.join(PROJECT_ROOT, 'data', 'input_videos', 'sample.mp4')
OUTPUT_DIR = os.path.join(PROJECT_ROOT, 'data', 'output', 'diarization_test')
VENV_PYTHON = os.path.join(PROJECT_ROOT, '.venv', 'Scripts', 'python.exe')

@pytest.fixture(scope="module")
def setup_test_environment():
    """테스트 실행 전 환경을 설정하고 필수 파일들을 확인하는 Fixture"""
    # 테스트 출력 디렉터리 정리 및 생성
    if os.path.exists(OUTPUT_DIR):
        for f in os.listdir(OUTPUT_DIR):
            os.remove(os.path.join(OUTPUT_DIR, f))
    else:
        os.makedirs(OUTPUT_DIR)
        
    # 테스트 비디오 파일 존재 여부 확인
    if not os.path.exists(INPUT_VIDEO_PATH):
        pytest.fail(f"테스트 비디오 파일을 찾을 수 없습니다: {INPUT_VIDEO_PATH}")
    
    yield

    # 테스트 후 정리 (필요 시)
    # print("테스트 환경 정리")


def test_diarization_from_video(setup_test_environment):
    """
    diarize.py 스크립트가 비디오 파일을 입력받아 화자 분리된 SRT 파일을 정상적으로 생성하는지 테스트합니다.
    """
    command = [
        VENV_PYTHON,
        SCRIPT_PATH,
        "-i", INPUT_VIDEO_PATH,
        "--output_dir", OUTPUT_DIR,
        "--whisper-model", "tiny",  # 테스트 시간을 줄이기 위해 작은 모델 사용
        "--no-stem" # 테스트 시 음원 분리 비활성화하여 속도 향상
    ]
    
    print(f"Executing test command: {' '.join(command)}")
    
    try:
        # 스크립트 실행 (타임아웃을 길게 설정)
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
            encoding='utf-8',
            errors='replace', # 인코딩 오류 발생 시 대체 문자로 처리
            timeout=1200  # 20분
        )
        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)

    except subprocess.TimeoutExpired as e:
        pytest.fail(f"Script execution timed out (1200s):\nSTDOUT:\n{e.stdout}\nSTDERR:\n{e.stderr}")
    except subprocess.CalledProcessError as e:
        pytest.fail(f"Script execution failed (Exit Code: {e.returncode}):\nSTDOUT:\n{e.stdout}\nSTDERR:\n{e.stderr}")

    # 예상 출력 파일 경로
    video_basename = os.path.splitext(os.path.basename(INPUT_VIDEO_PATH))[0]
    expected_srt_file = os.path.join(OUTPUT_DIR, f"{video_basename}.srt")
    
    # 1. 최종 SRT 파일이 생성되었는지 확인
    assert os.path.exists(expected_srt_file), f"Final output file {expected_srt_file} was not created."

    # 2. 파일 내용이 비어있지 않은지 확인
    with open(expected_srt_file, 'r', encoding='utf-8') as f:
        content = f.read()
    assert len(content) > 0, f"Output file {expected_srt_file} is empty."
    
    # 3. 화자 정보가 포함되어 있는지 확인 (예: Speaker 1:)
    assert "Speaker " in content, "Speaker information ('Speaker ...') not found in SRT file."