from src.dao.project_dao import ProjectDao


class ProjectService:
    def __init__(self) -> None:
        self.project_dao = ProjectDao()
