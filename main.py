import os
import re
import sqlite3
from flask import Flask
from threading import Thread
import telebot
from telebot import types

# 1. CONFIGURAÇÕES INICIAIS
TOKEN = os.environ.get("TELEGRAM_TOKEN")
bot = telebot.TeleBot(TOKEN)
DB_NAME = "cinema.db"

# 2. SERVIDOR FLASK (PARA O RENDER NÃO DORMIR)
app = Flask('')
@app.route('/')
def home(): 
    return "Bot online!"

def run_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# 3. BANCO DE DADOS
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS conteudos (id INTEGER PRIMARY KEY AUTOINCREMENT, titulo TEXT UNIQUE, genero TEXT, capa_url TEXT, sinopse TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS episodios (id INTEGER PRIMARY KEY AUTOINCREMENT, serie_id INTEGER, temporada INTEGER, episodio INTEGER, file_id TEXT, UNIQUE(serie_id, temporada, episodio))')
    conn.commit()
    conn.close()

init_db()

# 4. BUSCA INLINE (MENU DO TELEGRAM)
@bot.inline_handler(lambda query: True)
def query_text(inline_query):
    query = inline_query.query.strip()
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, titulo, genero, capa_url FROM conteudos WHERE titulo LIKE ? LIMIT 10", (f"%{query}%",))
    rows = cursor.fetchall()
    conn.close()
    
    results = []
    for row in rows:
        c_id, titulo, genero, capa_url = row
        results.append(types.InlineQueryResultArticle(
            id=str(c_id), title=titulo, description=f"🎭 {genero}",
            thumb_url=capa_url, input_message_content=types.InputTextMessageContent(f"/ver_{c_id}")
        ))
    bot.answer_inline_query(inline_query.id, results, cache_time=0)

# 5. COMANDOS BÁSICOS
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "🎬 Sistema pronto! Digite @ o nome do bot no chat para buscar, ou envie vídeos com a legenda correspondente.")

@bot.message_handler(commands=['nova_serie'])
def nova_serie(message):
    try:
        dados = message.text.replace("/nova_serie", "").strip().split('|')
        titulo, genero, capa, sinopse = [x.strip() for x in dados]
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO conteudos (titulo, genero, capa_url, sinopse) VALUES (?, ?, ?, ?)", (titulo, genero, capa, sinopse))
        conn.commit()
        conn.close()
        bot.reply_to(message, f"✅ Série **{titulo}** cadastrada!")
    except: 
        bot.reply_to(message, "⚠️ Use: /nova_serie Nome | Gênero | Link Capa | Sinopse")

# 6. EXIBIÇÃO DA SÉRIE COM BOTÕES CLICÁVEIS
@bot.message_handler(regexp=r"^/ver_\d+$")
def mostrar_episodios(message):
    serie_id = message.text.split("_")[1]
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT titulo, genero, capa_url, sinopse FROM conteudos WHERE id = ?", (serie_id,))
    serie = cursor.fetchone()
    
    cursor.execute("SELECT temporada, episodio, id FROM episodios
