import os
import re
import sqlite3
from threading import Thread
from flask import Flask
import telebot
from telebot import types

# 1. SERVIDOR FANTASMA PARA MANTER O RENDER ONLINE
app = Flask('')
@app.route('/')
def home(): return "Bot está vivo!"

def run_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# 2. CONFIGURAÇÕES
TOKEN = os.environ.get("TELEGRAM_TOKEN")
bot = telebot.TeleBot(TOKEN)
DB_NAME = "cinema.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS conteudos (id INTEGER PRIMARY KEY AUTOINCREMENT, tipo TEXT, titulo TEXT UNIQUE, genero TEXT, sinopse TEXT, capa_url TEXT, file_id TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS episodios (id INTEGER PRIMARY KEY AUTOINCREMENT, serie_id INTEGER, temporada INTEGER, episodio INTEGER, titulo_ep TEXT, file_id TEXT, UNIQUE(serie_id, temporada, episodio))')
    conn.commit()
    conn.close()

init_db()

# 3. BUSCA INLINE
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

# 4. COMANDOS
@bot.message_handler(commands=['nova_serie'])
def criar_nova_serie(message):
    try:
        dados = message.text.replace("/nova_serie", "").strip()
        partes = [p.strip() for p in dados.split('|')]
        if len(partes) < 4:
            bot.reply_to(message, "⚠️ Use: /nova_serie Nome | Gênero | Link Capa | Sinopse")
            return
        titulo, genero, capa_url, sinopse = partes
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO conteudos (tipo, titulo, genero, sinopse, capa_url) VALUES ('serie', ?, ?, ?, ?)", (titulo, genero, sinopse, capa_url))
        conn.commit()
        conn.close()
        bot.reply_to(message, f"✅ Série **{titulo}** cadastrada!")
    except Exception as e: bot.reply_to(message, f"Erro: {e}")

# 5. SALVAMENTO DE VÍDEOS (INTEGRADO)
@bot.message_handler(content_types=['video'])
def handle_video(message):
    if not message.caption:
        bot.reply_to(message, "❌ Envie o vídeo com a legenda: Titulo S01E01")
        return

    legenda = message.caption.strip()
    file_id = message.video.file_id
    match = re.search(r"(.+?)\s+[sS](\d+)[eE](\d+)", legenda)
    
    if match:
        nome_serie = match.group(1).strip()
        temp = int(match.group(2))
        ep = int(match.group(3))
        
        try:
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM conteudos WHERE titulo LIKE ?", (f"%{nome_serie}%",))
            row = cursor.fetchone()
            
            if row:
                cursor.execute("INSERT OR REPLACE INTO episodios (serie_id, temporada, episodio, file_id) VALUES (?, ?, ?, ?)", (row[0], temp, ep, file_id))
                conn.commit()
                bot.reply_to(message, f"✅ **{nome_serie}** - S{temp:02d}E{ep:02d} salvo!")
            else:
                bot.reply_to(message, "❌ Série não encontrada. Use /nova_serie.")
            conn.close()
        except Exception as e: bot.reply_to(message, f"Erro: {e}")

# 6. EXECUÇÃO
if __name__ == "__main__":
    Thread(target=run_server).start()
    bot.infinity_polling(timeout=60, long_polling_timeout=60)
