from pydantic import BaseModel
from models.core_models import Project


class ProjectWithUserResponse(BaseModel):
    project: Project
    user_email: str = ""
    user_full_name: str = ""
