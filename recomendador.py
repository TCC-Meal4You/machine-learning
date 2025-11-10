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
    # Arquivos adicionais para mapeamento de restrições e ingredientes
    df_restricoes = pd.read_csv(os.path.join(CAMINHO_PASTA_CSVS, 'tb_restricoes.csv'))
    df_ingredientes = pd.read_csv(os.path.join(CAMINHO_PASTA_CSVS, 'tb_ingredientes.csv'))
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


# ----------------------------------------------------
# 4. EXECUÇÃO DO SERVIDOR
# ----------------------------------------------------

# Para rodar a API: uvicorn recommender_api:app --reload
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)