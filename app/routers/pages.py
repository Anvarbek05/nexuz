"""HTML pages: a home page and one page per tool, in every language. Also sitemap.xml and robots.txt."""
import json

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates

from app.config import (APP_NAME, PREMIUM_DAYS, PREMIUM_PRICE_SUM, payment_providers, APP_VERSION, BASE_DIR, CONTACT_EMAIL, DEFAULT_LANG, GOOGLE_SITE_VERIFICATION,
                        LANG_LABELS, LANG_LOCALES, LANGS, LEGAL_UPDATED, PLANS, SITE_URL, STATIC_DIR)
from app.i18n import get_locale
from app.services import limits
from app.tools import GROUPS, TOOLS, TOOLS_BY_ID, TOOLS_BY_SLUG, icon_svg
from app.web import client_ip, current_user

templates = Jinja2Templates(directory=str(BASE_DIR / "app" / "templates"))
templates.env.globals["icon"] = icon_svg
router = APIRouter(include_in_schema=False)

# Pages that are not tools. They are listed in sitemap.xml. (login, register and account are not.)
INFO_SLUGS = ("pricing", "privacy", "terms")


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
           jsonld: dict, client: dict, status_code: int = 200, noindex: bool = False, **extra):
    loc = get_locale(lang)
    user = extra.pop("user", None) or current_user(request)
    context = {
        "user": user, "noindex": noindex, "google_verification": GOOGLE_SITE_VERIFICATION,
        "contact_email": CONTACT_EMAIL,
        **{f"{name}_url": path_for(lang, name) for name in ("login", "register", "account", "pricing", "privacy", "terms")},
        "lang": lang, "ui": loc["ui"], "version": APP_VERSION, "site_name": APP_NAME,
        "title": title, "description": description,
        "canonical": absolute(path_for(lang, slug)),
        "alternates": [{"hreflang": c, "href": absolute(path_for(c, slug))} for c in LANGS],
        "x_default": absolute(path_for(DEFAULT_LANG, slug)),
        "og_image": absolute("/static/img/og-image.png"), "og_locale": LANG_LOCALES[lang],
        "langs": [{"code": c, "label": LANG_LABELS[c], "url": path_for(c, slug), "current": c == lang} for c in LANGS],
        "home_url": path_for(lang), "converter_url": path_for(lang, TOOLS_BY_ID["uzbek"]["slug"]),
        "jsonld": _json(jsonld), "client": _json({**client, "lang": lang}),
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


def webpage_jsonld(lang: str, slug: str, name: str, description: str) -> dict:
    return {"@context": "https://schema.org", "@type": "WebPage", "name": name, "description": description,
            "url": absolute(path_for(lang, slug)), "inLanguage": lang}


def check_lang(lang: str) -> dict:
    if lang not in LANGS:
        raise HTTPException(404)
    return get_locale(lang)


@router.get("/{lang}/login")
@router.get("/{lang}/register")
def auth_page(request: Request, lang: str):
    mode = request.url.path.rstrip("/").split("/")[-1]            # "login" or "register"
    loc = check_lang(lang)
    ui = loc["ui"]
    if current_user(request):
        return RedirectResponse(path_for(lang, "account"), status_code=302)
    title, desc = ui[f"acc_{mode}_title"], ui[f"acc_{mode}_desc"]
    return render(request, "auth.html", lang, mode, f"{title} | {APP_NAME}", desc,
                  webpage_jsonld(lang, mode, title, desc), {"page": mode, "ui": ui}, noindex=True, mode=mode)


@router.get("/{lang}/account")
def account_page(request: Request, lang: str):
    loc = check_lang(lang)
    ui = loc["ui"]
    user = current_user(request)
    if user is None:
        return RedirectResponse(path_for(lang, "login"), status_code=302)
    summary = limits.Ticket(user, client_ip(request)).summary()
    title = ui["acc_title"]
    return render(request, "account.html", lang, "account", f"{title} | {APP_NAME}", ui["acc_desc"],
                  webpage_jsonld(lang, "account", title, ui["acc_desc"]), {"page": "account", "ui": ui},
                  noindex=True, user=user, summary=summary,
                  premium_until=user["premium_until"][:10] if summary["plan"] == "premium" else "")


PROVIDER_NAMES = {"click": "Click", "payme": "Payme"}


@router.get("/{lang}/pricing")
def pricing_page(request: Request, lang: str):
    loc = check_lang(lang)
    p = loc["pricing"]
    providers = payment_providers()
    plans = []
    for key in ("guest", "free", "premium"):
        rules, words = PLANS[key], p["plans"][key]
        if rules["per_day"] is None:
            ops = p["feat_ops_unlimited"]
        elif rules["per_day"] == 1:
            ops = p["feat_ops_one"]
        else:
            ops = p["feat_ops"].format(n=rules["per_day"])
        price, note = words["price"], words["note"]
        if key == "premium" and providers:       # payments are switched on: show the real price
            price = p["price_on"].format(price=f"{PREMIUM_PRICE_SUM:,}".replace(",", " "), days=PREMIUM_DAYS)
            note = words["note_on"].format(days=PREMIUM_DAYS)
        plans.append({"key": key, "name": words["name"], "price": price, "note": note,
                      "features": [ops, p["feat_size"].format(mb=rules["max_mb"])] + words["features"]})
    buttons = [{"id": c, "label": p["pay_with"].replace("{provider}", PROVIDER_NAMES[c])} for c in providers]
    return render(request, "pricing.html", lang, "pricing", f"{p['seo_title']} | {APP_NAME}", p["seo_desc"],
                  webpage_jsonld(lang, "pricing", p["title"], p["seo_desc"]),
                  {"page": "pricing", "ui": loc["ui"]}, p=p, plans=plans, buttons=buttons)


@router.get("/{lang}/privacy")
@router.get("/{lang}/terms")
def legal_page(request: Request, lang: str):
    which = request.url.path.rstrip("/").split("/")[-1]           # "privacy" or "terms"
    loc = check_lang(lang)
    doc = loc["legal"][which]
    if payment_providers():     # payments are on: use the texts that talk about paying
        paid = loc["legal"]["paid"]
        doc = {**doc, "sections": [dict(sec) for sec in doc["sections"]]}
        if which == "terms":
            doc["sections"][3]["p"] = [paid["terms_limits"]]               # "Limits and plans"
        else:
            doc["sections"][2]["p"] = doc["sections"][2]["p"] + [paid["privacy_extra"]]   # "Account data"
    return render(request, "legal.html", lang, which, f"{doc['seo_title']} | {APP_NAME}", doc["seo_desc"],
                  webpage_jsonld(lang, which, doc["title"], doc["seo_desc"]),
                  {"page": which, "ui": loc["ui"]}, doc=doc, legal=loc["legal"], updated=LEGAL_UPDATED[lang])


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
    user = current_user(request)
    account = limits.Ticket(user, client_ip(request)).summary()
    if tool.get("kind") == "text":
        return render(request, "uzbek.html", lang, slug, title, text["seo_desc"], jsonld,
                      {"page": "uzbek", "ui": loc["ui"], "account": account}, user=user, **common)
    client = {"page": "tool", "ui": loc["ui"], "tool": client_tool(tool, text), "account": account}
    return render(request, "tool.html", lang, slug, title, text["seo_desc"], jsonld, client, user=user,
                  account=account, **common)


@router.get("/sitemap.xml")
def sitemap():
    slugs = [""] + [t["slug"] for t in TOOLS] + list(INFO_SLUGS)
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
