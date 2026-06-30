from src.dao.tool_dao import ToolDao


class ToolService:
    def __init__(self) -> None:
        self.tool_dao = ToolDao()
