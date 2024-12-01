import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import requests
import logging
import time
from collections import defaultdict

API_KEY = '7441566490:AAEH1IMGBiIvisBjkH0DmLavDydsbd8T-24'
GEMINI_API_KEY = 'AIzaSyD5UcnXASfVpUa6UElDxYqZU6hxxwttj5M'
GEMINI_API_URL = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent'
CHANNEL_ID = '@Monopolist_Survivor'  # ID или @username канала

bot = telebot.TeleBot(API_KEY, parse_mode="Markdown")
user_count = set()
user_request_count = defaultdict(int)
user_modes = {}

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

PROGRAMMER_PROMPT = """
Создай пост в стиле вдохновляющего и познавательного бизнес-замеки с кратким, но сильным тезисом. 
Тема постов должна быть связана с финансами, бизнесом, финансовой грамотностью и мотивацией. 
Стиль постов — простой и понятный, как будто человек делится личным опытом. 
Каждый пост должен заканчиваться фразой, подчеркивающей основную мысль, и содержать подпись "©️ Монополист" и хештеги, 
например, #Бизнес или #Финграм. Тон должен быть уверенным, но не высокомерным. 
Приводите примеры из реальной жизни или истории компаний. Оформляй посты с короткими абзацами для удобства восприятия. СОЗДАЙ ТОЛЬКО 1 ТЕЗИС, НЕ УПОМИНАЯ СЛОВО ТЕЗИС И Т.П, СДЕЛАЙ ПУСТЫЕ СТРОЧКИ ПРИ ДРУГОМ ДРУГИХ ПРЕДЛОЖЕНИЯХ, И В ПЕРВОМ ТАКОМ ПРЕДЛОЖЕНИИ ПОСЛЕ ВСТУПЛЕНИЯ В НАЧАЛЕ ОСТАВЛЯЙ ТАКОЙ СИМВОЛ "
▷ "
"""

AUTHORIZED_USER_ID = 1420106372  # ID разрешенного пользователя

def is_authorized(user_id):
    return user_id == AUTHORIZED_USER_ID

@bot.message_handler(commands=['start'])
def send_welcome(message):
    if not is_authorized(message.from_user.id):
        bot.reply_to(message, "Извините, вы не авторизованы для использования этого бота.")
        return
    user_count.add(message.from_user.id)
    keyboard = InlineKeyboardMarkup()
    keyboard.row(InlineKeyboardButton("Программист", callback_data="programmer"))
    bot.reply_to(message, "Привет! Я Камилла, твой ассистент. Выбери режим, в котором ты хочешь работать:", reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    user_id = call.from_user.id
    if not is_authorized(user_id):
        bot.answer_callback_query(call.id, "Вы не авторизованы для использования этого бота.")
        return
    if call.data == "programmer":
        user_modes[user_id] = "programmer"
        bot.answer_callback_query(call.id, "Режим программиста активирован!")
        bot.send_message(call.message.chat.id, "Ты выбрал режим программиста. Задавай любые вопросы по программированию!")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.from_user.id
    if not is_authorized(user_id):
        bot.reply_to(message, "Извините, вы не авторизованы для использования этого бота.")
        return
    user_count.add(user_id)
    bot.send_chat_action(message.chat.id, 'typing')
    user_text = message.text.lower()

    if user_id in user_modes:
        mode = user_modes[user_id]
        if mode == "programmer":
            response = get_gemini_response(user_text, PROGRAMMER_PROMPT)
            send_gradual_message(message.chat.id, response)
            send_to_channel(response)  # Отправка сообщения в канал
    else:
        response = "Пожалуйста, выбери режим работы, используя команду /start"
        send_gradual_message(message.chat.id, response)

def send_gradual_message(chat_id, text):
    chunk_size = 100
    for i in range(0, len(text), chunk_size):
        chunk = text[i:i+chunk_size]
        if i == 0:
            sent_message = bot.send_message(chat_id, chunk)
        else:
            bot.edit_message_text(chat_id=chat_id, message_id=sent_message.message_id, text=text[:i+chunk_size])
        time.sleep(0.1)

def send_to_channel(text):
    """Функция для отправки сообщения в канал"""
    bot.send_message(CHANNEL_ID, text)

def get_gemini_response(question, prompt, max_retries=3, retry_delay=5):
    combined_message = f"{prompt}\n\nUser: {question}\nAssistant:"
    payload = {
        "contents": [{
            "parts": [{
                "text": combined_message
            }]
        }]
    }
    headers = {
        'Content-Type': 'application/json',
    }
    for attempt in range(max_retries):
        try:
            response = requests.post(f'{GEMINI_API_URL}?key={GEMINI_API_KEY}', json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            result = data['candidates'][0]['content']['parts'][0]['text']
            return result
        except Exception as e:
            logging.error(f"Ошибка при обращении к Gemini API (попытка {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                return "Извините, произошла ошибка при обработке запроса. Пожалуйста, попробуйте еще раз позже."

if __name__ == "__main__":
    while True:
        try:
            bot.polling(none_stop=True)
        except Exception as e:
            logging.error(f"Ошибка в основном цикле: {e}")
            time.sleep(15)