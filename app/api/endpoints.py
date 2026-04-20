from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session
from typing import List
from services.recomendador import rankeia_por_score
from connection import get_session
from services.recomendador import recall_por_restricao
from services.recomendador import rankeia_restaurante
from services.recomendador import rankeia_restaurante_composto
from services.ml.knn_service import get_restaurant_recommendations, get_meal_recommendations
from schemas import (
    UserRequestDTO,
    RecallResponseDTO,
    RankeiaScoreResponseDTO,
    RankeiaRestauranteResponseDTO,
    RankeiaCompostoResponseDTO,
    KNNRecommendationResponseDTO
)

# Definindo o Router
router = APIRouter()

# --- Endpoints ---

@router.post("/recall/filtra_restricoes", response_model=RecallResponseDTO)
def filtra_restricoes(
    request: UserRequestDTO, 
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
    
@router.post("/precision/rankeia_score", response_model=RankeiaScoreResponseDTO)
def rankeia_por_score_endpoint(
    request: UserRequestDTO,
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

@router.post("/precision/rankeia_por_compatibilidade_restaurante", response_model=RankeiaRestauranteResponseDTO)
def endpoint_rankeia_restaurante(
    request: UserRequestDTO,
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
    
@router.post("/precision/rankeia_restaurante_composto", response_model=RankeiaCompostoResponseDTO)
def endpoint_rankeia_restaurante_composto(
    request: UserRequestDTO,
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

# ------------------------------------ KNN abaixo ------------------------------------

@router.get("/usuarios/recomendacoes-knn/restaurantes/{id_usuario}", response_model=KNNRecommendationResponseDTO)
def recomendar_restaurantes_knn(
    id_usuario: int,
    min_score: float = Query(3.0, description="Nota mínima média exigida dos vizinhos para classificar um restaurante como recomendado."),
    session: Session = Depends(get_session)
):
    """
    Endpoint que retorna uma lista de IDs de restaurantes recomendados baseados no perfil do usuário (KNN).
    
    Parâmetros:
    - **id_usuario** (Path Parameter): ID numérico do usuário alvo da recomendação.
    - **min_score** (Query Parameter): Filtro tolerante de nota (padrão 3.0). Média >= min_score será recomendada.
    """
    try:
        resultado = get_restaurant_recommendations(session, user_id=id_usuario, min_score=min_score)
        
        # Cold start fallback (o serviço retorna um dict com a mensagem)
        if isinstance(resultado, dict) and "message" in resultado:
            return {"id_usuario": id_usuario, "message": resultado["message"], "recomendacoes": []}
            
        return {
            "id_usuario": id_usuario, 
            "recomendacoes": resultado,
            "message": "Recomendações geradas com sucesso."
        }
    except Exception as e:
        print("Erro no recomendar_restaurantes_knn:", e)
        raise HTTPException(status_code=500, detail="Erro interno ao treinar e recomendar via KNN.")

@router.get("/usuarios/recomendacoes-knn/refeicoes/{id_usuario}", response_model=KNNRecommendationResponseDTO)
def recomendar_refeicoes_knn(
    id_usuario: int,
    min_score: float = Query(3.0, description="Nota mínima média exigida dos vizinhos para classificar uma refeição como recomendada."),
    session: Session = Depends(get_session)
):
    """
    Endpoint que retorna uma lista de IDs de refeições recomendadas baseadas no perfil do usuário (KNN).
    Filtra automaticamente as intolerâncias do usuário ativo.
    
    Parâmetros:
    - **id_usuario** (Path Parameter): ID numérico do usuário alvo da recomendação.
    - **min_score** (Query Parameter): Filtro tolerante de nota (padrão 3.0). Média >= min_score será recomendada.
    """
    try:
        resultado = get_meal_recommendations(session, user_id=id_usuario, min_score=min_score)
        
        # Cold start fallback (o serviço retorna um dict com a mensagem)
        if isinstance(resultado, dict) and "message" in resultado:
            return {"id_usuario": id_usuario, "message": resultado["message"], "recomendacoes": []}
            
        return {
            "id_usuario": id_usuario, 
            "recomendacoes": resultado,
            "message": "Recomendações geradas com sucesso."
        }
    except Exception as e:
        print("Erro no recomendar_refeicoes_knn:", e)
        raise HTTPException(status_code=500, detail="Erro interno ao treinar e recomendar via KNN.")


@router.get("/usuarios/recomendacoes-knn/restaurantes/{id_usuario}", response_model=KNNRecommendationResponseDTO)
def recomendar_restaurantes_knn(
    id_usuario: int,
    session: Session = Depends(get_session)
):
    """
    Endpoint que retorna uma lista de IDs de restaurantes recomendados baseados no perfil do usuário (KNN).
    
    A documentação:
    - **id_usuario** (Path Parameter): ID numérico do usuário alvo da recomendação.
    """
    try:
        resultado = get_restaurant_recommendations(session, user_id=id_usuario)
        
        # Cold start fallback (o serviço retorna um dict com a mensagem)
        if isinstance(resultado, dict) and "message" in resultado:
            return {"id_usuario": id_usuario, "message": resultado["message"], "recomendacoes": []}
            
        return {
            "id_usuario": id_usuario, 
            "recomendacoes": resultado,
            "message": "Recomendações geradas com sucesso."
        }
    except Exception as e:
        print("Erro no recomendar_restaurantes_knn:", e)
        raise HTTPException(status_code=500, detail="Erro interno ao treinar e recomendar via KNN.")

@router.get("/usuarios/recomendacoes-knn/refeicoes/{id_usuario}", response_model=KNNRecommendationResponseDTO)
def recomendar_refeicoes_knn(
    id_usuario: int,
    session: Session = Depends(get_session)
):
    """
    Endpoint que retorna uma lista de IDs de refeições recomendadas baseadas no perfil do usuário (KNN).
    Filtra automaticamente as intolerâncias do usuário ativo.
    
    A documentação:
    - **id_usuario** (Path Parameter): ID numérico do usuário alvo da recomendação.
    """
    try:
        resultado = get_meal_recommendations(session, user_id=id_usuario)
        
        # Cold start fallback (o serviço retorna um dict com a mensagem)
        if isinstance(resultado, dict) and "message" in resultado:
            return {"id_usuario": id_usuario, "message": resultado["message"], "recomendacoes": []}
            
        return {
            "id_usuario": id_usuario, 
            "recomendacoes": resultado,
            "message": "Recomendações geradas com sucesso."
        }
    except Exception as e:
        print("Erro no recomendar_refeicoes_knn:", e)
        raise HTTPException(status_code=500, detail="Erro interno ao treinar e recomendar via KNN.")
