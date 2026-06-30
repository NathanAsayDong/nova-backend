from src.dao.base_dao import BaseDao
from src.model.responsibility import Responsibility


class ResponsibilityDao(BaseDao):
    """
    DAO for Responsibility model.
    """
    def __init__(self):
        super().__init__()