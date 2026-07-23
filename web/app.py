#!/usr/bin/env python3
"""skill-advisor Web UI — FastAPI + Jinja2"""

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from pathlib import Path

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR.parent / "data" / "skill-advisor.db"

app = FastAPI(title="skill-advisor", version="6.1.0")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

@app.get("/")
async def home(request: Request):
    return HTMLResponse(templates.get_template("index.html").render({"request": request, "query": "", "results": []}))

@app.get("/search")
async def search(request: Request, q: str = ""):
    results = []
    if q:
        import sqlite3
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        like = "%" + q + "%" 
        rows = conn.execute(
            "SELECT name, description, quality_score, installs FROM skills_merged WHERE name LIKE ? OR description LIKE ? ORDER BY quality_score DESC LIMIT 50",
            (like, like)
        ).fetchall()
        results = [dict(r) for r in rows]
        conn.close()
    return HTMLResponse(templates.get_template("search.html").render({"request": request, "query": q, "results": results}))

@app.get("/health")
async def health():
    return {"status": "ok", "version": "6.1.0"}

@app.get("/packs")
async def packs(request: Request):
    import sqlite3, json
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    # 从 profession_packs.py 读取职业包数据
    import sys
    sys.path.insert(0, str(BASE_DIR.parent / "scripts"))
    from profession_packs import PROFESSION_PACKS as PACKS_LIST
    packs_list = []
    for pack in PACKS_LIST:
        packs_list.append({
            "slug": pack["slug"],
            "name": pack["name"],
            "desc": pack["desc"],
            "skills": pack["skills"],
            "combo_guide": pack.get("combo_guide", "")
        })
    conn.close()
    return HTMLResponse(templates.get_template("packs.html").render({"request": request, "packs": packs_list}))

@app.get("/packs/{slug}")
async def pack_detail(request: Request, slug: str):
    import sys
    sys.path.insert(0, str(BASE_DIR.parent / "scripts"))
    from profession_packs import PROFESSION_PACKS as PACKS_LIST
    pack = next((p for p in PACKS_LIST if p.get("slug") == slug), None)
    if not pack:
        return {"error": "Pack not found"}
    return HTMLResponse(templates.get_template("pack_detail.html").render({"request": request, "pack": pack, "slug": slug}))
