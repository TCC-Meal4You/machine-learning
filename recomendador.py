import pandas as pd
from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn
import os   # Importar 'os' para manipulação de caminhos

# ----------------------------------------------------
# 1. CARREGAMENTO E SIMULAÇÃO DE DADOS
#    Alterado para ler os CSVs da pasta 'CSVs/'
# ----------------------------------------------------
# Define o prefixo do caminho
CAMINHO_PASTA_CSVS = 'CSVs/'
# Carregamento dos dados dos CSVs que você gerou:
try:
    df_refeicao = pd.read_csv(os.path.join(CAMINHO_PASTA_CSVS, 'tb_refeicao.csv'))
    df_usuario_restricao = pd.read_csv(os.path.join(CAMINHO_PASTA_CSVS, 'tb_restricoes_usuario.csv'))
    df_ingrediente_restricao = pd.read_csv(os.path.join(CAMINHO_PASTA_CSVS, 'tb_ingredientes_restricoes.csv'))
    df_refeicao_ingrediente = pd.read_csv(os.path.join(CAMINHO_PASTA_CSVS, 'tb_refeicao_ingrediente.csv'))
    df_refeicao_avaliacao = pd.read_csv(os.path.join(CAMINHO_PASTA_CSVS, 'refeicao_avaliacao.csv'))
    df_restricoes = pd.read_csv(os.path.join(CAMINHO_PASTA_CSVS, 'tb_restricoes.csv'))
    df_ingredientes = pd.read_csv(os.path.join(CAMINHO_PASTA_CSVS, 'tb_ingredientes.csv'))
    df_restaurante = pd.read_csv(os.path.join(CAMINHO_PASTA_CSVS, 'tb_restaurante.csv'))
    df_refeicao_restaurante = pd.read_csv(os.path.join(CAMINHO_PASTA_CSVS, 'tb_refeicao_restaurante.csv'))

except FileNotFoundError:
    # Caso não encontre, imprime a mensagem de erro e retorna DataFrames vazios
    print("Atenção: Arquivos CSV não encontrados na pasta 'CSVs/'. A API retornará uma lista vazia.")
    df_refeicao = pd.DataFrame({'id_refeicao': []})
    df_usuario_restricao = pd.DataFrame({'id_usuario': [], 'id_restricao': []})
    df_ingrediente_restricao = pd.DataFrame({'id_ingrediente': [], 'id_restricao': []})
    df_refeicao_ingrediente = pd.DataFrame({'id_refeicao': [], 'id_ingrediente': []})
    df_refeicao_avaliacao = pd.DataFrame({'id_refeicao': [], 'nota_media': [], 'qtd_avaliacoes': []})
    df_restricoes = pd.DataFrame({'id_restricao': [], 'nome_restricao': []})
    df_ingredientes = pd.DataFrame({'id_ingrediente': [], 'nome_ingrediente': []})
    df_restaurante = pd.DataFrame({'id_restaurante': [], 'nome_restaurante': []})
    df_refeicao_restaurante = pd.DataFrame({'id_refeicao': [], 'id_restaurante': []})

# ----------------------------------------------------
# 2. DEFINIÇÃO DA API E MODELO DE ENTRADA/SAÍDA (Swagger/JSON)
# ----------------------------------------------------

app = FastAPI(
    title="Meal4You Recommender ML Service",
    version="0.1.0",
    description="Microserviço de ML para o sistema de recomendação."
)

# Modelo de entrada (JSON que o Java enviará)
class UserRequest(BaseModel):
    id_usuario: int

# Modelo de saída (JSON que o Python retornará)
class RecomResult(BaseModel):
    id_refeicoes_candidatas: list[int]

# ----------------------------------------------------
# 3. ENDPOINT DE FILTRAGEM (Passo 1)
# ----------------------------------------------------

@app.post("/recall/filtra_restricoes", response_model=RecomResult)
def filtra_restricoes(request: UserRequest):
    """
    Realiza a filtragem inicial de refeições, excluindo aquelas que
    possuem ingredientes que violam as restrições alimentares do usuário.
    (Passo 1: Recall/Filtragem Determinística).
    """
    user_id = request.id_usuario

    # 1. Encontrar as IDs de restrição do usuário
    restricoes_usuario = df_usuario_restricao[
        df_usuario_restricao['id_usuario'] == user_id
    ]['id_restricao'].tolist()

    # Se o usuário não tem restrições, todas as refeições são candidatas
    if not restricoes_usuario:
        candidatos_validos = df_refeicao['id_refeicao'].tolist()
        return {"id_refeicoes_candidatas": candidatos_validos}

    # 2. Encontrar TODOS os ingredientes que contêm QUALQUER UMA dessas restrições
    #    (Ingredientes Proibidos)
    ingredientes_proibidos = df_ingrediente_restricao[
        df_ingrediente_restricao['id_restricao'].isin(restricoes_usuario)
    ]['id_ingrediente'].unique()

    # Se não há ingredientes proibidos nos dados, todas as refeições são candidatas
    if len(ingredientes_proibidos) == 0:
        candidatos_validos = df_refeicao['id_refeicao'].tolist()
        return {"id_refeicoes_candidatas": candidatos_validos}

    # 3. Encontrar as Refeições que USAM ingredientes proibidos
    refeicoes_proibidas = df_refeicao_ingrediente[
        df_refeicao_ingrediente['id_ingrediente'].isin(ingredientes_proibidos)
    ]['id_refeicao'].unique()

    # 4. Refeições CANDIDATAS (Todas as refeições MENOS as proibidas)
    candidatos_validos_df = df_refeicao[
        ~df_refeicao['id_refeicao'].isin(refeicoes_proibidas)
    ]

    return {"id_refeicoes_candidatas": candidatos_validos_df['id_refeicao'].tolist()}

@app.post("/precision/rankeia_score")
def rankeia_por_score(request: UserRequest):
    """
    Passo 2 (Precision): Ordena as refeições válidas com base nas notas e quantidade de avaliações.
    """
    user_id = request.id_usuario

    # Reutiliza o passo 1 para filtrar
    resultado_recall = filtra_restricoes(request)
    refeicoes_filtradas = resultado_recall['id_refeicoes_candidatas']

    # Junta com as avaliações
    df_merge = df_refeicao_avaliacao[df_refeicao_avaliacao['id_refeicao'].isin(refeicoes_filtradas)].copy()

    if df_merge.empty:
        return {"mensagem": "Nenhuma refeição válida encontrada após filtragem e avaliação."}

    # Cria um score ponderado (nota + peso da quantidade de avaliações)
    # peso 70% para nota média e 30% para volume de avaliações
    df_merge['score'] = (df_merge['nota_media'] * 0.7) + ((df_merge['qtd_avaliacoes'] / df_merge['qtd_avaliacoes'].max()) * 0.3 * 5)

    # Ordena do maior para o menor score
    df_merge = df_merge.sort_values(by='score', ascending=False)

    # Junta nome e preço da refeição para retorno mais completo
    df_final = df_merge.merge(df_refeicao, on='id_refeicao', how='left')[['id_refeicao', 'nome_refeicao', 'nota_media', 'qtd_avaliacoes', 'score', 'preco']]

    # Converte para lista de dicionários
    resultados = df_final.to_dict(orient='records')

    return {
        "id_usuario": user_id,
        "total_resultados": len(resultados),
        "refeicoes_rankeadas": resultados
    }

@app.post("/precision/rankeia_avaliacoes")
def rankeia_por_avaliacoes(request: UserRequest):
    user_id = request.id_usuario
    # Reutiliza o passo 1 para filtrar
    resultado_recall = filtra_restricoes(request)
    refeicoes_filtradas = resultado_recall['id_refeicoes_candidatas']

    # Junta com as avaliações
    df_merge = df_refeicao_avaliacao[df_refeicao_avaliacao['id_refeicao'].isin(refeicoes_filtradas)].copy()

    if df_merge.empty:
        return {"mensagem": "Nenhuma refeição válida encontrada após filtragem e avaliação."}

    # Ordena do maior para o menor (APENAS pela nota_media)
    df_merge = df_merge.sort_values(by='nota_media', ascending=False)

    # Junta nome e preço da refeição para retorno mais completo
    df_final = df_merge.merge(df_refeicao, on='id_refeicao', how='left')[['id_refeicao', 'nome_refeicao', 'nota_media', 'qtd_avaliacoes', 'preco']]

    # Converte para lista de dicionários
    resultados = df_final.to_dict(orient='records')

    return {
        "id_usuario": user_id,
        "total_resultados": len(resultados),
        "refeicoes_rankeadas": resultados
    }

@app.post("/precision/rankeia_qtd_avaliacoes")
def rankeia_por_quantidade_avaliacoes(request: UserRequest):
    user_id = request.id_usuario
    # Reutiliza o passo 1 para filtrar
    resultado_recall = filtra_restricoes(request)
    refeicoes_filtradas = resultado_recall['id_refeicoes_candidatas']

    # Junta com as avaliações
    df_merge = df_refeicao_avaliacao[df_refeicao_avaliacao['id_refeicao'].isin(refeicoes_filtradas)].copy()

    if df_merge.empty:
        return {"mensagem": "Nenhuma refeição válida encontrada após filtragem e avaliação."}

    # Ordena do maior para o menor (APENAS pela qtd_avaliacoes)
    df_merge = df_merge.sort_values(by='qtd_avaliacoes', ascending=False)

    # Junta nome e preço da refeição para retorno mais completo
    df_final = df_merge.merge(df_refeicao, on='id_refeicao', how='left')[['id_refeicao', 'nome_refeicao', 'nota_media', 'qtd_avaliacoes', 'preco']]

    # Converte para lista de dicionários
    resultados = df_final.to_dict(orient='records')

    return {
        "id_usuario": user_id,
        "total_resultados": len(resultados),
        "refeicoes_rankeadas": resultados
    }

@app.post("/restricoes/usuario")
def listar_restricoes_usuario(request: UserRequest):
    """
    Retorna as restrições alimentares associadas a um usuário.
    """
    user_id = request.id_usuario

    # Filtra as restrições do usuário
    restricoes_usuario = df_usuario_restricao[
        df_usuario_restricao['id_usuario'] == user_id
    ]['id_restricao'].tolist()

    return {"id_usuario": user_id, "restricoes": restricoes_usuario}


@app.get("/restricoes/refeicao/{id_refeicao}")
def listar_restricoes_refeicao(id_refeicao: int):
    # 1) Ingredientes da refeição
    ingredientes_ids = df_refeicao_ingrediente[
        df_refeicao_ingrediente['id_refeicao'] == id_refeicao
    ]['id_ingrediente'].unique().tolist()

    # Resolve nomes dos ingredientes (se disponível)
    ingredientes_info = []
    if not df_ingredientes.empty:
        ingredientes_df = df_ingredientes[df_ingredientes['id_ingrediente'].isin(ingredientes_ids)]
        # Preserva ordem aproximada
        for iid in ingredientes_ids:
            row = ingredientes_df[ingredientes_df['id_ingrediente'] == iid]
            nome = row['nome_ingrediente'].values[0] if not row.empty else None
            ingredientes_info.append({"id_ingrediente": int(iid), "nome_ingrediente": nome})
    else:
        ingredientes_info = [{"id_ingrediente": int(iid), "nome_ingrediente": None} for iid in ingredientes_ids]

    # 2) Mapeia ingredientes para restrições
    restricoes_ids = df_ingrediente_restricao[
        df_ingrediente_restricao['id_ingrediente'].isin(ingredientes_ids)
    ]['id_restricao'].unique().tolist()

    # 3) Resolve nomes das restrições
    restricoes_info = []
    if not df_restricoes.empty:
        restricoes_df = df_restricoes[df_restricoes['id_restricao'].isin(restricoes_ids)]
        for rid in restricoes_ids:
            row = restricoes_df[restricoes_df['id_restricao'] == rid]
            nome = row['nome_restricao'].values[0] if not row.empty else None
            restricoes_info.append({"id_restricao": int(rid), "nome_restricao": nome})
    else:
        restricoes_info = [{"id_restricao": int(rid), "nome_restricao": None} for rid in restricoes_ids]

    return {
        "id_refeicao": id_refeicao,
        "ingredientes": ingredientes_info,
        "restricoes": restricoes_info
    }

@app.post("/precision/rankeia_por_compatibilidade_restaurante")
def rankeia_restaurante(request: UserRequest):

    resultado_recall = filtra_restricoes(request)
    candidatos = resultado_recall["id_refeicoes_candidatas"]

    df_filtrado = df_refeicao_restaurante[
        df_refeicao_restaurante["id_refeicao"].isin(candidatos)
    ]

    if df_filtrado.empty:
        return {"rank_restaurantes": []}

    contagem = (
        df_filtrado.groupby("id_restaurante")["id_refeicao"]
        .count()
        .reset_index(name="qtd_refeicoes_compativeis")
        .sort_values(by="qtd_refeicoes_compativeis", ascending=False)
    )

    contagem = contagem.merge(df_restaurante, on="id_restaurante", how="left")

    return {
        "id_usuario": request.id_usuario,
        "rank_restaurantes": contagem.to_dict(orient="records")
    }


@app.post("/precision/rankeia_restaurante_composto")
def rankeia_restaurante_composto(request: UserRequest):
    """
    Rankear restaurantes por um score composto onde:
    - 0.6 = compatibilidade do restaurante com o usuário (fracão de refeições compatíveis)
    - 0.2 = avaliação média dos pratos compatíveis do restaurante (ponderada por qtd_avaliacoes)
    - 0.2 = quantidade total de avaliações dos pratos compatíveis (normalizada)

    Retorna restaurantes ordenados por esse score e, dentro de cada restaurante,
    a lista de refeições compatíveis (com campos úteis).
    """
    user_id = request.id_usuario

    resultado_recall = filtra_restricoes(request)
    candidatos = resultado_recall.get('id_refeicoes_candidatas', [])

    if not candidatos:
        return {"id_usuario": user_id, "restaurantes_ranked": []}

    # Total de refeições oferecidas por restaurante (base)
    rest_total = (
        df_refeicao_restaurante.groupby('id_restaurante')['id_refeicao']
        .nunique()
        .reset_index(name='total_oferecidas')
    )

    # Quantas dessas refeições são compatíveis com o usuário
    rest_compat = (
        df_refeicao_restaurante[df_refeicao_restaurante['id_refeicao'].isin(candidatos)]
        .groupby('id_restaurante')['id_refeicao']
        .nunique()
        .reset_index(name='qtd_refeicoes_compativeis')
    )

    # Mesclar informações básicas por restaurante
    df_rest = rest_total.merge(rest_compat, on='id_restaurante', how='left').fillna(0)
    # Pontuação de compatibilidade: fração de refeições compatíveis
    df_rest['pontuacao_compat'] = df_rest['qtd_refeicoes_compativeis'] / df_rest['total_oferecidas']

    # Remover restaurantes sem nenhuma refeição compatível
    df_rest = df_rest[df_rest['qtd_refeicoes_compativeis'] > 0]

    # Se nenhum restaurante tiver refeições compatíveis, retorna vazio
    if df_rest.empty:
        return {"id_usuario": user_id, "total_restaurantes": 0, "restaurantes_ranked": []}

    # Agregar avaliações dos pratos compatíveis por restaurante
    df_eval = df_refeicao_avaliacao[df_refeicao_avaliacao['id_refeicao'].isin(candidatos)].copy()
    if not df_eval.empty:
        # Ligar refeição -> restaurante
        df_eval = df_eval.merge(df_refeicao_restaurante, on='id_refeicao', how='left')
        # Calcular soma ponderada (nota * qtd) e total de avaliações por restaurante
        df_eval['nota_x_qtd'] = df_eval['nota_media'] * df_eval['qtd_avaliacoes']
        rest_eval = df_eval.groupby('id_restaurante').agg(
            total_avaliacoes=('qtd_avaliacoes', 'sum'),
            soma_nota_x_qtd=('nota_x_qtd', 'sum')
        ).reset_index()
        # Média ponderada por restaurante (soma(nota * qtd) / soma(qtd))
        rest_eval['media_avaliacao'] = rest_eval.apply(lambda r: (r['soma_nota_x_qtd'] / r['total_avaliacoes']) if r['total_avaliacoes'] > 0 else 0.0, axis=1)
    else:
        rest_eval = pd.DataFrame(columns=['id_restaurante', 'total_avaliacoes', 'soma_nota_x_qtd', 'media_avaliacao'])

    # Juntar métricas no dataframe de restaurantes
    df_rest = df_rest.merge(rest_eval[['id_restaurante', 'total_avaliacoes', 'media_avaliacao']], on='id_restaurante', how='left').fillna({'total_avaliacoes': 0, 'media_avaliacao': 0.0})

    # Normalizar 'media_avaliacao' e 'total_avaliacoes' para escala 0..1
    if df_rest['media_avaliacao'].max() == df_rest['media_avaliacao'].min():
        df_rest['media_avaliacao_norm'] = df_rest['media_avaliacao'].apply(lambda x: 1.0 if x > 0 else 0.0)
    else:
        min_r = df_rest['media_avaliacao'].min()
        max_r = df_rest['media_avaliacao'].max()
        df_rest['media_avaliacao_norm'] = (df_rest['media_avaliacao'] - min_r) / (max_r - min_r)

    max_rev = df_rest['total_avaliacoes'].max()
    df_rest['qtd_avaliacoes_norm'] = df_rest['total_avaliacoes'] / max_rev if max_rev > 0 else 0.0

    # Pesos conforme solicitado
    w_compat = 0.6
    w_avg = 0.2
    w_rev = 0.2

    # Pontuação composta do restaurante
    df_rest['pontuacao_composta'] = (
        df_rest['pontuacao_compat'] * w_compat
        + df_rest['media_avaliacao_norm'] * w_avg
        + df_rest['qtd_avaliacoes_norm'] * w_rev
    )

    # Preparar resposta: listar restaurantes ordenados com refeições compatíveis dentro
    df_rest = df_rest.merge(df_restaurante, on='id_restaurante', how='left')
    df_rest = df_rest.sort_values(by='pontuacao_composta', ascending=False)

    restaurantes = []
    for _, r in df_rest.iterrows():
        rid = int(r['id_restaurante'])
        # refeições compatíveis do restaurante
        meals_ids = df_refeicao_restaurante[(df_refeicao_restaurante['id_restaurante'] == rid) & (df_refeicao_restaurante['id_refeicao'].isin(candidatos))]['id_refeicao'].unique().tolist()
        meals = []
        if meals_ids:
            df_meals = df_refeicao[df_refeicao['id_refeicao'].isin(meals_ids)].merge(df_refeicao_avaliacao, on='id_refeicao', how='left')
            for _, m in df_meals.iterrows():
                meals.append({
                    'id_refeicao': int(m['id_refeicao']),
                    'nome_refeicao': m.get('nome_refeicao'),
                    'nota_media': float(m['nota_media']) if pd.notna(m.get('nota_media')) else None,
                    'qtd_avaliacoes': int(m['qtd_avaliacoes']) if pd.notna(m.get('qtd_avaliacoes')) else 0,
                    'preco': float(m['preco']) if pd.notna(m.get('preco')) else None
                })

            # ordenar refeições por nota_media desc, depois qtd
            meals = sorted(meals, key=lambda x: ((x['nota_media'] or 0), x['qtd_avaliacoes']), reverse=True)

        restaurantes.append({
            'nome_restaurante': r.get('nome_restaurante'),
            'compatibilidade_percent': round(float(r['pontuacao_compat']) * 100, 1),
            'score_final': round(float(r['pontuacao_composta']), 2),
            'qtd_refeicoes': int(r['qtd_refeicoes_compativeis']),
            'media_avaliacao': round(float(r['media_avaliacao']), 2)
        })

    return {
        'id_usuario': user_id,
        'total_restaurantes': len(restaurantes),
        'restaurantes_ranked': restaurantes
    }


# ----------------------------------------------------
# 4. EXECUÇÃO DO SERVIDOR
# ----------------------------------------------------

# Para rodar a API: uvicorn recomendador:app --reload
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)