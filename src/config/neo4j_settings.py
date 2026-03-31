from pydantic import BaseModel, SecretStr


class Neo4jSettings(BaseModel):
    uri: str
    user: str
    password: SecretStr
    embedding_dim: int
    vector_search_threshold: float

    @property
    def password_value(self) -> str:
        return self.password.get_secret_value()
