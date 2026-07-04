import os
import psycopg2
from psycopg2.extras import RealDictCursor
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters
import unicodedata
from flask import Flask, request
import asyncio
from threading import Thread

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
# Consulta ao banco (Ajustado para não repetir termos buscados)
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

        # Lista de campos usados na busca que serão removidos do texto final
        campos_ignorar = {"bitola", "isolacao", "tensao", "cor_isolacao", "fabricante_fantasia"}

        linhas = []
        linhas.append("📌 *Resultado da Consulta*")
        linhas.append("──────────────────────────")

        for campo, valor in resultado.items():
            # Se a coluna atual for um dos critérios da busca, o robô pula ela
            if campo.lower() in campos_ignorar:
                continue

            # Se o valor for nulo ou vazio, define como "Não consta"
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
    if not update.message or not update.message.text:
        return

    texto = update.message.text
    print(f"[LOG] Mensagem recebida do Telegram: {texto}")

    resposta = consultar_linha(texto)
    print(f"[LOG] Resposta gerada: {resposta}")

    try:
        await update.message.reply_text(resposta, parse_mode="Markdown")
    except Exception as e:
        print(f"[AVISO] Falha ao enviar Markdown. Erro: {e}")
        await update.message.reply_text(resposta)

# ============================================================
# FLASK + WEBHOOK (ESTABILIZADO COM THREADS)
# ============================================================

app_flask = Flask(__name__)
application = None
main_loop = None   

@app_flask.route("/", methods=["GET", "HEAD"])
def index():
    return "Bot está online e operacional!", 200

@app_flask.route("/ping", methods=["GET"])
def ping():
    return "Servidor ativo", 200

@app_flask.route("/webhook", methods=["POST"])
def webhook():
    global application, main_loop

    json_update = request.get_json()
    print(f"[DEBUG Webhook] Requisição recebida do Telegram.")

    if not application or not main_loop:
        print("[ERRO CRÍTICO] Telegram Application ou Loop ainda não foram iniciados!")
        return "Bot não iniciado", 200

    try:
        update = Update.de_json(json_update, application.bot)
        main_loop.call_soon_threadsafe(
            asyncio.create_task, 
            application.process_update(update)
        )
    except Exception as e:
        print("[ERRO Webhook] Falha ao processar update:", e)

    return "OK", 200

# ============================================================
# Inicialização do bot
# ============================================================

async def start_bot():
    global application, main_loop
    
    main_loop = asyncio.get_running_loop()
    
    TOKEN = os.getenv("TELEGRAM_TOKEN") or "8833233090:AAF-Sx76b0K84DmAFN7Xu6m4dvYzpJq9y24"
    TOKEN = TOKEN.strip()

    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    await application.initialize()
    await application.start()
    print("[SISTEMA] Telegram Bot iniciado com sucesso!")

# ============================================================
# Fluxo de Inicialização Principal com Threads Paralelas
# ============================================================

def rodar_bot_em_thread():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(start_bot())
    loop.run_forever()

if __name__ == "__main__":
    thread_telegram = Thread(target=rodar_bot_em_thread, daemon=True)
    thread_telegram.start()

    port = int(os.environ.get("PORT", 10000))
    app_flask.run(host="0.0.0.0", port=port)