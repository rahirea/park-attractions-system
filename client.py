import tkinter as tk
from tkinter import ttk, messagebox
import requests
import json

# Адрес нашего сервера
SERVER_URL = "http://127.0.0.1:8000"

class LoginWindow:
    """Окно входа/регистрации"""
    def __init__(self, root):
        self.root = root
        self.root.title("Парк развлечений - Вход")
        self.root.geometry("400x300")
        
        # Создаем фреймы
        login_frame = ttk.LabelFrame(root, text="Вход в систему", padding=10)
        login_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Поле логина
        ttk.Label(login_frame, text="Логин:").grid(row=0, column=0, sticky="w", pady=5)
        self.username_entry = ttk.Entry(login_frame, width=30)
        self.username_entry.grid(row=0, column=1, pady=5, padx=5)
        
        # Поле пароля
        ttk.Label(login_frame, text="Пароль:").grid(row=1, column=0, sticky="w", pady=5)
        self.password_entry = ttk.Entry(login_frame, width=30, show="*")
        self.password_entry.grid(row=1, column=1, pady=5, padx=5)
        
        # Кнопки
        btn_frame = ttk.Frame(login_frame)
        btn_frame.grid(row=2, column=0, columnspan=2, pady=20)
        
        ttk.Button(btn_frame, text="Войти", command=self.login).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Регистрация", command=self.register).pack(side="left", padx=5)
    
    def login(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        
        if not username or not password:
            messagebox.showerror("Ошибка", "Введите логин и пароль")
            return
        
        try:
            # Добавляем таймаут 5 секунд
            response = requests.post(
                f"{SERVER_URL}/login", 
                params={"username": username, "password": password},
                timeout=5  # Таймаут в секундах
            )
            
            if response.status_code == 200:
                # Получаем данные из ответа
                user_data = response.json()
                role = user_data.get("role", "user")
                
                messagebox.showinfo("Успех", f"Добро пожаловать, {username}!\nРоль: {role}")
                self.root.destroy()
                open_main_window(username, role)
            elif response.status_code == 401:
                messagebox.showerror("Ошибка", "Неверный логин или пароль")
            else:
                messagebox.showerror("Ошибка", f"Ошибка сервера: {response.status_code}")
                
        except requests.exceptions.Timeout:
            messagebox.showerror("Ошибка", "Превышено время ожидания ответа от сервера")
        except requests.exceptions.ConnectionError:
            messagebox.showerror("Ошибка", "Не удалось подключиться к серверу.\nУбедитесь, что server.py запущен!")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Неизвестная ошибка: {str(e)}")
            
    def register(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        
        if not username or not password:
            messagebox.showerror("Ошибка", "Введите логин и пароль")
            return
        
        try:
            response = requests.post(f"{SERVER_URL}/register", params={
                "username": username,
                "password": password,
                "role": "user"
            })
            
            if response.status_code == 200:
                messagebox.showinfo("Успех", "Пользователь зарегистрирован! Теперь войдите.")
            else:
                messagebox.showerror("Ошибка", "Пользователь уже существует")
        except requests.exceptions.ConnectionError:
            messagebox.showerror("Ошибка", "Сервер не доступен. Запустите server.py")


class MainWindow:
    """Основное окно приложения"""
    def __init__(self, root, username, role):  # Добавили параметр role
        self.root = root
        self.username = username
        self.role = role  # Сохраняем роль
        self.root.title(f"Парк развлечений - {username} ({role})")
        self.root.geometry("900x600")
        
        # Создаем вкладки
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Вкладка аттракционов (доступна всем)
        self.attractions_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.attractions_frame, text="Аттракционы")
        self.create_attractions_tab()
        
        # Вкладка клиентов (ТОЛЬКО для админов)
        if role == "admin":
            self.clients_frame = ttk.Frame(self.notebook)
            self.notebook.add(self.clients_frame, text="Подключенные клиенты")
            self.create_clients_tab()
        
        # Вкладка управления пользователями (ТОЛЬКО для админов)
        if role == "admin":
            self.users_frame = ttk.Frame(self.notebook)
            self.notebook.add(self.users_frame, text="Пользователи")
            self.create_users_tab()
        
        # Кнопка выхода
        ttk.Button(root, text="Выйти", command=self.logout).pack(pady=5)

    def create_attractions_tab(self):
        """Вкладка управления аттракционами"""
        # Фрейм добавления
        add_frame = ttk.LabelFrame(self.attractions_frame, text="Добавить аттракцион", padding=10)
        add_frame.pack(fill="x", padx=10, pady=10)
        
        ttk.Label(add_frame, text="Название:").grid(row=0, column=0, sticky="w", pady=5)
        self.attr_name = ttk.Entry(add_frame, width=30)
        self.attr_name.grid(row=0, column=1, pady=5, padx=5)
        
        ttk.Label(add_frame, text="Категория:").grid(row=0, column=2, sticky="w", pady=5)
        self.attr_category = ttk.Combobox(add_frame, values=["экстрим", "приключения", "классика"], width=20)
        self.attr_category.grid(row=0, column=3, pady=5, padx=5)
        self.attr_category.current(0)
        
        btn_frame = ttk.Frame(add_frame)
        btn_frame.grid(row=1, column=0, columnspan=4, pady=10)
        
        ttk.Button(btn_frame, text="Добавить (ORM)", command=lambda: self.add_attraction("orm")).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Добавить (SQL)", command=lambda: self.add_attraction("raw")).pack(side="left", padx=5)
        
        # Фрейм просмотра
        view_frame = ttk.LabelFrame(self.attractions_frame, text="Список аттракционов", padding=10)
        view_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Таблица
        columns = ("ID", "Название", "Категория")
        self.tree = ttk.Treeview(view_frame, columns=columns, show="headings", height=15)
        
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=200)
        
        self.tree.pack(side="left", fill="both", expand=True)
        
        # Скроллбар
        scrollbar = ttk.Scrollbar(view_frame, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # Кнопки управления
        ctrl_frame = ttk.Frame(view_frame)
        ctrl_frame.pack(fill="x", pady=10)
        
        ttk.Button(ctrl_frame, text="Обновить (ORM)", command=lambda: self.load_attractions("orm")).pack(side="left", padx=5)
        ttk.Button(ctrl_frame, text="Обновить (SQL)", command=lambda: self.load_attractions("raw")).pack(side="left", padx=5)
        
        # Фильтр
        ttk.Label(ctrl_frame, text="Фильтр по категории:").pack(side="left", padx=10)
        self.filter_category = ttk.Combobox(ctrl_frame, values=["Все", "экстрим", "приключения", "классика"], width=15)
        self.filter_category.pack(side="left", padx=5)
        self.filter_category.current(0)
        ttk.Button(ctrl_frame, text="Применить", command=self.apply_filter).pack(side="left", padx=5)
    
    def add_attraction(self, method):
        """Добавление аттракциона"""
        name = self.attr_name.get()
        category = self.attr_category.get()
        
        if not name:
            messagebox.showerror("Ошибка", "Введите название аттракциона")
            return
        
        try:
            if method == "orm":
                response = requests.post(f"{SERVER_URL}/attractions/orm", params={
                    "name": name,
                    "category": category
                })
            else:
                response = requests.post(f"{SERVER_URL}/attractions/raw", params={
                    "name": name,
                    "category": category
                })
            
            if response.status_code == 200:
                messagebox.showinfo("Успех", "Аттракцион добавлен!")
                self.attr_name.delete(0, tk.END)
                self.load_attractions("orm")
            else:
                messagebox.showerror("Ошибка", "Не удалось добавить аттракцион")
        except requests.exceptions.ConnectionError:
            messagebox.showerror("Ошибка", "Сервер не доступен")
    
    def load_attractions(self, method):
        """Загрузка списка аттракционов"""
        # Очищаем таблицу
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        try:
            if method == "orm":
                response = requests.get(f"{SERVER_URL}/attractions/orm")
            else:
                response = requests.get(f"{SERVER_URL}/attractions/raw")
            
            if response.status_code == 200:
                attractions = response.json()
                for attr in attractions:
                    self.tree.insert("", tk.END, values=(
                        attr.get("id", "N/A"),
                        attr.get("name", "N/A"),
                        attr.get("category", "N/A")
                    ))
        except requests.exceptions.ConnectionError:
            messagebox.showerror("Ошибка", "Сервер не доступен")
    
    def apply_filter(self):
        """Применение фильтра"""
        filter_val = self.filter_category.get()
        if filter_val == "Все":
            self.load_attractions("orm")
        else:
            try:
                response = requests.get(f"{SERVER_URL}/attractions/orm", params={"category": filter_val})
                if response.status_code == 200:
                    # Очищаем таблицу
                    for item in self.tree.get_children():
                        self.tree.delete(item)
                    attractions = response.json()
                    for attr in attractions:
                        self.tree.insert("", tk.END, values=(
                            attr.get("id", "N/A"),
                            attr.get("name", "N/A"),
                            attr.get("category", "N/A")
                        ))
            except requests.exceptions.ConnectionError:
                messagebox.showerror("Ошибка", "Сервер не доступен")
    
    def create_clients_tab(self):
        """Вкладка подключенных клиентов"""
        btn_frame = ttk.Frame(self.clients_frame)
        btn_frame.pack(pady=10)
        
        ttk.Button(btn_frame, text="Обновить список", command=self.load_clients).pack()
        
        # Текстовое поле для отображения
        self.clients_text = tk.Text(self.clients_frame, height=20, width=80)
        self.clients_text.pack(padx=10, pady=10, fill="both", expand=True)
    
    def load_clients(self):
        """Загрузка списка клиентов"""
        self.clients_text.delete(1.0, tk.END)
        
        try:
            response = requests.get(f"{SERVER_URL}/clients")
            if response.status_code == 200:
                data = response.json()
                clients = data.get("connected_clients", {})
                
                if not clients:
                    self.clients_text.insert(tk.END, "Нет подключенных клиентов\n")
                else:
                    self.clients_text.insert(tk.END, "Подключенные клиенты:\n")
                    self.clients_text.insert(tk.END, "=" * 60 + "\n\n")
                    
                    for username, info in clients.items():
                        self.clients_text.insert(tk.END, f"Пользователь: {username}\n")
                        self.clients_text.insert(tk.END, f"  Роль: {info.get('role', 'N/A')}\n")
                        self.clients_text.insert(tk.END, f"  Статус: {info.get('status', 'N/A')}\n")
                        self.clients_text.insert(tk.END, f"  Время входа: {info.get('login_time', 'N/A')}\n")
                        self.clients_text.insert(tk.END, "-" * 60 + "\n")
            else:
                self.clients_text.insert(tk.END, "Ошибка при получении данных\n")
        except requests.exceptions.ConnectionError:
            self.clients_text.insert(tk.END, "Сервер не доступен\n")
    
    def create_users_tab(self):
        """Вкладка управления пользователями"""
        delete_frame = ttk.LabelFrame(self.users_frame, text="Удаление пользователя", padding=10)
        delete_frame.pack(fill="x", padx=10, pady=10)
        
        ttk.Label(delete_frame, text="Логин пользователя:").grid(row=0, column=0, sticky="w", pady=5)
        self.delete_username = ttk.Entry(delete_frame, width=30)
        self.delete_username.grid(row=0, column=1, pady=5, padx=5)
        
        ttk.Label(delete_frame, text="Пароль для подтверждения:").grid(row=1, column=0, sticky="w", pady=5)
        self.delete_password = ttk.Entry(delete_frame, width=30, show="*")
        self.delete_password.grid(row=1, column=1, pady=5, padx=5)
        
        ttk.Button(delete_frame, text="Удалить пользователя", command=self.delete_user).grid(row=2, column=0, columnspan=2, pady=10)
    
    def delete_user(self):
        """Удаление пользователя"""
        username = self.delete_username.get()
        password = self.delete_password.get()
        
        if not username or not password:
            messagebox.showerror("Ошибка", "Введите логин и пароль")
            return
        
        if not messagebox.askyesno("Подтверждение", f"Вы действительно хотите удалить пользователя {username}?"):
            return
        
        try:
            response = requests.delete(
                f"{SERVER_URL}/users/{username}",
                params={"password": password, "current_user_role": "admin"}
            )
            
            if response.status_code == 200:
                messagebox.showinfo("Успех", "Пользователь удален")
                self.delete_username.delete(0, tk.END)
                self.delete_password.delete(0, tk.END)
            else:
                error_msg = response.json().get("detail", "Ошибка при удалении")
                messagebox.showerror("Ошибка", error_msg)
        except requests.exceptions.ConnectionError:
            messagebox.showerror("Ошибка", "Сервер не доступен")
    
    def logout(self):
        """Выход из системы"""
        try:
            requests.post(f"{SERVER_URL}/logout", params={"username": self.username})
        except:
            pass
        self.root.destroy()
        open_login_window()


def open_login_window():
    """Открытие окна входа"""
    root = tk.Tk()
    app = LoginWindow(root)
    root.mainloop()


def open_main_window(username, role):
    """Открытие основного окна"""
    root = tk.Tk()
    app = MainWindow(root, username, role)  # Передаем роль
    root.mainloop()


if __name__ == "__main__":
    # Устанавливаем библиотеку requests если нужно
    try:
        import requests
    except ImportError:
        import os
        os.system("pip install requests")
        import requests
    
    open_login_window()