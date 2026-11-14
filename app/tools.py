"""The list of tools: what each one is, where it lives, and how the website talks to it.
Visible texts (names, descriptions, labels) are NOT here. They live in app/locales/*.json."""
from markupsafe import Markup

ICONS = {
    "merge": '<rect x="3" y="3" width="10" height="12" rx="2"/><rect x="11" y="9" width="10" height="12" rx="2"/>',
    "split": '<path d="M12 3v18M7 8l-4 4 4 4M17 8l4 4-4 4"/>',
    "rotate": '<path d="M20 12a8 8 0 1 1-2.6-5.9M20 4v5h-5"/>',
    "compress": '<path d="M9 3v6H3M15 21v-6h6M9 9 3 3M15 15l6 6"/>',
    "drop": '<path d="M12 3s6 6.5 6 10.5a6 6 0 0 1-12 0C6 9.5 12 3 12 3z"/>',
    "image": '<rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="9" cy="10" r="1.6"/><path d="m21 16-5-5-9 9"/>',
    "lock": '<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/>',
    "unlock": '<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V8a4 4 0 0 1 7.5-2"/>',
    "text": '<path d="M4 6h10M9 4v2M6 6c0 4 3 7 7 8M12 6c0 3-2 6-6 8M13 20l4-9 4 9M14.5 17h5"/>',
}


def icon_svg(name: str) -> Markup:
    return Markup(
        '<svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" '
        'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">' + ICONS[name] + "</svg>"
    )


GROUPS = ("organize", "convert", "edit", "security")

_PDF = {"accept": ".pdf", "multiple": False, "min": 1}

TOOLS = [
    {"id": "merge", "slug": "merge-pdf", "group": "organize", "icon": "merge",
     "api": {"endpoint": "/api/merge", "accept": ".pdf", "multiple": True, "min": 2, "out": "merged.pdf", "options": []}},
    {"id": "split", "slug": "extract-pdf-pages", "group": "organize", "icon": "split",
     "api": {**_PDF, "endpoint": "/api/split", "suffix": "-pages.pdf",
             "options": [{"name": "pages", "type": "text", "value": "1"}]}},
    {"id": "rotate", "slug": "rotate-pdf", "group": "organize", "icon": "rotate",
     "api": {**_PDF, "endpoint": "/api/rotate", "suffix": "-rotated.pdf",
             "options": [{"name": "angle", "type": "select", "value": "90", "choices": ["90", "180", "270"]}]}},
    {"id": "compress", "slug": "compress-pdf", "group": "organize", "icon": "compress",
     "api": {**_PDF, "endpoint": "/api/compress", "suffix": "-compressed.pdf", "compare": True,
             "options": [{"name": "level", "type": "select", "value": "medium", "choices": ["low", "medium", "high"]}]}},
    {"id": "pdf2img", "slug": "pdf-to-images", "group": "convert", "icon": "image",
     "api": {**_PDF, "endpoint": "/api/pdf2img", "suffix": "-images.zip",
             "options": [{"name": "fmt", "type": "select", "value": "png", "choices": ["png", "jpg"]}]}},
    {"id": "img2pdf", "slug": "images-to-pdf", "group": "convert", "icon": "image",
     "api": {"endpoint": "/api/img2pdf", "accept": ".jpg,.jpeg,.png", "multiple": True, "min": 1,
             "out": "images.pdf", "options": []}},
    {"id": "uzbek", "slug": "uzbek-alphabet-converter", "group": "convert", "icon": "text", "kind": "text"},
    {"id": "watermark", "slug": "watermark-pdf", "group": "edit", "icon": "drop",
     "api": {**_PDF, "endpoint": "/api/watermark", "suffix": "-watermarked.pdf",
             "options": [{"name": "text", "type": "text", "value": "Nexuz"}]}},
    {"id": "protect", "slug": "protect-pdf", "group": "security", "icon": "lock",
     "api": {**_PDF, "endpoint": "/api/protect", "suffix": "-protected.pdf",
             "options": [{"name": "password", "type": "password"}]}},
    {"id": "unlock", "slug": "unlock-pdf", "group": "security", "icon": "unlock",
     "api": {**_PDF, "endpoint": "/api/unlock", "suffix": "-unlocked.pdf",
             "options": [{"name": "password", "type": "password"}]}},
]

TOOLS_BY_ID = {t["id"]: t for t in TOOLS}
TOOLS_BY_SLUG = {t["slug"]: t for t in TOOLS}
