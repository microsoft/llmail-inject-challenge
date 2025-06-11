import base64
from datetime import datetime
from dataclasses import dataclass, asdict, field
import json
import uuid


@dataclass
class User:
    login: str
    api_key: str = field(default_factory=lambda: str(uuid.uuid4()))
    team: str | None = None
    role: str = "competitor"
    blocked: bool = False

    __api_fields__ = ["login", "team", "role", "blocked"]

    def partition_key(self):
        return self.login

    def row_key(self):
        return self.login

    def rotate_auth_token(self):
        self.api_key = str(uuid.uuid4())

    def auth_token(self) -> str:
        content = json.dumps(
            {
                "login": self.login,
                "api_key": self.api_key,
            }
        )

        return base64.b64encode(content.encode("utf-8")).decode("utf-8")

    @staticmethod
    def from_auth_token(token: str) -> "User":
        content = base64.b64decode(token.encode("utf-8")).decode("utf-8")
        data = json.loads(content)

        return User(**data)
