import os
import argparse
from pydub import AudioSegment
import glob

def merge_audio_files(input_dir: str, output_file: str, pattern: str, silence_duration_ms: int = 200):
    """
    주어진 패턴과 일치하는 오디오 파일들을 병합하고, 파일들 사이에 묵음을 추가합니다.
    """
    print(f"--- 오디오 파일 병합 시작 ---")
    print(f"입력 디렉토리: {input_dir}")
    print(f"파일명 패턴: '{pattern}'")
    print(f"출력 파일: {output_file}")
    print(f"파일 간 묵음: {silence_duration_ms}ms")

    search_pattern = os.path.join(input_dir, pattern)
    generated_files = glob.glob(search_pattern)

    if not generated_files:
        print(f"--- 패턴 '{pattern}'과(와) 일치하는 오디오 파일을 찾을 수 없습니다. ---")
        return

    def get_filenumber(path):
        """파일 이름의 마지막 숫자 부분을 추출하여 정렬 기준으로 사용합니다."""
        try:
            basename = os.path.splitext(os.path.basename(path))[0]
            # 파일 이름의 마지막 '_' 뒤에 오는 숫자 부분을 추출합니다.
            return int(basename.split('_')[-1])
        except (ValueError, IndexError):
            # 숫자 부분을 찾을 수 없으면 파일 순서를 보장하기 위해 -1을 반환합니다.
            return -1

    # 파일 이름의 숫자 부분을 기준으로 정렬합니다.
    generated_files.sort(key=get_filenumber)

    print("\n--- 병합할 파일 목록 (순서대로) ---")
    for f in generated_files:
        print(os.path.basename(f))
    print("-------------------------------------\n")

    silence = AudioSegment.silent(duration=silence_duration_ms)
    combined = AudioSegment.empty()

    for i, file_path in enumerate(generated_files):
        if os.path.exists(file_path):
            try:
                # 파일 확장자를 기반으로 오디오를 로드합니다.
                file_extension = os.path.splitext(file_path)[1].lower()
                if file_extension == '.wav':
                    audio = AudioSegment.from_wav(file_path)
                elif file_extension == '.mp3':
                    audio = AudioSegment.from_mp3(file_path)
                elif file_extension == '.flac':
                    audio = AudioSegment.from_flac(file_path)
                else:
                    print(f"지원하지 않는 파일 형식입니다: {file_path}")
                    continue
                
                combined += audio
                if i < len(generated_files) - 1:
                    combined += silence
                print(f"병합 완료: {os.path.basename(file_path)}")
            except Exception as e:
                print(f"파일 처리 중 오류 발생 {file_path}: {e}")


    # 출력 디렉토리가 존재하지 않으면 생성합니다.
    output_dir = os.path.dirname(output_file)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    # 최종 파일을 내보냅니다.
    output_format = os.path.splitext(output_file)[1].lower().replace('.', '')
    if not output_format:
        output_format = 'wav' # 기본 포맷
        output_file += '.wav'

    combined.export(output_file, format=output_format)
    print(f"\n--- 모든 오디오 파일 병합 완료 ---")
    print(f"병합된 파일이 다음 경로에 저장되었습니다: {output_file}")

def main():
    parser = argparse.ArgumentParser(description="디렉토리 내의 오디오 파일들을 병합합니다.")
    
    parser.add_argument("input_dir", type=str, 
                        help="병합할 오디오 파일들이 있는 디렉토리 경로입니다.")
    parser.add_argument("output_file", type=str, 
                        help="병합된 오디오 파일의 출력 경로입니다. (예: merged_output.wav)")
    parser.add_argument("--pattern", type=str, default="*.wav", 
                        help="병합할 파일들을 선택하기 위한 glob 패턴입니다. (기본값: '*.wav')")
    parser.add_argument("--silence_ms", type=int, default=200, 
                        help="오디오 파일 사이에 추가할 묵음의 길이(ms)입니다. (기본값: 200)")

    args = parser.parse_args()

    merge_audio_files(args.input_dir, args.output_file, args.pattern, args.silence_ms)

if __name__ == "__main__":
    main()
