import os
import psycopg2
from psycopg2.extras import RealDictCursor
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters
import unicodedata
from flask import Flask, request
import asyncio

# ============================================================
# Função para normalizar texto
# ============================================================

def normalizar(texto):
    if texto is None:
        return None
    texto = texto.strip().upper()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return texto

# ============================================================
# Conexão com o banco PostgreSQL (Render)
# ============================================================

def get_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASS"),
        port=os.getenv("DB_PORT"),
        sslmode="require"
    )

# ============================================================
# Consulta ao banco
# ============================================================

def consultar_linha(texto_usuario):
    try:
        partes = texto_usuario.split(";")

        if len(partes) < 5:
            return "Entrada inválida. Use: bitola;isolacao;tensao;cor;fabricante"

        bitola, isolacao, tensao, cor, fabricante = [normalizar(p) for p in partes]

        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            SELECT *
            FROM produtos
            WHERE UPPER(TRIM(bitola)) = %s
              AND UPPER(TRIM(isolacao)) = %s
              AND UPPER(TRIM(tensao)) = %s
              AND UPPER(TRIM(cor_isolacao)) = %s
              AND UPPER(TRIM(fabricante_fantasia)) = %s
            LIMIT 1;
        """, (bitola, isolacao, tensao, cor, fabricante))

        resultado = cur.fetchone()

        cur.close()
        conn.close()

        if not resultado:
            return "Nenhum produto encontrado."

        linhas = []
        linhas.append("📌 *Resultado da Consulta*")
        linhas.append("──────────────────────────")

        for campo, valor in resultado.items():
            if valor is None or (isinstance(valor, str) and valor.strip() == ""):
                valor_formatado = "Não consta"
            else:
                valor_formatado = str(valor)

            linhas.append(f"*{campo}*: {valor_formatado}")

        linhas.append("──────────────────────────")

        return "\n".join(linhas)

    except Exception as e:
        return f"Erro ao acessar o banco: {e}"

# ============================================================
# Handler do Telegram
# ============================================================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text
    resposta = consultar_linha(texto)
    await update.message.reply_text(resposta, parse_mode="Markdown")

# ============================================================
# WEBHOOK (Flask)
# ============================================================

app_flask = Flask(__name__)
application = None  # Instanciado globalmente

@app_flask.route("/", methods=["POST"])
def webhook():
    if application:
        json_update = request.get_json()
        
        # Converte o JSON recebido em um objeto Update do Telegram
        update = Update.de_json(json_update, application.bot)
        
        # Processa a mensagem de forma assíncrona no loop ativo
        loop = asyncio.get_event_loop()
        loop.create_task(application.process_update(update))
        
    return "OK", 200

# ============================================================
# Inicialização do bot
# ============================================================

async def main():
    global application

    # Buscando o Token do ambiente e aplicando o .strip() para remover espaços e '\n'
    TOKEN = os.getenv("TELEGRAM_TOKEN")
    TOKEN = "8833233090:AAF-Sx76b0K84DmAFN7Xu6m4dvYzpJq9y24"
    if not TOKEN:
        raise ValueError("A variável de ambiente TELEGRAM_TOKEN não foi configurada!")
    
    TOKEN = TOKEN.strip()
    
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Inicializa a estrutura do bot sem abrir o Polling interno
    await application.initialize()
    await application.start()

    print("Bot iniciado internamente. Aguardando requisições do Flask...")

if __name__ == "__main__":
    # Correção crucial para Python 3.14+: Garante a existência do Event Loop
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
    # Inicializa o bot do Telegram
    loop.run_until_complete(main())
    
    # Inicia o servidor Flask usando a porta dinâmica fornecida pelo Render
    port = int(os.environ.get("PORT", 10000))
    app_flask.run(host="0.0.0.0", port=port)