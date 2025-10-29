import os
import sys
import argparse
import srt
import torchaudio
from chatterbox.tts import ChatterboxTTS
from pydub import AudioSegment

# --- 경로 설정 ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(os.path.join(PROJECT_ROOT, 'scripts'))

def generate_audio_from_srt(srt_path: str, output_dir: str):
    """
    SRT 파일의 각 자막 라인을 Chatterbox를 사용하여 음성 파일로 변환합니다.
    """
    print(f"--- Chatterbox TTS 오디오 생성 시작 ---")
    print(f"입력 SRT 파일: {srt_path}")
    print(f"출력 디렉터리: {output_dir}")

    os.makedirs(output_dir, exist_ok=True)

    try:
        with open(srt_path, 'r', encoding='utf-8') as f:
            srt_content = f.read()
    except FileNotFoundError:
        print(f"오류: 입력 파일 {srt_path}를 찾을 수 없습니다.")
        return

    subtitles = list(srt.parse(srt_content))
    
    try:
        # CUDA 사용 시도, 실패 시 CPU 사용
        model = ChatterboxTTS.from_pretrained(device="cuda")
        print("ChatterboxTTS가 CUDA를 사용하여 초기화되었습니다.")
    except Exception as e:
        print(f"CUDA를 사용할 수 없거나 로딩 중 오류가 발생했습니다: {e}. CPU로 전환합니다.")
        model = ChatterboxTTS.from_pretrained(device="cpu")
        print("ChatterboxTTS가 CPU를 사용하여 초기화되었습니다.")

    for sub in subtitles:
        output_filename = f"{sub.index}.wav"
        output_path = os.path.join(output_dir, output_filename)
        
        try:
            audio_waveform = model.generate(sub.content)
            torchaudio.save(output_path, audio_waveform.cpu(), 24000)
            print(f"  생성 완료: {output_path}")
        except Exception as e:
            print(f"  오류 발생 (자막 ID: {sub.index}): {e}")

    print("--- 모든 자막에 대한 오디오 생성 완료 ---")

def merge_audio_files(audio_dir: str, srt_path: str, output_path: str):
    """
    타임스탬프에 맞춰 개별 오디오 파일들을 하나의 파일로 병합합니다.
    """
    print(f"--- 오디오 파일 병합 시작 ---")
    print(f"오디오 디렉터리: {audio_dir}")
    print(f"SRT 파일: {srt_path}")
    print(f"출력 파일: {output_path}")

    try:
        with open(srt_path, 'r', encoding='utf-8') as f:
            srt_content = f.read()
    except FileNotFoundError:
        print(f"오류: SRT 파일 {srt_path}를 찾을 수 없습니다.")
        return

    subtitles = list(srt.parse(srt_content))
    
    # 최종 오디오의 총 길이를 계산합니다.
    total_duration = subtitles[-1].end.total_seconds() * 1000
    final_audio = AudioSegment.silent(duration=total_duration)

    for sub in subtitles:
        audio_path = os.path.join(audio_dir, f"{sub.index}.wav")
        if os.path.exists(audio_path):
            try:
                segment = AudioSegment.from_wav(audio_path)
                start_time = sub.start.total_seconds() * 1000
                final_audio = final_audio.overlay(segment, position=start_time)
                print(f"  병합: {audio_path}")
            except Exception as e:
                print(f"  오디오 파일 병합 중 오류 발생 ({audio_path}): {e}")
        else:
            print(f"  경고: 오디오 파일을 찾을 수 없습니다: {audio_path}")

    try:
        final_audio.export(output_path, format="wav")
        print(f"--- 오디오 병합 완료. 최종 파일: {output_path} ---")
    except Exception as e:
        print(f"  최종 오디오 파일 저장 중 오류 발생: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Chatterbox TTS를 사용하여 SRT 파일로부터 음성을 생성하고 병합합니다.")
    parser.add_argument("srt_path", type=str, help="입력 SRT 파일의 경로입니다.")
    parser.add_argument("output_dir", type=str, help="생성된 개별 오디오 파일을 저장할 디렉터리입니다.")
    parser.add_argument("merged_output_path", type=str, help="병합된 최종 오디오 파일의 경로입니다.")
    
    args = parser.parse_args()
    
    generate_audio_from_srt(args.srt_path, args.output_dir)
    merge_audio_files(args.output_dir, args.srt_path, args.merged_output_path)
