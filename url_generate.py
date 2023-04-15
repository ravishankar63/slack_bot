import os
from typing import Optional

def url_generate(state: str, redirect_uri: Optional[str] = None, team: Optional[str] = None) -> str:
    url = (
        f"{os.environ['tyke_url']}?"
        f"state={state}"
    )
    if redirect_uri is not None:
        url += f"&redirect_uri={redirect_uri}"
    if team is not None:
        url += f"&team={team}"
    return url