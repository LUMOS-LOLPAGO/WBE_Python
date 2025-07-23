import asyncio
import websockets
import numpy as np
from concurrent.futures import ThreadPoolExecutor
from worker.stt.util.stt_worker_util import VoiceActivityDetector
from worker.stt.stt_worker_process import whisper_pipeline

# 최대 11개의 쓰레드를 가지는 쓰레들 풀 생성
executor = ThreadPoolExecutor(max_workers=11)


async def handle_connection(websocket):
    print("🎧 클라이언트 연결됨")

    # stt_worker_util.py 에서 음성 활동 감지 및 녹음 처리를 위한 VoiceActivityDetector 객체 생성
    vad = VoiceActivityDetector()
    # Summoner ID와 오디오 큐 초기화
    summoner_id = "4545"
    audio_queue = asyncio.Queue()
    # 비동기 이벤트 루프 가져오기
    loop = asyncio.get_event_loop()

    # TTS 결과를 WebSocket 으로 클라이언트에게 전송하는 비동기 함수
    async def tts_sender():
        while True:
            # audio_queue 에서 오디오 데이터를 가져온다
            mp3_data = await audio_queue.get()
            try:
                # WebSocket 을 통해 음성 데이터를 클라이언트로 전송한다
                await websocket.send(mp3_data)
                print("📤 mp3 전송 완료")
            except Exception as e:
                print(f"❌ WebSocket 전송 에러: {e}")
            finally:
                # 작업이 완료되었음을 audio_queue에 알린다
                audio_queue.task_done()

    # TTS 전송 작업을 비동기적으로 시작
    tts_task = asyncio.create_task(tts_sender())

    try:
        # WebSocket 메시지를 비동기적으로 수신
        async for message in websocket:
            # 메시지가 "ping" 문자열인 경우 무시
            if isinstance(message, str) and message == "ping":
                continue
            # 메시지가 바이트가 아닌 경우 무시
            if not isinstance(message, bytes):
                continue

            # 음성 활동 감지 및 녹음 처리
            pcm = np.frombuffer(message, dtype=np.int16).astype(np.float32) / 32768.0
            result = vad.process_audio(pcm)

            # 음성 활동이 감지되면 녹음된 오디오 데이터를 Whisper 파이프라인으로 전달
            if result is not None:
                print("🛑 음성 녹음 종료 → Whisper 분석 시작")
                loop.run_in_executor(executor, whisper_pipeline, summoner_id, result, audio_queue, loop)

    # WebSocket 연결이 종료되거나 예외가 발생
    except websockets.exceptions.ConnectionClosed as e:
        print(f"🔌 연결 종료됨: {e}")
    finally:
        # TTS 전송 작업을 종료
        tts_task.cancel()

        print("❌ 연결 종료됨")


# WebSocket 서버를 시작하는 비동기 함수
async def start_websocket_server():
    print("📡 WebSocket 서버 시작 (ws://0.0.0.0:8888)")
    # 클라이언트가 WebSocket 연결을 시도할 때마다 handle_connection 함수가 코루틴을 새로 실행해준다
    async with websockets.serve(handle_connection, "0.0.0.0", 8888, max_size=2**22, ping_interval=None,):
        # 서버가 종료되지 않도록 무한 대기
        await asyncio.Future()
