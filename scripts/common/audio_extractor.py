import os
import subprocess
import tempfile

def extract_audio(video_path: str, output_dir: str) -> str:
    """
    ffmpeg을 사용하여 비디오 파일에서 오디오를 추출합니다.
    16kHz, 16-bit, single-channel WAV 파일로 변환합니다.
    Args:
        video_path (str): 입력 비디오 파일의 경로.
        output_dir (str): 임시 오디오 파일을 저장할 디렉터리.
    Returns:
        str: 생성된 임시 WAV 파일의 경로.
    Raises:
        FileNotFoundError: 비디오 파일이 존재하지 않을 경우.
        subprocess.CalledProcessError: ffmpeg 실행에 실패할 경우.
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"입력 비디오 파일을 찾을 수 없습니다: {video_path}")

    temp_wav_path = tempfile.NamedTemporaryFile(
        prefix="temp_audio_",
        suffix=".wav",
        dir=output_dir,
        delete=False
    ).name

    print(f"임시 오디오 파일 생성 중: {temp_wav_path}")

    command = [
        "ffmpeg",
        "-i", video_path,
        "-ar", "16000",      # 샘플링 레이트를 16kHz로 설정
        "-ac", "1",           # 오디오 채널을 1개(모노)로 설정
        "-c:a", "pcm_s16le",  # 16-bit PCM 오디오 코덱 사용
        "-y",                 # 이미 파일이 존재하면 덮어쓰기
        temp_wav_path
    ]

    try:
        # ffmpeg 실행 시 자세한 로그는 숨깁니다.
        subprocess.run(
            command,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE
        )
        print("오디오 추출 완료.")
        return temp_wav_path
    except subprocess.CalledProcessError as e:
        print(f"ffmpeg 실행 중 오류 발생:")
        print(e.stderr.decode('utf-8'))
        # 실패 시 임시 파일 삭제
        if os.path.exists(temp_wav_path):
            os.remove(temp_wav_path)
        raise
    except FileNotFoundError:
        print("오류: ffmpeg가 설치되어 있지 않거나 PATH에 설정되지 않았습니다.")
        raise
