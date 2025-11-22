from fastapi import FastAPI, HTTPException
# FastAPI - основной класс для создания API приложения
# HTTPException - для возврата HTTP ошибок клиенту (404, 500, и т.д.)

from fastapi.middleware.cors import CORSMiddleware
'''CORSMiddleware - middleware для обработки CORS (это механизм безопасности в браузерах, 
   который разрешает или блокирует запросы между разными источниками (доменами))
   Позволяет вашему API принимать запросы с других доменов (например, с фронтенда на другом порту)'''

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

import psycopg2
# psycopg2 - драйвер для подключения к PostgreSQL

from psycopg2.extras import RealDictCursor
'''RealDictCursor - специальный курсор, который возвращает результаты запросов в виде
   словарей (dict) вместо кортежей (tuples). Упрощает работу с данными: row['id'] вместо row[0]'''

import os
from dotenv import load_dotenv
''' os - доступ к переменным окружения операционной системы
    load_dotenv - загружает переменные из файла .env в окружение
    Позволяет хранить чувствительные данные (пароли, ключи) отдельно от кода'''

from pydantic import BaseModel
''' BaseModel - базовый класс для создания моделей данных (схем)
    Обеспечивает автоматическую валидацию (проверка, что данные соответствуют ожидаемым правилам
    и формату), сериализацию (процесс преобразования данных из одного формата в другой) и документацию API
    FastAPI использует Pydantic для проверки входящих/исходящих данных'''

from typing import List, Optional

load_dotenv() # загрузили .env

my_api = FastAPI(title='Bank sys')

my_api.mount("/static", StaticFiles(directory="static"), name="static")

# Разрешаем cors для связи с html
my_api.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],  # Только нужные методы
    allow_headers=["*"],  # Только нужные заголовки
)

class Login(BaseModel):
    passport_series: str
    passport_number: str
    password: str

class ClientProfile(BaseModel):
    profile_id: int
    client_id: int
    last_name: str
    first_name: str
    middle_name: Optional[str]
    gender: str
    age: int
    marital_status: str
    account_number: str
    capital: float

def connect_bd(): # для подключения к нашей базе данных
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        database=os.getenv("DB_NAME", "clients"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "2006_KR"),
        cursor_factory=RealDictCursor
    )

@my_api.get("/")
async def serve_index():
    return FileResponse("static/airlines.lk.html")

@my_api.get("/ticket.html")
async def serve_profile():
    return FileResponse("static/ticket.html")

# OPTIONS endpoint
@my_api.options("/api/login")
async def options_login():
    return {"message": "OK"}

"""Аутентификация клиента"""
@my_api.post("/api/login")  # POST запрос для логина
async def login_client(login_data: Login):
    print(f"Получены данные: {login_data}")  # Отладочное сообщение
    conn = None
    try:
        conn = connect_bd()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT a.client_id, p.* 
                FROM clients_auth a
                JOIN clients_profile p ON a.client_id = p.client_id
                WHERE a.passport_series = %s 
                AND a.passport_number = %s 
                AND a.password = %s
            """, (login_data.passport_series, login_data.passport_number, login_data.password))
            
            client = cur.fetchone()
            
            if not client:
                print("Клиент не найден в базе")  # Отладка
                raise HTTPException(status_code=401, detail="Неверные паспортные данные или пароль")
            
            print(f"Найден клиент: {client}")  # Отладка
            return dict(client)
        
    except HTTPException:
        # Это ожидаемая ошибка - клиент не найден
        raise    
    except Exception as e:
        print(f"Ошибка базы данных: {e}")  # Отладка
        raise HTTPException(status_code=500, detail="Ошибка сервера")
    finally:
        if conn:
            conn.close()


@my_api.get("/api/client/{client_id}")
async def get_client_profile(client_id: int):
    """Получить профиль клиента по ID"""
    conn = connect_bd()
    try:
        with conn.cursor() as cur:
            cur.execute("""SELECT * FROM clients_profile WHERE client_id = %s""", (client_id,))
            profile = cur.fetchone()
            
            if not profile:
                raise HTTPException(status_code=404, detail="Клиент не найден")
            
            return dict(profile)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Ошибка сервера")
    finally:
        conn.close()

@my_api.get("/")
async def root():
    return {"message": "Bank API работает"}
