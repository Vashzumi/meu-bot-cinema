import sqlite3
import telebot

# ================= CONFIGURAÇÕES =================
API_TOKEN = "8340453598:AAEZklpIxiRdkfuV_-LgQ4sBXuH1YBZ69gg"
DONO_ID = 6151964355  # ID do usuário
# =================================================

bot = telebot.TeleBot(API_TOKEN)

def iniciar_banco():
    conn = sqlite3.connect("cinema.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS filmes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            file_id TEXT NOT NULL,
            tipo TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

@bot.message_handler(commands=['start', 'ajuda'])
def enviar_boas_vindas(message):
    texto = (
        "🎬 **Bem-vindo ao 7th Heaven Filme Bot!**\n\n"
        "Digite o nome do filme ou série que você está procurando e eu farei a busca no catálogo."
    )
    if message.from_user.id == DONO_ID:
        texto += (
            "\n\n⚙️ **Modo Administrador Ativo:**\n"
            "Para cadastrar um novo filme, basta **encaminhar** o vídeo/arquivo para cá "
            "e colocar o nome do filme na legenda (caption) do envio."
        )
    bot.reply_to(message, texto, parse_mode='Markdown')

@bot.message_handler(func=lambda msg: msg.from_user.id == DONO_ID, content_types=['video', 'document'])
def cadastrar_filme(message):
    nome_filme = message.caption
    if not nome_filme:
        bot.reply_to(message, "❌ Erro: Envie ou encaminhe o arquivo incluindo o nome do filme na legenda (caption)!")
        return

    if message.content_type == 'video':
        file_id = message.video.file_id
        tipo = 'video'
    else:
        file_id = message.document.file_id
        tipo = 'documento'

    conn = sqlite3.connect("cinema.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO filmes (nome, file_id, tipo) VALUES (?, ?, ?)", (nome_filme, file_id, tipo))
    conn.commit()
    conn.close()

    bot.reply_to(message, f"✅ **Sucesso!**\nFilme cadastrado: `{nome_filme}`", parse_mode='Markdown')

@bot.message_handler(func=lambda msg: True, content_types=['text'])
def buscar_filme(message):
    termo_busca = message.text.strip()

    if len(termo_busca) < 2:
        bot.reply_to(message, "⚠️ Digite pelo menos 2 letras para pesquisar.")
        return

    conn = sqlite3.connect("cinema.db")
    cursor = conn.cursor()
    cursor.execute("SELECT file_id, nome, tipo FROM filmes WHERE nome LIKE ?", ('%' + termo_busca + '%',))
    resultados = cursor.fetchall()
    conn.close()

    if resultados:
        bot.reply_to(message, f"🔍 Encontrei {len(resultados)} resultado(s). Enviando...")
        for filme in resultados:
            file_id, nome, tipo = filme
            try:
                if tipo == 'video':
                    bot.send_video(message.chat.id, file_id, caption=f"🎬 {nome}")
                else:
                    bot.send_document(message.chat.id, file_id, caption=f"🎬 {nome}")
            except Exception as e:
                bot.send_message(message.chat.id, f"❌ Erro ao enviar {nome}. O arquivo pode ter sido removido da fonte.")
    else:
        bot.reply_to(
            message, 
            "🍿 Não encontrei nenhum filme com esse nome no catálogo.\n"
            "Dica: Tente pesquisar apenas uma palavra-chave (ex: digite apenas 'Ultimato')."
        )

if __name__ == "__main__":
    iniciar_banco()
    print("🤖 Bot iniciado com sucesso...")
    bot.infinity_polling()
