import pandas as pd
import numpy as np

# --- DEFINIÇÕES GERAIS ---
# Definindo as entidades base (para as chaves primárias)
NUM_USUARIOS = 5
NUM_REFEICOES = 10
NUM_INGREDIENTES = 20
NUM_RESTRICOES = 5
RESTRICOES_NOMES = ['Lactose', 'Glúten', 'Nozes', 'Ovo', 'Carne_Bovina']

# --- 1. TABELAS DE DOMÍNIO/BASE ---

# 1.1 tb_restricoes
df_restricoes = pd.DataFrame({
    'id_restricao': range(1, NUM_RESTRICOES + 1),
    'nome_restricao': RESTRICOES_NOMES
})

# 1.2 tb_usuario
df_usuario = pd.DataFrame({
    'id_usuario': range(1000, 1000 + NUM_USUARIOS),
    'nome_usuario': [f'Cliente_{i}' for i in range(1, NUM_USUARIOS + 1)]
})

# 1.3 tb_ingredientes
df_ingredientes = pd.DataFrame({
    'id_ingrediente': range(100, 100 + NUM_INGREDIENTES),
    'nome_ingrediente': [f'Ingrediente_{i}' for i in range(1, NUM_INGREDIENTES + 1)]
})

# 1.4 tb_refeicao (Simplificada, sem restaurante)
df_refeicao = pd.DataFrame({
    'id_refeicao': range(500, 500 + NUM_REFEICOES),
    'nome_refeicao': [f'Prato_A{i}' for i in range(1, NUM_REFEICOES + 1)],
    'preco': np.round(np.random.uniform(20.0, 80.0, NUM_REFEICOES), 2)
})

# --- 2. TABELAS DE RELACIONAMENTO (N:N) PARA FILTRAGEM ---

# 2.1 tb_restricoes_usuario
# Simula que cada usuário tem entre 0 e 3 restrições.
dados_usuario_restricao = []
for user_id in df_usuario['id_usuario']:
    # Escolhe um número aleatório de restrições para o usuário
    num_restricoes = np.random.randint(0, 4)
    # Escolhe as IDs de restrição aleatoriamente sem repetição
    restricoes_escolhidas = np.random.choice(df_restricoes['id_restricao'], num_restricoes, replace=False)
    for res_id in restricoes_escolhidas:
        dados_usuario_restricao.append({'id_usuario': user_id, 'id_restricao': res_id})

df_restricoes_usuario = pd.DataFrame(dados_usuario_restricao)

# 2.2 tb_ingredientes_restricoes
# Simula quais restrições estão presentes em cada ingrediente.
# Assumimos que a maioria dos ingredientes tem 0 ou 1 restrição.
dados_ingrediente_restricao = []
for ing_id in df_ingredientes['id_ingrediente']:
    # 70% de chance de ter 0 ou 1 restrição.
    num_restricoes = np.random.choice([0, 1, 2], p=[0.4, 0.4, 0.2])
    
    restricoes_escolhidas = np.random.choice(df_restricoes['id_restricao'], num_restricoes, replace=False)
    for res_id in restricoes_escolhidas:
        dados_ingrediente_restricao.append({'id_ingrediente': ing_id, 'id_restricao': res_id})

df_ingrediente_restricao = pd.DataFrame(dados_ingrediente_restricao).drop_duplicates()

# 2.3 tb_refeicao_ingrediente
# Simula a composição das refeições (cada refeição tem 2 a 5 ingredientes).
dados_refeicao_ingrediente = []
for ref_id in df_refeicao['id_refeicao']:
    num_ingredientes = np.random.randint(2, 6)
    ingredientes_escolhidos = np.random.choice(df_ingredientes['id_ingrediente'], num_ingredientes, replace=False)
    for ing_id in ingredientes_escolhidos:
        dados_refeicao_ingrediente.append({'id_refeicao': ref_id, 'id_ingrediente': ing_id})

df_refeicao_ingrediente = pd.DataFrame(dados_refeicao_ingrediente).drop_duplicates()


# --- EXPORTAR PARA CSV ---

dfs_para_exportar = {
    'tb_usuario.csv': df_usuario,
    'tb_restricoes.csv': df_restricoes,
    'tb_ingredientes.csv': df_ingredientes,
    'tb_refeicao.csv': df_refeicao,
    'tb_restricoes_usuario.csv': df_restricoes_usuario,
    'tb_ingredientes_restricoes.csv': df_ingrediente_restricao,
    'tb_refeicao_ingrediente.csv': df_refeicao_ingrediente
}

# Salvar todos os DataFrames como arquivos CSV
for nome_arquivo, df in dfs_para_exportar.items():
    df.to_csv(nome_arquivo, index=False)
    print(f"Arquivo '{nome_arquivo}' criado com sucesso.")