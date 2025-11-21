from sqlmodel import create_engine, Session
from typing import Generator

# --- CONFIGURAÇÃO AQUI ---
# 1: trocar USUARIO e SENHA conforme seu MySQL local ou em nuvem
# 2: trocar o nome do banco de dados se necessário
# 3: trocar o host e porta se necessário
# 4: trocar o NOME DO BANCO conforme o banco criado no seu MySQL
DATABASE_URL = "mysql+pymysql://USUARIO:SENHA@127.0.0.1:3306/NOME_DO_BANCO"

# Cria o motor de conexão.
engine = create_engine(DATABASE_URL, echo=True)

def get_session() -> Generator[Session, None, None]:
    """
    Dependência do FastAPI para fornecer uma sessão de banco de dados
    para cada requisição.
    """
    with Session(engine) as session:
        yield session