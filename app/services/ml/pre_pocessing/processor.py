import pandas as pd

def create_user_restaurant_matrix(data: list[dict]) -> pd.DataFrame:
    """
    Pivot: cria matriz de usuários vs restaurantes usando as notas como valores.
    """
    if not data:
        return pd.DataFrame()
        
    df = pd.DataFrame(data)
    
    # Valida presença das colunas essenciais
    if not all(col in df.columns for col in ['id_usuario', 'id_restaurante', 'nota']):
        raise ValueError("Dados insuficientes: faltando id_usuario, id_restaurante ou nota")
        
    # pivot_table no lugar de pivot para tratar registros possivelmente duplicados fazendo mean()
    matrix = df.pivot_table(index='id_usuario', columns='id_restaurante', values='nota', aggfunc='mean')
    
    # Preenche valores nulos com 0 conforme a Task 3.1
    matrix = matrix.fillna(0)
    return matrix


def create_user_meal_matrix(data: list[dict]) -> pd.DataFrame:
    """
    Pivot: cria matriz de usuários vs refeições usando as notas como valores.
    """
    if not data:
        return pd.DataFrame()
        
    df = pd.DataFrame(data)
    
    if not all(col in df.columns for col in ['id_usuario', 'id_refeicao', 'nota']):
        raise ValueError("Dados insuficientes: faltando id_usuario, id_refeicao ou nota")
        
    # pivot_table no lugar de pivot
    matrix = df.pivot_table(index='id_usuario', columns='id_refeicao', values='nota', aggfunc='mean')
    
    # Preenche valores nulos com 0 conforme a Task 3.1
    matrix = matrix.fillna(0)
    return matrix
