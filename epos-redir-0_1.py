
import requests
from datetime import datetime, timedelta
from urllib.parse import quote
import telebot


#  Настройки

PROFILE_ID = xxxxxxxx               # id берем из запросов
BOT_TOKEN = "tg token"   # вопросы?
BASE_URL = "https://edu-epos.permkrai.ru"
ALLOWED_USER_ID = xxxxxxxxxxx    # айди вашего аккаунта в тг дабы чужие не юзали бот

# токен мы тоже берем из запросика
#                           ПРОЛИСТАЙ ВЕСЬ КОД ТАМ ЕСТЬ ЕЩЕ ПАРА ИНДИВИДУАЛЬНЫХ ПЕРЕМЕННЫХ
#  Чтение токена из файла

import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TOKEN_FILE = os.path.join(SCRIPT_DIR, "token.txt") 

def read_token(file_name=TOKEN_FILE):
    if not os.path.exists(file_name):
        raise FileNotFoundError("Токен ЭПОС не найден.")
    with open(file_name, "r", encoding="utf-8") as f:
        token = f.read().strip()
    if not token:
        raise ValueError("Файл token.txt пустой")
    return token


#запрос на дз
def get_homework_chislo(token, profile_id, target_date):
    try:
        target_day = datetime.strptime(target_date, "%d.%m.%Y").strftime("%A")
    except ValueError:
        return "дата должна быть в формате xx.xx.xxxx" # дата должна быть в формате xx.xx.xxxx

    session = requests.Session()
    session.cookies.update({
        "USESSION": token,
        "auth_token": token,
        "auth_token_by_context": token,
        "profile_id": str(profile_id),
        "profile_id_by_context": str(profile_id),
        "is_auth": "true",
        "is_auth_by_context": "true",
        "from_sudir": "true",
        "aid": "13",
    })
    session.headers.update({
        "Accept": "application/json",
        "auth-token": token,
        "profile-id": str(profile_id),
        "X-Requested-With": "XMLHttpRequest",
        "Origin": BASE_URL,
        "Referer": f"{BASE_URL}/student_diary/student_diary/{profile_id}",
        "User-Agent": "Mozilla/5.0",
    })

    url = f"{BASE_URL}/core/api/student_homeworks"
    params = {
        "begin_date": target_date,
        "end_date": target_date,
        "academic_year_id": 18, # не помню ворк ли без этого, но ваш возраст сюда писать
        "student_profile_id": profile_id,
        "page": 1,
        "per_page": 1000,
        "pid": profile_id,
    }

    try:
        r = session.get(url, params=params, timeout=10)
    except requests.RequestException as e:
        return f"Ошибка сети: {e}"

    if r.status_code != 200:
        return f"Ошибка запроса: {r.status_code}"

    all_data = r.json()
    data = [
        hw for hw in all_data
        if hw.get("homework_entry", {}).get("homework", {}).get("date_prepared_for") == target_date
    ]

    if not data:
        return f"{target_date} ({target_day})\n— На этот день ДЗ нет —"

    result = [f"{target_date} ({target_day})", f"Всего ДЗ: {len(data)}\n"]

    for hw in data:
        homework_entry = hw.get("homework_entry", {})
        homework = homework_entry.get("homework", {})
        subject = homework.get("subject", {}).get("name", "Неизвестный предмет")
        description = homework_entry.get("description") or "— без задания —"
        text = f"🔹 {subject}\n   {description}"

        attachments = homework_entry.get("attachments", []) # аттачи
        if attachments:
            text += "\n   Доп. материалы:"
            for att in attachments:
                name = att.get("file_file_name", "Без названия")
                path = att.get("path", "")
                url = f"{BASE_URL}{quote(path)}" if path else "#"
                text += f"\n      - {name}: {url}"
        else:
            text += "\n   Доп. материалов нема"

        result.append(text)

    return "\n\n".join(result)

# тг бот
bot = telebot.TeleBot(BOT_TOKEN)

@bot.message_handler(commands=['dz'])
def send_homework(message):
    if message.from_user.id != ALLOWED_USER_ID:
        return  # игнорируем чужаков лохов

    token = read_token()
    if not token:
        bot.send_message(message.chat.id, "Токен ЭПОС не найден.")
        return

    args = message.text.split()
    if len(args) > 1:
        try:
            if args[1].lower() == "завтра":
                target_date = (datetime.now() + timedelta(days=1)).strftime("%d.%m.%Y")
            elif args[1].lower() == "сегодня":
                target_date = datetime.now().strftime("%d.%m.%Y")
            else:
                target_date_obj = datetime.strptime(args[1], "%d.%m.%Y")
                target_date = target_date_obj.strftime("%d.%m.%Y")
        except ValueError:
            bot.send_message(message.chat.id, "ДД.MM.ГГГГ")
            return
    else:
        target_date = (datetime.now() + timedelta(days=1)).strftime("%d.%m.%Y")

    homework_text = get_homework_chislo(token, PROFILE_ID, target_date)

    # чтобы тг не ломался при большиъ соо
    for chunk in [homework_text[i:i+4000] for i in range(0, len(homework_text), 4000)]:
        bot.send_message(message.chat.id, chunk)

print("стартуемм")
bot.polling(none_stop=True)
