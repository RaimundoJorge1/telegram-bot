import os
import psycopg2
from psycopg2.extras import RealDictCursor
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters
import unicodedata
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
                valor_formatado = "Nãoconsta"
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
# Inicialização do bot — VERSÃO FINAL COMPATÍVEL COM PTB 21.x
# ============================================================

async def main():
   # TOKEN = os.getenv("TELEGRAM_TOKEN")
    TOKEN = "8833233090:AAFI8ptnJj6MB6aBD7lUfKH8AXsIpEizSHA"
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot iniciado...")

    await app.initialize()
    await app.start()
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
