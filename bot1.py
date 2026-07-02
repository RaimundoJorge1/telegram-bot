import os
import threading
from flask import Flask
import telebot
import pg8000

# ============================
# LOGS DO TELEBOT (MOSTRA ERROS)
# ============================
telebot.logger.setLevel(10)

# ============================
# TOKEN DO TELEGRAM
# ============================
TOKEN = os.getenv("TELEGRAM_TOKEN")
bot = telebot.TeleBot(TOKEN)

# ============================
# CONEXÃO COM O BANCO
# ============================
def conectar():
    return pg8000.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASS"),
        database=os.getenv("DB_NAME"),
        port=int(os.getenv("DB_PORT", "5432"))
    )

# ============================
# FUNÇÃO PARA PREPARAR TEXTO
# ============================
def preparar(valor):
    valor = valor.lower()
    valor = valor.replace(".", "").replace(",", "").replace(" ", "").replace("-", "")
    return f"%{valor}%"

# ============================
# COMANDO /start
# ============================
@bot.message_handler(commands=['start'])
def start(msg):
    bot.reply_to(msg,
        "Envie os filtros no formato:\n\n"
        "bitola;isolacao;tensao;cor;fabricante\n\n"
        "Exemplo:\n1.5;PVC;750;Preta;PHELPS DODGE"
    )

# ============================
# RECEBER MENSAGENS
# ============================
@bot.message_handler(func=lambda m: True)
def receber(msg):
    try:
        texto = msg.text.split(";")

        if len(texto) != 5:
            bot.reply_to(msg, "Formato inválido. Use:\nbitola;isolacao;tensao;cor;fabricante")
            return

        bitola, isolacao, tensao, cor, fabricante = texto

        conn = conectar()
        cur = conn.cursor()

        sql = """
            SELECT *
            FROM produtos
            WHERE 
                REPLACE(REPLACE(REPLACE(LOWER(Bitola), '.', ''), ',', ''), ' ', '') LIKE %s
            AND REPLACE(REPLACE(REPLACE(LOWER(Isolacao), '.', ''), ',', ''), ' ', '') LIKE %s
            AND REPLACE(REPLACE(REPLACE(LOWER(Tensao), '.', ''), ',', ''), ' ', '') LIKE %s
            AND REPLACE(REPLACE(REPLACE(LOWER(Cor_Isolacao), '.', ''), ',', ''), ' ', '') LIKE %s
            AND REPLACE(REPLACE(REPLACE(REPLACE(LOWER(Fabricante_Fantasia), '.', ''), ',', ''), ' ', ''), '-', '') LIKE %s
            LIMIT 20;
        """

        cur.execute(sql, (
            preparar(bitola),
            preparar(isolacao),
            preparar(tensao),
            preparar(cor),
            preparar(fabricante)
        ))

        linhas = cur.fetchall()
        colunas = [desc[0] for desc in cur.description]

        if not linhas:
            bot.reply_to(msg, "Nenhum resultado encontrado.")
            return

        resposta = ""
        for linha in linhas:
            item = dict(zip(colunas, linha))
            resposta += f"{item}\n\n"

        bot.reply_to(msg, resposta)

    except Exception as e:
        bot.reply_to(msg, f"Erro: {e}")
        print("ERRO NO BOT:", e)

# ============================
# FLASK PARA MANTER O RENDER ATIVO
# ============================
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot rodando no Render!"

# ============================
# THREAD PARA RODAR O BOT
# ============================
def iniciar_bot():
    bot.infinity_polling()

# ============================
# INICIAR FLASK + BOT
# ============================
if __name__ == "__main__":
    threading.Thread(target=iniciar_bot).start()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
