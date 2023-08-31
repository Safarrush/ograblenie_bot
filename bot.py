import telebot
import requests
from bs4 import BeautifulSoup
import sqlite3

event_url = ""
# Замените 'YOUR_BOT_TOKEN' на токен вашего бота
bot = telebot.TeleBot('6275603125:AAGEl6ysowwR5DidT9eZ0MgnSuU8kIfWPyI')


upcoming_events = {}
user_used_command = {}


@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Привет! Я бот, который поможет тебе поучаствовать в розыгрыше. Просто напиши /select_winners для выбора бойцов победителей предстоящего турнира.")


user_winners = {}


@bot.message_handler(commands=['select_winners'])
def select_winners(message):
    user_id = message.from_user.id
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
            message.chat.id, "Упс. Пока еще рано!.")

    if user_exists:
        bot.reply_to(message, "Вы уже сделали свой выбор.")
    else:
        try:
            conn = sqlite3.connect('selected_matches.db')
            cursor = conn.cursor()

            cursor.execute('SELECT * FROM selected_matches')
            selected_matches = cursor.fetchall()

            cursor.close()
            conn.close()

            selected_matches_numbers = [match[0] for match in selected_matches]

            process_winner(message, user_id, selected_matches_numbers, index=0)
        except:
            bot.send_message(
                message.chat.id, 'Пока рано!'
            )


def process_winner(message, user_id, selected_matches_numbers, index=0):
    if index >= len(selected_matches_numbers) and message.text not in ['/select_winners']:
        bot.reply_to(message, "Все выборы победителей были успешно записаны.")
        return

    match_id = selected_matches_numbers[index]

    conn = sqlite3.connect('selected_matches.db')
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM selected_matches WHERE id = ?', (match_id,))
    match_data = cursor.fetchone()

    cursor.close()
    conn.close()

    bot.reply_to(message, f"Выберите победителя из пары бойцов:")
    bot.send_message(
        message.chat.id, f"1. {match_data[2]} (Коэффициент: {match_data[4]})\n2. {match_data[3]} (Коэффициент: {match_data[5]})")
    bot.register_next_step_handler(
        message, process_winner_selection_step, user_id, selected_matches_numbers, index, match_id)


def process_winner_selection_step(message, user_id, selected_matches_numbers, index, match_id):
    winner_index = message.text.strip()  # Убираем лишние пробелы

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
        else:
            winner = match_data[3]

        conn = sqlite3.connect('selected_matches.db')
        cursor = conn.cursor()

        cursor.execute('INSERT INTO user_winner_selections (user_id, match_id, winner) VALUES (?, ?, ?)',
                       (user_id, match_id, winner))
        conn.commit()

        cursor.close()
        conn.close()

        index += 1
        process_winner(message, user_id, selected_matches_numbers, index)
    else:
        bot.reply_to(
            message, "Некорректный выбор. Пожалуйста, выберите 1 или 2.")
        process_winner(message, user_id, selected_matches_numbers, index)


bot.polling()
