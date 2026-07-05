import os
import re
import sqlite3
from flask import Flask
from threading import Thread
import telebot
from telebot import types

# 1. SERVIDOR PARA MANTER O RENDER ONLINE
app = Flask('')
@app.route('/')
def home(): return "Bot online!"

# 2. CONFIGURAÇÕES
TOKEN = os.environ.get("TELEGRAM_TOKEN")
bot = telebot.TeleBot(TOKEN)
DB_NAME = "cinema.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS conteudos (id INTEGER PRIMARY KEY AUTOINCREMENT, tipo TEXT, titulo TEXT UNIQUE, genero TEXT, sinopse TEXT, capa_url TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS episodios (id INTEGER PRIMARY KEY AUTOINCREMENT, serie_id INTEGER, temporada INTEGER, episodio INTEGER, file_id TEXT, UNIQUE(serie_id, temporada, episodio))')
    conn.commit()
    conn.close()

init_db()

# 3. BUSCA INLINE
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

# 4. COMANDOS
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
    except: bot.reply_to(message, "⚠️ Use: /nova_serie Nome | Gênero | Link Capa | Sinopse")

@bot.message_handler(content_types=['video'])
def handle_video(message):
    legenda = message.caption or ""
    match = re.search(r"(.+?)\s+[sS](\d+)[eE](\d+)", legenda)
    if match:
        nome, temp, ep = match.groups()
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM conteudos WHERE titulo LIKE ?", (f"%{nome.strip()}%",))
        row = cursor.fetchone()
        if row:
            cursor.execute("INSERT OR REPLACE INTO episodios (serie_id, temporada, episodio, file_id) VALUES (?, ?, ?, ?)", (row[0], int(temp), int(ep), message.video.file_id))
            conn.commit()
            bot.reply_to(message, f"✅ S{temp}E{ep} salvo em {nome}!")
        conn.close()

# 5. EXECUÇÃO LIMPA (EVITA O ERRO 409)
if __name__ == "__main__":
    Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080))), daemon=True).start()
    bot.remove_webhook()
    print("Iniciando Bot...")
    bot.infinity_polling(skip_pending=True)
