import os
import pandas as pd
from sqlalchemy import create_engine

# ==============================================================================
# CONFIGURAÇÕES DE CONEXÃO (Ajustado para o seu banco na nuvem)
# ==============================================================================
DB_USER = "telegramdb_8moi_user"
DB_PASSWORD = "zlQIJGukDahScimSblpMxW5IMODL3tOz"  # <-- Insira aqui a senha fornecida pela nuvem
DB_HOST = "dpg-d918t9sm0tmc73ee1ah0-a"     # <-- Cole o Host/Server da nuvem (Não use 127.0.0.1)
DB_PORT = "5432"
DB_NAME = "telegramdb_8moi"
TABELA_ALVO = "produtos"
PLANILHA_NOME = "Cabo_singelo.xlsx"

def importar_planilha_para_postgres():
    # 1. Verificar se a planilha existe na pasta
    if not os.path.exists(PLANILHA_NOME):
        print(f"❌ Erro: O arquivo '{PLANILHA_NOME}' não foi encontrado nesta pasta.")
        return

    print("📊 Lendo a planilha Excel...")
    try:
        df = pd.read_excel(PLANILHA_NOME)
    except Exception as e:
        print(f"❌ Erro ao ler a planilha Excel: {e}")
        return

    # 2. Tratamento de Colunas (Garantir letras minúsculas)
    df.columns = [col.strip().lower() for col in df.columns]

    # Se a coluna 'seq' estiver na planilha, removemos para o banco gerar o SERIAL automático
    if 'seq' in df.columns:
        df = df.drop(columns=['seq'])

    print(f"🚀 Conectando ao banco em nuvem '{DB_NAME}' e enviando dados...")
    
    # 3. Montar a URL de conexão padrão para bancos em nuvem
    # sslmode=require é obrigatório para a maioria das hospedagens na nuvem (Render, Neon, etc.)
    conexao_url = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?sslmode=require"
    
    try:
        engine = create_engine(conexao_url)
        
        # 4. Inserir dados na tabela existente
        df.to_sql(
            name=TABELA_ALVO, 
            con=engine, 
            if_exists='append', 
            index=False,
            method='multi'  # Otimiza a velocidade de inserção na nuvem
        )
        
        print(f"✅ Sucesso! {len(df)} registros foram carregados na tabela '{TABELA_ALVO}'.")

    except Exception as e:
        print(f"❌ Ocorreu um erro ao inserir no banco de dados:")
        print(e)

if __name__ == "__main__":
    importar_planilha_para_postgres()