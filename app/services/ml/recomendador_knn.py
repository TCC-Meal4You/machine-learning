import pandas as pd
from sklearn.neighbors import NearestNeighbors
import numpy as np

class KNNRecommender:
    def __init__(self, k_neighbors: int):
        """
        Inicializa o wrapper do NearestNeighbors.
        Métrica deve ser cosine e algoritmo brute.
        """
        self.k_neighbors = k_neighbors
        self.model = NearestNeighbors(n_neighbors=self.k_neighbors, metric='cosine', algorithm='brute')
        self.matrix: pd.DataFrame = None

    def fit(self, matrix: pd.DataFrame):
        """
        Carrega a matriz para a memória e treina o modelo.
        """
        self.matrix = matrix
        if not self.matrix.empty:
            # O Numpy Array extraído do DataFrame será mantido na memória (Stateless para a execução atual)
            self.model.fit(self.matrix.values)

    def get_neighbors(self, user_id: int, k=None) -> list[int]:
        """
        Retorna uma lista contendo os IDs dos usuários mais similares.
        """
        if self.matrix is None or self.matrix.empty:
            return []
            
        if user_id not in self.matrix.index:
            # Caso o usuário nunca tenha avaliado antes (Cold Start)
            return []
            
        k_val = k if k is not None else self.k_neighbors
        
        # Consideramos buscar (k+1) porque a própria distância pro usuário alvo entrará como primeira
        n_neighbors_to_fetch = min(k_val + 1, len(self.matrix))
        if n_neighbors_to_fetch == 0:
            return []
            
        # Pega a feature row do usuário alvo
        user_index = self.matrix.index.get_loc(user_id)
        user_features = self.matrix.iloc[user_index, :].values.reshape(1, -1)
        
        distances, indices = self.model.kneighbors(user_features, n_neighbors=n_neighbors_to_fetch)
        
        # Remapeia o índice do numpy para o 'id_usuario' da matriz pandas
        neighbors_ids = []
        for idx in indices.flatten():
            n_id = self.matrix.index[idx]
            if n_id != user_id:
                neighbors_ids.append(int(n_id))
                
        return neighbors_ids[:k_val]
