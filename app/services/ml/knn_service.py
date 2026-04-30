from sqlmodel import Session, select, col
from app.models.db_models import (
    UsuarioAvalia, RefeicaoAvalia, UsuarioRestricao,
    IngredienteRestricao, RefeicaoIngrediente
)
from app.services.ml.pre_pocessing.processor import create_user_restaurant_matrix, create_user_meal_matrix
from app.services.ml.recomendador_knn import KNNRecommender

def get_restaurant_recommendations(session: Session, user_id: int, k=16, min_score: float = 3.0):
    """
    Fluxo A: Orquestra recomendações de restaurantes usando KNN e filtra por nota >= min_score.
    """
    # Buscar todas as linhas de usuario_avalia
    avaliacoes = session.exec(select(UsuarioAvalia)).all()
    if not avaliacoes:
        return []

    # Validar Cold Start
    user_evals = [av for av in avaliacoes if av.id_usuario == user_id]
    if not user_evals:
        return {"message": "Você não avaliou nenhum restaurante ainda, para poder receber recomendações mais alinhadas ao seu perfil avalie pelo menos 1 restaurante."}

    # Prepara dados para o processor criar a matriz
    data = [{"id_usuario": av.id_usuario, "id_restaurante": av.id_restaurante, "nota": av.nota} for av in avaliacoes]
    matrix = create_user_restaurant_matrix(data)

    # Instanciar e treinar KNN
    recommender = KNNRecommender(k_neighbors=k)
    recommender.fit(matrix)
    
    # Buscar vizinhos
    vizinhos = recommender.get_neighbors(user_id)
    if not vizinhos:
        return []

    # Filtrar avaliações que pertencem apenas aos vizinhos encontrados
    vizinhos_evals = [av for av in avaliacoes if av.id_usuario in vizinhos]
    
    restaurante_notas = {}
    for av in vizinhos_evals:
        if av.id_restaurante not in restaurante_notas:
            restaurante_notas[av.id_restaurante] = []
        restaurante_notas[av.id_restaurante].append(av.nota)

    # Calcular média da nota dada *apenas* pelos vizinhos mais próximos
    restaurante_medias = {rid: sum(notas)/len(notas) for rid, notas in restaurante_notas.items()}

    # Filtro 1: Restaurantes bem avaliados pelos vizinhos (nota >= min_score)
    recomendados = {rid: media for rid, media in restaurante_medias.items() if media >= min_score}

    # Filtro 2: Remover restaurantes que o user_id alvo já avaliou/visitou
    user_restaurantes = {av.id_restaurante for av in user_evals}
    recomendados_filtrados = {rid: media for rid, media in recomendados.items() if rid not in user_restaurantes}

    # Ordenação (Ranqueamento) pela média descrescente
    ranked = sorted(recomendados_filtrados.keys(), key=lambda rid: recomendados_filtrados[rid], reverse=True)

    return ranked


def get_meal_recommendations(session: Session, user_id: int, k=16, min_score: float = 3.0):
    """
    Fluxo B: Orquestra recomendações de refeições usando KNN e aplica filtro de restrição alimentar.
    """
    # Buscar todas as linhas de refeicao_avalia
    avaliacoes = session.exec(select(RefeicaoAvalia)).all()
    if not avaliacoes:
        return []

    # Validar Cold Start
    user_evals = [av for av in avaliacoes if av.id_usuario == user_id]
    if not user_evals:
        return {"message": "Você não avaliou nenhuma refeição ainda, para poder receber recomendações mais alinhadas ao seu perfil avalie pelo menos 1 refeição."}

    # Prepara dados para o processor criar a matriz
    data = [{"id_usuario": av.id_usuario, "id_refeicao": av.id_refeicao, "nota": av.nota} for av in avaliacoes]
    matrix = create_user_meal_matrix(data)

    # Instanciar e treinar KNN
    recommender = KNNRecommender(k_neighbors=k)
    recommender.fit(matrix)
    
    # Buscar vizinhos
    vizinhos = recommender.get_neighbors(user_id)
    if not vizinhos:
        return []

    # Filtrar avaliações da refeição que pertencem apenas aos vizinhos
    vizinhos_evals = [av for av in avaliacoes if av.id_usuario in vizinhos]
    
    refeicao_notas = {}
    for av in vizinhos_evals:
        if av.id_refeicao not in refeicao_notas:
            refeicao_notas[av.id_refeicao] = []
        refeicao_notas[av.id_refeicao].append(av.nota)

    # Calcular média da nota dada *apenas* pelos vizinhos mais próximos
    refeicao_medias = {rid: sum(notas)/len(notas) for rid, notas in refeicao_notas.items()}

    # Filtro 1: Refeições bem avaliadas pelos vizinhos (nota >= min_score) e ainda não testadas pelo usuário
    user_refeicoes = {av.id_refeicao for av in user_evals}
    recomendados_iniciais = [rid for rid, media in refeicao_medias.items() if media >= min_score and rid not in user_refeicoes]

    if not recomendados_iniciais:
        return []

    # Filtro 2: Intersecção de Restrições (Remover refeições com ingredientes proibidos)
    user_restr = session.exec(
        select(UsuarioRestricao.id_restricao).where(UsuarioRestricao.id_usuario == user_id)
    ).all()

    if user_restr:
        # Pega IDs de ingredientes proibidos para essas restrições
        ingred_proibidos = session.exec(
            select(IngredienteRestricao.id_ingrediente).where(col(IngredienteRestricao.id_restricao).in_(user_restr))
        ).all()

        if ingred_proibidos:
            # Encontra quais refeições recomendadas contêm ingredientes proibidos
            ref_proibidas = session.exec(
                select(RefeicaoIngrediente.id_refeicao)
                .where(col(RefeicaoIngrediente.id_ingrediente).in_(ingred_proibidos))
                .where(col(RefeicaoIngrediente.id_refeicao).in_(recomendados_iniciais))
            ).all()

            ref_proibidas_set = set(ref_proibidas)
            # Exclui refeições proibidas da lista inicial
            recomendados_iniciais = [rid for rid in recomendados_iniciais if rid not in ref_proibidas_set]

    # Ordenação (Ranqueamento) pela média descrescente
    ranked = sorted(recomendados_iniciais, key=lambda rid: refeicao_medias[rid], reverse=True)

    return ranked
