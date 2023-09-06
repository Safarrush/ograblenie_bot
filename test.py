import sqlite3

# Подключение к базе данных
conn = sqlite3.connect('selected_matches.db')
cursor = conn.cursor()

# Запрос всех записей из таблицы selected_matches
cursor.execute('SELECT * FROM selected_matches')
selected_matches = cursor.fetchall()

# Вывод данных о выбранных боях
print("Информация из таблицы selected_matches:")
for row in selected_matches:
    print(
        f"Event: {row[1]}, Fighter 1: {row[2]}, {row[4]}, Fighter 2: {row[3]}, {row[5]}")

# Закрытие соединения с базой данных
conn.close()

# Подключение к базе данных
conn = sqlite3.connect('selected_matches.db')
cursor = conn.cursor()

# Запрос всех записей из таблицы user_winner_selections
cursor.execute('SELECT * FROM user_winner_selections')
user_winners = cursor.fetchall()

# Вывод данных о выборах победителей
print("\nИнформация из таблицы user_winner_selections:")
for row in user_winners:
    print(f"User ID: {row[1]}, Match ID: {row[2]}, Winner: {row[3]}")

# Закрытие соединения с базой данных
cursor.close()
conn.close()

conn = sqlite3.connect('selected_matches.db')
cursor = conn.cursor()

# Запрос всех записей из таблицы winners
cursor.execute('SELECT * FROM winners')
winners = cursor.fetchall()

# Вывод данных о победителях
print("\nИнформация из таблицы winners:")
for row in winners:
    print(f"Event: {row[1]}, Winner: {row[2]}")

# Закрытие соединения с базой данных
cursor.close()
conn.close()

conn = sqlite3.connect('selected_matches.db')
cursor = conn.cursor()

# Запрос всех записей из таблицы user_match_predictions
cursor.execute('SELECT * FROM user_match_predictions')
user_predictions = cursor.fetchall()

# Вывод данных о количестве угаданных боев
print("\nИнформация из таблицы user_match_predictions:")
for row in user_predictions:
    print(f"User ID: {row[0]}, Correct Predictions: {row[1]}")

# Закрытие соединения с базой данных
cursor.close()
conn.close()

conn = sqlite3.connect('selected_matches.db')
cursor = conn.cursor()

# Запрос всех записей из таблицы user_match_predictions
status = cursor.execute('SELECT * FROM play')
print("\nИнформация из таблицы play")
for row in status:
    print(f"{row[0]}")
cursor.close()
conn.close()

conn = sqlite3.connect('selected_matches.db')
cursor = conn.cursor()

# Запрос всех записей из таблицы user_match_predictions
status = cursor.execute('SELECT * FROM url')
print("\nИнформация из таблицы url")
for row in status:
    print(f"{row[0]}")
cursor.close()
conn.close()
