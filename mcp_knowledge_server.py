#!/usr/bin/env python3
"""MCP Knowledge Server — search local knowledge base articles via MCP protocol."""

import json
import os
import sys
from collections import Counter
from pathlib import Path

ARTICLES_DIR = Path(__file__).resolve().parent / "knowledge" / "articles"

PROTOCOL_VERSION = "2025-03-26"
SERVER_NAME = "mcp-knowledge-server"
SERVER_VERSION = "1.0.0"

_articles_cache = None


def _load_articles():
    global _articles_cache
    if _articles_cache is not None:
        return _articles_cache
    articles = []
    if not ARTICLES_DIR.is_dir():
        _articles_cache = articles
        return articles
    for fpath in sorted(ARTICLES_DIR.iterdir()):
        if fpath.suffix == ".json":
            try:
                with fpath.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                articles.append(data)
            except (json.JSONDecodeError, OSError):
                pass
    _articles_cache = articles
    return articles


def _search_articles(keyword, limit=5):
    articles = _load_articles()
    keyword_lower = keyword.lower()
    results = []
    for article in articles:
        title = article.get("title", "")
        summary = article.get("summary", "")
        tags = article.get("tags", [])
        if (keyword_lower in title.lower()
                or keyword_lower in summary.lower()
                or any(keyword_lower in t.lower() for t in tags)):
            results.append(article)
    results.sort(key=lambda a: a.get("analysis", {}).get("score", 0), reverse=True)
    return results[:limit]


def _get_article(article_id):
    articles = _load_articles()
    for article in articles:
        if article.get("id") == article_id:
            return article
    return None


def _knowledge_stats():
    articles = _load_articles()
    total = len(articles)
    source_counter = Counter()
    tag_counter = Counter()
    for article in articles:
        source = article.get("source_platform", "unknown")
        source_counter[source] += 1
        for tag in article.get("tags", []):
            tag_counter[tag] += 1
    return {
        "total_articles": total,
        "source_distribution": dict(source_counter),
        "top_tags": tag_counter.most_common(10),
    }


def _build_tool_list():
    return [
        {
            "name": "search_articles",
            "description": "Search articles by keyword in title, summary, and tags",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "keyword": {
                        "type": "string",
                        "description": "Keyword to search for",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results",
                        "default": 5,
                    },
                },
                "required": ["keyword"],
            },
        },
        {
            "name": "get_article",
            "description": "Get full article content by its ID",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "article_id": {
                        "type": "string",
                        "description": "Article ID",
                    },
                },
                "required": ["article_id"],
            },
        },
        {
            "name": "knowledge_stats",
            "description": "Return knowledge base statistics",
            "inputSchema": {
                "type": "object",
                "properties": {},
            },
        },
    ]


def _handle_initialize(params):
    return {
        "protocolVersion": PROTOCOL_VERSION,
        "capabilities": {
            "tools": {},
        },
        "serverInfo": {
            "name": SERVER_NAME,
            "version": SERVER_VERSION,
        },
    }


def _handle_tools_list(params):
    return {"tools": _build_tool_list()}


def _handle_tools_call(params):
    name = params.get("name", "")
    arguments = params.get("arguments", {})

    if name == "search_articles":
        keyword = arguments.get("keyword", "")
        limit = arguments.get("limit", 5)
        if not keyword:
            return {"content": [{"type": "text", "text": "keyword is required"}]}
        results = _search_articles(keyword, limit)
        return {"content": [{"type": "text", "text": json.dumps(results, ensure_ascii=False, indent=2)}]}

    elif name == "get_article":
        article_id = arguments.get("article_id", "")
        if not article_id:
            return {"content": [{"type": "text", "text": "article_id is required"}]}
        article = _get_article(article_id)
        if article is None:
            return {"content": [{"type": "text", "text": f"Article not found: {article_id}"}]}
        return {"content": [{"type": "text", "text": json.dumps(article, ensure_ascii=False, indent=2)}]}

    elif name == "knowledge_stats":
        stats = _knowledge_stats()
        return {"content": [{"type": "text", "text": json.dumps(stats, ensure_ascii=False, indent=2)}]}

    else:
        raise ValueError(f"Unknown tool: {name}")


_METHOD_HANDLERS = {
    "initialize": _handle_initialize,
    "tools/list": _handle_tools_list,
    "tools/call": _handle_tools_call,
}


def _read_message():
    line = sys.stdin.readline()
    if not line:
        return None
    return json.loads(line)


def _write_message(msg):
    data = json.dumps(msg, ensure_ascii=False)
    sys.stdout.write(data + "\n")
    sys.stdout.flush()


def _make_error(id, code, message):
    return {"jsonrpc": "2.0", "id": id, "error": {"code": code, "message": message}}


def _make_success(id, result):
    return {"jsonrpc": "2.0", "id": id, "result": result}


def main():
    while True:
        try:
            req = _read_message()
            if req is None:
                break
        except (json.JSONDecodeError, EOFError):
            break

        req_id = req.get("id")
        method = req.get("method", "")
        params = req.get("params", {})

        handler = _METHOD_HANDLERS.get(method)
        if handler is None:
            _write_message(_make_error(req_id, -32601, f"Method not found: {method}"))
            continue

        try:
            result = handler(params)
            _write_message(_make_success(req_id, result))
        except Exception as e:
            _write_message(_make_error(req_id, -32603, str(e)))


if __name__ == "__main__":
    main()
