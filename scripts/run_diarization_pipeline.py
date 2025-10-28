import os
import torch
import argparse
import sys
import warnings
import subprocess

# --- 경로 설정 ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
VENDOR_SCRIPT_PATH = os.path.join(PROJECT_ROOT, 'scripts', 'vendor', 'whisper-diarization', 'diarize.py')
VENV_PYTHON = os.path.join(PROJECT_ROOT, '.venv', 'Scripts', 'python.exe')

# scripts 및 common 경로 추가
sys.path.append(os.path.join(PROJECT_ROOT, 'scripts'))
from common.audio_extractor import extract_audio

# 불필요한 경고 메시지 숨기기
warnings.filterwarnings("ignore", category=UserWarning, module='pytorch_lightning')
warnings.filterwarnings("ignore", category=DeprecationWarning)


def is_gpu_available():
    """
    사용 가능한 GPU가 있는지 확인하고, 있으면 True를 반환합니다.
    """
    return torch.cuda.is_available()

def run_diarization_pipeline(input_path: str, output_dir: str, no_stem: bool, whisper_model: str, device: str, language: str = None, suppress_numerals: bool = False, batch_size: int = 8):
    """
    whisper-diarization 파이프라인을 서브프로세스로 실행합니다.
    """
    print("--- 화자 분리 및 음성 변환 시작 ---")
    
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"입력 파일을 찾을 수 없습니다: {input_path}")

    os.makedirs(output_dir, exist_ok=True)

    # 장치 설정: 사용자가 명시하지 않으면 GPU 우선 사용
    if device is None:
        device = "cuda" if is_gpu_available() else "cpu"
    
    print(f"사용 장치: {device}")
    print(f"입력 파일: {input_path}")
    print(f"모델: {whisper_model}")

    audio_path_to_process = None
    is_temp_audio = False
    try:
        # 입력 파일이 비디오인지 확인
        video_extensions = ['.mp4', '.mkv', '.mov', '.avi', '.flv', '.webm']
        if any(input_path.lower().endswith(ext) for ext in video_extensions):
            print("비디오 파일 감지됨. 오디오를 추출합니다...")
            audio_path_to_process = extract_audio(input_path, output_dir)
            is_temp_audio = True
            print(f"임시 오디오 파일이 생성되었습니다: {audio_path_to_process}")
        else:
            audio_path_to_process = input_path

        # vendor/diarize.py를 서브프로세스로 실행
        command = [
            VENV_PYTHON, VENDOR_SCRIPT_PATH,
            "-a", os.path.abspath(audio_path_to_process),
            "--whisper-model", whisper_model,
            "--device", device,
            "--batch-size", str(batch_size),
            # diarize.py는 출력 경로를 직접 지정하는 옵션이 없으므로,
            # 실행 후 결과 파일을 원하는 위치로 이동해야 합니다.
        ]
        if no_stem:
            command.append("--no-stem")
        if language:
            command.append("--language")
            command.append(language)
        if suppress_numerals:
            command.append("--suppress_numerals")

        print(f"Executing vendor script: {' '.join(command)}")
        subprocess.run(command, check=True, capture_output=True, text=True, encoding='utf-8', errors='replace')

        # 결과 파일은 vendor 스크립트의 기본 출력 위치(오디오 파일과 동일한 디렉토리)에 생성됩니다.
        processed_audio_basename = os.path.splitext(os.path.basename(audio_path_to_process))[0]
        generated_srt_path = os.path.join(os.path.dirname(audio_path_to_process), f"{processed_audio_basename}.srt")
        
        original_input_basename = os.path.splitext(os.path.basename(input_path))[0]
        final_srt_path = os.path.join(output_dir, f"{original_input_basename}.srt")

        if os.path.exists(generated_srt_path):
            if os.path.exists(final_srt_path):
                os.remove(final_srt_path)
            os.rename(generated_srt_path, final_srt_path)
            print(f"화자 분리 완료. 결과가 저장되었습니다: {final_srt_path}")
            return final_srt_path
        else:
            raise FileNotFoundError(f"화자 분리 결과 파일(.srt)이 생성되지 않았습니다: {generated_srt_path}")

    except subprocess.CalledProcessError as e:
        print(f"Vendor 스크립트 실행 실패 (Exit Code: {e.returncode}):\nSTDOUT:\n{e.stdout}\nSTDERR:\n{e.stderr}")
        raise
    except Exception as e:
        print(f"화자 분리 중 오류가 발생했습니다: {e}")
        raise
    finally:
        # 임시 오디오 파일 정리
        if is_temp_audio and audio_path_to_process and os.path.exists(audio_path_to_process):
            print(f"임시 오디오 파일을 삭제합니다: {audio_path_to_process}")
            os.remove(audio_path_to_process)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="whisper-diarization을 사용하여 비디오/오디오 파일의 화자를 분리하고 텍스트로 변환합니다.")
    parser.add_argument("-i", "--input_path", type=str, required=True, help="처리할 비디오 또는 오디오 파일의 경로입니다.")
    parser.add_argument("--output_dir", type=str, default=os.path.join(PROJECT_ROOT, 'data', 'output', 'diarization'), help="출력 파일을 저장할 디렉터리입니다.")
    parser.add_argument("--no-stem", action="store_true", help="음원 분리(stemming)를 비활성화합니다.")
    parser.add_argument("--whisper-model", type=str, default="medium", help="사용할 Whisper 모델입니다. (예: tiny, base, small, medium, large)")
    parser.add_argument("--device", type=str, default=None, help="사용할 장치를 선택합니다. (예: 'cuda', 'cpu'). 지정하지 않으면 자동으로 선택됩니다.")
    parser.add_argument("--language", type=str, default=None, help="음성 인식 언어를 수동으로 지정합니다.")
    parser.add_argument("--suppress_numerals", action="store_true", help="숫자를 발음대로 텍스트로 변환합니다. (정렬 정확도 향상)")
    parser.add_argument("--batch-size", type=int, default=8, help="추론 배치 크기입니다.")

    args = parser.parse_args()
    
    run_diarization_pipeline(
        input_path=args.input_path, 
        output_dir=args.output_dir, 
        no_stem=args.no_stem, 
        whisper_model=args.whisper_model, 
        device=args.device,
        language=args.language,
        suppress_numerals=args.suppress_numerals,
        batch_size=args.batch_size
    )
