import telebot
import sqlite3
from telebot import types
import time
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from datetime import datetime

ALLOWED_USER_ID = 263275700

bot = telebot.TeleBot('6275603125:AAGEl6ysowwR5DidT9eZ0MgnSuU8kIfWPyI')


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
            CREATE TABLE IF NOT EXISTS registration (
                id INTEGER PRIMARY KEY,
                tg_id INTEGER UNIQUE,
                date_time TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS players (
                id INTEGER PRIMARY KEY,
                tg_id INTEGER UNIQUE
            )
        ''')
        conn.commit()
    except sqlite3.Error as e:
        print(f"Error: {str(e)}")


conn, cursor = create_connection('selected_matches.db')

if conn is not None and cursor is not None:
    create_tables(cursor)
    conn.close()
else:
    print("Failed to create a database connection.")


event_url = ""

upcoming_events = {}
user_used_command = {}


def restrict_access(func):
    def wrapper(message, *args, **kwargs):
        if message.from_user.id == ALLOWED_USER_ID:
            return func(message, *args, **kwargs)
        else:
            bot.reply_to(message, "У вас нет доступа к этой команде.")
    return wrapper


@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = types.InlineKeyboardMarkup()
    item = types.InlineKeyboardButton(
        "Выбрать бойцов", callback_data='select_winners')
    markup.add(item)
    now = datetime.now()
    current_time = now.strftime("%Y-%m-%d %H:%M:%S")
    conn, cursor = create_connection('selected_matches.db')
    if conn is not None and cursor is not None:
        cursor.execute(
            'INSERT OR IGNORE INTO registration (tg_id, date_time) VALUES (?, ?)',
            (message.chat.id, current_time,)
        )
        conn.commit()
        cursor.close()
        conn.close()
    bot.send_message(
        message.chat.id,
        'Привет! Я бот, который поможет тебе поучаствовать в розыгрыше. Нажми кнопку ниже, чтобы выбрать бойцов победителей предстоящего турнира:',
        reply_markup=markup
    )


user_winners = {}


@bot.callback_query_handler(func=lambda call: call.data == 'select_winners')
def select_winners(call):
    user_id = call.from_user.id
    try:
        with sqlite3.connect('selected_matches.db') as conn:
            cursor = conn.cursor()

            # Вставляем пользователя, если его еще нет в таблице players
            cursor.execute(
                'INSERT OR IGNORE INTO players (tg_id) VALUES (?)', (user_id,))
            conn.commit()

            # Проверяем статус игры
            cursor.execute('SELECT * FROM play')
            a = 0
            for row in cursor:
                a = row[0]
            if a != 1:
                cursor.execute(
                    'SELECT user_id FROM user_winner_selections WHERE user_id = ?', (user_id,))
                user_exists = cursor.fetchone()

                if user_exists:
                    bot.send_message(call.message.chat.id,
                                     "Вы уже сделали свой выбор.")
                else:
                    cursor.execute('SELECT * FROM selected_matches')
                    selected_matches = cursor.fetchall()

                    if not selected_matches:
                        bot.send_message(call.message.chat.id, 'Пока рано!')
                        send_welcome(call.message)
                    else:
                        selected_matches_numbers = [match[0]
                                                    for match in selected_matches]
                        process_winner(call.message, user_id,
                                       selected_matches_numbers, index=0)
            else:
                bot.send_message(call.message.chat.id, 'Прием заявок закрыт!')

    except Exception as e:
        print(f"An error occurred: {str(e)}")
        bot.send_message(call.message.chat.id, "Упс. Пока еще рано!")


def process_winner(message, user_id, selected_matches_numbers, index=0):
    print(selected_matches_numbers)
    markup = None
    print(index)
    if index >= len(selected_matches_numbers):
        bot.send_message(message.chat.id,
                         'Все выборы победителей были успешно записаны.',
                         reply_markup=types.ReplyKeyboardRemove())
        return
    match_id = selected_matches_numbers[index]
    conn, cursor = create_connection('selected_matches.db')
    if conn is not None and cursor is not None:
        cursor.execute(
            'SELECT * FROM selected_matches WHERE id = ?', (match_id,))
        match_data = cursor.fetchone()
        cursor.close()
        conn.close()
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    button1 = types.KeyboardButton('1')
    button2 = types.KeyboardButton('2')
    markup.add(button1, button2)
    time.sleep(1)
    bot.send_message(
        message.chat.id,
        'Выберите победителя из пары бойцов:'
    )
    bot.send_message(
        message.chat.id,
        f'1. {match_data[2]} (Коэффициент: {match_data[4]})\n2. {match_data[3]} (Коэффициент: {match_data[5]})',
        reply_markup=markup
    )

    bot.register_next_step_handler(
        message, process_winner_selection_step,
        user_id, selected_matches_numbers, index,
        match_id
    )


def process_winner_selection_step(message, user_id,
                                  selected_matches_numbers,
                                  index, match_id):
    winner_index = message.text.strip()  # Убираем лишние пробелы
    try:

        if winner_index == '1' or winner_index == '2':
            conn, cursor = create_connection('selected_matches.db')
            if conn is not None and cursor is not None:
                cursor.execute(
                    'SELECT * FROM selected_matches WHERE id = ?', (match_id,))
                match_data = cursor.fetchone()
                cursor.close()
                conn.close()
                if winner_index == '1':
                    winner = match_data[2]
                elif winner_index == '2':
                    winner = match_data[3]
                conn, cursor = create_connection('selected_matches.db')
                if conn is not None and cursor is not None:
                    cursor.execute(
                        'INSERT OR IGNORE INTO user_winner_selections '
                        '(user_id, match_id, winner) VALUES (?, ?, ?)',
                        (user_id, match_id, winner)
                    )
                    conn.commit()
                    cursor.close()
                    conn.close()
                    index += 1
                    process_winner(message, user_id,
                                   selected_matches_numbers, index)
        else:
            bot.send_message(
                message.chat.id,
                'Некорректный выбор. Пожалуйста, выберите 1 или 2.'
            )
            process_winner(message, user_id,
                           selected_matches_numbers, index)
    except ValueError:
        # Обработка некорректных данных или запросов
        print("An error occurred:")


@bot.message_handler(commands=['itog'])
@restrict_access
def itog(message):
    count = 0
    try:
        conn, cursor = create_connection('selected_matches.db')
        if conn is not None and cursor is not None:
            col = cursor.execute('SELECT Count(*) FROM players')
            for row in col:
                count = row[0]
            cursor.close()
            conn.close()
    except Exception as e:
        print(f"An error occurred: {str(e)}")
    try:
        conn, cursor = create_connection('selected_matches.db')
        if conn is not None and cursor is not None:

            # Запрос для получения данных о пользователях,
            # их баллах и местах, отсортированных по убыванию баллов
            cursor.execute(
                'SELECT user_id, correct_predictions, place '
                'FROM user_match_predictions '
                'ORDER BY correct_predictions DESC')

            # Получаем результаты запроса
            user_results = cursor.fetchall()
            conn.commit()
            cursor.close()
            conn.close()

        # Итерируемся по результатам и добавляем их на изображение
            for i, result in enumerate(user_results):
                user_id, place, user_score = result
                template = Image.open('4.jpg')
                draw = ImageDraw.Draw(template)
                font = ImageFont.truetype('ufc.ttf', size=60)
                text = f'Ваше место {user_score} из {count}\n  {place} балла(-ов)!'

                # Приблизительно вычисляем размер текста
                # Это значение может потребоваться настроить
                text_width = len(text) * 10
                # Вычисляем координаты для центрирования текста
                x = (template.width - text_width) / 2
                y = 760  # Выберите подходящий отступ для вертикальной позиции
                # Добавляем текст на изображение
                draw.text((x, y), text, fill="black", font=font)
            # Сохраняем изображение с результатами
                buffer = BytesIO()
            # Сохраняем изображение с результатами в буфер
                template.save(buffer, format="JPEG")
            # Отправляем изображение пользователю из буфера
                bot.send_photo(user_id, buffer.getvalue())
    except Exception as e:
        print(f"An error occurred: {str(e)}")


@bot.message_handler(commands=['open'])
@restrict_access
def open(message):
    try:
        conn, cursor = create_connection('selected_matches.db')
        if conn is not None and cursor is not None:

            # Запрос для получения данных о пользователях,
            # их баллах и местах, отсортированных по убыванию баллов
            cursor.execute(
                'SELECT tg_id FROM registration ORDER BY tg_id DESC'
            )
            # Получаем результаты запроса
            user_results = cursor.fetchall()
            conn.commit()
            cursor.close()
            conn.close()
            for i, result in enumerate(user_results):
                user_id = result
                print(user_id[0])
                try:
                    bot.send_message(user_id[0], 'Открыт прием ставок!')
                except Exception as e:
                    print(
                        f"Error sending message to user_id {user_id}: {str(e)}")
    except Exception as e:
        print(f"An error occurred: {str(e)}")


bot.polling()
conn.close()
