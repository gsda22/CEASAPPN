import streamlit as st
import sqlite3
import hashlib
import pandas as pd
from PIL import Image
import datetime
import pytz
from babel.dates import format_datetime

# Configurar o fuso horário de Brasília
BRASILIA_TZ = pytz.timezone('America/Sao_Paulo')

# Database setup
def init_db():
    conn = sqlite3.connect('ceasa.db')
    c = conn.cursor()
    
    # Entidade forte: Usuários
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE NOT NULL,
                  password_hash TEXT NOT NULL,
                  role TEXT NOT NULL,  -- admin, registrador, auditor
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # Entidade forte: Lojas
    c.execute('''CREATE TABLE IF NOT EXISTS stores
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT UNIQUE NOT NULL)''')
    
    # Entidade forte: Produtos (com coluna code)
    c.execute('''CREATE TABLE IF NOT EXISTS products
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  code TEXT UNIQUE,
                  name TEXT NOT NULL,
                  category TEXT,  -- Herança potencial: ex., perecíveis
                  unit TEXT NOT NULL)''')  # ex., kg, unidade
    
    # Entidade fraca: Registros (depende de produto, loja, usuário)
    c.execute('''CREATE TABLE IF NOT EXISTS registrations
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  product_id INTEGER NOT NULL,
                  store_id INTEGER NOT NULL,
                  quantity REAL NOT NULL,
                  registered_by INTEGER NOT NULL,
                  registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY (product_id) REFERENCES products(id),
                  FOREIGN KEY (store_id) REFERENCES stores(id),
                  FOREIGN KEY (registered_by) REFERENCES users(id))''')
    
    # Entidade fraca: Auditorias (depende de registro)
    c.execute('''CREATE TABLE IF NOT EXISTS audits
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  registration_id INTEGER NOT NULL,
                  actual_quantity REAL NOT NULL,
                  audited_by INTEGER NOT NULL,
                  audited_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY (registration_id) REFERENCES registrations(id),
                  FOREIGN KEY (audited_by) REFERENCES users(id))''')
    
    # Verificar e adicionar coluna code se não existir
    c.execute("PRAGMA table_info(products)")
    columns = [info[1] for info in c.fetchall()]
    if 'code' not in columns:
        c.execute("ALTER TABLE products ADD COLUMN code TEXT UNIQUE")
        c.execute("UPDATE products SET code = id WHERE code IS NULL")
        st.warning("Coluna 'code' adicionada à tabela products. Códigos existentes foram preenchidos com IDs. Atualize os códigos manualmente, se necessário.")
    
    # Dados iniciais
    c.execute("SELECT COUNT(*) FROM users")
    if c.fetchone()[0] == 0:
        default_admin_pass = hashlib.sha256("123456".encode()).hexdigest()
        c.execute("INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                  ("admin", default_admin_pass, "admin"))
    
    c.execute("SELECT COUNT(*) FROM stores")
    if c.fetchone()[0] == 0:
        stores = ["SUSSUCA", "VIDA NOVA", "ALPHAVILLE"]
        for store in stores:
            c.execute("INSERT INTO stores (name) VALUES (?)", (store,))
    
    conn.commit()
    conn.close()

init_db()

# Funções auxiliares
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def check_credentials(username, password):
    conn = sqlite3.connect('ceasa.db')
    c = conn.cursor()
    c.execute("SELECT password_hash, role FROM users WHERE username = ?", (username,))
    result = c.fetchone()
    conn.close()
    if result and result[0] == hash_password(password):
        return result[1]  # retorna o papel
    return None

def get_stores():
    conn = sqlite3.connect('ceasa.db')
    c = conn.cursor()
    c.execute("SELECT id, name FROM stores")
    stores = c.fetchall()
    conn.close()
    return stores

def get_products():
    conn = sqlite3.connect('ceasa.db')
    c = conn.cursor()
    c.execute("SELECT id, code, name, category, unit FROM products")
    products = c.fetchall()
    conn.close()
    return products

def get_unique_categories():
    conn = sqlite3.connect('ceasa.db')
    c = conn.cursor()
    c.execute("SELECT DISTINCT category FROM products WHERE category IS NOT NULL")
    categories = [row[0] for row in c.fetchall()]
    conn.close()
    return ["Todas"] + sorted(categories)  # Adiciona "Todas" como opção padrão

def get_unique_users():
    conn = sqlite3.connect('ceasa.db')
    c = conn.cursor()
    c.execute("SELECT id, username FROM users")
    users = c.fetchall()
    conn.close()
    return ["Todos"] + [f"{user[1]} (ID: {user[0]})" for user in users]  # Ad
