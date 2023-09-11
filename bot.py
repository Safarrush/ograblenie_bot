import telebot
import requests
from bs4 import BeautifulSoup
import sqlite3
from telebot import types
import time
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from datetime import datetime


conn = sqlite3.connect('selected_matches.db')
cursor = conn.cursor()
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

event_url = ""

bot = telebot.TeleBot('6275603125:AAGEl6ysowwR5DidT9eZ0MgnSuU8kIfWPyI')


upcoming_events = {}
user_used_command = {}


@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = types.InlineKeyboardMarkup()
    item = types.InlineKeyboardButton(
        "Выбрать бойцов", callback_data='select_winners')
    markup.add(item)
    now = datetime.now()
    current_time = now.strftime("%Y-%m-%d %H:%M:%S")
    print(message.chat.id)
    print(current_time)
    conn = sqlite3.connect('selected_matches.db')
    cursor = conn.cursor()
    cursor.execute(
        'INSERT OR IGNORE INTO registration (tg_id, date_time) VALUES (?, ?)', (message.chat.id, current_time,))
    conn.commit()

    cursor.close()
    conn.close()

    bot.send_message(
        message.chat.id, "Привет! Я бот, который поможет тебе поучаствовать в розыгрыше. Нажми кнопку ниже, чтобы выбрать бойцов победителей предстоящего турнира:", reply_markup=markup)


user_winners = {}


@bot.callback_query_handler(func=lambda call: call.data == 'select_winners')
def select_winners(call):
    user_id = call.from_user.id
    conn = sqlite3.connect('selected_matches.db')
    cursor = conn.cursor()
    cursor.execute(
        'INSERT OR IGNORE INTO players (tg_id) VALUES (?)', (user_id,))
    conn.commit()

    cursor.close()
    conn.close()
    conn = sqlite3.connect('selected_matches.db')
    cursor = conn.cursor()

    # Запрос всех записей из таблицы user_match_predictions
    status = cursor.execute('SELECT * FROM play')
    a = 0
    for row in status:
        a = row[0]
    cursor.close()
    conn.close()
    if a != 1:
        try:
            conn = sqlite3.connect('selected_matches.db')
            cursor = conn.cursor()
            cursor.execute(
                'SELECT user_id FROM user_winner_selections WHERE user_id = ?', (user_id,))
            user_exists = cursor.fetchone()
            cursor.close()
            conn.close()
        except:
            bot.send_message(
                call.message.chat.id, "Упс. Пока еще рано!.")

        if user_exists:
            bot.send_message(call.message.chat.id,
                             "Вы уже сделали свой выбор.")
        else:
            try:
                conn = sqlite3.connect('selected_matches.db')
                cursor = conn.cursor()

                cursor.execute('SELECT * FROM selected_matches')
                selected_matches = cursor.fetchall()

                cursor.close()
                conn.close()

                selected_matches_numbers = [match[0]
                                            for match in selected_matches]

                process_winner(call.message, user_id,
                               selected_matches_numbers, index=0)
            except:
                bot.send_message(
                    call.message.chat.id, 'Пока рано!'
                )
    else:
        bot.send_message(
            call.message.chat.id, 'Прием заявок закрыт!'
        )


@bot.callback_query_handler(func=lambda call: call.data == 'select_winners')
def process_winner(message, user_id, selected_matches_numbers, index=0):
    print(selected_matches_numbers)
    markup = None
    print(index)
    if index >= len(selected_matches_numbers):
        bot.send_message(message.chat.id, "Все выборы победителей были успешно записаны.",
                         reply_markup=types.ReplyKeyboardRemove())
        return
    match_id = selected_matches_numbers[index]

    conn = sqlite3.connect('selected_matches.db')
    cursor = conn.cursor()

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
        message.chat.id, f"Выберите победителя из пары бойцов:")
    bot.send_message(
        message.chat.id, f"1. {match_data[2]} (Коэффициент: {match_data[4]})\n2. {match_data[3]} (Коэффициент: {match_data[5]})", reply_markup=markup)

    bot.register_next_step_handler(
        message, process_winner_selection_step, user_id, selected_matches_numbers, index, match_id)


def process_winner_selection_step(message, user_id, selected_matches_numbers, index, match_id):
    winner_index = message.text.strip()  # Убираем лишние пробелы
    try:

        if winner_index == '1' or winner_index == '2':
            conn = sqlite3.connect('selected_matches.db')
            cursor = conn.cursor()

            cursor.execute(
                'SELECT * FROM selected_matches WHERE id = ?', (match_id,))
            match_data = cursor.fetchone()

            cursor.close()
            conn.close()

            if winner_index == '1':
                winner = match_data[2]
            elif winner_index == '2':
                winner = match_data[3]

            conn = sqlite3.connect('selected_matches.db')
            cursor = conn.cursor()

            cursor.execute('INSERT INTO user_winner_selections (user_id, match_id, winner) VALUES (?, ?, ?)',
                           (user_id, match_id, winner))
            conn.commit()

            cursor.close()
            conn.close()

            index += 1
            process_winner(message, user_id,
                           selected_matches_numbers, index)
        else:
            bot.send_message(
                message.chat.id, "Некорректный выбор. Пожалуйста, выберите 1 или 2.")
            process_winner(message, user_id,
                           selected_matches_numbers, index)
    except ValueError:
        pass  # Обработка некорректных данных или запросов


@bot.message_handler(commands=['itog'])
def itog(message):
    count = 0
    try:
        conn = sqlite3.connect('selected_matches.db')
        cursor = conn.cursor()

        col = cursor.execute('SELECT Count(*) FROM players')
        for row in col:
            count = row[0]
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"An error occurred: {str(e)}")
    try:
        conn = sqlite3.connect('selected_matches.db')
        cursor = conn.cursor()

        # Запрос для получения данных о пользователях, их баллах и местах, отсортированных по убыванию баллов
        cursor.execute(
            'SELECT user_id, correct_predictions, place FROM user_match_predictions ORDER BY correct_predictions DESC')

        # Получаем результаты запроса
        user_results = cursor.fetchall()
        print(len(user_results))

        # Итерируемся по результатам и добавляем их на изображение
        for i, result in enumerate(user_results):
            user_id, place, user_score = result
            template = Image.open('4.jpg')
            draw = ImageDraw.Draw(template)
            font = ImageFont.truetype('123.otf', size=30)
            text = f"Вы заняли {user_score}/{count} место с {place} баллами!"

            # Приблизительно вычисляем размер текста
            # Это значение может потребоваться настроить
            text_width = len(text) * 10

            # Вычисляем координаты для центрирования текста
            x = (template.width - text_width) / 2
            y = 500  # Выберите подходящий отступ для вертикальной позиции

            # Добавляем текст на изображение
            draw.text((x, y), text, fill="black", font=font)

        # Сохраняем изображение с результатами
            buffer = BytesIO()

        # Сохраняем изображение с результатами в буфер
            template.save(buffer, format="JPEG")

        # Отправляем изображение пользователю из буфера
            bot.send_photo(user_id, buffer.getvalue())

        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"An error occurred: {str(e)}")


bot.polling()
conn.close()
