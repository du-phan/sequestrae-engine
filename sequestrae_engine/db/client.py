import os
from typing import Optional

from supabase import Client, create_client


class SupabaseClient:
    _instance: Optional[Client] = None

    @classmethod
    def get_client(cls, project_url: str = None, api_key: str = None) -> Client:
        if cls._instance is None:
            project_url = project_url or os.getenv("SUPABASE_PROJECT_URL")
            api_key = api_key or os.getenv("SUPABASE_API_KEY")

            if not project_url or not api_key:
                raise ValueError("Missing Supabase credentials")

            cls._instance = create_client(project_url, api_key)
        return cls._instance
