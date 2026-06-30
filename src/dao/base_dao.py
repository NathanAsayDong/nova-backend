import os

from supabase import Client, create_client

class BaseDao:
    """
    Base class for all DAOs.
    """
    def __init__(self):
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        if not url or not key:
            raise Exception("Missing SUPABASE_URL or SUPABASE_KEY environment variable")
        self.supabase = create_client(url, key)

    @property
    def client(self) -> Client:
        return self.supabase
