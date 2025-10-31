import os
import sys
import argparse
import whisper
import torch
from typing import Optional

# --- 경로 설정 ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(os.path.join(PROJECT_ROOT, 'scripts'))

from common.audio_extractor import extract_audio
from common.gpu_utils import check_gpu_availability, get_device  # 새 모듈 임포트

def transcribe_video(video_path: str, output_dir: str, language: str = "ja", model_size: str = "turbo"):
    """
    OpenAI Whisper 라이브러리를 사용하여 비디오 파일의 음성을 텍스트로 변환합니다.
    AMD GPU (ROCm) 지원으로 GPU 가속 가능.
    """
    print(f"--- OpenAI Whisper를 통한 음성 변환 시작 ---")
    print(f"비디오: {video_path}, 모델: {model_size}, 언어: {language}")
    
    # GPU 가속 확인 (모듈화된 로직 사용)
    gpu_info = check_gpu_availability()
    device = get_device()
    print(f"GPU 상태: {gpu_info['details']}")
    
    # 출력 디렉터리 생성
    os.makedirs(output_dir, exist_ok=True)

    audio_path: Optional[str] = None
    try:
        audio_path = extract_audio(video_path, output_dir)
        print(f"임시 오디오 파일이 생성되었습니다: {audio_path}")

        print("Whisper 모델을 로드하고 변환을 시작합니다...")
        model = whisper.load_model(model_size, device=device)
        result = model.transcribe(audio_path, language=language, verbose=True)

        output_filename_no_ext = os.path.splitext(os.path.basename(video_path))[0]
        srt_path = os.path.join(output_dir, f"{output_filename_no_ext}.srt")
        
        with open(srt_path, 'w', encoding='utf-8') as f:
            for segment in result['segments']:
                start_time = format_timestamp(segment['start'])
                end_time = format_timestamp(segment['end'])
                text = segment['text'].strip()
                f.write(f"{segment['id'] + 1}\n{start_time} --> {end_time}\n{text}\n\n")
        
        print(f"음성 변환 완료. SRT 파일이 저장되었습니다: {srt_path}")

        target_srt_path = os.path.join(output_dir, "created.srt")
        if os.path.exists(target_srt_path):
            os.remove(target_srt_path)
        os.rename(srt_path, target_srt_path)
        print(f"파일명을 'created.srt'로 변경했습니다: {target_srt_path}")
        
        return target_srt_path

    except Exception as e:
        print(f"Whisper 변환 중 오류가 발생했습니다: {e}")
        raise
    finally:
        # 임시 오디오 파일 정리
        if audio_path and os.path.exists(audio_path):
            print(f"임시 파일을 정리합니다: {audio_path}")
            os.remove(audio_path)

def format_timestamp(seconds: float) -> str:
    """SRT 형식의 타임스탬프 생성 (HH:MM:SS,mmm)"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OpenAI Whisper를 사용하여 비디오 파일의 음성을 텍스트로 변환합니다.")
    parser.add_argument("video_path", type=str, help="처리할 비디오 파일의 경로입니다.")
    parser.add_argument("--output_dir", type=str, required=True, help="출력 SRT 파일을 저장할 디렉터리입니다.")
    parser.add_argument("--language", type=str, default="ja", help="음성 인식에 사용할 언어입니다. (기본값: ja)")
    parser.add_argument("--model_size", type=str, default="medium", choices=["tiny", "base", "small", "medium", "large"], 
                        help="Whisper 모델 크기입니다. (기본값: medium)")
    
    args = parser.parse_args()
    
    transcribe_video(args.video_path, args.output_dir, args.language, args.model_size)