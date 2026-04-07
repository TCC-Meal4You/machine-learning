from contextlib import asynccontextmanager
from fastapi import FastAPI
from scalar_fastapi import get_scalar_api_reference
from connection import engine
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


# -_-_-_- SCALAR DOCS & API Testing -_-_-_-
@app.get("/scalar", include_in_schema=False)
async def scalar_html():
    return get_scalar_api_reference(
        openapi_url=app.openapi_url,
        title=app.title,
    )
# -_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-


@app.get("/")
def health_check():
    return {"status": "ok", "message": "O Serviço de ML está rodando e conectado ao MySQL."}

# Para rodar: uvicorn main:app --reload