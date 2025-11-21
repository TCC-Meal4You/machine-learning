from typing import Optional
from sqlmodel import Field, SQLModel
from datetime import date
from decimal import Decimal

# --- TABELAS INDEPENDENTES OU DE ADMINISTRAÇÃO ---

class AdministradorRestaurante(SQLModel, table=True):
    __tablename__ = "administrador_restaurante"
    id_admin: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(max_length=200, unique=True)
    nome: str = Field(max_length=150)
    senha: Optional[str] = Field(default=None, max_length=60)

class Usuario(SQLModel, table=True):
    __tablename__ = "usuario"
    id_usuario: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(max_length=200, unique=True)
    nome: str = Field(max_length=150)
    senha: Optional[str] = Field(default=None, max_length=60)

class Restricao(SQLModel, table=True):
    __tablename__ = "restricao"
    id_restricao: Optional[int] = Field(default=None, primary_key=True)
    tipo: str = Field(max_length=100, unique=True)

# --- TABELAS PRINCIPAIS DE NEGÓCIO ---

class Restaurante(SQLModel, table=True):
    __tablename__ = "restaurante"
    id_restaurante: Optional[int] = Field(default=None, primary_key=True)
    ativo: bool # Mapeamento de BIT(1)
    bairro: str = Field(max_length=60)
    cep: str = Field(max_length=8)
    cidade: str = Field(max_length=60)
    complemento: Optional[str] = Field(default=None, max_length=30)
    descricao: str = Field(max_length=200)
    logradouro: str = Field(max_length=200)
    nome: str = Field(max_length=120)
    numero: int
    tipo_comida: str = Field(max_length=100)
    uf: str = Field(max_length=2)
    id_admin: int = Field(foreign_key="administrador_restaurante.id_admin")

class Ingrediente(SQLModel, table=True):
    __tablename__ = "ingrediente"
    id_ingrediente: Optional[int] = Field(default=None, primary_key=True)
    nome: str = Field(max_length=150)
    id_admin: int = Field(foreign_key="administrador_restaurante.id_admin")

class Refeicao(SQLModel, table=True):
    __tablename__ = "refeicao"
    id_refeicao: Optional[int] = Field(default=None, primary_key=True)
    descricao: Optional[str] = None # TEXT no MySQL pode ser str sem limite definido no Field
    disponivel: bool # Mapeamento de BIT(1)
    nome: str = Field(max_length=120)
    preco: Decimal = Field(max_digits=10, decimal_places=2)
    tipo: Optional[str] = Field(default=None, max_length=100)
    id_restaurante: int = Field(foreign_key="restaurante.id_restaurante")

class SocialLogin(SQLModel, table=True):
    __tablename__ = "social_login"
    id: Optional[int] = Field(default=None, primary_key=True)
    provider: str = Field(max_length=255)
    provider_id: str = Field(max_length=255)
    id_adm: Optional[int] = Field(default=None, foreign_key="administrador_restaurante.id_admin")
    id_usuario: Optional[int] = Field(default=None, foreign_key="usuario.id_usuario")

# --- TABELAS DE RELACIONAMENTO (JOIN TABLES) ---
# Todas usam chaves primárias compostas (ambos os campos são PK)

class IngredienteRestricao(SQLModel, table=True):
    __tablename__ = "ingrediente_restricao"
    id_ingrediente: int = Field(foreign_key="ingrediente.id_ingrediente", primary_key=True)
    id_restricao: int = Field(foreign_key="restricao.id_restricao", primary_key=True)

class RefeicaoIngrediente(SQLModel, table=True):
    __tablename__ = "refeicao_ingrediente"
    id_ingrediente: int = Field(foreign_key="ingrediente.id_ingrediente", primary_key=True)
    id_refeicao: int = Field(foreign_key="refeicao.id_refeicao", primary_key=True)

class RestauranteFavorito(SQLModel, table=True):
    __tablename__ = "restaurante_favorito"
    id_restaurante: int = Field(foreign_key="restaurante.id_restaurante", primary_key=True)
    id_usuario: int = Field(foreign_key="usuario.id_usuario", primary_key=True)

class UsuarioRestricao(SQLModel, table=True):
    __tablename__ = "usuario_restricao"
    id_restricao: int = Field(foreign_key="restricao.id_restricao", primary_key=True)
    id_usuario: int = Field(foreign_key="usuario.id_usuario", primary_key=True)

# --- TABELA CRUCIAL PARA O PASSO 2 (ML Colaborativo) ---

class UsuarioAvalia(SQLModel, table=True):
    __tablename__ = "usuario_avalia"
    id_restaurante: int = Field(foreign_key="restaurante.id_restaurante", primary_key=True)
    id_usuario: int = Field(foreign_key="usuario.id_usuario", primary_key=True)
    nota: int
    comentario: str = Field(max_length=255)
    data_avaliacao: date