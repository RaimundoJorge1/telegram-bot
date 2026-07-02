import os
import psycopg2
from psycopg2.extras import RealDictCursor
from telegram.ext import Updater, MessageHandler, Filters

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
        sslmode="require"   # <<< ESSENCIAL PARA O RENDER
    )

# ============================
# Função que processa mensagens
# ============================

def process_message(text):
    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Exemplo: consulta simples
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
# Handler do Telegram
# ============================

def handle_message(update, context):
    texto = update.message.text
    resposta = process_message(texto)
    update.message.reply_text(resposta)

# ============================
# Inicialização do bot
# ============================

def main():
    TOKEN = os.getenv("TELEGRAM_TOKEN")

    if not TOKEN:
        print("ERRO: TELEGRAM_TOKEN não encontrado nas variáveis de ambiente.")
        return

    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

    print("Bot iniciado...")
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
