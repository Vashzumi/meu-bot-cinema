import os
import re
import sqlite3
from threading import Thread
from flask import Flask
import telebot
from telebot import types

# ----------------------------------------------------
# 1. SERVIDOR FANTASMA PARA MANTER O RENDER ONLINE
# ----------------------------------------------------
app = Flask('')

@app.route('/')
def home():
    return "Bot está vivo e operando!"

def run_server():
    # O Render sempre passa uma porta na variável de ambiente PORT
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# ----------------------------------------------------
# 2. CONFIGURAÇÃO DO BOT E BANCO DE DATOS
# ----------------------------------------------------
TOKEN = os.environ.get("TELEGRAM_TOKEN")
bot = telebot.TeleBot(TOKEN)

DB_NAME = "cinema.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # Tabela para Filmes e Capas Principais de Séries
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS conteudos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo TEXT,          -- 'filme' ou 'serie'
            titulo TEXT UNIQUE,
            genero TEXT,
            sinopse TEXT,
            capa_url TEXT,
            file_id TEXT        -- Apenas para filmes
        )
    ''')
    # Tabela exclusiva para os episódios das séries
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS episodios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            serie_id INTEGER,
            temporada INTEGER,
            episodio INTEGER,
            titulo_ep TEXT,
            file_id TEXT,
            FOREIGN KEY(serie_id) REFERENCES conteudos(id),
            UNIQUE(serie_id, temporada, episodio)
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# ----------------------------------------------------
# 3. CADASTRO DE CONTEÚDOS (FLUXO DO ADMINISTRADOR)
# ----------------------------------------------------

# Regex para identificar episódios (Ex: Flash S01E15)
EPISODIO_REGEX = re.compile(r"(.+?)\s+[sS](\d+)[eE](\d+)(?:\s+-\s+(.+))?", re.IGNORECASE)

@bot.message_handler(content_types=['video'])
def handle_video_upload(message):
    # Se não tiver legenda, não temos como processar
    if not message.caption:
        bot.reply_to(message, "❌ Por favor, envie o vídeo adicionando uma legenda formatada.")
        return

    legenda = message.caption.strip()
    file_id = message.video.file_id

    # VERIFICAÇÃO: É um episódio de série? (Padrão: Nome S01E15)
    match = EPISODIO_REGEX.search(legenda)
    if match:
        nome_serie = match.group(1).strip()
        temporada = int(match.group(2))
        episodio = int(match.group(3))
        titulo_ep = match.group(4).strip() if match.group(4) else f"Episódio {episodio}"

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Verifica se a série já foi cadastrada previamente
        cursor.execute("SELECT id FROM conteudos WHERE titulo = ? AND tipo = 'serie'", (nome_serie,))
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            bot.reply_to(message, f"❌ A série **{nome_serie}** ainda não foi cadastrada.\n\nPara cadastrar uma série, envie o comando:\n`/nova_serie Nome da Série | Gênero | Link_da_Capa | Sinopse`")
            return
        
        serie_id = row[0]
        
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO episodios (serie_id, temporada, episodio, titulo_ep, file_id)
                VALUES (?, ?, ?, ?, ?)
            ''', (serie_id, temporada, episodio, titulo_ep, file_id))
            conn.commit()
            bot.reply_to(message, f"✅ **{nome_serie}** - S{temporada:02d}E{episodio:02d} salvo com sucesso!")
        except Exception as e:
            bot.reply_to(message, f"❌ Erro ao salvar episódio: {e}")
        finally:
            conn.close()

    # Se não tiver o padrão S01E15, trata como FILME profissional
    else:
        linhas = [l.strip() for l in legenda.split('\n') if l.strip()]
        titulo = "Filme Sem Título"
        genero = "Não informado"
        sinopse = "Não informada"
        capa_url = "https://images.unsplash.com/photo-1489599849927-2ee91cede3ba" # Padrão se falhar

        for linha in linhas:
            if "Gênero:" in linha:
                genero = linha.replace("Gênero:", "").replace("🎭", "").strip()
            elif "Sinopse:" in linha:
                sinopse = linha.replace("Sinopse:", "").replace("🍿", "").strip()
            elif "Capa:" in linha:
                capa_url = linha.replace("Capa:", "").replace("🖼️", "").strip()
            elif not linha.startswith("---") and not "Assista" in linha:
                titulo = linha.replace("🎬", "").strip()

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO conteudos (tipo, titulo, genero, sinopse, capa_url, file_id)
                VALUES ('filme', ?, ?, ?, ?, ?)
            ''', (titulo, genero, sinopse, capa_url, file_id))
            conn.commit()
            bot.reply_to(message, f"✅ Filme **{titulo}** cadastrado com sucesso no catálogo!")
        except Exception as e:
            bot.reply_to(message, f"❌ Erro ao salvar filme: {e}")
        finally:
            conn.close()

# Comando para criar a "pasta" principal da série antes dos episódios
@bot.message_handler(commands=['nova_serie'])
def criar_nova_serie(message):
    try:
        dados = message.text.replace("/nova_serie", "").strip()
        partes = [p.strip() for p in dados.split('|')]
        
        if len(partes) < 4:
            bot.reply_to(message, "⚠️ Use o formato correto:\n`/nova_serie Nome | Gênero | Link da Capa (URL) | Sinopse`")
            return
        
        titulo, genero, capa_url, sinopse = partes[0], partes[1], partes[2], partes[3]
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO conteudos (tipo, titulo, genero, sinopse, capa_url, file_id)
            VALUES ('serie', ?, ?, ?, ?, NULL)
        ''', (titulo, genero, capa_url, sinopse))
        conn.commit()
        conn.close()
        
        bot.reply_to(message, f"🎬 Série **{titulo}** cadastrada! Agora você já pode enviar os episódios usando a legenda padrão (`{titulo} S01E01`).")
    except Exception as e:
        bot.reply_to(message, f"❌ Erro ao criar série: {e}")

# ----------------------------------------------------
# 4. BUSCA INLINE (MENU FLUTUANTE COM CAPINHAS)
# ----------------------------------------------------
@bot.inline_handler(lambda query: True)
def query_text(inline_query):
    try:
        query = inline_query.query.strip()
        results = []
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        if query == "":
            cursor.execute("SELECT id, tipo, titulo, genero, capa_url FROM conteudos LIMIT 10")
        else:
            cursor.execute("SELECT id, tipo, titulo, genero, capa_url FROM conteudos WHERE titulo LIKE ? LIMIT 10", (f"%{query}%",))
            
        rows = cursor.fetchall()
        conn.close()
        
        for index, row in enumerate(rows):
            c_id, tipo, titulo, genero, capa_url = row
            
            # Monta o card do menu flutuante
            desc = f"🎭 Gênero: {genero} | 📦 Tipo: {tipo.capitalize()}"
            
            # Quando a pessoa clica no menu inline, envia o comando secreto para abrir o conteúdo
            input_content = types.InputTextMessageContent(f"/ver_{tipo}_{c_id}")
            
            item = types.InlineQueryResultArticle(
                id=str(index),
                title=titulo,
                description=desc,
                thumb_url=capa_url,
                input_message_content=input_content
            )
            results.append(item)
            
        bot.answer_inline_query(inline_query.id, results, cache_time=1)
    except Exception as e:
        print(f"Erro no inline: {e}")

# ----------------------------------------------------
# 5. EXIBIÇÃO DE CONTEÚDOS E SELETORES DINÂMICOS
# ----------------------------------------------------

# Abre painel principal de um Filme
@bot.message_handler(regexp=r"^/ver_filme_\d+")
def ver_filme_inline(message):
    filme_id = message.text.split("_")[-1]
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT titulo, genero, sinopse, capa_url, file_id FROM conteudos WHERE id = ?", (filme_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        titulo, genero, sinopse, capa_url, file_id = row
        texto = f"🎬 **{titulo}**\n\n🎭 **Gênero:** {genero}\n🍿 **Sinopse:** {sinopse}"
        
        # Apaga a mensagem de texto do comando e envia o filme direto
        bot.delete_message(message.chat.id, message.message_id)
        bot.send_video(message.chat.id, file_id, caption=texto, parse_mode="Markdown")

# Abre painel principal de uma Série (Menu de Temporadas)
@bot.message_handler(regexp=r"^/ver_serie_\d+")
def ver_serie_inline(message):
    serie_id = message.text.split("_")[-1]
    abrir_menu_temporadas(message.chat.id, message.message_id, serie_id, editar=False)

def abrir_menu_temporadas(chat_id, message_id, serie_id, editar=True):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT titulo, genero, sinopse, capa_url FROM conteudos WHERE id = ?", (serie_id,))
    row = cursor.fetchone()
    
    # Busca quais temporadas possuem episódios salvos
    cursor.execute("SELECT DISTINCT temporada FROM episodios WHERE serie_id = ? ORDER BY temporada", (serie_id,))
    temps = cursor.fetchall()
    conn.close()
    
    if row:
        titulo, genero, sinopse, capa_url = row
        texto = f"📺 **{titulo}**\n\n🎭 **Gênero:** {genero}\n🍿 **Sinopse:** {sinopse}\n\n--- \n🎞️ Selecione a temporada desejada abaixo:"
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        botoes = [types.InlineKeyboardButton(f"▶️ Temporada {t[0]}", callback_data=f"temp_{serie_id}_{t[0]}") for t in temps]
        markup.add(*botoes)
        
        if editar:
            bot.edit_message_text(texto, chat_id, message_id, reply_markup=markup, parse_mode="Markdown")
        else:
            bot.delete_message(chat_id, message_id)
            # Como séries não têm um vídeo principal, enviamos a capa como foto com o menu
            bot.send_photo(chat_id, capa_url, caption=texto, reply_markup=markup, parse_mode="Markdown")

# ----------------------------------------------------
# 6. CALLBACKS (CLIQUES NOS BOTÕES INLINE)
# ----------------------------------------------------
@bot.callback_query_handler(func=lambda call: True)
def handle_callback_buttons(call):
    dados = call.data.split("_")
    comando = dados[0]
    
    # Clicou em uma Temporada -> Mostra os Episódios
    if comando == "temp":
        serie_id, num_temp = dados[1], int(dados[2])
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT id, episodio, titulo_ep FROM episodios WHERE serie_id = ? AND temporada = ? ORDER BY episodio", (serie_id, num_temp))
        eps = cursor.fetchall()
        conn.close()
        
        markup = types.InlineKeyboardMarkup(row_width=3)
        botoes_ep = [types.InlineKeyboardButton(f"Ep {e[1]}", callback_data=f"play_{e[0]}") for e in eps]
        markup.add(*botoes_ep)
        markup.add(types.InlineKeyboardButton("⬅️ Voltar para Temporadas", callback_data=f"voltar_s_{serie_id}"))
        
        bot.edit_message_caption(f"🎞️ **Temporada {num_temp}**\nEscolha o episódio para assistir:", call.message.chat.id, call.message.message_id, reply_markup=markup)
        
    # Voltar para a lista de temporadas
    elif comando == "voltar":
        serie_id = dados[2]
        # Recria o painel de temporadas alterando a legenda da foto
        abrir_menu_temporadas(call.message.chat.id, call.message.message_id, serie_id, editar=False)
        bot.delete_message(call.message.chat.id, call.message.message_id)

    # Clicou em um Episódio -> Envia o Vídeo com botões Passar/Voltar
    elif comando == "play":
        ep_id = dados[1]
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        # Puxa os dados do ep atual e as infos da série
        cursor.execute('''
            SELECT e.file_id, e.temporada, e.episodio, e.titulo_ep, c.titulo, c.id 
            FROM episodios e JOIN conteudos c ON e.serie_id = c.id WHERE e.id = ?
        ''', (ep_id,))
        atual = cursor.fetchone()
        
        if atual:
            file_id, temp, ep, titulo_ep, nome_serie, s_id = atual
            
            # Busca se existe um episódio anterior e um próximo
            cursor.execute("SELECT id FROM episodios WHERE serie_id = ? AND temporada = ? AND episodio = ?", (s_id, temp, ep - 1))
            ant_row = cursor.fetchone()
            cursor.execute("SELECT id FROM episodios WHERE serie_id = ? AND temporada = ? AND episodio = ?", (s_id, temp, ep + 1))
            prox_row = cursor.fetchone()
            conn.close()
            
            legenda_video = f"📺 **{nome_serie}**\n🎬 **Temporada:** {temp} | **Episódio:** {ep}\n📌 **Nome:** {titulo_ep}"
            
            markup = types.InlineKeyboardMarkup(row_width=2)
            botoes_navegacao = []
            
            if ant_row:
                botoes_navegacao.append(types.InlineKeyboardButton("◀️ Ep. Anterior", callback_data=f"play_{ant_row[0]}"))
            if prox_row:
                botoes_navegacao.append(types.InlineKeyboardButton("Próximo Ep. ➡️", callback_data=f"play_{prox_row[0]}"))
                
            markup.add(*botoes_navegacao)
            
            # Se clicou a partir de outro episódio, remove o anterior para não acumular vídeos na tela
            try:
                bot.delete_message(call.message.chat.id, call.message.message_id)
            except:
                pass
                
            bot.send_video(call.message.chat.id, file_id, caption=legenda_video, reply_markup=markup, parse_mode="Markdown")

# ----------------------------------------------------
# 7. EXECUÇÃO PARALELA (BOT + SERVER)
# ----------------------------------------------------
if __name__ == "__main__":
    # Inicia o servidor Flask em uma linha separada (Thread)
    server_thread = Thread(target=run_server)
    server_thread.start()
    
    print("Servidor Fantasma ativo. Iniciando Polling do Telegram...")
    # Executa o bot continuamente
    bot.infinity_polling()
