
import sqlite3

conn = sqlite3.connect('park.db')
cursor = conn.cursor()

cursor.execute("SELECT id, username, role FROM users")
users = cursor.fetchall()

print("Пользователи в базе:")
for user in users:
    print(f"ID: {user[0]}, Логин: {user[1]}, Роль: {user[2]}")

conn.close()