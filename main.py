import os
import re
import sqlite3
from flask import Flask
from threading import Thread
import telebot
from telebot import types

# 1. SERVIDOR WEB (PRO RENDER NÃO CAIR)
app = Flask('')
@app.route('/')
def home(): 
    return "Bot online!"

def run_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# 2. CONFIGURAÇÃO DO BOT
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

# 3. COMANDOS DO SEU PRIMEIRO CÓDIGO
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "🎬 Bot online e pronto!")

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

# 4. INICIALIZAÇÃO SEGURA
if __name__ == "__main__":
    bot.remove_webhook()
    
    # Inicia o servidor web em segundo plano
    Thread(target=run_server, daemon=True).start()
    
    print("Iniciando Bot...")
    bot.infinity_polling(skip_pending=True)
    
