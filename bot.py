import os
import psycopg2
from psycopg2.extras import RealDictCursor
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters

# ============================
# Conexão com o banco (Render)
# ============================

def get_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASS"),
        port=os.getenv("DB_PORT"),
        sslmode="require"
    )

# ============================
# Processamento da mensagem
# ============================

def process_message(text):
    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Exemplo de consulta
        cur.execute("SELECT * FROM produtos LIMIT 1;")
        resultado = cur.fetchone()

        cur.close()
        conn.close()

        if resultado:
            return f"Produto encontrado: {resultado}"
        else:
            return "Nenhum produto encontrado."

    except Exception as e:
        return f"Erro ao acessar o banco: {e}"

# ============================
# Handler do Telegram (async)
# ============================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text
    resposta = process_message(texto)
    await update.message.reply_text(resposta)

# ============================
# Inicialização do bot
# ============================

def main():
    TOKEN = os.getenv("TELEGRAM_TOKEN")

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot iniciado...")
    app.run_polling()

if __name__ == "__main__":
    main()
