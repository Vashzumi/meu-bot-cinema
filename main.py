import os
import telebot

# Pega o token de forma segura pelas variáveis de ambiente do Render
BOT_TOKEN = os.environ.get('BOT_TOKEN')

# Verifica se o token foi configurado
if not BOT_TOKEN:
    print("ERRO: O token do bot não foi configurado nas variáveis de ambiente!")
    exit()

bot = telebot.TeleBot(BOT_TOKEN)

# Responde ao comando /start ou /help
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    texto = (
        "🎬 Olá! Eu sou o seu bot de Filmes e Séries!\n\n"
        "Ainda estou em construção, mas em breve poderei te ajudar "
        "a encontrar as melhores opções para assistir."
    )
    bot.reply_to(message, texto)

# Responde a qualquer outra mensagem de texto
@bot.message_handler(func=lambda message: True)
def echo_all(message):
    bot.reply_to(message, "Anotado! Em breve vou conseguir buscar esse filme/série para você. 🍿")

if __name__ == "__main__":
    print("🤖 Bot iniciado com sucesso e rodando...")
    # O infinity_polling mantém o bot rodando o tempo todo sem cair
    bot.infinity_polling()
