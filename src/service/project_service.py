from src.dao.project_dao import ProjectDao
from src.model.project import Project


class ProjectService:
    """
    CRUD over projects.

    The mutating methods take plain scalars and return JSON-serializable
    dicts so they can be registered directly as agent tools (the tool layer
    json-dumps whatever comes back).
    """

    def __init__(self) -> None:
        self.project_dao = ProjectDao()

    @staticmethod
    def _to_dict(project: Project) -> dict:
        return {"id": project.id, **project.to_payload()}

    def get_all_projects(self) -> list[Project]:
        return self.project_dao.get_all()

    def get_project(self, id: int) -> Project | None:
        return self.project_dao.get(id)

    def create_project(self, name: str, description: str | None = None) -> dict:
        name = (name or "").strip()
        if not name:
            raise ValueError("A project name is required.")
        project = self.project_dao.create(Project(name=name, description=description))
        return self._to_dict(project)

    def update_project(
        self,
        project_id: int,
        name: str | None = None,
        description: str | None = None,
    ) -> dict:
        project = self.project_dao.get(int(project_id))
        if project is None:
            raise ValueError(f"Project {project_id} does not exist.")

        if name is not None:
            name = name.strip()
            if not name:
                raise ValueError("A project name cannot be blank.")
            project.name = name
        if description is not None:
            project.description = description

        updated = self.project_dao.update(project.id, project)
        if updated is None:
            raise ValueError(f"Project {project_id} could not be updated.")
        return self._to_dict(updated)

    def list_projects(self) -> list[dict]:
        return [self._to_dict(project) for project in self.project_dao.get_all()]

    def delete_project(self, id: int) -> None:
        self.project_dao.delete(int(id))
