import json
import os

SUBSCRIBERS_FILE = os.path.join(os.path.dirname(__file__), "subscribers.json")


def _load() -> dict:
    if os.path.exists(SUBSCRIBERS_FILE):
        with open(SUBSCRIBERS_FILE, "r") as f:
            data = json.load(f)
    else:
        data = {"users": [], "groups": []}

    # 從環境變數載入預設訂閱者（逗號分隔），避免重新部署後遺失
    env_users = os.environ.get("DEFAULT_SUBSCRIBERS", "")
    for uid in env_users.split(","):
        uid = uid.strip()
        if uid and uid not in data["users"]:
            data["users"].append(uid)

    return data


def _save(data: dict):
    with open(SUBSCRIBERS_FILE, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def add_user(user_id: str):
    data = _load()
    if user_id not in data["users"]:
        data["users"].append(user_id)
        _save(data)


def remove_user(user_id: str):
    data = _load()
    if user_id in data["users"]:
        data["users"].remove(user_id)
        _save(data)


def add_group(group_id: str):
    data = _load()
    if group_id not in data["groups"]:
        data["groups"].append(group_id)
        _save(data)


def remove_group(group_id: str):
    data = _load()
    if group_id in data["groups"]:
        data["groups"].remove(group_id)
        _save(data)


def get_all_targets() -> list:
    data = _load()
    return data["users"] + data["groups"]
