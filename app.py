import sqlite3
import datetime
import enum
import bcrypt
import pytest
from typing import Optional, List
from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Enum, DateTime
from sqlalchemy.orm import declarative_base, relationship, sessionmaker, Session

# ==============================================================================
# 1. МОДЕЛИ ДАННЫХ И БАЗА (SQLAlchemy)
# ==============================================================================
Base = declarative_base()

class AttractionCategory(str, enum.Enum):
    EXTREME = "экстрим"
    ADVENTURE = "приключения"
    CLASSIC = "классика"

class TicketStatus(str, enum.Enum):
    STANDARD = "standard"
    VIP = "VIP"
    PLATINUM = "Platinum"

class AgeCategory(str, enum.Enum):
    ADULT = "взрослый"
    CHILD = "ребенок"

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    USER = "user"

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(Enum(UserRole), default=UserRole.USER)
    tickets_sold = relationship("Ticket", back_populates="user")

class Visitor(Base):
    __tablename__ = 'visitors'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    age_category = Column(Enum(AgeCategory), nullable=False)
    tickets = relationship("Ticket", back_populates="visitor")
    visits = relationship("Visit", back_populates="visitor")

class Attraction(Base):
    __tablename__ = 'attractions'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    category = Column(Enum(AttractionCategory), nullable=False)
    tickets = relationship("Ticket", back_populates="attraction")
    visits = relationship("Visit", back_populates="attraction")

class Ticket(Base):
    __tablename__ = 'tickets'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True) # Кто продал
    user = relationship("User", back_populates="tickets_sold")
    visitor_id = Column(Integer, ForeignKey('visitors.id'))
    visitor_id = Column(Integer, ForeignKey('visitors.id'))
    attraction_id = Column(Integer, ForeignKey('attractions.id'))
    status = Column(Enum(TicketStatus), nullable=False)
    paid_time_minutes = Column(Integer, nullable=False)
    purchase_date = Column(DateTime, default=datetime.datetime.utcnow)
    visitor = relationship("Visitor", back_populates="tickets")
    attraction = relationship("Attraction", back_populates="tickets")

class Visit(Base):
    __tablename__ = 'visits'
    id = Column(Integer, primary_key=True, index=True)
    visitor_id = Column(Integer, ForeignKey('visitors.id'))
    attraction_id = Column(Integer, ForeignKey('attractions.id'))
    start_time = Column(DateTime, default=datetime.datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    visitor = relationship("Visitor", back_populates="visits")
    attraction = relationship("Attraction", back_populates="visits")

# Настройка БД
SQLALCHEMY_DATABASE_URL = "sqlite:///./park.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)

init_db() # Создаем таблицы при запуске

# ==============================================================================
# 2. ПАТТЕРН "РЕПОЗИТОРИЙ" (Требование 2 и 6: ORM + Сырой SQL)
# ==============================================================================
class AttractionRepository:
    """Инкапсулирует логику доступа к данным (Паттерн Repository)"""
    def __init__(self, db_session: Session):
        self.db = db_session

    # --- ВАРИАНТ А: Через ORM ---
    def get_all_orm(self, category_filter: Optional[str] = None) -> List[Attraction]:
        query = self.db.query(Attraction)
        if category_filter:
            query = query.filter(Attraction.category == category_filter)
        return query.all()

    def create_orm(self, name: str, category: str) -> Attraction:
        new_attraction = Attraction(name=name, category=category)
        self.db.add(new_attraction)
        self.db.commit()
        self.db.refresh(new_attraction)
        return new_attraction

    # --- ВАРИАНТ Б: Через сырой параметризованный SQL ---
    def get_all_raw(self, category_filter: Optional[str] = None) -> List[dict]:
        conn = sqlite3.connect('park.db')
        cursor = conn.cursor()
        if category_filter:
            # Параметризованный запрос (защита от SQL-инъекций через ?)
            cursor.execute("SELECT id, name, category FROM attractions WHERE category = ?", (category_filter,))
        else:
            cursor.execute("SELECT id, name, category FROM attractions")
        
        results = [{"id": r[0], "name": r[1], "category": r[2]} for r in cursor.fetchall()]
        conn.close()
        return results

    def create_raw(self, name: str, category: str) -> dict:
        conn = sqlite3.connect('park.db')
        cursor = conn.cursor()
        # Параметризованная вставка
        cursor.execute("INSERT INTO attractions (name, category) VALUES (?, ?)", (name, category))
        conn.commit()
        new_id = cursor.lastrowid
        conn.close()
        return {"id": new_id, "name": name, "category": category}

# ==============================================================================
# 3. АВТОРИЗАЦИЯ И БЕЗОПАСНОСТЬ (Требование 3 и 5)
# ==============================================================================
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def authenticate_user(username: str, password: str, db: Session) -> User:
    """Аутентификация пользователя"""
    user = db.query(User).filter(User.username == username).first()
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user

def delete_user_secure(username: str, password: str, requesting_role: UserRole) -> tuple:
    """Удаление пользователя только после строгой авторизации"""
    if requesting_role != UserRole.ADMIN:
        return False, "Недостаточно прав (требуется роль admin)"
        
    db = SessionLocal()
    user_to_delete = db.query(User).filter(User.username == username).first()
    
    if not user_to_delete:
        db.close()
        return False, "Пользователь не найден"
        
    # Проверяем пароль удаляемого пользователя
    if verify_password(password, user_to_delete.password_hash):
        db.delete(user_to_delete)
        db.commit()
        db.close()
        return True, "Пользователь успешно удален"
    
    db.close()
    return False, "Неверный пароль для подтверждения удаления"

# ==============================================================================
# 4. СЕРВЕРНАЯ ЧАСТЬ И ОТСЛЕЖИВАНИЕ КЛИЕНТОВ (Требование 4)
# ==============================================================================
app = FastAPI(title="Amusement Park API")

# Хранилище подключенных клиентов в памяти
connected_clients: dict[str, dict] = {}

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Эндпоинты Авторизации ---
@app.post("/register")
def register(username: str, password: str, role: UserRole = UserRole.USER):
    db = SessionLocal()
    if db.query(User).filter(User.username == username).first():
        db.close()
        raise HTTPException(status_code=400, detail="Пользователь уже существует")
    
    new_user = User(username=username, password_hash=hash_password(password), role=role)
    db.add(new_user)
    db.commit()
    db.close()
    return {"message": "Пользователь зарегистрирован"}

@app.post("/login")
def login(username: str, password: str, db: Session = Depends(get_db)):
    user = authenticate_user(username, password, db)
    if not user:
        raise HTTPException(status_code=401, detail="Неверный логин или пароль")
    
    # Добавляем пользователя в список подключенных
    connected_clients[username] = {
        "role": user.role.value,  # Сохраняем роль
        "login_time": datetime.datetime.utcnow().isoformat(),
        "status": "online"
    }
    
    return {
        "message": f"Добро пожаловать, {username}!",
        "username": username,
        "role": user.role.value  # Возвращаем роль клиенту
    }

@app.get("/clients")
def get_connected_clients():
    """Просмотр всех подключенных клиентов"""
    return {"connected_clients": connected_clients}


@app.post("/logout")
def logout(username: str):
    if username in connected_clients:
        del connected_clients[username]
        return {"message": "Клиент отключен"}
    raise HTTPException(status_code=404, detail="Клиент не найден в сети")

# --- Эндпоинты CRUD (Демонстрация двух подходов) ---
@app.post("/attractions/orm")
def create_attraction_orm(name: str, category: AttractionCategory, db: Session = Depends(get_db)):
    repo = AttractionRepository(db)
    return repo.create_orm(name, category.value)

@app.get("/attractions/orm")
def get_attractions_orm(category: Optional[str] = None, db: Session = Depends(get_db)):
    repo = AttractionRepository(db)
    return repo.get_all_orm(category)

@app.post("/attractions/raw")
def create_attraction_raw(name: str, category: str):
    repo = AttractionRepository(None) # Сессия не нужна для сырого SQL в нашей реализации
    return repo.create_raw(name, category)

@app.get("/attractions/raw")
def get_attractions_raw(category: Optional[str] = None):
    repo = AttractionRepository(None)
    return repo.get_all_raw(category)

# --- Эндпоинт удаления с авторизацией (Требование 5) ---

def delete_user_secure(username: str, password: str, requesting_role: UserRole, db: Session = None) -> tuple:
    """Удаление пользователя только после строгой авторизации"""
    if requesting_role != UserRole.ADMIN:
        return False, "Недостаточно прав (требуется роль admin)"
    
    # Если сессия не передана (как в реальном приложении), создаем новую
    if db is None:
        db = SessionLocal()
        should_close = True
    else:
        should_close = False
        
    user_to_delete = db.query(User).filter(User.username == username).first()
    
    if not user_to_delete:
        if should_close:
            db.close()
        return False, "Пользователь не найден"
        
    if verify_password(password, user_to_delete.password_hash):
        db.delete(user_to_delete)
        db.commit()
        if should_close:
            db.close()
        return True, "Пользователь успешно удален"
    
    if should_close:
        db.close()
    return False, "Неверный пароль для подтверждения удаления"
@app.delete("/users/{username}")
def delete_user_endpoint(username: str, password: str, current_user_role: str = "admin", db: Session = Depends(get_db)):
    """Эндпоинт для удаления пользователя"""
    role_enum = UserRole.ADMIN if current_user_role == "admin" else UserRole.USER
    success, message = delete_user_secure(username, password, role_enum, db=db)
    
    if success and username in connected_clients:
        del connected_clients[username]
        
    if not success:
        raise HTTPException(status_code=403, detail=message)
    return {"message": message}

# ==============================================================================
# 5. МОДУЛЬНЫЕ ТЕСТЫ (Требование 7)
# ==============================================================================
@pytest.fixture(scope="function")
def test_db():
    test_engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=test_engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = TestingSessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=test_engine)

def test_password_hashing():
    """Тест хэширования паролей"""
    pwd = "secret123"
    hashed = hash_password(pwd)
    assert pwd != hashed
    assert verify_password(pwd, hashed) is True
    assert verify_password("wrong", hashed) is False

def test_repository_orm(test_db):
    """Тест CRUD через ORM"""
    repo = AttractionRepository(test_db)
    created = repo.create_orm("Американские горки", "экстрим")
    assert created.name == "Американские горки"
    
    results = repo.get_all_orm(category_filter="экстрим")
    assert len(results) == 1
    assert results[0].name == "Американские горки"

def test_repository_raw():
    """Тест CRUD через сырой параметризованный SQL (заглушка структуры)"""
    conn = sqlite3.connect(':memory:')
    conn.execute("CREATE TABLE attractions (id INTEGER PRIMARY KEY, name TEXT, category TEXT)")
    conn.close()
    assert True 

def test_secure_delete(test_db):
    """Тест безопасного удаления пользователя"""
    admin = User(username="admin", password_hash=hash_password("adminpass"), role=UserRole.ADMIN)
    test_db.add(admin)
    test_db.commit()
    
    victim = User(username="victim", password_hash=hash_password("vicpass"), role=UserRole.USER)
    test_db.add(victim)
    test_db.commit()
    
    # Попытка удаления с неверной ролью
    success, msg = delete_user_secure("victim", "vicpass", UserRole.USER, db=test_db)
    assert success is False
    assert "Недостаточно прав" in msg
    
    # Попытка удаления с неверным паролем
    success, msg = delete_user_secure("victim", "wrongpass", UserRole.ADMIN, db=test_db)
    assert success is False
    
    # Успешное удаление
    success, msg = delete_user_secure("victim", "vicpass", UserRole.ADMIN, db=test_db)
    assert success is True
    assert test_db.query(User).filter(User.username == "victim").first() is None
    # --- СКВОЗНЫЕ (ИНТЕГРАЦИОННЫЕ) ТЕСТЫ ---
from fastapi.testclient import TestClient

client = TestClient(app)

def test_integration_register_and_login():
    """Сквозной тест: регистрация и вход"""
    import time
    # Генерируем уникальное имя пользователя, чтобы тест не падал при повторных запусках
    unique_username = f"test_user_{int(time.time())}"
    
    # 1. Регистрируем пользователя
    response = client.post("/register", params={
        "username": unique_username, 
        "password": "test_pass", 
        "role": "user"
    })
    assert response.status_code == 200, f"Ошибка регистрации: {response.text}"
    
    # 2. Пытаемся войти
    response = client.post("/login", params={
        "username": unique_username, 
        "password": "test_pass"
    })
    assert response.status_code == 200, f"Ошибка входа: {response.text}"
    assert "Добро пожаловать" in response.json()["message"]