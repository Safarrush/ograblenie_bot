import telebot
import requests
from bs4 import BeautifulSoup
import sqlite3
from telebot import types


event_url = ""
# Замените 'YOUR_BOT_TOKEN' на токен вашего бота
bot = telebot.TeleBot('6275603125:AAGEl6ysowwR5DidT9eZ0MgnSuU8kIfWPyI')


upcoming_events = {}
user_used_command = {}


@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = types.InlineKeyboardMarkup()
    item = types.InlineKeyboardButton(
        "Выбрать бойцов", callback_data='select_winners')
    markup.add(item)

    bot.send_message(
        message.chat.id, "Привет! Я бот, который поможет тебе поучаствовать в розыгрыше. Нажми кнопку ниже, чтобы выбрать бойцов победителей предстоящего турнира:", reply_markup=markup)


user_winners = {}


@bot.callback_query_handler(func=lambda call: call.data == 'select_winners')
def select_winners(call):
    user_id = call.from_user.id
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

    if index < len(selected_matches_numbers):
        match_id = selected_matches_numbers[index]

        conn = sqlite3.connect('selected_matches.db')
        cursor = conn.cursor()

        cursor.execute(
            'SELECT * FROM selected_matches WHERE id = ?', (match_id,))
        match_data = cursor.fetchone()

        cursor.close()
        conn.close()

        markup = types.InlineKeyboardMarkup(row_width=2)
        button_1 = types.InlineKeyboardButton(
            "1", callback_data=f'{user_id}_{selected_matches_numbers}_{index}_{match_id}_1')
        button_2 = types.InlineKeyboardButton(
            "2", callback_data=f'{user_id}_{selected_matches_numbers}_{index}_{match_id}_2')
        markup.add(button_1, button_2)
        bot.send_message(
            message.chat.id, f"Выберите победителя из пары бойцов:")
        bot.send_message(
            message.chat.id, f"1. {match_data[2]} (Коэффициент: {match_data[4]})\n2. {match_data[3]} (Коэффициент: {match_data[5]})", reply_markup=markup)
    else:
        bot.reply_to(message, "Все выборы победителей были успешно записаны.")
    # bot.register_next_step_handler(
    # message, process_winner_selection_step, user_id, selected_matches_numbers, index, match_id)


@bot.callback_query_handler(func=lambda call: True)
def process_winner_callback(call):
    call.data.split('_')
    try:
        data = call.data.split('_')
        user_id = int(data[0])
        selected_matches = data[1]
        selected_matches1 = [s.split(',') for s in selected_matches]
        selected_matches_numbers = [
            int(item[0]) for item in selected_matches1 if item[0].isdigit()]

        index = int(data[2])
        match_id = int(data[3])

        winner_index = data[4]  # Получаем выбор пользователя

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
            process_winner(call.message, user_id,
                           selected_matches_numbers, index)
        else:
            bot.send_message(
                call.message.chat.id, "Некорректный выбор. Пожалуйста, выберите 1 или 2.")
    except ValueError:
        pass  # Обработка некорректных данных или запросов


bot.polling()
