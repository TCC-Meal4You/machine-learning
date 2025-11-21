from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from pydantic import BaseModel
from typing import List

from database.connection import get_session
from services.recommendation import recall_por_restricao

# Definindo o Router
router = APIRouter()

# --- Schemas Pydantic (Entrada e Saída) ---
class UserRequest(BaseModel):
    id_usuario: int

class RecomResult(BaseModel):
    id_refeicoes_candidatas: List[int]

# --- Endpoints ---

@router.post("/recall/filtra_restricoes", response_model=RecomResult)
def filtra_restricoes(
    request: UserRequest, 
    session: Session = Depends(get_session)
):
    """
    Endpoint que realiza o Passo 1 (Recall):
    Recebe um usuário e retorna apenas IDs de refeições seguras para suas restrições.
    """
    try:
        # Chama a lógica que criamos no services/recommendation.py
        candidatos = recall_por_restricao(session, request.id_usuario)
        return {"id_refeicoes_candidatas": candidatos}
    except Exception as e:
        # Em produção, logar o erro real 'e'
        print(f"Erro no recall: {e}")
        raise HTTPException(status_code=500, detail="Erro interno ao processar filtragem.")
    