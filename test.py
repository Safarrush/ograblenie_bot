import sqlite3

# Подключение к базе данных
conn = sqlite3.connect('selected_matches.db')
cursor = conn.cursor()

# Запрос всех записей из таблицы selected_matches
cursor.execute('SELECT * FROM selected_matches')
selected_matches = cursor.fetchall()

# Вывод данных о выбранных боях
for row in selected_matches:
    print(f"Event: {row[1]}, Fighter 1: {row[2]}, Fighter 2: {row[3]}")

# Закрытие соединения с базой данных
conn.close()