from sqlmodel import Session, select, col
from models.db_models import (
    UsuarioRestricao, 
    IngredienteRestricao, 
    RefeicaoIngrediente, 
    Refeicao
)

def recall_por_restricao(session: Session, id_usuario: int) -> list[int]:
    """
    Passo 1: Recupera todas as refeições que NÃO contêm ingredientes
    conflitantes com as restrições do usuário.
    """
    
    # 1. Buscar IDs das restrições do usuário
    # SQL: SELECT id_restricao FROM usuario_restricao WHERE id_usuario = ...
    statement_restricoes = select(UsuarioRestricao.id_restricao).where(
        UsuarioRestricao.id_usuario == id_usuario
    )
    ids_restricoes = session.exec(statement_restricoes).all()

    # Se o usuário não tem restrições, retorna todas as refeições disponíveis
    if not ids_restricoes:
        statement_all = select(Refeicao.id_refeicao).where(Refeicao.disponivel == True)
        return session.exec(statement_all).all()

    # 2. Buscar IDs dos ingredientes que possuem essas restrições
    # SQL: SELECT id_ingrediente FROM ingrediente_restricao WHERE id_restricao IN (...)
    statement_ingredientes = select(IngredienteRestricao.id_ingrediente).where(
        col(IngredienteRestricao.id_restricao).in_(ids_restricoes)
    )
    ids_ingredientes_proibidos = session.exec(statement_ingredientes).all()

    # Se não há ingredientes proibidos vinculados, retorna tudo
    if not ids_ingredientes_proibidos:
        statement_all = select(Refeicao.id_refeicao).where(Refeicao.disponivel == True)
        return session.exec(statement_all).all()

    # 3. Buscar IDs das refeições que contêm esses ingredientes proibidos
    # SQL: SELECT id_refeicao FROM refeicao_ingrediente WHERE id_ingrediente IN (...)
    statement_refeicoes_proibidas = select(RefeicaoIngrediente.id_refeicao).where(
        col(RefeicaoIngrediente.id_ingrediente).in_(ids_ingredientes_proibidos)
    )
    ids_refeicoes_proibidas = session.exec(statement_refeicoes_proibidas).unique().all()

    # 4. Buscar as refeições finais (Todas DISPONIVEIS exceto as proibidas)
    # SQL: SELECT id_refeicao FROM refeicao WHERE disponivel=1 AND id_refeicao NOT IN (...)
    query_final = select(Refeicao.id_refeicao).where(
        Refeicao.disponivel == True
    )
    
    if ids_refeicoes_proibidas:
        query_final = query_final.where(
            col(Refeicao.id_refeicao).not_in(ids_refeicoes_proibidas)
        )

    candidatos = session.exec(query_final).all()
    
    return list(candidatos)