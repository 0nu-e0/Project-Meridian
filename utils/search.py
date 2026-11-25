# -----------------------------------------------------------------------------
# Project Meridian
# Copyright (c) 2025 Jereme Shaver
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
# -----------------------------------------------------------------------------
# File: search.py
# Description: Search across tasks, projects, notes, and mind maps. Every word
#              typed must appear somewhere in an item; matches in the title rank
#              above matches in the body.
# Author: Jereme Shaver
# -----------------------------------------------------------------------------

import html
import re
from dataclasses import dataclass, field

TASK, PROJECT, NOTE, MINDMAP = "task", "project", "note", "mindmap"
KIND_ORDER = [TASK, PROJECT, NOTE, MINDMAP]
KIND_LABELS = {TASK: "Tasks", PROJECT: "Projects", NOTE: "Notes", MINDMAP: "Mind maps"}
PER_KIND_LIMIT = 6
SNIPPET_WIDTH = 90


@dataclass
class Result:
    kind: str
    id: str
    title: str
    detail: str = ""  # what it is (category, status...) or the text around the match
    score: int = 0
    extra: dict = field(default_factory=dict)  # e.g. the matching mind map shape


def words_of(query):
    return [word for word in query.lower().split() if word]


def score(words, title, body):
    """None if any word is missing; otherwise higher for better matches"""
    title_l, body_l = title.lower(), body.lower()
    if not all(word in title_l or word in body_l for word in words):
        return None
    value = 0
    phrase = " ".join(words)
    if title_l.startswith(phrase):
        value += 100
    elif phrase in title_l:
        value += 60
    value += sum(30 for word in words if word in title_l)
    value += sum(5 for word in words if word in body_l)
    return value


def snippet(body, words, width=SNIPPET_WIDTH):
    """The bit of body around the first word found, on one line"""
    flat = " ".join(body.split())
    lower = flat.lower()
    hits = [lower.find(word) for word in words if lower.find(word) >= 0]
    if not hits:
        return ""
    start = max(0, min(hits) - width // 3)
    text = flat[start:start + width]
    return ("…" if start > 0 else "") + text + ("…" if start + width < len(flat) else "")


def html_to_text(content):
    """Plain text from a note's rich text (drops the style block and tags)"""
    content = re.sub(r"(?is)<head.*?</head>", " ", content or "")
    content = re.sub(r"(?is)<(br|/p|/div|/li)[^>]*>", "\n", content)
    return html.unescape(re.sub(r"<[^>]+>", " ", content))


def _detail(words, title, fields, fallback):
    """Show where the words matched if not all of them are in the title. fields are the
    separate texts searched (description, comments...); the snippet comes from one of them."""
    if all(word in title.lower() for word in words):
        return fallback
    for text in fields:
        if any(word in text.lower() for word in words):
            return snippet(text, words) or fallback
    return fallback


def search_everything(query, logger, per_kind=PER_KIND_LIMIT):
    """Results for query across all kinds, best first within each kind"""
    words = words_of(query)
    if not words:
        return []
    results = []
    for finder in (_tasks, _projects, _notes, _mindmaps):
        try:
            found = sorted(finder(words, logger), key=lambda r: -r.score)
        except Exception as e:  # one unreadable file shouldn't stop the rest
            logger.error(f"Search couldn't read {finder.__name__.strip('_')}: {e}")
            continue
        results.extend(found[:per_kind])
    return results


def _tasks(words, logger):
    from ui.custom_widgets.rich_text import description_plain_text
    from utils.tasks_io import load_tasks_from_json
    for task in load_tasks_from_json(logger).values():
        comments = [entry.content for entry in getattr(task, "entries", []) or []]
        fields = [description_plain_text(task), *comments, task.category_name or "", task.assignee or ""]
        value = score(words, task.title, "\n".join(fields))
        if value is not None:
            status = "Archived" if getattr(task, "archived", False) else task.status.value
            yield Result(TASK, task.id, task.title, _detail(words, task.title, fields,
                                                             f"{task.category_name}  ·  {status}"), value)


def _projects(words, logger):
    from utils.projects_io import load_projects_from_json
    for project in load_projects_from_json(logger).values():
        body = getattr(project, "description", "") or ""
        value = score(words, project.title, body)
        if value is not None:
            yield Result(PROJECT, project.id, project.title, _detail(words, project.title, [body], "Project"), value)


def _notes(words, logger):
    from utils.notes_io import load_notes_from_json
    for note_id, note in (load_notes_from_json(logger) or {}).items():
        title = note.get("title") or "Untitled"
        body = html_to_text(note.get("content", ""))
        value = score(words, title, body)
        if value is not None:
            yield Result(NOTE, note_id, title, _detail(words, title, [body], "Note"), value)


def _mindmaps(words, logger):
    from utils.mindmap_io import load_mindmaps_from_json
    for mindmap in load_mindmaps_from_json(logger).values():
        texts = [(node.get("id"), node.get("text") or node.get("title") or "") for node in mindmap.nodes or []]
        texts += [(None, line.get("label", "")) for line in mindmap.connections or [] if line.get("label")]
        body = " ".join(text for _, text in texts)
        value = score(words, mindmap.title, body)
        if value is None:
            continue
        # The shape to show: the first one holding a searched word
        node_id = next((nid for nid, text in texts if any(word in text.lower() for word in words)), None)
        count = sum(1 for node in mindmap.nodes or [] if node.get("kind") != "frame")
        yield Result(MINDMAP, mindmap.id, mindmap.title,
                     _detail(words, mindmap.title, [text for _, text in texts], f"{count} shape{'s' if count != 1 else ''}"),
                     value, {"node_id": node_id})
