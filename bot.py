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
        
        # Cria um objeto Update do telegram com base nos dados do Flask
        update = Update.de_json(json_update, application.bot)
        
        # Pega o loop atual de eventos para rodar a tarefa assíncrona de processamento
        loop = asyncio.get_event_loop()
        loop.create_task(application.process_update(update))
        
    return "OK", 200

# ============================================================
# Inicialização do bot
# ============================================================

async def main():
    global application

    # ⚠️ RECOMENDAÇÃO: Use variáveis de ambiente para o token!
    TOKEN = os.getenv("TELEGRAM_TOKEN", "8833233090:AAFI8ptnJj6MB6aBD7lUfKH8AXsIpEizSHA")
    
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Inicializa os componentes internos do bot sem abrir o polling tradicional
    await application.initialize()
    await application.start()

    print("Bot iniciado internamente. Aguardando requisições do Flask...")

if __name__ == "__main__":
    # Correção crucial para Python 3.14+: Criar e configurar o loop de eventos explicitamente
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
    # Executa a inicialização do Telegram
    loop.run_until_complete(main())
    
    # Inicia o servidor Flask na porta do Render
    port = int(os.environ.get("PORT", 10000))
    app_flask.run(host="0.0.0.0", port=port)