import os
import sys
import argparse

# --- 경로 설정 ---
# 이 스크립트가 있는 디렉토리(scripts)를 sys.path에 추가하여
# create_subtitles와 llm_correction을 임포트할 수 있게 함.
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# scripts 폴더의 상위 폴더(프로젝트 루트)에서도 모듈을 찾을 수 있게 설정할 필요가 있다면 추가
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)

import create_subtitles
import llm_correction

def main():
    parser = argparse.ArgumentParser(description="Whisper로 자막을 생성하고 Gemini LLM으로 교정합니다.")
    parser.add_argument("--video_path", type=str, required=True, help="처리할 비디오 파일의 경로입니다.")
    parser.add_argument("--output_dir", type=str, required=True, help="출력 결과물을 저장할 디렉터리입니다.")
    parser.add_argument("--language", type=str, default="ja", help="음성 인식에 사용할 언어입니다. (기본값: ja)")
    parser.add_argument("--model_size", type=str, default="turbo", choices=["tiny", "base", "small", "medium", "turbo", "large"], 
                        help="Whisper 모델 크기입니다. (기본값: turbo)")
    
    args = parser.parse_args()
    
    # 출력 디렉터리 확인 및 생성
    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)

    # 1단계: Whisper를 이용한 자막 생성
    print("\n========== [1단계] Whisper 자막 생성 시작 ==========")
    generated_srt_path = create_subtitles.transcribe_video(
        video_path=args.video_path, 
        output_dir=args.output_dir, 
        language=args.language, 
        model_size=args.model_size
    )
    print(f"========== [1단계] 완료: {generated_srt_path} ==========\n")

    # 2단계: LLM을 이용한 자막 교정
    print("========== [2단계] Gemini LLM 자막 교정 시작 ==========")
    corrected_srt_path = os.path.join(args.output_dir, "corrected.srt")
    
    llm_correction.correct_srt_with_gemini(
        source_srt_path=generated_srt_path,
        output_srt_path=corrected_srt_path
    )
    print(f"========== [2단계] 완료: {corrected_srt_path} ==========\n")
    
    print(f"모든 작업이 완료되었습니다.\n최종 파일: {corrected_srt_path}")

if __name__ == "__main__":
    main()
