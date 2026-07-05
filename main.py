import os
import re
import sqlite3
from flask import Flask
from threading import Thread
import telebot
from telebot import types

app = Flask('')
@app.route('/')
def home(): return "Bot online!"

TOKEN = os.environ.get("TELEGRAM_TOKEN")
bot = telebot.TeleBot(TOKEN)
DB_NAME = "cinema.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS conteudos (id INTEGER PRIMARY KEY AUTOINCREMENT, titulo TEXT UNIQUE, genero TEXT, capa_url TEXT, sinopse TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS episodios (id INTEGER PRIMARY KEY AUTOINCREMENT, serie_id INTEGER, temporada INTEGER, episodio INTEGER, file_id TEXT, UNIQUE(serie_id, temporada, episodio))')
    conn.commit()
    conn.close()

init_db()

# BUSCA INLINE
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

# COMANDO /ver_X (A PONTE QUE FALTAVA)
@bot.message_handler(regexp=r"^/ver_\d+$")
def mostrar_episodios(message):
    serie_id = message.text.split("_")[1]
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT temporada, episodio, file_id FROM episodios WHERE serie_id = ? ORDER BY temporada, episodio", (serie_id,))
    eps = cursor.fetchall()
    conn.close()
    
    if not eps:
        bot.reply_to(message, "❌ Nenhum episódio salvo para esta série.")
        return

    resposta = "🎬 **Episódios Disponíveis:**\n\n"
    for t, e, fid in eps:
        resposta += f"• Temporada {t} - Episódio {e}\n"
    bot.reply_to(message, resposta)

# SALVAR VÍDEO
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

if __name__ == "__main__":
    Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080))), daemon=True).start()
    bot.remove_webhook()
    bot.infinity_polling(skip_pending=True)
