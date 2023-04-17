import os
from typing import Optional
from dotenv import load_dotenv
load_dotenv()

def url_generate(state: Optional[str] = None, redirect_uri: Optional[str] = None, team_id: Optional[str] = None, user_id: Optional[str] = None) -> str:
    url = (
        f"{os.environ['TYKE_UI']}/slack/oauth?"
        f"source=slack"
        f"&redirect_uri={redirect_uri}"
        f"&user={user_id}"
    )
    # if redirect_uri is not None:
    #     url += f"&redirect_uri={redirect_uri}"
    # if team is not None:
    #     url += f"&team={team}"
    return url