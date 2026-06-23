import os

from dotenv import load_dotenv
from notion_client import Client

load_dotenv()

_NOTION_MAX_TEXT_LEN = 2000
_NOTION_MAX_CHILDREN = 100

# Notion code 블록이 허용하는 language 값 (공식 목록)
_NOTION_CODE_LANGUAGES = {
    "abap", "abc", "agda", "arduino", "ascii art", "assembly", "bash", "basic",
    "bnf", "c", "c#", "c++", "clojure", "coffeescript", "coq", "css", "dart",
    "dhall", "diff", "docker", "ebnf", "elixir", "elm", "erlang", "f#", "flow",
    "fortran", "gherkin", "glsl", "go", "graphql", "groovy", "haskell", "hcl",
    "html", "idris", "java", "javascript", "json", "julia", "kotlin", "latex",
    "less", "lisp", "livescript", "llvm ir", "lua", "makefile", "markdown",
    "markup", "matlab", "mathematica", "mermaid", "nix", "notion formula",
    "objective-c", "ocaml", "pascal", "perl", "php", "plain text", "powershell",
    "prolog", "protobuf", "purescript", "python", "r", "racket", "reason",
    "ruby", "rust", "sass", "scala", "scheme", "scss", "shell", "smalltalk",
    "solidity", "sql", "swift", "toml", "typescript", "vb.net", "verilog",
    "vhdl", "visual basic", "webassembly", "xml", "yaml", "java/c/c++/c#",
}

# 흔한 별칭 → Notion 정식 명칭
_LANGUAGE_ALIASES = {
    "js": "javascript",
    "jsx": "javascript",
    "ts": "typescript",
    "tsx": "typescript",
    "node": "javascript",
    "py": "python",
    "py3": "python",
    "sh": "shell",
    "zsh": "shell",
    "console": "shell",
    "bash": "bash",
    "shell-session": "shell",
    "yml": "yaml",
    "text": "plain text",
    "txt": "plain text",
    "plaintext": "plain text",
    "dockerfile": "docker",
    "golang": "go",
    "rb": "ruby",
    "rs": "rust",
    "kt": "kotlin",
    "objc": "objective-c",
    "htm": "html",
    "vue": "html",
    "md": "markdown",
    "c++": "c++",
    "cpp": "c++",
    "cs": "c#",
    "csharp": "c#",
    "psql": "sql",
    "postgres": "sql",
    "postgresql": "sql",
    "mysql": "sql",
    "env": "bash",
    "dotenv": "bash",
}


def _normalize_language(raw: str) -> str:
    """코드펜스 언어 태그를 Notion이 허용하는 값으로 정규화해요."""
    lang = raw.strip().lower()
    if not lang:
        return "plain text"
    lang = _LANGUAGE_ALIASES.get(lang, lang)
    return lang if lang in _NOTION_CODE_LANGUAGES else "plain text"


def _make_client() -> Client:
    return Client(auth=os.environ["NOTION_API_KEY"])


def create_blog_page(topic_page_id: str, title: str, content_md: str) -> str:
    """블로그 글을 Notion 페이지로 저장하고 URL을 반환해요."""
    client = _make_client()
    blocks = _md_to_blocks(content_md)
    first_chunk = blocks[:_NOTION_MAX_CHILDREN]
    rest = blocks[_NOTION_MAX_CHILDREN:]

    response = client.pages.create(
        parent={"page_id": topic_page_id},
        properties={
            "title": {"title": [{"text": {"content": title}}]},
        },
        children=first_chunk,
    )
    page_id = response["id"]

    for i in range(0, len(rest), _NOTION_MAX_CHILDREN):
        client.blocks.children.append(
            block_id=page_id,
            children=rest[i : i + _NOTION_MAX_CHILDREN],
        )

    return f"https://notion.so/{page_id.replace('-', '')}"


def _md_to_blocks(md: str) -> list[dict]:
    """마크다운 텍스트를 Notion API 블록 리스트로 변환해요."""
    blocks = []
    lines = md.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]

        if line.startswith("```"):
            code_lines = []
            lang = _normalize_language(line[3:])
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                code_lines.append(lines[i])
                i += 1
            code_content = "\n".join(code_lines)
            for chunk in _split_text(code_content):
                blocks.append(
                    {
                        "object": "block",
                        "type": "code",
                        "code": {
                            "rich_text": [{"type": "text", "text": {"content": chunk}}],
                            "language": lang,
                        },
                    }
                )
        elif line.startswith("### "):
            blocks.append(_heading_block(3, line[4:]))
        elif line.startswith("## "):
            blocks.append(_heading_block(2, line[3:]))
        elif line.startswith("# "):
            blocks.append(_heading_block(1, line[2:]))
        elif line.startswith("- ") or line.startswith("* "):
            for chunk in _split_text(line[2:]):
                blocks.append(_bullet_block(chunk))
        elif line.strip():
            for chunk in _split_text(line):
                blocks.append(_paragraph_block(chunk))

        i += 1

    return blocks


def _split_text(text: str) -> list[str]:
    """2000자 제한을 넘는 텍스트를 청크로 분할해요."""
    if len(text) <= _NOTION_MAX_TEXT_LEN:
        return [text]
    return [text[i: i + _NOTION_MAX_TEXT_LEN] for i in range(0, len(text), _NOTION_MAX_TEXT_LEN)]


def _heading_block(level: int, text: str) -> dict:
    key = f"heading_{level}"
    return {
        "object": "block",
        "type": key,
        key: {"rich_text": [{"type": "text", "text": {"content": text.strip()[:_NOTION_MAX_TEXT_LEN]}}]},
    }


def _paragraph_block(text: str) -> dict:
    return {
        "object": "block",
        "type": "paragraph",
        "paragraph": {"rich_text": [{"type": "text", "text": {"content": text.strip()}}]},
    }


def _bullet_block(text: str) -> dict:
    return {
        "object": "block",
        "type": "bulleted_list_item",
        "bulleted_list_item": {"rich_text": [{"type": "text", "text": {"content": text.strip()}}]},
    }
