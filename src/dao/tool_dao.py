from src.dao.base_dao import BaseDao
from src.model.tool import Tool


class ToolDao(BaseDao):
    """
    DAO for Tool model.
    """
    def __init__(self):
        super().__init__()