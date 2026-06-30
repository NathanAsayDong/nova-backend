from src.dao.responsibility_dao import ResponsibilityDao


class ResponsibilityService:
    def __init__(self) -> None:
        self.responsibility_dao = ResponsibilityDao()
