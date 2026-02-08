import json
import os
import re
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException, WebDriverException, StaleElementReferenceException

from paths import ISIS_FILES_DIR, ISIS_RESOURCES_DIR, ensure_dir


ACTIVITY_URL_RE = re.compile(r"/mod/([^/]+)/")


@dataclass
class ActivityRecord:
    index: int
    title: str
    modname: str
    url: str
    text: str
    external_urls: List[str]
    downloaded_files: List[str]
    chapters: Optional[List[Dict[str, str]]] = None


def sanitize_filename(filename: str) -> str:
    sanitized = re.sub(r"[\\/*?:\"<>|]", "", filename)
    sanitized = re.sub(r"\s+", " ", sanitized).strip()
    sanitized = re.sub(r"^(CON|PRN|AUX|NUL|COM\d|LPT\d)(\..+)?$", "_reserved_", sanitized, flags=re.I)
    if not sanitized:
        return "untitled"
    return sanitized


def _slugify(text: str, max_len: int = 80) -> str:
    text = sanitize_filename(text)
    if len(text) > max_len:
        return text[:max_len].rstrip()
    return text


def _activity_modname(url: str, fallback: str = "unknown") -> str:
    match = ACTIVITY_URL_RE.search(url or "")
    if match:
        return match.group(1)
    return fallback


def _extract_text_by_selectors(driver, selectors: Iterable[str]) -> str:
    for selector in selectors:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
        except WebDriverException:
            continue
        if not elements:
            continue
        parts = []
        for element in elements:
            text = (element.text or "").strip()
            if text:
                parts.append(text)
        if parts:
            return "\n".join(parts)
    return ""


def _extract_external_urls(driver) -> List[str]:
    urls: List[str] = []
    try:
        links = driver.find_elements(By.CSS_SELECTOR, "a[href^='http']")
    except WebDriverException:
        return urls
    for link in links:
        href = link.get_attribute("href") or ""
        if not href:
            continue
        if "isis.tu-berlin.de" in href:
            continue
        if href not in urls:
            urls.append(href)
    return urls


def _extract_file_links(driver) -> List[str]:
    links: List[str] = []
    try:
        elements = driver.find_elements(By.CSS_SELECTOR, "a[href*='pluginfile.php']")
    except WebDriverException:
        return links
    for element in elements:
        href = element.get_attribute("href") or ""
        if not href:
            continue
        if href not in links:
            links.append(href)
    return links


def _wait_for_downloads(download_dir: Path, timeout: int = 180) -> bool:
    start = time.time()
    while time.time() - start < timeout:
        try:
            entries = os.listdir(download_dir)
        except FileNotFoundError:
            entries = []
        if not any(name.endswith(".crdownload") for name in entries):
            return True
        time.sleep(1)
    return False


def _unique_destination(dest_dir: Path, filename: str) -> Path:
    dest = dest_dir / filename
    if not dest.exists():
        return dest
    stem = dest.stem
    suffix = dest.suffix
    for idx in range(1, 1000):
        candidate = dest_dir / f"{stem}_{idx}{suffix}"
        if not candidate.exists():
            return candidate
    return dest


def _move_new_downloads(download_dir: Path, dest_dir: Path, before: Set[str]) -> List[str]:
    ensure_dir(dest_dir)
    moved: List[str] = []
    try:
        after = set(os.listdir(download_dir))
    except FileNotFoundError:
        return moved
    new_files = [name for name in after if name not in before and not name.endswith(".crdownload")]
    for name in new_files:
        src = download_dir / name
        if not src.is_file():
            continue
        if src.suffix.lower() == ".zip":
            try:
                src.unlink()
            except OSError:
                pass
            continue
        dest = _unique_destination(dest_dir, name)
        src.rename(dest)
        moved.append(str(dest))
    return moved


def _open_in_new_tab(driver, url: str) -> None:
    original_handle = None
    try:
        original_handle = driver.current_window_handle
        existing_handles = set(driver.window_handles)
        driver.execute_script("window.open(arguments[0], '_blank');", url)
        time.sleep(0.2)
        handles_after = driver.window_handles
        new_handles = [h for h in handles_after if h not in existing_handles]
        if not new_handles:
            driver.get(url)
            time.sleep(1.0)
            return
        new_handle = new_handles[-1]
        driver.switch_to.window(new_handle)
        driver.get(url)
        time.sleep(1.0)
        try:
            driver.close()
        except WebDriverException:
            pass
        if original_handle and original_handle in driver.window_handles:
            driver.switch_to.window(original_handle)
    except WebDriverException:
        try:
            if original_handle and original_handle in driver.window_handles:
                driver.switch_to.window(original_handle)
            driver.get(url)
            time.sleep(1.0)
        except WebDriverException:
            pass


def _download_links(driver, links: List[str], download_dir: Path, dest_dir: Path) -> List[str]:
    if not links:
        return []
    try:
        before = set(os.listdir(download_dir))
    except FileNotFoundError:
        before = set()
    for link in links:
        _open_in_new_tab(driver, link)
    _wait_for_downloads(download_dir)
    return _move_new_downloads(download_dir, dest_dir, before)


def _collect_activity_refs(driver) -> List[Tuple[str, str, str]]:
    activities: List[Tuple[str, str, str]] = []
    try:
        container = driver.find_elements(By.CSS_SELECTOR, "#course-content, .course-content")
        roots = container if container else [driver]
    except WebDriverException:
        roots = [driver]

    seen: Set[str] = set()
    for root in roots:
        try:
            elements = root.find_elements(By.CSS_SELECTOR, "li.activity, div.activity-item")
        except WebDriverException:
            continue
        for element in elements:
            try:
                link = element.find_element(By.CSS_SELECTOR, "a.aalink, a[href*='/mod/']")
            except NoSuchElementException:
                continue
            url = link.get_attribute("href") or ""
            if not url or "/mod/" not in url:
                continue
            if url in seen:
                continue
            seen.add(url)
            title = (link.text or "").strip()
            if not title:
                try:
                    title = element.text.strip().split("\n")[0]
                except Exception:
                    title = ""
            modname = element.get_attribute("data-modname") or element.get_attribute("data-modtype") or _activity_modname(url)
            activities.append((url, title, modname))
    return activities


def _extract_book_chapters(driver) -> List[Dict[str, str]]:
    chapters: List[Dict[str, str]] = []
    try:
        toc_links = driver.find_elements(By.CSS_SELECTOR, "div.book_toc a")
    except WebDriverException:
        toc_links = []
    toc = [(link.get_attribute("href"), link.text.strip()) for link in toc_links if link.get_attribute("href")]
    seen: Set[str] = set()
    for href, title in toc:
        if href in seen:
            continue
        seen.add(href)
        try:
            driver.get(href)
        except WebDriverException:
            continue
        time.sleep(0.5)
        text = _extract_text_by_selectors(driver, [
            "div[role='main'] .book_content",
            "div[role='main'] .book-content",
            "div[role='main']",
        ])
        chapters.append({"title": title or "Chapter", "text": text})
    return chapters


def scrape_course_resources(driver, course_id: str) -> None:
    ensure_dir(ISIS_FILES_DIR)
    ensure_dir(ISIS_RESOURCES_DIR)

    course_files_dir = ISIS_FILES_DIR / str(course_id)
    ensure_dir(course_files_dir)

    course_resources_dir = ISIS_RESOURCES_DIR / str(course_id)
    ensure_dir(course_resources_dir)

    download_dir = ISIS_FILES_DIR / "_downloads"
    ensure_dir(download_dir)

    try:
        driver.get(f"https://isis.tu-berlin.de/course/view.php?id={course_id}")
        WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "li.activity, div.activity-item"))
        )
    except TimeoutException:
        pass

    activities = _collect_activity_refs(driver)
    activity_records: List[ActivityRecord] = []
    seen_file_urls: Set[str] = set()

    page_file_links = _extract_file_links(driver)
    overview_links = [link for link in page_file_links if link not in seen_file_urls]
    for link in overview_links:
        seen_file_urls.add(link)
    if overview_links:
        overview_dir = course_files_dir / "_course_page"
        _download_links(driver, overview_links, download_dir, overview_dir)

    for index, (url, title, modname) in enumerate(activities):
        try:
            driver.get(url)
        except WebDriverException:
            continue
        time.sleep(0.5)

        text = ""
        chapters = None
        if modname == "page":
            text = _extract_text_by_selectors(driver, [
                "div[role='main'] .page-content",
                "div[role='main'] .generalbox",
                "div[role='main']",
            ])
        elif modname == "book":
            chapters = _extract_book_chapters(driver)
            text = "\n".join(ch["text"] for ch in chapters if ch.get("text"))
        elif modname == "assign":
            text = _extract_text_by_selectors(driver, [
                "div[role='main'] .intro",
                "div[role='main'] .assignintro",
                "div[role='main']",
            ])
        elif modname == "forum":
            text = _extract_text_by_selectors(driver, [
                "div[role='main'] .intro",
                "div[role='main']",
            ])
        else:
            text = _extract_text_by_selectors(driver, [
                "div[role='main']",
            ])

        external_urls = _extract_external_urls(driver)

        file_links = _extract_file_links(driver)
        if modname == "resource" and not file_links:
            file_links = [url]

        new_links = [link for link in file_links if link not in seen_file_urls]
        for link in new_links:
            seen_file_urls.add(link)

        downloaded_files: List[str] = []
        if new_links:
            activity_folder = _slugify(f"{index:03d}_{title or modname}")
            dest_dir = course_files_dir / activity_folder
            moved = _download_links(driver, new_links, download_dir, dest_dir)
            downloaded_files = [str(Path(path).relative_to(ISIS_FILES_DIR)) for path in moved]

        record = ActivityRecord(
            index=index,
            title=title or modname,
            modname=modname,
            url=url,
            text=text,
            external_urls=external_urls,
            downloaded_files=downloaded_files,
            chapters=chapters,
        )
        activity_records.append(record)

    output_path = course_resources_dir / "activities.json"
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump([asdict(record) for record in activity_records], handle, ensure_ascii=False, indent=2)
