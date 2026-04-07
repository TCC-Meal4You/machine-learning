from pydantic import BaseModel
from typing import List, Optional

# --- Requests ---
class UserRequestDTO(BaseModel):
    id_usuario: int

# --- Responses ---

# 1. /recall/filtra_restricoes
class RecallResponseDTO(BaseModel):
    id_refeicoes_candidatas: List[int]

# 2. /precision/rankeia_score
class RefeicaoRankeadaDTO(BaseModel):
    id_refeicao: int
    nome_refeicao: str
    preco: float
    id_restaurante: int
    nome_restaurante: str
    nota_media_restaurante: float
    qtd_avaliacoes_restaurante: int
    score: float

class RankeiaScoreResponseDTO(BaseModel):
    id_usuario: int
    total_resultados: int
    refeicoes_rankeadas: List[RefeicaoRankeadaDTO]

# 3. /precision/rankeia_por_compatibilidade_restaurante
class RestauranteCompatibilidadeDTO(BaseModel):
    id_restaurante: int
    nome_restaurante: str
    qtd_refeicoes_compativeis: int

class RankeiaRestauranteResponseDTO(BaseModel):
    id_usuario: int
    rank_restaurantes: List[RestauranteCompatibilidadeDTO]

# 4. /precision/rankeia_restaurante_composto
class RefeicaoCompativelDTO(BaseModel):
    id_refeicao: int
    nome: str
    descricao: Optional[str] = None
    preco: float

class RestauranteCompostoDTO(BaseModel):
    id_restaurante: int
    nome_restaurante: str
    compatibilidade_percent: float
    media_avaliacao: float
    total_avaliacoes: int
    score_final: float
    qtd_refeicoes_compativeis: int
    refeicoes_compativeis: List[RefeicaoCompativelDTO]

class RankeiaCompostoResponseDTO(BaseModel):
    id_usuario: int
    total_restaurantes: int
    restaurantes_ranked: List[RestauranteCompostoDTO]
