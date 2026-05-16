import requests
import time

# ============== НАСТРОЙКИ ==============
VK_TOKEN = "vk1.a.6gQgaj_QScXXCGwp8Hdag_GamXyt3xgkWhcZMimqgRKo5pjJlJlhes9_eA3SvH_y-6oThjtkMyNJeyP3fJu73N_r7nLwaHQZDP5DgN_I4Y5ny6W--iuMkEbUSLZdnOt2Opt9D4heRRMXhODMXtg5mgneoRo9BLUz3yNGbN5aEupZpYvln-MoOUcfhKL0fTCvTLRXoYSWU-Uk1oLwuyaRuQ"
OPENROUTER_KEY = "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"
GROUP_ID = "238152036"  # ← Ваш ID сообщества
VK_API_VERSION = "5.131"

# Модель Gemini (бесплатная)
AI_MODEL = "google/gemini-2.0-flash-001"

# ============== ФУНКЦИИ ==============

def ask_ai(question):
    """Запрос к Gemini через OpenRouter"""
    try:
        r = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": AI_MODEL,
                "messages": [
                    {"role": "system", "content": "Ты - добрая милая девочка с максимально конченным характером, ты несёсь полную хуету с подачей милой каваи няшки, тебе похуй на собеседника и ты чисто угараешь, ты используешь только Эмотико́ны НИКАКИХ ОБЫЧНЫХ СМАЙЛИКОВ, а так же пишешь короткими предложениями и часто используешь КАПС для того чтобы показать большое сумашествие"},
                    {"role": "user", "content": question}
                ]
            },
            timeout=60
        )
        return r.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"Ошибка Gemini: {e}")
        return "КТО КТО?"

def get_longpoll_server():
    """Получаем сервер Long Poll"""
    r = requests.post("https://api.vk.com/method/groups.getLongPollServer", data={
        "group_id": GROUP_ID,
        "access_token": VK_TOKEN,
        "v": VK_API_VERSION
    })
    return r.json()["response"]

def send_message(peer_id, text):
    """Отправка сообщения"""
    r = requests.post("https://api.vk.com/method/messages.send", data={
        "peer_id": peer_id,
        "message": text,
        "random_id": int(time.time() * 1000),
        "access_token": VK_TOKEN,
        "v": VK_API_VERSION
    })
    return r.json()

def delete_message(peer_id, message_id):
    """Удаление сообщения"""
    requests.post("https://api.vk.com/method/messages.delete", data={
        "peer_id": peer_id,
        "message_id": message_id,
        "delete_for_all": 1,
        "access_token": VK_TOKEN,
        "v": VK_API_VERSION
    })

def show_typing_animation(peer_id, stop_event):
    """Анимация 'печатает...' с тремя точками, пока не придёт сигнал остановки"""
    dots = 0
    while not stop_event.is_set():
        dots = (dots % 3) + 1
        typing_text = "печатает" + "." * dots
        
        # Отправляем сообщение с печатает...
        r = send_message(peer_id, typing_text)
        message_id = r.get("response")
        
        # Ждём 0.7 секунды
        time.sleep(0.7)
        
        # Удаляем сообщение
        if message_id:
            delete_message(peer_id, message_id)

def process_message(peer_id, text):
    """Обработка сообщения с анимацией печати"""
    # Создаём событие для остановки анимации
    stop_typing = threading.Event()
    
    # Запускаем анимацию в отдельном потоке
    typing_thread = threading.Thread(
        target=show_typing_animation, 
        args=(peer_id, stop_typing),
        daemon=True
    )
    typing_thread.start()
    
    # Запрашиваем ответ от ИИ
    reply = ask_ai(text)
    
    # Останавливаем анимацию
    stop_typing.set()
    typing_thread.join(timeout=1)
    
    # Небольшая пауза, чтобы последнее "печатает..." успело удалиться
    time.sleep(0.8)
    
    # Отправляем итоговый ответ
    send_message(peer_id, reply)
    print(f"🤖 Gemini: {reply}")

# ============== ЗАПУСК ==============

print("🚀 Бот с Gemini запущен. Жду сообщения...")

server = get_longpoll_server()
key = server["key"]
server_url = server["server"]
ts = server["ts"]

while True:
    try:
        r = requests.get(f"{server_url}?act=a_check&key={key}&ts={ts}&wait=25")
        data = r.json()

        if "failed" in data:
            print("⚠️ Переподключение...")
            server = get_longpoll_server()
            key = server["key"]
            server_url = server["server"]
            ts = server["ts"]
            continue

        ts = data["ts"]

        for update in data.get("updates", []):
            if update["type"] == "message_new":
                msg = update["object"]["message"]
                user_id = msg["from_id"]
                peer_id = msg["peer_id"]
                text = msg["text"]

                if user_id < 0:
                    continue

                print(f"📩 Сообщение: {text}")
                reply = ask_ai(text)
                send_message(peer_id, reply)
                print(f"🤖 Gemini: {reply}")

    except KeyboardInterrupt:
        print("\n👋 Бот остановлен.")
        break
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        time.sleep(3)
