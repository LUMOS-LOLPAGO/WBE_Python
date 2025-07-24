import tempfile, os, requests
import whisper
import numpy as np
from openai import OpenAI
from dotenv import load_dotenv
from worker.tts.tts_worker_process import generate_tts_mp3
import asyncio

# 환경 변수 로딩
load_dotenv()

# OpenAI API 키 가져오기
openai_api_key = os.getenv("OPENAI_API_KEY")
# OpenAI 클라이언트 객체 생성
client = OpenAI(api_key=openai_api_key)
# Whisper 모델 로딩 (large 모델 사용)
model = whisper.load_model("large")


# OpenAI 프롬프트 템플릿 파일 불러오는 메서드
def load_prompt_template(file_path: str) -> str:
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


# 음성 -> 텍스트 -> GPT 분석 -> TTS 응답 -> WebSocket 전송까지 담당하는 파이프라인
def whisper_pipeline(summoner_id, region, audio_data, audio_queue, loop):
    print(f"[🔊 Whisper] {summoner_id} 음성 분석 시작")

    # 입력된 float32 PCM 오디오 데이터를 임시 wav 파일로 저장
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmpfile:
        from scipy.io import wavfile
        wavfile.write(tmpfile.name, 16000, (audio_data * 32768).astype(np.int16))
        path = tmpfile.name

    # Whisper 모델로 음성 인식 (음성을 텍스트로 변환)
    result = model.transcribe(path)
    raw_text = result["text"]
    os.remove(path) # 임시 파일 삭제

    # stt 결과 출력
    print(f"[raw_text] : {raw_text}")

    # GPT 에 전달할 프롬프트 로드 및 텍스트 삽입
    prompt_template = load_prompt_template("prompt/champion_spell_prompt.txt")
    prompt = prompt_template.format(raw_text=raw_text)

    # 프롬프트를 이용하여 GPT-4 모델 호출
    try:
        gpt_response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=100
        )
    except Exception as e:
        print(f"[GPT 호출 오류]: {e}")
        return

    # GPT 응답에서 정제된 최종 텍스트 추출
    final_text = gpt_response.choices[0].message.content.strip()
    print(f"[🎯 결과] {summoner_id}: {final_text}")

    # Spring 서버로 결과 전송 ([챔피언 이름] [스펠 이름])
    response = requests.post("https://lolpago.com/spell", json={
        "summonerId": summoner_id,
        "finalText": final_text,
        "region": region
    })

    # Spring 서버 응답 CREATED 아니면 에러 처리
    if response.status_code != 201:
        print(f"Spring 서버 응답 실패: {response.status_code} - {response.text}")
        return

    # 서버 응답 데이터 파싱
    response_data = response.json()

    # 🎧 TTS 생성 (mp3 binary 반환)
    tts_mp3 = generate_tts_mp3(response_data["spellCheckMessage"])
    if tts_mp3:
        # WebSocket 송신 큐에 TTS mp3 데이터 넣기 (비동기 처리)
        asyncio.run_coroutine_threadsafe(audio_queue.put(tts_mp3), loop)

    # 쿨다운 요청 파라미터 구성
    spell_cool_down_params = {
        "summonerId": summoner_id,
        "championName": response_data["championName"],
        "spellName": response_data["spellName"]
    }

    # 스펠 쿨다운이 끝났을 때 알람 메세지 요청
    try:
        cooldown_response = requests.get("https://lolpago/spell/await",
                                         params=spell_cool_down_params,
                                         timeout=360)

        # Spring 서버 응답 OK
        if cooldown_response.status_code == 200:
            # 서버 응답 데이터 파싱
            cooldown_data = cooldown_response.json()
            print(f"쿨다운 메시지: {cooldown_data['spellCoolDownMessage']}")
            # 쿨다운 완료 메세지 음성으로 생성
            tts_cd = generate_tts_mp3(cooldown_data["spellCoolDownMessage"])
            if tts_cd:
                # WebSocket 송신 큐에 mp3 데이터 비동기 전송
                asyncio.run_coroutine_threadsafe(audio_queue.put(tts_cd), loop)
        else:
            print(f"쿨다운 요청 실패: {cooldown_response.status_code} - {cooldown_response.text}")
    except Exception as e:
        print(f"쿨다운 요청 예외 발생: {e}")
