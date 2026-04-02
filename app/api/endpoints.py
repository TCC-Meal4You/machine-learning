from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from pydantic import BaseModel
from typing import List
from app.services.recomendador import rankeia_por_score
from app.connection import get_session
from app.services.recomendador import recall_por_restricao
from app.services.recomendador import rankeia_restaurante
from app.services.recomendador import rankeia_restaurante_composto

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
    
@router.post("/precision/rankeia_score")
def rankeia_por_score_endpoint(
    request: UserRequest,
    session: Session = Depends(get_session)
):
    """
    Recebe id_usuario, executa recall e ordena por score (média do restaurante + volume).
    """
    try:
        resultados = rankeia_por_score(session, request.id_usuario)
        return {
            "id_usuario": request.id_usuario,
            "total_resultados": len(resultados),
            "refeicoes_rankeadas": resultados
        }
    except Exception as e:
        print("Erro no endpoint rankeia_por_score:", e)
        raise HTTPException(status_code=500, detail="Erro interno ao calcular ranking.")

@router.post("/precision/rankeia_por_compatibilidade_restaurante")
def endpoint_rankeia_restaurante(
    request: UserRequest,
    session: Session = Depends(get_session)
):
    """
    Endpoint mínimo: chama rankeia_restaurante(session, id_usuario)
    e devolve o ranking de restaurantes compatíveis.
    """
    try:
        resultado = rankeia_restaurante(session, request.id_usuario)
        return {
            "id_usuario": request.id_usuario,
            "rank_restaurantes": resultado
        }
    except Exception as e:
        print("Erro no endpoint rankeia_por_compatibilidade_restaurante:", e)
        raise HTTPException(status_code=500, detail="Erro interno ao calcular compatibilidade por restaurante.")  
    
@router.post("/precision/rankeia_restaurante_composto")
def endpoint_rankeia_restaurante_composto(
    request: UserRequest,
    session: Session = Depends(get_session)
):
    try:
        resultado = rankeia_restaurante_composto(
            session=session,
            id_usuario=request.id_usuario
        )
        return {
            "id_usuario": request.id_usuario,
            "total_restaurantes": len(resultado),
            "restaurantes_ranked": resultado
        }
    except Exception as e:
        print("Erro no rankeia_restaurante_composto:", e)
        raise HTTPException(status_code=500, detail="Erro interno ao calcular ranking composto.")