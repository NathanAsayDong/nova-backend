from src.dao.base_dao import BaseDao
from src.model.project import Project


class ProjectDao(BaseDao):
    """
    DAO for Project model.
    """
    def __init__(self):
        super().__init__()
