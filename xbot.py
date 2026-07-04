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
# Handler do Telegram (MODIFICADO COM RASTREAMENTO E PROTEÇÃO)
# ============================================================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    texto = update.message.text
    print(f"[LOG] Mensagem recebida do Telegram: {texto}")

    resposta = consultar_linha(texto)
    print(f"[LOG] Resposta gerada: {resposta}")

    try:
        # Tenta responder com a formatação Markdown ativa
        await update.message.reply_text(resposta, parse_mode="Markdown")
    except Exception as e:
        print(f"[AVISO] Falha ao enviar Markdown (caractere inválido). Erro: {e}")
        # Se falhar pelo Markdown, envia como texto puro para garantir a entrega
        await update.message.reply_text(resposta)

# ============================================================
# FLASK + WEBHOOK (CORRIGIDO PARA THREADS)
# ============================================================

app_flask = Flask(__name__)
application = None
main_loop = None   # loop principal do bot

@app_flask.route("/", methods=["GET", "HEAD"])
def index():
    return "Bot está online e operacional!", 200

@app_flask.route("/ping", methods=["GET"])
def ping():
    return "Servidor ativo", 200

@app_flask.route("/webhook", methods=["POST"])
def webhook():
    global application, main_loop

    if application and main_loop:
        json_update = request.get_json()

        try:
            update = Update.de_json(json_update, application.bot)
        except Exception as e:
            print("Erro ao decodificar update:", e)
            return "OK", 200

        # Envia o update para o loop principal do bot com segurança
        asyncio.run_coroutine_threadsafe(
            application.process_update(update),
            main_loop
        )

    return "OK", 200

# ============================================================
# Inicialização do bot
# ============================================================

async def main():
    global application, main_loop

    main_loop = asyncio.get_running_loop()

    TOKEN = os.getenv("TELEGRAM_TOKEN") or "8833233090:AAF-Sx76b0K84DmAFN7Xu6m4dvYzpJq9y24"
    TOKEN = TOKEN.strip()

    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    await application.initialize()
    await application.start()

    print("Bot iniciado internamente. Aguardando requisições do Flask...")

if __name__ == "__main__":
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    loop.run_until_complete(main())

    port = int(os.environ.get("PORT", 10000))
    app_flask.run(host="0.0.0.0", port=port)