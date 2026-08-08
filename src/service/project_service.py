from src.dao.conversation_dao import ConversationDao
from src.dao.memory_chunk_dao import MemoryChunkDao
from src.dao.message_dao import MessageDao
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
        self.conversation_dao = ConversationDao()
        self.memory_chunk_dao = MemoryChunkDao()
        self.message_dao = MessageDao()

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

    def delete_project(self, project_id: int, force: bool = False) -> dict:
        """
        Delete a project and everything under it.

        The project fk cascades, so this also destroys the project's
        conversations, those conversations' messages, and its memory chunks —
        permanently. Deleting a project that still has dependents is therefore
        refused unless force is set, so the model has to report the blast
        radius to the user and get a yes before anything is destroyed.
        """
        project = self.project_dao.get(int(project_id))
        if project is None:
            raise ValueError(f"Project {project_id} does not exist.")

        conversations = self.conversation_dao.get_by_project(project.id)
        message_count = self.message_dao.count_for_conversations(
            [conversation.uuid for conversation in conversations]
        )
        memory_chunk_count = self.memory_chunk_dao.count_for_project(project.id)

        if (conversations or memory_chunk_count) and not force:
            raise ValueError(
                f"Project {project.id} ('{project.name}') still has "
                f"{len(conversations)} conversation(s), {message_count} message(s), "
                f"and {memory_chunk_count} memory chunk(s) attached. Deleting the "
                "project permanently deletes all of them (the database cascades). "
                "Report exactly this to the user and get explicit confirmation "
                "first, then retry with force set to true."
            )

        # Cascading fks handle conversations, messages, and memory chunks.
        self.project_dao.delete(project.id)

        return {
            "status": "deleted",
            "project": self._to_dict(project),
            "cascade_deleted": {
                "conversations": len(conversations),
                "messages": message_count,
                "memory_chunks": memory_chunk_count,
            },
        }
