from contextlib import asynccontextmanager
from fastapi import FastAPI
from database.connection import engine
from models.db_models import SQLModel
from api.endpoints import router as api_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Inicializando modelos e conexão com o banco...")
    SQLModel.metadata.create_all(engine)
    yield
    print("Encerrando conexão...")

app = FastAPI(
    title="Meal4You Recommender ML",
    version="1.0.0",
    lifespan=lifespan
)

# --- INCLUINDO AS ROTAS AQUI ---
app.include_router(api_router)

@app.get("/")
def health_check():
    return {"status": "ok", "message": "O Serviço de ML está rodando e conectado ao MySQL."}

# Para rodar: uvicorn main:app --reload