import json
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _resolve_env_path(var_name, default_path):
    value = os.environ.get(var_name)
    if not value:
        return default_path
    path = Path(value)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path


DATA_DIR = _resolve_env_path("CRAWLER_DATA_DIR", PROJECT_ROOT / "rag" / "crawler" / "data")

ISIS_DIR = DATA_DIR / "isis"
ISIS_META_DIR = ISIS_DIR / "meta"
ISIS_COURSE_INFOS_DIR = ISIS_DIR / "course_infos"
ISIS_FORUMS_DIR = ISIS_DIR / "forums"
ISIS_FORUM_DATA_DIR = ISIS_FORUMS_DIR / "course_forum_data"
ISIS_PDFS_DIR = ISIS_DIR / "pdfs"
ISIS_VIDEOS_DIR = ISIS_DIR / "videos"
ISIS_COURSE_ID_MANAGER_DIR = ISIS_META_DIR / "course_id_manager"

MOSES_DIR = DATA_DIR / "moses"
MOSES_META_DIR = MOSES_DIR / "meta"
MOSES_COURSE_INFOS_DIR = MOSES_DIR / "course_infos"

ISIS_COURSE_ID_FILE = ISIS_META_DIR / "course_id_saved.json"
ISIS_FORUM_ID_FILE = ISIS_META_DIR / "forum_id_saved.json"
ISIS_DOWNLOAD_LOG_FILE = ISIS_META_DIR / "download_log.json"
ISIS_FAILED_HREFS_FILE = ISIS_META_DIR / "failed_hrefs.json"
ISIS_UPLOAD_LOG_FILE = ISIS_META_DIR / "upload_log.txt"
MOSES_COURSE_ID_FILE = MOSES_META_DIR / "course_id_saved_moses.json"
ISIS_ALL_COURSE_IDS_FILE = ISIS_COURSE_ID_MANAGER_DIR / "all_course_ids.json"
ISIS_ALL_ACCESSIBLE_COURSES_FILE = ISIS_COURSE_ID_MANAGER_DIR / "all_accessible_courses.json"
ISIS_ALL_COURSE_IDS_HTML = ISIS_COURSE_ID_MANAGER_DIR / "all_course_IDs.html"
ISIS_MY_COURSE_IDS_FILE = ISIS_COURSE_ID_MANAGER_DIR / "my_course_ids.json"



def ensure_dir(path):
    Path(path).mkdir(parents=True, exist_ok=True)



def ensure_json_file(path, default=None):
    path = Path(path)
    ensure_dir(path.parent)
    if path.exists():
        return
    if default is None:
        default = []
    with path.open("w", encoding="utf-8") as file:
        json.dump(default, file)



def ensure_text_file(path, default=""):
    path = Path(path)
    ensure_dir(path.parent)
    if path.exists():
        return
    path.write_text(default, encoding="utf-8")
