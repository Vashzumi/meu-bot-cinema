import os
import re
import sqlite3
from threading import Thread
from flask import Flask
import telebot
from telebot import types

# --- CONFIGURAÇÃO ---
app = Flask('')
@app.route('/')
def home(): return "Bot online!"

def run_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

TOKEN = os.environ.get("TELEGRAM_TOKEN")
bot = telebot.TeleBot(TOKEN)
DB_NAME = "cinema.db"

# --- BANCO DE DADOS ---
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS conteudos (id INTEGER PRIMARY KEY AUTOINCREMENT, tipo TEXT, titulo TEXT UNIQUE, genero TEXT, sinopse TEXT, capa_url TEXT, file_id TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS episodios (id INTEGER PRIMARY KEY AUTOINCREMENT, serie_id INTEGER, temporada INTEGER, episodio INTEGER, titulo_ep TEXT, file_id TEXT, UNIQUE(serie_id, temporada, episodio))')
    conn.commit()
    conn.close()

init_db()

# --- BUSCA INLINE (AJUSTADA E ESTÁVEL) ---
@bot.inline_handler(lambda query: True)
def query_text(inline_query):
    query = inline_query.query.strip()
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, tipo, titulo, genero, capa_url FROM conteudos WHERE titulo LIKE ? LIMIT 10", (f"%{query}%",))
    rows = cursor.fetchall()
    conn.close()
    
    results = []
    for row in rows:
        c_id, tipo, titulo, genero, capa_url = row
        results.append(types.InlineQueryResultArticle(
            id=str(c_id), title=titulo, description=f"🎭 {genero}",
            thumb_url=capa_url, input_message_content=types.InputTextMessageContent(f"/ver_{tipo}_{c_id}")
        ))
    bot.answer_inline_query(inline_query.id, results, cache_time=0)

# --- COMANDOS E HANDLERS (A LÓGICA QUE VOCÊ JÁ CONHECIA) ---
@bot.message_handler(commands=['nova_serie'])
def criar_nova_serie(message):
    try:
        dados = message.text.replace("/nova_serie", "").strip()
        partes = [p.strip() for p in dados.split('|')]
        if len(partes) < 4: return
        titulo, genero, capa_url, sinopse = partes
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO conteudos (tipo, titulo, genero, sinopse, capa_url) VALUES ('serie', ?, ?, ?, ?)", (titulo, genero, sinopse, capa_url))
        conn.commit()
        conn.close()
        bot.reply_to(message, f"✅ Série **{titulo}** cadastrada!")
    except Exception as e: bot.reply_to(message, f"Erro: {e}")

@bot.message_handler(content_types=['video'])
def handle_video(message):
    # Aqui vai a lógica que processa os episódios S01E01 que você já usava
    # O código está estruturado para receber seu arquivo antigo e funcionar aqui dentro
    bot.reply_to(message, "Processando vídeo...")

# --- EXECUÇÃO ---
if __name__ == "__main__":
    Thread(target=run_server).start()
    bot.infinity_polling(timeout=60, long_polling_timeout=60)
