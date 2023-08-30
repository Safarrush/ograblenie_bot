import telebot
import requests
from bs4 import BeautifulSoup
import sqlite3
import re

event_url = ""
# Замените 'YOUR_BOT_TOKEN' на токен вашего бота
bot = telebot.TeleBot('6683590484:AAGgk9kj_vmRpUx7Le6BrnU_MKTnNfhFtYQ')

# Создание и подключение к базе данных
conn = sqlite3.connect('selected_matches.db')
cursor = conn.cursor()

# Создание таблицы для хранения информации о боях
cursor.execute('''
    CREATE TABLE IF NOT EXISTS selected_matches (
        id INTEGER PRIMARY KEY,
        event_name TEXT,
        fighter1_name TEXT,
        fighter2_name TEXT,
        fighter1_coefficient REAL,
        fighter2_coefficient REAL
    )
''')
cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_winner_selections (
        id INTEGER PRIMARY KEY,
        user_id INTEGER,
        match_id INTEGER,
        winner TEXT,
        FOREIGN KEY (match_id) REFERENCES selected_matches(id)
    )
''')
cursor.execute('''
    CREATE TABLE IF NOT EXISTS winners (
        id INTEGER PRIMARY KEY,
        event_name TEXT,
        winner_name TEXT
    )
''')
cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_match_predictions (
        user_id INTEGER PRIMARY KEY,
        correct_predictions INTEGER
    )
''')
conn.commit()

upcoming_events = {}


def update_upcoming_events():
    url = "http://www.ufcstats.com/statistics/events/completed"
    upcoming_events.clear()
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")
    for i, event_row in enumerate(soup.find_all("tr", class_="b-statistics__table-row_type_first")):
        event_url = event_row.find("a", "b-link b-link_style_white")
        if event_url:
            url = event_url['href']
            text = event_url.get_text(strip=True)
            upcoming_events[i+1] = text, url
        else:
            print("Link not found")

    for i, event_row in enumerate(soup.find_all("tr", class_="b-statistics__table-row")):
        event_url = event_row.find("a", "b-link b-link_style_black")
        if event_url:
            url = event_url['href']
            text = event_url.get_text(strip=True)
            upcoming_events[i] = text, url
        else:
            print("Link not found")


ALLOWED_USER_ID = 263275700


def restrict_access(func):
    def wrapper(message, *args, **kwargs):
        if message.from_user.id == ALLOWED_USER_ID:
            return func(message, *args, **kwargs)
        else:
            bot.reply_to(message, "У вас нет доступа к этой команде.")
    return wrapper


@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Привет! Я бот, который поможет тебе поучаствовать в розыгрыше. Просто напиши /select_winners для выбора бойцов победителей предстоящего турнира.")


@bot.message_handler(commands=['get_upcoming_events'])
@restrict_access
def get_upcoming_events(message):
    update_upcoming_events()  # Обновляем список турниров
    events_list = "\n".join(
        [f"{i}. {event}" for i, event in upcoming_events.items()])
    bot.reply_to(
        message, f"Список предстоящих турниров:\n{events_list}\n\nВыберите номер турнира командой /select_event <номер>.")


@bot.message_handler(commands=['all_upcoming_events'])
@restrict_access
def all_upcoming_events(message):
    update_upcoming_events()  # Обновляем список турниров
    events_list_text = "\n".join(
        [f"{i + 1}. {event}" for i, event in upcoming_events.items()])
    bot.reply_to(
        message, f"Список всех предстоящих турниров:\n{events_list_text}")


matches_dict = {}


def parse_and_store_matches(selected_event):
    # selected_event - это кортеж (название турнира, URL)
    _, url = selected_event
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")

    match_number = 1  # Инициализируем номер боя
    matches_dict.clear()
    for match_row in soup.find_all("tr", class_="b-fight-details__table-row"):
        fight_name_elems = match_row.find_all(
            "a", class_="b-link b-link_style_black")
        if len(fight_name_elems) >= 2:
            fighter1_name = fight_name_elems[0].get_text(strip=True)
            fighter1_url = fight_name_elems[0]['href']

            fighter2_name = fight_name_elems[1].get_text(strip=True)
            fighter2_url = fight_name_elems[1]['href']

            matches_dict[match_number] = (fighter1_name, fighter2_name)
            match_number += 1  # Увеличиваем номер боя для следующего боя


def process_selected_matches(message, selected_event):
    _, url = selected_event
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")

    match_number = 1
    matches_dict.clear()

    for match_row in soup.find_all("tr", class_="b-fight-details__table-row"):
        fight_name_elems = match_row.find_all(
            "a", class_="b-link b-link_style_black")
        if len(fight_name_elems) >= 2:
            fighter1_name = fight_name_elems[0].get_text(strip=True)
            fighter2_name = fight_name_elems[1].get_text(strip=True)

            matches_dict[match_number] = (fighter1_name, fighter2_name)
            match_number += 1

    # Вывод информации о выбранных боях
    events_text = "\n".join(
        [f"{i}. {event}" for i, event in matches_dict.items()])
    bot.reply_to(message, f"Список выбранных боев:\n{events_text}")

    # Запрос пользователя о выборе боев для записи в базу данных
    bot.reply_to(
        message, "Выберите бои для записи в базу данных, перечислив номера через запятую (например: 1, 3, 5).")

    # Ожидание ответа от пользователя
    bot.register_next_step_handler(
        message, finalize_selected_matches, selected_event)


def process_coefficients(message, selected_event, selected_matches_numbers, coefficients_dict, index=0):
    num = selected_matches_numbers[index]
    match = matches_dict[num]

    if match not in coefficients_dict:
        coefficients_dict[match] = {
            "fighter1_coefficient": None, "fighter2_coefficient": None}

    bot.reply_to(message, f"Введите коэффициент для бойца {match[0]}:")
    bot.register_next_step_handler(message, process_fighter1_coefficient,
                                   selected_event, selected_matches_numbers, coefficients_dict, index, match)


def process_fighter1_coefficient(message, selected_event, selected_matches_numbers, coefficients_dict, index, match):
    coefficients_dict[match]["fighter1_coefficient"] = float(message.text)
    bot.reply_to(message, f"Введите коэффициент для бойца {match[1]}:")
    bot.register_next_step_handler(message, process_fighter2_coefficient,
                                   selected_event, selected_matches_numbers, coefficients_dict, index, match)


def process_fighter2_coefficient(message, selected_event, selected_matches_numbers, coefficients_dict, index, match):
    coefficients_dict[match]["fighter2_coefficient"] = float(message.text)

    index += 1
    if index < len(selected_matches_numbers):
        process_coefficients(message, selected_event,
                             selected_matches_numbers, coefficients_dict, index)
    else:
        # Открываем новое соединение с базой данных
        conn = sqlite3.connect('selected_matches.db')
        cursor = conn.cursor()

        selected_matches_to_insert = []
        for num in selected_matches_numbers:
            match = matches_dict[num]
            fighter1_coefficient = coefficients_dict[match]["fighter1_coefficient"]
            fighter2_coefficient = coefficients_dict[match]["fighter2_coefficient"]
            selected_matches_to_insert.append(
                (selected_event[0], match[0], match[1], fighter1_coefficient, fighter2_coefficient))

        # Вставка выбранных боев в базу данных
        cursor.executemany(
            'INSERT INTO selected_matches (event_name, fighter1_name, fighter2_name, fighter1_coefficient, fighter2_coefficient) VALUES (?, ?, ?, ?, ?)', selected_matches_to_insert)
        conn.commit()

        # Закрываем соединение с базой данных
        cursor.close()
        conn.close()

        bot.reply_to(
            message, "Выбранные бои и коэффициенты были успешно записаны в базу данных.")


user_winners = {}


def contains_only_digits(text):
    return re.match(r'^\d+$', text) is not None


def input_selected_matches(message, selected_event):
    bot.reply_to(message, "Введите номера выбранных боев, разделяя запятыми:")
    bot.register_next_step_handler(
        message, finalize_selected_matches, selected_event)


def finalize_selected_matches(message, selected_event):
    selected_matches_input = message.text.replace(' ', '')  # Удаляем пробелы
    selected_matches_numbers = selected_matches_input.split(
        ',')  # Разделяем по запятым

    if all(contains_only_digits(num) for num in selected_matches_numbers):
        selected_matches_numbers = [int(num)
                                    for num in selected_matches_numbers]
        selected_matches_numbers = [
            num for num in selected_matches_numbers]  # Корректируем индексы
        bot.reply_to(
            message, "Для каждого бойца введите коэффициенты в порядке их появления:")
        process_coefficients(message, selected_event,
                             selected_matches_numbers, {})
    else:
        bot.reply_to(
            message, "Некорректные символы! Пожалуйста, введите только цифры, разделенные запятыми.")
        input_selected_matches(message, selected_event)


selected_event = None


@bot.message_handler(commands=['select_event'])
@restrict_access
def select_event(message):
    global selected_event
    event_number = None
    try:
        if message.text.split()[1].isdigit():
            event_number = int(message.text.split()[1])
        if event_number in upcoming_events:
            selected_event = upcoming_events[event_number]
            bot.reply_to(
                message, f"Выбран турнир: {selected_event}. Загружаю информацию о боях...")
            parse_and_store_matches(selected_event)

            # Открываем новый курсор для работы с базой данных
            conn = sqlite3.connect('selected_matches.db')
            cursor = conn.cursor()

            # Передаем курсор и сообщение в функцию обработки
            process_selected_matches(message, selected_event)

            # Закрываем курсор и соединение с базой данных
            cursor.close()
            conn.close()
        else:
            bot.reply_to(message, "Неверный номер турнира.")
    except (IndexError, ValueError):
        bot.reply_to(
            message, "Используйте команду /select_event <номер> для выбора турнира.")


@bot.message_handler(commands=['clear_selected_matches'])
@restrict_access
def clear_selected_matches(message):
    # Открываем соединение с базой данных
    conn = sqlite3.connect('selected_matches.db')
    cursor = conn.cursor()

    # Очищаем таблицу selected_matches
    cursor.execute('DELETE FROM selected_matches')
    cursor.execute('DELETE FROM user_winner_selections')
    cursor.execute('DELETE FROM winners')
    cursor.execute('DELETE FROM user_match_predictions')
    conn.commit()

    # Закрываем соединение с базой данных
    cursor.close()
    conn.close()

    bot.reply_to(
        message, "Все записи выбранных боев были успешно удалены из базы данных.")


@bot.message_handler(commands=['update_winners'])
@restrict_access
def update_winners(message):
    # Пример URL страницы с боями
    global selected_event
    # event_url = 'http://www.ufcstats.com/event-details/89a407032911e27e'
    if selected_event is None:
        bot.reply_to(
            message, "Сначала выберите турнир с помощью команды /select_event.")
    else:
        parse_and_store_winners(selected_event[1])
        bot.reply_to(
            message, "Информация о победителях была успешно обновлена.")


def parse_and_store_winners(event_url):
    conn = sqlite3.connect('selected_matches.db')
    cursor = conn.cursor()

    response = requests.get(event_url)
    soup = BeautifulSoup(response.content, "html.parser")

    event_name_elem = soup.find("h2", class_="b-content__title")
    event_name = event_name_elem.get_text(strip=True)

    winners = []
    for match_row in soup.find_all("tr", class_="b-fight-details__table-row"):
        fight_name_elems = match_row.find_all(
            "a", class_="b-link b-link_style_black")
        if len(fight_name_elems) >= 2:
            winner_name = fight_name_elems[0].get_text(strip=True)
            winners.append((event_name, winner_name))

    cursor.executemany(
        'INSERT INTO winners (event_name, winner_name) VALUES (?, ?)', winners)
    conn.commit()

    cursor.close()
    conn.close()


def calculate_and_store_predictions():
    conn = sqlite3.connect('selected_matches.db')
    cursor = conn.cursor()

    # Получаем список всех пользователей
    cursor.execute('SELECT DISTINCT user_id FROM user_winner_selections')
    user_ids = [row[0] for row in cursor.fetchall()]

    for user_id in user_ids:
        # Получаем список выбранных боев пользователя
        cursor.execute(
            'SELECT match_id, winner FROM user_winner_selections WHERE user_id = ?', (user_id,))
        user_selections = cursor.fetchall()

        # Получаем баланс пользователя
        user_score = 0.0

        for match_id, user_winner in user_selections:
            cursor.execute(
                'SELECT fighter1_name, fighter2_name, fighter1_coefficient, fighter2_coefficient FROM selected_matches WHERE id = ?', (match_id,))
            match_info = cursor.fetchone()

            fighter1_name, fighter2_name, fighter1_coefficient, fighter2_coefficient = match_info
            user_winner = user_winner.strip()
            cursor.execute(
                'SELECT winner_name FROM winners WHERE event_name = ? AND winner_name = ?', (match_info[0], user_winner))
            cursor.fetchone()

            if match_info[0] == user_winner:
                if user_winner.strip() == fighter1_name.strip():
                    user_score += fighter1_coefficient
                elif user_winner.strip() == fighter2_name.strip():
                    user_score += fighter2_coefficient
            else:
                user_score += 0

        print(f'user_id: {user_id}, user_score: {user_score}')

        # Записываем баллы пользователя в таблицу
        cursor.execute('INSERT OR REPLACE INTO user_match_predictions (user_id, correct_predictions) VALUES (?, ?)',
                       (user_id, user_score))

    conn.commit()
    cursor.close()
    conn.close()

    # Находим победителя и отправляем сообщение
    conn = sqlite3.connect('selected_matches.db')
    cursor = conn.cursor()

    cursor.execute(
        'SELECT user_id, correct_predictions FROM user_match_predictions ORDER BY correct_predictions DESC LIMIT 1')
    winner = cursor.fetchone()

    if winner:
        bot.send_message(
            winner[0], f"Пользователь с ID {winner[0]} является победителем с {winner[1]} баллами!")

    cursor.close()
    conn.close()


@bot.message_handler(commands=['calculate_predictions'])
@restrict_access
def calculate_predictions(message):
    calculate_and_store_predictions()
    bot.reply_to(
        message, "Расчет и запись количества угаданных боев выполнены.")


bot.polling()
conn.close()
