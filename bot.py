import telebot
import requests
from bs4 import BeautifulSoup
import sqlite3

# Замените 'YOUR_BOT_TOKEN' на токен вашего бота
bot = telebot.TeleBot('6275603125:AAGEl6ysowwR5DidT9eZ0MgnSuU8kIfWPyI')

# Создание и подключение к базе данных
conn = sqlite3.connect('selected_matches.db')
cursor = conn.cursor()

# Создание таблицы для хранения информации о боях
cursor.execute('''
    CREATE TABLE IF NOT EXISTS selected_matches (
        id INTEGER PRIMARY KEY,
        event_name TEXT,
        fighter1_name TEXT,
        fighter2_name TEXT
    )
''')

conn.commit()

upcoming_events = {}

def update_upcoming_events():
    url = "http://www.ufcstats.com/statistics/events/upcoming"
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")
    upcoming_events.clear()
    for i, event_row in enumerate(soup.find_all("tr", class_="b-statistics__table-row")):
        event_name_elem = event_row.find("i", class_="b-statistics__table-content")
        event_url = event_row.find("a", "b-link b-link_style_black")
        if event_url:
            url = event_url['href']
            text = event_url.get_text(strip=True)
            upcoming_events[i + 1] = text, url
        else:
            print("Link not found")
        

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Привет! Я бот, который поможет тебе получить информацию о предстоящих турнирах UFC. Просто напиши /get_upcoming_events для списка турниров или /all_upcoming_events для полного списка.")

@bot.message_handler(commands=['get_upcoming_events'])
def get_upcoming_events(message):
    update_upcoming_events()  # Обновляем список турниров
    events_list = "\n".join([f"{i}. {event}" for i, event in upcoming_events.items()])
    bot.reply_to(message, f"Список предстоящих турниров:\n{events_list}\n\nВыберите номер турнира командой /select_event <номер>.")

@bot.message_handler(commands=['all_upcoming_events'])
def all_upcoming_events(message):
    update_upcoming_events()  # Обновляем список турниров
    events_list_text = "\n".join([f"{i + 1}. {event}" for i, event in upcoming_events.items()])
    bot.reply_to(message, f"Список всех предстоящих турниров:\n{events_list_text}")

matches_dict = {}
def parse_and_store_matches(selected_event):
    _, url = selected_event  # selected_event - это кортеж (название турнира, URL)
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")
    
    match_number = 1  # Инициализируем номер боя
    matches_dict.clear()
    for match_row in soup.find_all("tr", class_="b-fight-details__table-row"):
        fight_name_elems = match_row.find_all("a", class_="b-link b-link_style_black")
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
        fight_name_elems = match_row.find_all("a", class_="b-link b-link_style_black")
        if len(fight_name_elems) >= 2:
            fighter1_name = fight_name_elems[0].get_text(strip=True)
            fighter2_name = fight_name_elems[1].get_text(strip=True)
            
            matches_dict[match_number] = (fighter1_name, fighter2_name)
            match_number += 1

    # Вывод информации о выбранных боях
    events_text = "\n".join([f"{i + 1}. {event}" for i, event in matches_dict.items()])
    bot.reply_to(message, f"Список выбранных боев:\n{events_text}")
    
    # Запрос пользователя о выборе боев для записи в базу данных
    bot.reply_to(message, "Выберите бои для записи в базу данных, перечислив номера через запятую (например: 1, 3, 5).")

    # Ожидание ответа от пользователя
    bot.register_next_step_handler(message, finalize_selected_matches, selected_event)

def finalize_selected_matches(message, selected_event):
    selected_matches_numbers = [int(num) - 1 for num in message.text.replace(' ', '').split(',')]  # Корректируем номера боев

    # Отфильтровать выбранные бои и записать их в базу данных
    selected_matches_to_insert = [(selected_event[0], match[0], match[1]) for num, match in matches_dict.items() if num in selected_matches_numbers]

    # Открываем новый курсор для работы с базой данных
    conn = sqlite3.connect('selected_matches.db')
    cursor = conn.cursor()

    # Вставка выбранных боев в базу данных
    cursor.executemany('INSERT INTO selected_matches (event_name, fighter1_name, fighter2_name) VALUES (?, ?, ?)', selected_matches_to_insert)
    conn.commit()

    # Закрываем соединение с базой данных
    cursor.close()
    conn.close()

    bot.reply_to(message, "Выбранные бои были успешно записаны в базу данных.")



@bot.message_handler(commands=['select_event'])
def select_event(message):
    try:
        event_number = int(message.text.split()[1])
        print(event_number)
        if event_number in upcoming_events:
            selected_event = upcoming_events[event_number]
            bot.reply_to(message, f"Выбран турнир: {selected_event}. Загружаю информацию о боях...")
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
        bot.reply_to(message, "Используйте команду /select_event <номер> для выбора турнира.")

@bot.message_handler(commands=['clear_selected_matches'])
def clear_selected_matches(message):
    # Открываем соединение с базой данных
    conn = sqlite3.connect('selected_matches.db')
    cursor = conn.cursor()

    # Очищаем таблицу selected_matches
    cursor.execute('DELETE FROM selected_matches')
    conn.commit()

    # Закрываем соединение с базой данных
    cursor.close()
    conn.close()

    bot.reply_to(message, "Все записи выбранных боев были успешно удалены из базы данных.")


bot.polling()
conn.close()
