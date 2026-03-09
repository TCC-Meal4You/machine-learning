from sqlmodel import Session, select, col
from sqlalchemy import func 
from models.db_models import (
    UsuarioRestricao, 
    IngredienteRestricao, 
    RefeicaoIngrediente, 
    Refeicao,
    UsuarioAvalia,
    Restaurante
)
from typing import List, Dict

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


def rankeia_por_score(
    session: Session,
    id_usuario: int,
    peso_nota: float = 0.7,
    peso_qtd: float = 0.3
) -> List[Dict]:

    # 1) Recall
    candidatos = recall_por_restricao(session, id_usuario)
    if not candidatos:
        return []

    # 2) Buscar informações das refeições
    stmt_ref = select(
        Refeicao.id_refeicao,
        Refeicao.nome,
        Refeicao.preco,
        Refeicao.id_restaurante
    ).where(col(Refeicao.id_refeicao).in_(candidatos))

    refeicoes_rows = session.exec(stmt_ref).all()

    # 3) Agregar média e quantidade de avaliações por restaurante
    stmt_agg = select(
        UsuarioAvalia.id_restaurante,
        func.avg(UsuarioAvalia.nota).label("nota_media"),
        func.count(UsuarioAvalia.nota).label("qtd_avaliacoes")
    ).group_by(UsuarioAvalia.id_restaurante)

    agg_rows = session.exec(stmt_agg).all()

    agg_map = {
        r[0]: {
            "nota_media": float(r[1]) if r[1] is not None else 0.0,
            "qtd_avaliacoes": int(r[2])
        }
        for r in agg_rows
    }

    max_qtd = max((v["qtd_avaliacoes"] for v in agg_map.values()), default=0)

    # 4) Buscar nomes dos restaurantes
    ids_restaurantes = list({row[3] for row in refeicoes_rows})

    stmt_rest = select(Restaurante.id_restaurante, Restaurante.nome).where(
        col(Restaurante.id_restaurante).in_(ids_restaurantes)
    )
    rest_rows = session.exec(stmt_rest).all()

    # dicionário id_restaurante → nome_restaurante
    restaurante_map = {r[0]: r[1] for r in rest_rows}

    # 5) Montar resultado final com score + nome restaurante
    resultados = []

    for rid, nome_ref, preco, id_rest in refeicoes_rows:
        stats = agg_map.get(id_rest, {"nota_media": 0.0, "qtd_avaliacoes": 0})
        nota_media = stats["nota_media"]
        qtd_av = stats["qtd_avaliacoes"]

        popularidade_norm = (qtd_av / max_qtd) if max_qtd > 0 else 0

        score = (nota_media * peso_nota) + (popularidade_norm * peso_qtd * 5)

        resultados.append({
            "id_refeicao": rid,
            "nome_refeicao": nome_ref,
            "preco": float(preco),
            "id_restaurante": id_rest,
            "nome_restaurante": restaurante_map.get(id_rest, "Desconhecido"),

            "nota_media_restaurante": round(nota_media, 3),
            "qtd_avaliacoes_restaurante": qtd_av,

            "score": round(score, 4)
        })

    return sorted(resultados, key=lambda x: x["score"], reverse=True)

def rankeia_restaurante(session: Session, id_usuario: int) -> List[Dict]:
    """
    Conta quantas refeições compatíveis (após recall) cada restaurante tem
    e retorna ranking com id, nome e quantidade de refeições compatíveis.
    """
    # 1) recall (retorna lista de ids de refeicao)
    candidatos = recall_por_restricao(session, id_usuario)
    if not candidatos:
        return []

    # 2) buscar id_refeicao -> id_restaurante para os candidatos
    stmt_ref = select(Refeicao.id_refeicao, Refeicao.id_restaurante).where(
        col(Refeicao.id_refeicao).in_(candidatos)
    )
    refeicoes_rows = session.exec(stmt_ref).all()  # lista de (id_refeicao, id_restaurante)
    if not refeicoes_rows:
        return []

    # 3) contar quantas refeições compatíveis por restaurante
    contagem = {}
    for _, id_rest in refeicoes_rows:
        contagem[id_rest] = contagem.get(id_rest, 0) + 1

    if not contagem:
        return []

    ids_restaurantes = list(contagem.keys())

    # 4) buscar nomes dos restaurantes
    stmt_rest = select(Restaurante.id_restaurante, Restaurante.nome).where(
        col(Restaurante.id_restaurante).in_(ids_restaurantes)
    )
    rest_rows = session.exec(stmt_rest).all()  # lista de (id_restaurante, nome)
    rest_map = {r[0]: r[1] for r in rest_rows}

    # 5) montar lista ordenada pelo número de refeições compatíveis (desc)
    resultado = []
    for id_rest, qtd in sorted(contagem.items(), key=lambda x: x[1], reverse=True):
        resultado.append({
            "id_restaurante": int(id_rest),
            "nome_restaurante": rest_map.get(id_rest, "Desconhecido"),
            "qtd_refeicoes_compativeis": int(qtd)
        })

    return resultado

def rankeia_restaurante_composto(
    session: Session,
    id_usuario: int,
    w_compat: float = 0.6,
    w_avg: float = 0.2,
    w_rev: float = 0.2
) -> List[Dict]:

    candidatos = recall_por_restricao(session, id_usuario)
    if not candidatos:
        return []

    stmt_ref = select(
        Refeicao.id_refeicao,
        Refeicao.id_restaurante
    ).where(col(Refeicao.id_refeicao).in_(candidatos))

    rows = session.exec(stmt_ref).all()
    if not rows:
        return []

    rest_compat = {}
    for _, id_rest in rows:
        rest_compat[id_rest] = rest_compat.get(id_rest, 0) + 1

    ids_restaurantes = list(rest_compat.keys())

    stmt_total = select(
        Refeicao.id_restaurante,
        func.count(Refeicao.id_refeicao)
    ).where(col(Refeicao.id_restaurante).in_(ids_restaurantes)) \
     .group_by(Refeicao.id_restaurante)

    total_rows = session.exec(stmt_total).all()
    rest_total = {r[0]: r[1] for r in total_rows}

    compat = {}
    for rid in ids_restaurantes:
        compat[rid] = rest_compat[rid] / rest_total.get(rid, 1)

    stmt_eval = select(
        UsuarioAvalia.id_restaurante,
        UsuarioAvalia.nota
    ).where(col(UsuarioAvalia.id_restaurante).in_(ids_restaurantes))

    eval_rows = session.exec(stmt_eval).all()

    soma_nota = {}
    qtd_nota = {}

    for rid, nota in eval_rows:
        soma_nota[rid] = soma_nota.get(rid, 0) + nota
        qtd_nota[rid] = qtd_nota.get(rid, 0) + 1

    media_aval = {}
    total_aval = {}

    for rid in ids_restaurantes:
        total = qtd_nota.get(rid, 0)
        total_aval[rid] = total
        media_aval[rid] = (soma_nota.get(rid, 0) / total) if total > 0 else 0.0

    max_media = max(media_aval.values()) if media_aval else 1
    min_media = min(media_aval.values()) if media_aval else 0

    media_norm = {}
    if max_media == min_media:
        for rid in ids_restaurantes:
            media_norm[rid] = 1.0 if media_aval[rid] > 0 else 0.0
    else:
        for rid in ids_restaurantes:
            media_norm[rid] = (media_aval[rid] - min_media) / (max_media - min_media)

    max_reviews = max(total_aval.values()) if total_aval else 1
    reviews_norm = {
        rid: (total_aval[rid] / max_reviews) if max_reviews > 0 else 0.0
        for rid in ids_restaurantes
    }

    score_final = {}
    for rid in ids_restaurantes:
        score_final[rid] = (
            compat[rid] * w_compat
            + media_norm[rid] * w_avg
            + reviews_norm[rid] * w_rev
        )

    stmt_rest = select(Restaurante.id_restaurante, Restaurante.nome).where(
        col(Restaurante.id_restaurante).in_(ids_restaurantes)
    )
    rest_rows = session.exec(stmt_rest).all()
    rest_nomes = {r[0]: r[1] for r in rest_rows}

    resultado = []
    for rid in sorted(score_final, key=score_final.get, reverse=True):
        resultado.append({
            "id_restaurante": rid,
            "nome_restaurante": rest_nomes.get(rid, "Desconhecido"),
            "compatibilidade_percent": round(compat[rid] * 100, 1),
            "media_avaliacao": round(media_aval[rid], 2),
            "total_avaliacoes": total_aval[rid],
            "score_final": round(score_final[rid], 4),
            "qtd_refeicoes_compativeis": rest_compat[rid]
        })

    # ---------------------------
    # REFEIÇÕES COMPATÍVEIS POR RESTAURANTE (NOVO BLOCO)
    # ---------------------------
    stmt_ref_info = select(
        Refeicao.id_refeicao,
        Refeicao.id_restaurante,
        Refeicao.nome,
        Refeicao.descricao,
        Refeicao.preco,
    ).where(col(Refeicao.id_refeicao).in_(candidatos))

    ref_info_rows = session.exec(stmt_ref_info).all()

    refeicoes_por_rest = {rid: [] for rid in ids_restaurantes}

    for r in ref_info_rows:
        refeicoes_por_rest[r.id_restaurante].append({
            "id_refeicao": r.id_refeicao,
            "nome": r.nome,
            "descricao": r.descricao,
            "preco": r.preco,
        })

    for item in resultado:
        rid = item["id_restaurante"]
        item["refeicoes_compativeis"] = refeicoes_por_rest.get(rid, [])

    return resultado
