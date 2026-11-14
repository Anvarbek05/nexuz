"""HTML pages: a home page and one page per tool, in every language. Also sitemap.xml and robots.txt."""
import json

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates

from app.config import (APP_NAME, APP_VERSION, BASE_DIR, DEFAULT_LANG, LANG_LABELS,
                        LANG_LOCALES, LANGS, SITE_URL, STATIC_DIR)
from app.i18n import get_locale
from app.tools import GROUPS, TOOLS, TOOLS_BY_ID, TOOLS_BY_SLUG, icon_svg

templates = Jinja2Templates(directory=str(BASE_DIR / "app" / "templates"))
templates.env.globals["icon"] = icon_svg
router = APIRouter(include_in_schema=False)


def _json(data) -> str:
    """JSON that is safe inside a <script> tag."""
    return json.dumps(data, ensure_ascii=False).replace("</", "<\\/")


def path_for(lang: str, slug: str = "") -> str:
    return f"/{lang}/{slug}" if slug else f"/{lang}/"


def absolute(path: str) -> str:
    return SITE_URL.rstrip("/") + path


def pick_language(request: Request) -> str:
    for part in request.headers.get("accept-language", "").split(","):
        code = part.split(";")[0].strip().lower()[:2]
        if code in LANGS:
            return code
    return DEFAULT_LANG


def tool_cards(lang: str) -> list[dict]:
    loc = get_locale(lang)
    return [
        {"id": t["id"], "group": t["group"], "icon": t["icon"], "url": path_for(lang, t["slug"]),
         "name": loc["tools"][t["id"]]["name"], "desc": loc["tools"][t["id"]]["desc"]}
        for t in TOOLS
    ]


def related_cards(lang: str, tool: dict, limit: int = 4) -> list[dict]:
    cards = [c for c in tool_cards(lang) if c["id"] != tool["id"]]
    cards.sort(key=lambda c: c["group"] != tool["group"])   # same group first (stable sort)
    return cards[:limit]


def client_tool(tool: dict, text: dict) -> dict:
    """Everything the browser needs to run one tool, with texts in the right language."""
    api = dict(tool["api"])
    options = []
    for opt in api["options"]:
        words = text["options"][opt["name"]]
        item = {"name": opt["name"], "type": opt["type"], "label": words["label"], "help": words.get("help", "")}
        if "value" in opt:
            item["value"] = opt["value"]
        if opt["type"] == "select":
            item["choices"] = [[v, words["choices"][v]] for v in opt["choices"]]
        options.append(item)
    api["options"] = options
    api.update(id=tool["id"], button=text["button"], need=text["need"])
    return api


def render(request: Request, template: str, lang: str, slug: str, title: str, description: str,
           jsonld: dict, client: dict, status_code: int = 200, **extra):
    loc = get_locale(lang)
    context = {
        "lang": lang, "ui": loc["ui"], "version": APP_VERSION, "site_name": APP_NAME,
        "title": title, "description": description,
        "canonical": absolute(path_for(lang, slug)),
        "alternates": [{"hreflang": c, "href": absolute(path_for(c, slug))} for c in LANGS],
        "x_default": absolute(path_for(DEFAULT_LANG, slug)),
        "og_image": absolute("/static/img/og-image.png"), "og_locale": LANG_LOCALES[lang],
        "langs": [{"code": c, "label": LANG_LABELS[c], "url": path_for(c, slug), "current": c == lang} for c in LANGS],
        "home_url": path_for(lang), "converter_url": path_for(lang, TOOLS_BY_ID["uzbek"]["slug"]),
        "jsonld": _json(jsonld), "client": _json(client),
        **extra,
    }
    return templates.TemplateResponse(request, template, context, status_code=status_code)


def not_found(request: Request):
    first = request.url.path.strip("/").split("/")[0]
    lang = first if first in LANGS else pick_language(request)
    ui = get_locale(lang)["ui"]
    return render(request, "404.html", lang, "", f"{ui['not_found_title']} | {APP_NAME}", ui["not_found_text"],
                  {"@context": "https://schema.org", "@type": "WebPage", "name": ui["not_found_title"]},
                  {"page": "404", "ui": ui}, status_code=404)


@router.get("/")
def root(request: Request):
    return RedirectResponse(path_for(pick_language(request)), status_code=302)


@router.get("/{lang}/")
def home(request: Request, lang: str):
    if lang not in LANGS:
        raise HTTPException(404)
    ui = get_locale(lang)["ui"]
    url = absolute(path_for(lang))
    jsonld = {"@context": "https://schema.org", "@type": "WebSite", "name": APP_NAME, "url": url, "inLanguage": lang}
    return render(request, "home.html", lang, "", ui["home_title"], ui["home_desc"], jsonld,
                  {"page": "home", "ui": ui}, cards=tool_cards(lang), groups=GROUPS)


@router.get("/{lang}/{slug}")
def tool_page(request: Request, lang: str, slug: str):
    tool = TOOLS_BY_SLUG.get(slug)
    if lang not in LANGS or tool is None:
        raise HTTPException(404)
    loc = get_locale(lang)
    text = loc["tools"][tool["id"]]
    jsonld = {
        "@context": "https://schema.org", "@type": "WebApplication", "name": text["name"],
        "description": text["seo_desc"], "url": absolute(path_for(lang, slug)),
        "applicationCategory": "UtilitiesApplication", "operatingSystem": "Any", "inLanguage": lang,
        "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"},
    }
    common = dict(tool=tool, text=text, steps=text["steps"], related=related_cards(lang, tool))
    title = f"{text['seo_title']} | {APP_NAME}"
    if tool.get("kind") == "text":
        return render(request, "uzbek.html", lang, slug, title, text["seo_desc"], jsonld,
                      {"page": "uzbek", "ui": loc["ui"]}, **common)
    client = {"page": "tool", "ui": loc["ui"], "tool": client_tool(tool, text)}
    return render(request, "tool.html", lang, slug, title, text["seo_desc"], jsonld, client, **common)


@router.get("/sitemap.xml")
def sitemap():
    slugs = [""] + [t["slug"] for t in TOOLS]
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">']
    for slug in slugs:
        for lang in LANGS:
            lines.append("  <url>")
            lines.append(f"    <loc>{absolute(path_for(lang, slug))}</loc>")
            for alt in LANGS:
                lines.append(f'    <xhtml:link rel="alternate" hreflang="{alt}" href="{absolute(path_for(alt, slug))}"/>')
            lines.append("  </url>")
    lines.append("</urlset>")
    return Response("\n".join(lines), media_type="application/xml")


@router.get("/robots.txt")
def robots():
    body = f"User-agent: *\nAllow: /\nDisallow: /api/\n\nSitemap: {absolute('/sitemap.xml')}\n"
    return Response(body, media_type="text/plain")


@router.get("/favicon.svg")
def favicon_svg():
    return FileResponse(STATIC_DIR / "img" / "favicon.svg", media_type="image/svg+xml")


@router.get("/favicon.ico")
def favicon_ico():
    return FileResponse(STATIC_DIR / "img" / "favicon.ico", media_type="image/x-icon")
