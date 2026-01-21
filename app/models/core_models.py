from __future__ import annotations

from uuid import UUID, uuid4
from urllib.parse import urlparse
from pydantic import BaseModel, Field
from datetime import datetime

class AnalysisHistoryItem(BaseModel):
    date: datetime
    job_id: str  # uuid-4

    def __init__(self, **data):
        super().__init__(**data)
        UUID(self.job_id, version=4)

class Repo(BaseModel):
    repo_url: str  # url http(s)
    repo_branch: str = Field(..., max_length=50)  # max-characters: 50
    repo_token: str = Field(default=None, max_length=256) #write only, no se devuelve cuando se consulta
    repo_usr: str = "" #write only, no se devuelve cuando se consulta

    def __init__(self, **data):
        super().__init__(**data)
        parsed = urlparse(self.repo_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError(f"URL de repo inválida: {self.repo_url}")

class Module(BaseModel):
    name: str = Field(..., max_length=140)  # max-characters: 140
    description: str = Field(..., max_length=280)  # max-characters: 280
    repo: Repo
    code_analysis_history: list[AnalysisHistoryItem] = Field(default_factory=list)
    functional_analysis_history: list[AnalysisHistoryItem] = Field(default_factory=list)

class Application(BaseModel):
    project_id: str # uuid-4
    id: str = Field(default_factory=lambda: str(uuid4())) # uuid-4
    name: str = Field(..., max_length=140)  # max-characters: 140
    modules: list[Module] = Field(default_factory=list)
    summary: Summary

    def __init__(self, **data):
        super().__init__(**data)
        UUID(self.project_id, version=4)
        

class Project(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))  # uuid-4
    name: str = Field(..., max_length=140)  # max-characters: 140
    applications: list[str] = Field(default_factory=list) 
    user_id: str # uuid-4   
    
    def __init__(self, **data):
        super().__init__(**data)
        UUID(self.id, version=4)

class Summary(BaseModel):
    modules: int = 0
    externalsystems: int = 0
    technologies: int = 0