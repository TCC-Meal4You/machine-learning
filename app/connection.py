import os
from pathlib import Path
from dotenv import load_dotenv
from sqlmodel import create_engine, Session
from typing import Generator

# Define o caminho para o arquivo .env usando Pathlib
env_path = Path(__file__).resolve().parent.parent / ".env"

# Tenta carregar o .env se ele existir (desenvolvimento local)
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    # Em produção (Railway), as variáveis já estarão no ambiente do sistema
    load_dotenv()

# Ao rodar localmente, configurar arquivo '.env' com:
# 1. DB_DRIVER= db-driver
# 2. DB_USER= user
# 3. DB_PASSWORD= senha
# 4. DB_HOST= host
# 5. DB_PORT= port
# 6. DB_NAME= db-name

# Reconstrói a URL a partir de variáveis individuais
DB_DRIVER = os.getenv("DB_DRIVER", "mysql+pymysql")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

DATABASE_URL = f"{DB_DRIVER}://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

if not all([DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME]):
    raise ValueError("Faltam variáveis de ambiente para a conexão com o banco de dados.")

# Cria o motor de conexão.
engine = create_engine(DATABASE_URL, echo=True)

def get_session() -> Generator[Session, None, None]:
    """
    Dependência do FastAPI para fornecer uma sessão de banco de dados
    para cada requisição.
    """
    with Session(engine) as session:
        yield session