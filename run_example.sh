#!/bin/bash

# 가상환경 활성화 (필요한 경우)
# source venv/bin/activate

# 스크립트 실행 예시
# --video_path: 비디오 파일 경로
# --output_dir: 결과물이 저장될 폴더 경로
# --language: 언어 코드 (기본값: ja)
# --model_size: Whisper 모델 크기 (기본값: turbo)

echo "자막 생성 및 교정 스크립트를 실행합니다..."

venv/bin/python3 scripts/auto_subtitle.py \
    --video_path "/home/jay-gim/dev/regen.voice/data/00_videos/SONE_841_cut.mp4" \
    --output_dir "/home/jay-gim/dev/regen.voice/data/01_subtitles" \
    --language "ja" \
    --model_size "turbo"

echo "스크립트 실행이 완료되었습니다."
