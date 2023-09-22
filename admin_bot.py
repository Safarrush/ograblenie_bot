import telebot
import requests
from bs4 import BeautifulSoup
import sqlite3
import re
from telebot import types
import datetime

event_url = ""

bot = telebot.TeleBot('6683590484:AAGgk9kj_vmRpUx7Le6BrnU_MKTnNfhFtYQ')


def create_connection(db_file):
    try:
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        return conn, cursor
    except sqlite3.Error as e:
        print(f"Error: {str(e)}")
        return None, None


def create_tables(cursor):
    try:
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
                correct_predictions INTEGER,
                place INTEGER
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS play (
                id INTEGER
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS url (
                url_adress TEXT
            )
        ''')
        conn.commit()
    except sqlite3.Error as e:
        print(f"Error: {str(e)}")


upcoming_events = {}

conn, cursor = create_connection('selected_matches.db')

if conn is not None and cursor is not None:
    create_tables(cursor)
    conn.close()
else:
    print("Failed to create a database connection.")


@bot.callback_query_handler(func=lambda call: call.data == 'stop')
def playing_boy(call):
    markup = types.InlineKeyboardMarkup()
    item1 = types.InlineKeyboardButton(
        "Возобновить прием заявок!", callback_data='restart')
    markup.add(item1)
    conn, cursor = create_connection('selected_matches.db')
    if conn is not None and cursor is not None:
        cursor.execute(
            'INSERT INTO play (id) VALUES (1)')
        conn.commit()

        cursor.close()
        conn.close()
        bot.send_message(call.message.chat.id,
                         'Прием заявок остановлен!', reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data == 'restart')
def restart_boy(call):
    markup = types.InlineKeyboardMarkup()
    item1 = types.InlineKeyboardButton(
        "Остановить прием заявок!", callback_data='stop')
    item2 = types.InlineKeyboardButton(
        "Загрузить победителей", callback_data='update_winners')
    markup.add(item1, item2)
    conn, cursor = create_connection('selected_matches.db')
    if conn is not None and cursor is not None:
        cursor.execute(
            'INSERT INTO play (id) VALUES (0)')
        conn.commit()

        cursor.close()
        conn.close()
        bot.send_message(call.message.chat.id,
                         'Прием заявок возобновлен!', reply_markup=markup)


def update_upcoming_events():
    try:
        url = "http://www.ufcstats.com/statistics/events/completed"
        upcoming_events.clear()
        response = requests.get(url)
        soup = BeautifulSoup(response.content, "html.parser")
        for i, event_row in enumerate(soup.find_all(
            "tr",
            class_="b-statistics__table-row_type_first")
        ):
            event_url = event_row.find("a", "b-link b-link_style_white")
            if event_url:
                url = event_url['href']
                text = event_url.get_text(strip=True)
                upcoming_events[i+1] = text, url
            else:
                print("Link not found")

        for i, event_row in enumerate(
            soup.find_all("tr",
                          class_="b-statistics__table-row")
        ):
            event_url = event_row.find("a", "b-link b-link_style_black")
            if event_url:
                url = event_url['href']
                text = event_url.get_text(strip=True)
                upcoming_events[i] = text, url
            else:
                print("Link not found")
    except Exception as e:
        print(f"An error occurred: {str(e)}")


@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = types.InlineKeyboardMarkup()
    item1 = types.InlineKeyboardButton(
        'Посмотреть турниры',
        callback_data='get_upcoming_events'
    )
    item2 = types.InlineKeyboardButton(
        'Очистить данные с прошлого турнира',
        callback_data='clear_selected_matches'
    )
    markup.add(item1, item2)
    bot.send_message(
        message.chat.id,
        'Привет! Я бот, который поможет тебе поучаствовать в розыгрыше.',
        reply_markup=markup
    )


@bot.callback_query_handler(
    func=lambda call: call.data == 'get_upcoming_events'
)
def get_upcoming_events(call):
    markup = types.InlineKeyboardMarkup()
    item = types.InlineKeyboardButton(
        "Выбрать турнир", callback_data='select_event')
    markup.add(item)
    update_upcoming_events()  # Обновляем список турниров
    events_list = "\n".join(
        [f"{i}. {event}" for i, event in upcoming_events.items()])
    bot.send_message(
        call.message.chat.id,
        f'Список предстоящих турниров:\n{events_list}\n\nВыберите номер турнира, нажав кнопку ниже.',
        reply_markup=markup
    )


@bot.message_handler(commands=['all_upcoming_events'])
def all_upcoming_events(message):
    update_upcoming_events()  # Обновляем список турниров
    events_list_text = "\n".join(
        [f"{i + 1}. {event}" for i, event in upcoming_events.items()])
    bot.send_message(
        message.chat.id,
        f'Список всех предстоящих турниров:\n{events_list_text}'
    )


matches_dict = {}


def parse_and_store_matches(selected_event):
    # selected_event - это кортеж (название турнира, URL)
    try:
        _, url = selected_event
        response = requests.get(url)
        soup = BeautifulSoup(response.content, "html.parser")
        match_number = 1  # Инициализируем номер боя
        matches_dict.clear()
        for match_row in soup.find_all(
            "tr",
            class_="b-fight-details__table-row"
        ):
            fight_name_elems = match_row.find_all(
                "a", class_="b-link b-link_style_black")
            if len(fight_name_elems) >= 2:
                fighter1_name = fight_name_elems[0].get_text(strip=True)
                fighter2_name = fight_name_elems[1].get_text(strip=True)
                matches_dict[match_number] = (fighter1_name, fighter2_name)
                match_number += 1  # Увеличиваем номер боя для следующего боя
    except Exception as e:
        print(f"An error occurred: {str(e)}")


def process_selected_matches(message, selected_event):
    try:
        _, url = selected_event
        response = requests.get(url)
        soup = BeautifulSoup(response.content, "html.parser")

        match_number = 1
        matches_dict.clear()

        for match_row in soup.find_all(
            "tr",
            class_="b-fight-details__table-row"
        ):
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
        bot.send_message(
            message.chat.id, f"Список выбранных боев:\n{events_text}")
        # Запрос пользователя о выборе боев для записи в базу данных
        bot.send_message(
            message.chat.id,
            'Выберите бои для записи в базу данных, '
            'перечислив номера через запятую (например: 1, 3, 5).')
        # Ожидание ответа от пользователя
        bot.register_next_step_handler(
            message, finalize_selected_matches, selected_event)
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        bot.send_message(
            message.chat.id, 'Упс. Что-то не так! Начни заново'
        )


def process_coefficients(message, selected_event,
                         selected_matches_numbers,
                         coefficients_dict, index=0):
    try:
        num = selected_matches_numbers[index]
        match = matches_dict[num]

        if match not in coefficients_dict:
            coefficients_dict[match] = {
                "fighter1_coefficient": None, "fighter2_coefficient": None}

        bot.reply_to(
            message,
            f'Введите коэффициент для бойца {match[0]}. Пример (1.2):')
        bot.register_next_step_handler(message,
                                       process_fighter1_coefficient,
                                       selected_event,
                                       selected_matches_numbers,
                                       coefficients_dict, index, match)
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        bot.send_message(
            message.chat.id, 'Что-то не так!'
        )
        input_selected_matches(message, selected_event)


def process_fighter1_coefficient(message, selected_event,
                                 selected_matches_numbers,
                                 coefficients_dict, index,
                                 match):
    try:
        coefficients_dict[match]["fighter1_coefficient"] = float(message.text)
        bot.reply_to(
            message,
            f'Введите коэффициент для бойца {match[1]}. Пример (1.2):'
        )
        bot.register_next_step_handler(message,
                                       process_fighter2_coefficient,
                                       selected_event,
                                       selected_matches_numbers,
                                       coefficients_dict, index, match)
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        bot.send_message(message.chat.id, 'Неверный формат. Давай все заново!')
        process_coefficients(
            message, selected_event,
            selected_matches_numbers,
            coefficients_dict, index=0
        )


def process_fighter2_coefficient(
    message, selected_event,
    selected_matches_numbers,
    coefficients_dict, index, match
):
    markup = types.InlineKeyboardMarkup()
    item = types.InlineKeyboardButton(
        "Загрузить победителей", callback_data='update_winners')
    item2 = types.InlineKeyboardButton(
        "Остановить прием заявок", callback_data='stop')
    item3 = types.InlineKeyboardButton(
        "Участники", callback_data='count_registr')
    item4 = types.InlineKeyboardButton(
        "Удалить данные", callback_data='clear_selected')
    markup.add(item, item2, item3, item4)
    try:
        coefficients_dict[match]["fighter2_coefficient"] = float(message.text)

        index += 1
        if index < len(selected_matches_numbers):
            process_coefficients(message, selected_event,
                                 selected_matches_numbers,
                                 coefficients_dict, index)
        else:
            # Открываем новое соединение с базой данных
            conn, cursor = create_connection('selected_matches.db')
            if conn is not None and cursor is not None:
                selected_matches_to_insert = []
                existing_matches = set()
                for num in selected_matches_numbers:
                    match = matches_dict[num]
                    fighter1_coefficient = coefficients_dict[match]["fighter1_coefficient"]
                    fighter2_coefficient = coefficients_dict[match]["fighter2_coefficient"]
                    fighter1_name = match[0]
                    fighter2_name = match[1]

                    if (fighter1_name, fighter2_name) not in existing_matches:
                        existing_matches.add((fighter1_name, fighter2_name))
                        # Проверка наличия боя в базе данных
                        cursor.execute(
                            'SELECT * FROM selected_matches '
                            'WHERE fighter1_name = ? AND fighter2_name = ?',
                            (fighter1_name, fighter2_name)
                        )
                        existing_match = cursor.fetchone()

                        if not existing_match:
                            selected_matches_to_insert.append(
                                (selected_event[0],
                                 fighter1_name, fighter2_name,
                                 fighter1_coefficient, fighter2_coefficient
                                 )
                            )

                # Вставка выбранных боев в базу данных
                cursor.executemany(
                    'INSERT INTO selected_matches '
                    '(event_name, fighter1_name, fighter2_name, fighter1_coefficient, fighter2_coefficient) '
                    'VALUES (?, ?, ?, ?, ?)',
                    selected_matches_to_insert
                )
                conn.commit()
                # Закрываем соединение с базой данных
                cursor.close()
                conn.close()
                bot.send_message(
                    message.chat.id,
                    'Выбранные бои и коэффициенты '
                    'были успешно записаны в базу данных.',
                    reply_markup=markup
                )
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        bot.send_message(message.chat.id, 'Неверный формат. Давай все заново!')
        process_coefficients(
            message, selected_event,
            selected_matches_numbers,
            coefficients_dict, index=0
        )


user_winners = {}


def contains_only_digits(text):
    return re.match(r'^\d+$', text) is not None


def input_selected_matches(message, selected_event):
    bot.send_message(
        message.chat.id, "Введите номера выбранных боев, разделяя запятыми:")
    bot.register_next_step_handler(
        message, finalize_selected_matches, selected_event)


def finalize_selected_matches(message, selected_event):
    selected_matches_input = message.text.replace(
        ' ', '')  # Удаляем пробелы
    selected_matches_numbers = selected_matches_input.split(
        ',')  # Разделяем по запятым

    if all(contains_only_digits(num) for num in selected_matches_numbers):
        try:
            selected_matches_numbers = [int(num)
                                        for num in selected_matches_numbers]
            # Корректируем индексы
            selected_matches_numbers = [
                num for num in selected_matches_numbers]
            bot.send_message(
                message.chat.id,
                'Для каждого бойца введите '
                'коэффициенты в порядке их появления:'
            )
            process_coefficients(message, selected_event,
                                 selected_matches_numbers, {})
        except Exception as e:
            print(f"An error occurred: {str(e)}")
            bot.send_message(
                message.chat.id,
                'Некорректные символы! '
                'Пожалуйста, введите только цифры, разделенные запятыми.')
            input_selected_matches(message, selected_event)
    else:
        bot.send_message(
            message.chat.id,
            'Некорректные символы! '
            'Пожалуйста, введите только цифры, разделенные запятыми.'
        )
        input_selected_matches(message, selected_event)


selected_event = None
states = {}

# Обработчик команды /select_event


@bot.callback_query_handler(func=lambda call: call.data == 'select_event')
def select_event(call):
    # Устанавливаем состояние 'waiting_for_event_number' для пользователя
    states[call.message.chat.id] = 'waiting_for_event_number'
    # Отправляем сообщение, ожидая ввод номера турнира
    bot.send_message(call.message.chat.id, "Введите номер турнира для выбора:")

# Обработчик текстового ввода после команды /select_event


@bot.message_handler(
    func=lambda message: states.get(
        message.chat.id) == 'waiting_for_event_number'
)
def process_event_number(message):
    global selected_event
    event_number = message.text.strip()

    try:
        if event_number.isdigit() and int(event_number) in upcoming_events:
            selected_event = upcoming_events[int(event_number)]
            print(selected_event[1])
            conn, cursor = create_connection('selected_matches.db')
            if conn is not None and cursor is not None:
                cursor.execute(
                    'INSERT OR REPLACE INTO url (url_adress) VALUES (?)',
                    (selected_event[1],)
                )
                conn.commit()

                cursor.close()
                conn.close()
                bot.send_message(
                    message.chat.id,
                    f'Выбран турнир: {selected_event}. '
                    f'Загружаю информацию о боях...'
                )
            parse_and_store_matches(selected_event)
            # Открываем новый курсор для работы с базой данных
            conn, cursor = create_connection('selected_matches.db')
            if conn is not None and cursor is not None:
                # Передаем курсор и сообщение в функцию обработки
                process_selected_matches(message, selected_event)
                # Закрываем курсор и соединение с базой данных
                cursor.close()
                conn.close()
        else:
            bot.reply_to(message, "Неверный номер турнира.")
    except (IndexError, ValueError):
        bot.reply_to(
            message, "Используйте команду для выбора турнира.")


@bot.callback_query_handler(
    func=lambda call: call.data == 'clear_selected_matches'
)
def clear_selected_matches(call):

    try:
        # Открываем соединение с базой данных
        conn, cursor = create_connection('selected_matches.db')
        if conn is not None and cursor is not None:
            # Очищаем таблицу selected_matches
            cursor.execute('DELETE FROM selected_matches')
            cursor.execute('DELETE FROM user_winner_selections')
            cursor.execute('DELETE FROM winners')
            cursor.execute('DELETE FROM user_match_predictions')
            cursor.execute('DELETE from play')
            cursor.execute('DELETE from url')
            cursor.execute('DELETE from players')
            conn.commit()
            # Закрываем соединение с базой данных
            cursor.close()
            conn.close()
        bot.send_message(
            call.message.chat.id,
            "Все записи выбранных боев удалены из базы данных."
        )
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        bot.send_message(
            call.message.chat.id, 'Упс. Что-то не так! Начни заново'
        )


@bot.callback_query_handler(func=lambda call: call.data == 'clear_selected')
def clear_selected(call):

    try:
        # Открываем соединение с базой данных
        conn, cursor = create_connection('selected_matches.db')
        if conn is not None and cursor is not None:
            # Очищаем таблицу selected_matches
            cursor.execute('DELETE FROM selected_matches')
            conn.commit()
            # Закрываем соединение с базой данных
            cursor.close()
            conn.close()
            bot.send_message(
                call.message.chat.id,
                'Все записи выбранных боев удалены из базы данных.'
            )

    except Exception as e:
        print(f"An error occurred: {str(e)}")
        bot.send_message(
            call.message.chat.id, 'Упс. Что-то не так! Начни заново'
        )


@bot.callback_query_handler(func=lambda call: call.data == 'update_winners')
def update_winners(call):
    # Пример URL страницы с боями
    markup = types.InlineKeyboardMarkup()
    item = types.InlineKeyboardButton(
        'Подвести итог', callback_data='calculate_predictions')
    item2 = types.InlineKeyboardButton(
        'Удалить победителей', callback_data='clear_winners')
    markup.add(item, item2)
    selected_event = None
    conn, cursor = create_connection('selected_matches.db')
    if conn is not None and cursor is not None:

        # Запрос всех записей из таблицы user_match_predictions
        status = cursor.execute('SELECT * FROM url')
        for row in status:
            selected_event = row[0]
        cursor.close()
        conn.close()
    try:
        if selected_event is None:
            bot.send_message(
                call.message.chat.id,
                'Сначала выберите турнир с '
                'помощью команд /get_upcoming_'
                'events и /select_event.')
        else:
            parse_and_store_winners(selected_event)
            bot.send_message(
                call.message.chat.id,
                "Информация о победителях была успешно обновлена.",
                reply_markup=markup
            )
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        bot.send_message(
            call.message.chat.id,
            'Упс. Что-то не так! Начни заново'
        )


def parse_and_store_winners(event_url):
    try:
        conn, cursor = create_connection('selected_matches.db')
        if conn is not None and cursor is not None:
            response = requests.get(event_url)
            soup = BeautifulSoup(response.content, "html.parser")
            event_name_elem = soup.find("h2", class_="b-content__title")
            event_name = event_name_elem.get_text(strip=True)
            winners = []
            for match_row in soup.find_all(
                "tr",
                class_="b-fight-details__table-row"
            ):
                fight_name_elems = match_row.find_all(
                    "a", class_="b-link b-link_style_black")
                win_elements = match_row.find_all(
                    "i", class_="b-flag__text")
                wins = [win.get_text(strip=True) for win in win_elements]
                if len(fight_name_elems) >= 2 and wins[0] == 'win':
                    winner_name = fight_name_elems[0].get_text(strip=True)
                    winners.append((event_name, winner_name))
                elif len(fight_name_elems) >= 2 and wins[0] == 'draw':
                    winners.append((event_name, 'draw'))
                else:
                    print('no matches')

            cursor.executemany(
                'INSERT INTO winners (event_name, winner_name) '
                'VALUES (?, ?)', winners
            )
            conn.commit()

            cursor.close()
            conn.close()
    except Exception as e:
        print(f"An error occurred: {str(e)}")


def calculate_and_store_predictions():
    try:
        conn, cursor = create_connection('selected_matches.db')
        if conn is not None and cursor is not None:

            # Получаем список всех пользователей
            cursor.execute(
                'SELECT DISTINCT user_id FROM user_winner_selections')
            user_ids = [row[0] for row in cursor.fetchall()]

            user_scores = []
            cursor.execute(
                'SELECT winner_name FROM winners')
            winners = [row[0] for row in cursor.fetchall()]

            for user_id in user_ids:
                # Получаем список выбранных боев пользователя
                cursor.execute(
                    'SELECT match_id, winner FROM user_winner_selections '
                    'WHERE user_id = ?', (user_id,)
                )
                user_selections = cursor.fetchall()

                # Получаем баланс пользователя
                user_score = 0.0
                score_draw = 0
                for i in winners:
                    if i == 'draw':
                        score_draw += 1
                user_score += score_draw

                for match_id, user_winner in user_selections:
                    cursor.execute(
                        'SELECT fighter1_name, fighter2_name, '
                        'fighter1_coefficient, fighter2_coefficient '
                        'FROM selected_matches WHERE id = ?',
                        (match_id,)
                    )
                    match_info = cursor.fetchone()
                    fighter1_name, fighter2_name, fighter1_coefficient, fighter2_coefficient = match_info
                    user_winner = user_winner.strip()
                    cursor.execute(
                        'SELECT winner_name FROM winners WHERE winner_name = ?',
                        (user_winner,)
                    )
                    a = cursor.fetchone()
                    if a:
                        if a[0].strip() == fighter1_name:
                            user_score += fighter1_coefficient
                        elif a[0].strip() == fighter2_name:
                            user_score += fighter2_coefficient
                    else:
                        user_score += 0

                user_scores.append((user_id, round(user_score, 2)))

            # Сортируем пользователей по баллам в убывающем порядке
            user_scores.sort(key=lambda x: x[1], reverse=True)

            for index, (user_id, user_score) in enumerate(user_scores, start=1):
                # Записываем место пользователя и его баллы в таблицу
                cursor.execute(
                    'INSERT OR REPLACE INTO user_match_predictions '
                    '(user_id, correct_predictions, place) '
                    'VALUES (?, ?, ?) ',
                    (user_id, user_score, index)
                )
            conn.commit()
            cursor.close()
            conn.close()

    except Exception as e:
        print(f"An error occurred: {str(e)}")


@bot.callback_query_handler(
    func=lambda call: call.data == 'calculate_predictions'
)
def calculate_predictions(call):
    calculate_and_store_predictions()
    bot.send_message(
        call.message.chat.id,
        "Расчет и запись количества угаданных боев выполнены."
    )


@bot.message_handler(commands=['count'])
def count_of_players(message):
    conn, cursor = create_connection('selected_matches.db')
    if conn is not None and cursor is not None:

        col = cursor.execute('SELECT Count(*) FROM players')
        for row in col:
            count = row[0]
            bot.send_message(message.chat.id, f'Количество игроков: {count}')
        cursor.close()
        conn.close()


@bot.callback_query_handler(func=lambda call: call.data == 'count_registr')
def players(call):
    count = 0
    try:
        conn, cursor = create_connection('selected_matches.db')
        if conn is not None and cursor is not None:
            col = cursor.execute('SELECT Count(*) FROM players')
            for row in col:
                count = row[0]
            cursor.close()
            conn.close()
            bot.send_message(call.message.chat.id,
                             f'Количество участников: {count}')
    except Exception as e:
        print(f"An error occurred: {str(e)}")


@bot.callback_query_handler(func=lambda call: call.data == 'clear_winners')
def clear_winners(call):

    try:
        # Открываем соединение с базой данных
        conn, cursor = create_connection('selected_matches.db')
        if conn is not None and cursor is not None:
            # Очищаем таблицу selected_matches
            cursor.execute('DELETE FROM winners')
            conn.commit()
            # Закрываем соединение с базой данных
            cursor.close()
            conn.close()
            bot.send_message(
                call.message.chat.id,
                'Все записи победителей удалены из базы данных.'
            )

    except Exception as e:
        print(f"An error occurred: {str(e)}")
        bot.send_message(
            call.message.chat.id, 'Упс. Что-то не так! Начни заново'
        )


bot.polling()
conn.close()
