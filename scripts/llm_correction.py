import os
import sys
import argparse
import srt
import re
import google.generativeai as genai
from dotenv import load_dotenv

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(os.path.join(PROJECT_ROOT, 'scripts'))

load_dotenv()
CORRECTION_PROMPT = '''You are an expert subtitle translator and editor. Your task is to correct the following list of Japanese subtitles.

**Instructions:**
1.  For each numbered line, provide a corrected version of the Japanese text.
2.  **Output Format:** Your response MUST be a numbered list matching the input. Each line MUST start with the number and a colon (e.g., "1: text"). Do NOT include any other text, explanations, or apologies in your response.
3.  **Correction Rules:**
    *   Correct any transcription errors (e.g., '??') based on the context of the surrounding lines.
    *   Fix all punctuation and spelling mistakes.
    *   If a sentence is too long (over 20 characters), do NOT split it into multiple lines. Instead, insert a '||' marker at the appropriate split point.
    *   Remove excessive and meaningless repetitions of characters or words (e.g., 'えええええ'), but keep natural filler words like 'ええと' or 'あの'.
    *   Preserve the original meaning of the sentence.

**Original Subtitles:**
{original_texts}

**Corrected Subtitles:**
'''

# Gemini API 설정
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY가 .env 파일에 설정되지 않았습니다.")
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('models/gemini-pro-latest')

def correct_srt_with_gemini(source_srt_path: str, output_srt_path: str):
    """
    Gemini API를 사용하여 SRT 파일의 내용을 한 번의 요청으로 교정합니다.
    """
    print(f"--- Gemini API를 사용한 SRT 교정 시작 ---")
    print(f"입력 SRT 파일: {source_srt_path}")

    try:
        with open(source_srt_path, 'r', encoding='utf-8') as f:
            srt_content = f.read()
    except FileNotFoundError:
        print(f"오류: 입력 파일 {source_srt_path}를 찾을 수 없습니다.")
        return

    subtitles = list(srt.parse(srt_content))
    
    # 모든 자막 내용을 하나의 문자열로 합칩니다。
    original_texts = "\n".join([f"{i+1}: {sub.content}" for i, sub in enumerate(subtitles)])

    prompt = CORRECTION_PROMPT.format(original_texts=original_texts)

    try:
        response = model.generate_content(prompt)
        corrected_text_block = response.text.strip()
        
        # 응답에서 교정된 문장들을 추출합니다.
        corrected_lines = re.findall(r"^\d+:\s*(.*)", corrected_text_block, re.MULTILINE)

        if not corrected_lines or len(corrected_lines) != len(subtitles):
            raise ValueError(f"오류: 원본 자막({len(subtitles)}개)과 교정된 자막({len(corrected_lines)}개)의 수가 일치하지 않거나, 응답 형식이 잘못되었습니다.")

        new_subtitles = []
        for i, sub in enumerate(subtitles):
            corrected_line = corrected_lines[i]
            if "||" in corrected_line:
                parts = corrected_line.split("||")
                num_parts = len(parts)
                duration_per_part = (sub.end - sub.start) / num_parts
                current_start = sub.start
                for part_text in parts:
                    new_end = current_start + duration_per_part
                    new_sub = srt.Subtitle(
                        index=len(new_subtitles) + 1,
                        start=current_start,
                        end=new_end,
                        content=part_text.strip()
                    )
                    new_subtitles.append(new_sub)
                    current_start = new_end
                    print(f'  분할된 교정: "{part_text.strip()}"')
            else:
                new_sub = srt.Subtitle(
                    index=len(new_subtitles) + 1,
                    start=sub.start,
                    end=sub.end,
                    content=corrected_line
                )
                new_subtitles.append(new_sub)
                print(f'  교정: "{sub.content}" -> "{corrected_line}"')

        corrected_subtitles = new_subtitles

    except Exception as e:
        print(f"  Gemini API 처리 중 오류 발생: {e}")
        # 오류 발생 시 원본 자막을 그대로 사용
        print("  오류로 인해 원본 자막을 사용합니다.")
        corrected_subtitles = subtitles

    # 교정된 자막을 새로운 SRT 파일로 저장
    final_srt_content = srt.compose(corrected_subtitles)
    try:
        with open(output_srt_path, 'w', encoding='utf-8') as f:
            f.write(final_srt_content)
        print(f"교정 완료. 새로운 SRT 파일이 저장되었습니다: {output_srt_path}")
    except IOError as e:
        print(f"오류: 출력 파일 {output_srt_path}를 쓰는 중 오류가 발생했습니다: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gemini API를 사용하여 SRT 파일의 내용을 교정합니다.")
    parser.add_argument("source_srt_path", type=str, help="교정할 원본 SRT 파일의 경로입니다.")
    parser.add_argument("output_srt_path", type=str, help="교정된 내용을 저장할 SRT 파일의 경로입니다.")
    
    args = parser.parse_args()
    
    correct_srt_with_gemini(args.source_srt_path, args.output_srt_path)
