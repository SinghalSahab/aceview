import os
from supabase import create_client, Client


SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SECRET_KEY = os.environ[
    "SUPABASE_SECRET_KEY"
]

supabase: Client = create_client(
    SUPABASE_URL,
    SUPABASE_SECRET_KEY
)