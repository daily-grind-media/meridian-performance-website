#!/usr/bin/env python3
"""
Meridian Performance — static site builder (no dependencies, Python 3.8+).

    python3 build.py                                  # PRODUCTION build -> dist/
    python3 build.py --base-url=https://www.domain.com  # production build with the domain passed in
    python3 build.py --preview                        # PREVIEW build    -> preview/
                                                      #   demo blog content, noindex everywhere,
                                                      #   robots.txt blocks crawling, links end in index.html

Configuration (edit these, never the generated HTML):
    content/site.json        domain (base_url), business details, social profile URLs
    content/pages.json       routes + SEO title/description/indexing for every static page
    content/authors.json     authors
    content/categories.json  blog categories
    content/blog/<slug>/     one folder per article: meta.json + body.html

Templates: src/*.html  ·  Assets: assets/  ·  See README.md.
"""
import html, json, math, re, shutil, sys, pathlib, datetime
from urllib.parse import urlparse

ROOT = pathlib.Path(__file__).parent
SRC = ROOT / "src"
CONTENT = ROOT / "content"
PREVIEW = "--preview" in sys.argv
OUT = ROOT / ("preview" if PREVIEW else "dist")

SITE = json.loads((CONTENT / "site.json").read_text())
PAGES = {k: v for k, v in json.loads((CONTENT / "pages.json").read_text()).items() if not k.startswith("_")}
AUTHORS = json.loads((CONTENT / "authors.json").read_text())
CATEGORIES = json.loads((CONTENT / "categories.json").read_text())
CAT_NAME = {c["slug"]: c["name"] for c in CATEGORIES}
BIZ = SITE["business"]
LOCATION = BIZ["location_label"]

_cli_base = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--base-url=")), None)
BASE = (_cli_base if _cli_base is not None else SITE.get("base_url", "")).strip().rstrip("/")
if BASE and not re.match(r"^https?://[^/\s]+", BASE):
    sys.exit(f"base_url must start with http:// or https:// (got {BASE!r})")
ROOT_PATH = (urlparse(BASE).path.rstrip("/") + "/") if BASE else "/"   # used by the 404 page
WARNINGS = []

# ---------------------------------------------------------------- routing
def route_for(key):
    if key.startswith("article:"):
        return "blog/" + key.split(":", 1)[1] + "/"
    return PAGES[key]["route"]


def out_path_for(key):
    r = route_for(key)
    return r if r.endswith(".html") else r + "index.html"


def depth_of(out_path):
    return out_path.count("/")


def prefix(out_path):
    """Path prefix from a page back to the site root."""
    if out_path == "404.html" and not PREVIEW:
        return ROOT_PATH          # 404 can be served at any depth: use root-absolute links
    return "../" * depth_of(out_path)


def url(key, out_path):
    """Link from the page at out_path to the route `key`."""
    rel = prefix(out_path) + route_for(key)
    if PREVIEW and not rel.endswith(".html"):
        return rel + "index.html"
    return rel or "./"


def abs_url(key):
    return f"{BASE}/{route_for(key)}" if BASE else ""


def abs_asset(path):
    return f"{BASE}/{path.lstrip('/')}" if BASE else ""

# ---------------------------------------------------------------- icons
ICONS = {
    "arrow": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="square" aria-hidden="true"><path d="M3 12h17M14 6l6 6-6 6"/></svg>',
    "arrow-left": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="square" aria-hidden="true"><path d="M21 12H4M10 6l-6 6 6 6"/></svg>',
    "bars": '<svg viewBox="0 0 36 36" fill="currentColor" aria-hidden="true"><rect x="4" y="22" width="5" height="10"/><rect x="12" y="16" width="5" height="16"/><rect x="20" y="10" width="5" height="22"/><rect x="28" y="4" width="5" height="28"/></svg>',
    "fuel": '<svg viewBox="0 0 36 36" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="square" aria-hidden="true"><path d="M9 4v9a4 4 0 0 0 8 0V4M13 4v28M25 32V4c-4 2-6 7-6 12 0 3 2 5 6 5"/></svg>',
    "target": '<svg viewBox="0 0 36 36" fill="none" stroke="currentColor" stroke-width="2.4" aria-hidden="true"><circle cx="18" cy="18" r="11"/><circle cx="18" cy="18" r="2.5" fill="currentColor" stroke="none"/><path d="M18 2v8M18 26v8M2 18h8M26 18h8"/></svg>',
    "star": '<svg viewBox="0 0 20 20" fill="currentColor" aria-hidden="true"><path d="M10 1.5l2.6 5.6 6.1.7-4.5 4.2 1.2 6L10 15l-5.4 3 1.2-6L1.3 7.8l6.1-.7z"/></svg>',
}

# Social platforms: label + icon. Order and visibility come from content/site.json.
SOCIAL_PLATFORMS = {
    "facebook": ("Facebook", '<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M13.6 21.5v-8.2h2.8l.4-3.3h-3.2V7.9c0-.9.3-1.6 1.6-1.6h1.7V3.4c-.3 0-1.3-.1-2.5-.1-2.5 0-4.2 1.5-4.2 4.3V10H7.4v3.3h2.8v8.2h3.4z"/></svg>'),
    "instagram": ("Instagram", '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><rect x="3.2" y="3.2" width="17.6" height="17.6" rx="5"/><circle cx="12" cy="12" r="4.1"/><circle cx="17.3" cy="6.7" r="1.1" fill="currentColor" stroke="none"/></svg>'),
    "linkedin": ("LinkedIn", '<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><rect x="3.6" y="9" width="3.6" height="11.5"/><circle cx="5.4" cy="5.3" r="2.1"/><path d="M10 9h3.4v1.6c.5-.9 1.7-1.9 3.6-1.9 3.6 0 4.3 2.4 4.3 5.5v6.3h-3.6v-5.6c0-1.3 0-3.1-1.9-3.1s-2.2 1.5-2.2 3v5.7H10z"/></svg>'),
    "youtube": ("YouTube", '<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M21.6 7.2c-.2-.9-.9-1.6-1.8-1.8C18.2 5 12 5 12 5s-6.2 0-7.8.4c-.9.2-1.6.9-1.8 1.8C2 8.8 2 12 2 12s0 3.2.4 4.8c.2.9.9 1.6 1.8 1.8C5.8 19 12 19 12 19s6.2 0 7.8-.4c.9-.2 1.6-.9 1.8-1.8.4-1.6.4-4.8.4-4.8s0-3.2-.4-4.8zM10 15V9l5.2 3L10 15z"/></svg>'),
}


def social_urls():
    """Configured profiles in display order: [(key, label, icon, url_or_empty)]."""
    out = []
    for key in SITE.get("social_order", []):
        if key not in SOCIAL_PLATFORMS:
            WARNINGS.append(f"social_order: unknown platform '{key}'")
            continue
        label, icon = SOCIAL_PLATFORMS[key]
        out.append((key, label, icon, (SITE.get("social", {}).get(key) or "").strip()))
    return out


def social_links(variant="footer"):
    items = []
    for key, label, icon, href in social_urls():
        if href:
            items.append(f'<li><a class="social__link" href="{esc(href)}" target="_blank" rel="noopener noreferrer" aria-label="{label} (opens in a new tab)">{icon}<span class="social__label">{label}</span></a></li>')
        elif PREVIEW:
            # Visible in preview only, so the layout can be reviewed before URLs exist.
            items.append(f'<li><span class="social__link is-pending" role="img" aria-label="{label} (link not set yet)" title="{label} URL not set yet">{icon}<span class="social__label">{label}</span></span></li>')
    if not items:
        return ""
    return f'<ul class="social social--{variant}" aria-label="Meridian Performance on social media">{"".join(items)}</ul>'


def stars():
    return '<span class="stars" role="img" aria-label="5 out of 5 stars">' + ICONS["star"] * 5 + "</span>"


def esc(s):
    return html.escape(s or "", quote=True)

# ---------------------------------------------------------------- structured data
def ld(obj):
    return '<script type="application/ld+json">' + json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "</script>"


def biz_id():
    return f"{BASE}/#business"


def site_id():
    return f"{BASE}/#website"


def person_id(author_key):
    a = AUTHORS.get(author_key, {})
    return f'{abs_url(a.get("about_page", "about"))}#{author_key}'


def same_as(d):
    return [u.strip() for u in (d or {}).values() if isinstance(u, str) and u.strip().startswith("http")]


def person_node(author_key):
    a = AUTHORS[author_key]
    node = {"@type": "Person", "@id": person_id(author_key), "name": a["name"],
            "jobTitle": a.get("role", "").split(",")[0].strip() or None,
            "worksFor": {"@id": biz_id()}, "url": abs_url(a.get("about_page", "about"))}
    s = same_as(a.get("social"))
    if s:
        node["sameAs"] = s
    return {k: v for k, v in node.items() if v}


def business_node():
    node = {
        "@type": "LocalBusiness", "@id": biz_id(), "name": BIZ["name"], "url": f"{BASE}/",
        "description": BIZ["description"],
        "logo": {"@type": "ImageObject", "url": abs_asset("assets/img/logo-full.webp")},
        "image": abs_asset(SITE["default_og_image"]["src"]),
        "address": {"@type": "PostalAddress", "addressLocality": BIZ["locality"],
                    "addressRegion": BIZ["region"], "addressCountry": BIZ["country"]},
        "areaServed": {"@type": "City", "name": BIZ["locality"]},
        "founder": {"@id": person_id(BIZ["founder"])},
        "makesOffer": [{"@type": "Offer", "itemOffered": {"@type": "Service", "name": s}} for s in BIZ.get("services", [])],
    }
    s = [u for _, _, _, u in social_urls() if u] + [u for k, u in (SITE.get("social") or {}).items()
                                                   if u and k not in SITE.get("social_order", [])]
    if s:
        node["sameAs"] = s
    return node


def website_node():
    return {"@type": "WebSite", "@id": site_id(), "url": f"{BASE}/", "name": SITE["name"],
            "publisher": {"@id": biz_id()}, "inLanguage": "en-US"}


def page_jsonld(key, title, desc):
    """Structured data for static pages. Only emitted once a production domain is set."""
    if not BASE or PREVIEW:
        return ""
    kind = PAGES.get(key, {}).get("schema")
    graph = []
    if kind == "home":
        graph = [website_node(), business_node(), person_node(BIZ["founder"])]
    elif kind == "about":
        graph = [{"@type": "AboutPage", "@id": abs_url(key), "url": abs_url(key), "name": title,
                  "description": desc, "isPartOf": {"@id": site_id()}, "mainEntity": {"@id": person_id(BIZ["founder"])}},
                 person_node(BIZ["founder"]), business_node()]
    elif kind == "contact":
        graph = [{"@type": "ContactPage", "@id": abs_url(key), "url": abs_url(key), "name": title,
                  "description": desc, "isPartOf": {"@id": site_id()}, "about": {"@id": biz_id()}}]
    elif kind == "blog":
        graph = [{"@type": "Blog", "@id": abs_url(key), "url": abs_url(key), "name": "Meridian Insights",
                  "description": desc, "publisher": {"@id": biz_id()}, "isPartOf": {"@id": site_id()}}]
    return ld({"@context": "https://schema.org", "@graph": graph}) if graph else ""

# ---------------------------------------------------------------- partials
def head(out_path, key, title, desc, *, og_image=None, og_type="website", index=True, extra=""):
    """<head> contents. og_image: dict(src, width, height, alt)."""
    P = prefix(out_path)
    indexable = index and not PREVIEW
    canonical = abs_url(key) if indexable else ""
    img = og_image or SITE["default_og_image"]
    tags = [
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">',
        f"<title>{esc(title)}</title>",
        f'<meta name="description" content="{esc(desc)}">',
        '<meta name="robots" content="' + ("index, follow, max-image-preview:large" if indexable
                                          else "noindex, nofollow" if PREVIEW else "noindex, follow") + '">',
        '<meta name="theme-color" content="#0A0A0A">',
    ]
    if canonical:
        tags.append(f'<link rel="canonical" href="{esc(canonical)}">')
    tags += [
        f'<meta property="og:site_name" content="{esc(SITE["name"])}">',
        f'<meta property="og:locale" content="{esc(SITE.get("locale", "en_US"))}">',
        f'<meta property="og:type" content="{og_type}">',
        f'<meta property="og:title" content="{esc(title)}">',
        f'<meta property="og:description" content="{esc(desc)}">',
    ]
    if BASE:  # Open Graph needs absolute URLs, so these wait for the production domain
        tags.append(f'<meta property="og:url" content="{esc(abs_url(key))}">')
        tags.append(f'<meta property="og:image" content="{esc(abs_asset(img["src"]))}">')
        if img.get("width"):
            tags.append(f'<meta property="og:image:width" content="{img["width"]}">')
            tags.append(f'<meta property="og:image:height" content="{img["height"]}">')
        tags.append(f'<meta property="og:image:alt" content="{esc(img.get("alt") or SITE["name"])}">')
        tags.append(f'<meta name="twitter:image" content="{esc(abs_asset(img["src"]))}">')
    tags += [
        '<meta name="twitter:card" content="summary_large_image">',
        f'<meta name="twitter:title" content="{esc(title)}">',
        f'<meta name="twitter:description" content="{esc(desc)}">',
        f'<link rel="icon" type="image/png" href="{P}assets/img/favicon.png">',
        f'<link rel="apple-touch-icon" href="{P}assets/img/favicon.png">',
        f'<link rel="preload" href="{P}assets/fonts/russo-one-400.woff2" as="font" type="font/woff2" crossorigin>',
        f'<link rel="preload" href="{P}assets/fonts/rajdhani-600.woff2" as="font" type="font/woff2" crossorigin>',
        f'<link rel="preload" href="{P}assets/fonts/inter-400.woff2" as="font" type="font/woff2" crossorigin>',
        f'<link rel="stylesheet" href="{P}assets/css/site.css">',
    ]
    return "\n".join(tags) + ("\n" + extra if extra else "")


NAV = [  # key, label, target
    ("about", "About", "about"),
    ("coaching", "Coaching", "home#coaching"),
    ("method", "Method", "home#method"),
    ("results", "Results", "home#results"),
    ("blog", "Blog", "blog"),
    ("contact", "Contact", "contact"),
]


def link_target(target, out_path, is_home):
    if "#" in target:
        k, frag = target.split("#")
        return f"#{frag}" if is_home else f"{url(k, out_path)}#{frag}"
    return url(target, out_path)


def header(out_path, active, is_home=False):
    P = prefix(out_path)
    cur = lambda k: ' aria-current="page"' if k == active else ""
    desk = "\n".join(f'        <a class="nav__link" href="{link_target(t, out_path, is_home)}"{cur(k)}>{l}</a>' for k, l, t in NAV)
    mob = "\n".join(f'      <li><a href="{link_target(t, out_path, is_home)}"{cur(k)}>{l}</a></li>' for k, l, t in NAV)
    home = url("home", out_path)
    contact = url("contact", out_path)
    return f'''<a class="skip-link" href="#main">Skip to content</a>
<div class="grain" aria-hidden="true"></div>
<header class="nav" id="top">
  <div class="nav__inner">
    <a class="brand" href="{home}" aria-label="Meridian Performance home">
      <img class="brand__icon" src="{P}assets/img/logo-icon.webp" width="329" height="326" alt="">
      <img class="brand__word" src="{P}assets/img/logo-wordmark.webp" width="815" height="142" alt="Meridian Performance">
    </a>
    <nav class="nav__links" aria-label="Primary">
{desk}
    </nav>
    <a class="btn btn--outline-red nav__cta" href="{contact}">Get Started</a>
    <button class="nav__toggle" type="button" aria-expanded="false" aria-controls="site-menu" aria-label="Open menu"><span></span><span></span><span></span></button>
  </div>
</header>
<div class="menu" id="site-menu" aria-hidden="true">
  <nav aria-label="Mobile">
    <ul class="menu__list">
      <li><a href="{home}"{cur("home")}>Home</a></li>
{mob}
    </ul>
  </nav>
  <div class="menu__foot">
    <a class="btn btn--primary" href="{contact}">Get Started {ICONS["arrow"]}</a>
    <p class="caption">{LOCATION} · Online coaching</p>
  </div>
</div>'''


def footer(out_path, is_home=False):
    P = prefix(out_path)
    u = lambda k: url(k, out_path)
    t = lambda target: link_target(target, out_path, is_home)
    return f'''<footer class="footer">
  <div class="wrap">
    <div class="footer__top">
      <div class="footer__brand">
        <a href="{u("home")}" aria-label="Meridian Performance home"><img src="{P}assets/img/logo-full.webp" width="828" height="491" alt="Meridian Performance" loading="lazy" decoding="async"></a>
        <p>Personalized coaching, nutrition guidance and accountability in {LOCATION}, and online.</p>
        {social_links("footer")}
      </div>
      <div>
        <h2 class="footer__h">Explore</h2>
        <ul>
          <li><a href="{u("about")}">About Chance</a></li>
          <li><a href="{t("home#coaching")}">Coaching</a></li>
          <li><a href="{t("home#method")}">The Meridian Method</a></li>
          <li><a href="{t("home#results")}">Results</a></li>
          <li><a href="{u("blog")}">Blog</a></li>
        </ul>
      </div>
      <div>
        <h2 class="footer__h">Train</h2>
        <address>
          <span>{LOCATION}</span>
          <span class="muted">Online coaching, wherever you train</span>
        </address>
      </div>
      <div>
        <h2 class="footer__h">Contact</h2>
        <ul>
          <li><a href="{u("contact")}#message">Send a message</a></li>
          <li><a href="{u("contact")}#book">Book a consultation</a></li>
        </ul>
      </div>
    </div>
    <div class="footer__ghost" aria-hidden="true">Meridian</div>
    <div class="footer__bottom">
      <span>© {datetime.date.today().year} Meridian Performance</span>
      <nav aria-label="Legal">
        <a href="{u("privacy")}">Privacy Policy</a>
        <a href="{u("terms")}">Terms of Service</a>
      </nav>
    </div>
  </div>
</footer>
<script src="{P}assets/js/site.js" defer></script>'''


def render_markers(text, out_path, key, is_home=False):
    """Expand {{...}} markers. Also used for article bodies (links/assets only)."""
    if "{{HEAD}}" in text:
        cfg = PAGES[key]
        text = text.replace("{{HEAD}}", head(out_path, key, cfg["title"], cfg["description"], index=cfg.get("index", True),
                                             extra=page_jsonld(key, cfg["title"], cfg["description"])))
    text = re.sub(r'\{\{HEADER active="([^"]*)"\}\}', lambda m: header(out_path, m.group(1), is_home), text)
    text = text.replace("{{FOOTER}}", footer(out_path, is_home))
    if "{{SOCIAL_ROW}}" in text:
        links = social_links("inline")
        text = text.replace("{{SOCIAL_ROW}}", f'<div class="contact-social"><p class="contact-social__label">Follow Meridian Performance</p>{links}</div>' if links else "")
    text = text.replace("{{LOCATION}}", LOCATION)
    text = text.replace("{{STARS}}", stars())
    text = text.replace("{{A}}", prefix(out_path))
    text = re.sub(r"\{\{U:([a-z:\-0-9]+)\}\}", lambda m: url(m.group(1), out_path), text)
    text = re.sub(r"\{\{ICON ([a-z-]+)\}\}", lambda m: ICONS[m.group(1)], text)
    assert "{{" not in text, (out_path, text[text.index("{{"):text.index("{{") + 80])
    return text

# ---------------------------------------------------------------- blog data
def reading_minutes(body_html):
    words = len(re.sub(r"<[^>]+>", " ", body_html).split())
    return max(1, math.ceil(words / 225))


def load_articles():
    arts = []
    for meta_file in sorted((CONTENT / "blog").glob("*/meta.json")):
        folder = meta_file.parent
        m = json.loads(meta_file.read_text())
        m["slug"] = folder.name
        status = m.get("status", "draft")
        m["is_demo"] = status == "demo"
        if status == "published" and not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", folder.name):
            WARNINGS.append(f"{folder.name}: article folder (slug) should be lowercase words joined by hyphens")
        body_path = folder / m.get("body_file", "body.html")
        m["body"] = body_path.read_text() if body_path.exists() else ""
        m["minutes"] = reading_minutes(m["body"])
        if status == "published":
            for field in ("title", "category", "excerpt", "date", "author"):  # hero image is optional
                if not m.get(field):
                    WARNINGS.append(f"{folder.name}: published article missing '{field}'")
            if not (m.get("seo") or {}).get("description"):
                WARNINGS.append(f"{folder.name}: published article missing seo.description (falls back to excerpt)")
            if m.get("hero") and not m["hero"].get("alt"):
                WARNINGS.append(f"{folder.name}: hero image has no alt text")
            if m.get("author") and m["author"] not in AUTHORS:
                WARNINGS.append(f"{folder.name}: unknown author '{m['author']}'")
        if status in ("published", "demo") and m.get("category") not in CAT_NAME:
            WARNINGS.append(f"{folder.name}: unknown category '{m.get('category')}'")
        if status == "published" or (PREVIEW and status == "demo"):
            arts.append(m)
    arts.sort(key=lambda a: (a.get("date") or "", a.get("order", 0)), reverse=True)
    return arts


def fmt_date(a):
    if not a.get("date"):
        return "Publish date"
    d = datetime.date.fromisoformat(a["date"])
    return f"{d:%b} {d.day}, {d.year}"


def date_tag(a):
    if a.get("date"):
        return f'<time datetime="{a["date"]}">{fmt_date(a)}</time>'
    return '<span>Publish date</span>'


def demo_badge(a):
    return '<span class="demo-badge">Demo · placeholder</span>' if a["is_demo"] else ""


def img_attrs(a, out_path, sizes):
    """src/srcset for an article image (hero 1600w + thumb 900w)."""
    img = a.get("hero") or {}
    P = prefix(out_path)
    src = P + img.get("src", "").lstrip("/")
    if img.get("thumb"):
        return f'src="{src}" srcset="{P + img["thumb"].lstrip("/")} 900w, {src} 1600w" sizes="{sizes}"'
    return f'src="{src}"'


def thumb_src(a, out_path):
    img = a.get("hero") or {}
    return prefix(out_path) + (img.get("thumb") or img.get("src", "")).lstrip("/")


def meta_row(a):
    return f'<p class="post-meta">{date_tag(a)}<i aria-hidden="true"></i><span>{a["minutes"]} min read</span></p>'


def preview_card(a, out_path, variant="row", heading="h3"):
    """Reusable article preview component."""
    href = url("article:" + a["slug"], out_path)
    cat = CAT_NAME.get(a.get("category"), "")
    has_img = bool((a.get("hero") or {}).get("src"))
    media = (f'<a class="post__media" href="{href}" tabindex="-1" aria-hidden="true"><img src="{thumb_src(a, out_path)}" alt="" width="900" height="600" loading="lazy" decoding="async"></a>'
             if has_img else "")
    return f'''<article class="post post--{variant}{"" if has_img else " post--noimg"}" data-category="{esc(a.get("category"))}">
  {media}
  <div class="post__body">
    <p class="post__cat"><span>{esc(cat)}</span>{demo_badge(a)}</p>
    <{heading} class="post__title"><a href="{href}">{esc(a["title"])}</a></{heading}>
    <p class="post__excerpt">{esc(a.get("excerpt"))}</p>
    {meta_row(a)}
  </div>
</article>'''


def article_cta(out_path):
    return f'''<section class="article-cta" aria-labelledby="article-cta-title">
  <div class="article-cta__inner">
    <span class="article-cta__needle" aria-hidden="true"></span>
    <h2 class="article-cta__title" id="article-cta-title">Ready to put it into <span class="red">practice?</span></h2>
    <p class="article-cta__copy">Personalized coaching can help turn information into a plan built around you.</p>
    <a class="btn btn--primary" href="{url("contact", out_path)}">Get Started {ICONS["arrow"]}</a>
    <p class="article-cta__links"><a href="{url("home", out_path)}#coaching">Coaching options</a><i aria-hidden="true"></i><a href="{url("home", out_path)}#method">The Meridian Method</a><i aria-hidden="true"></i><a href="{url("about", out_path)}">About Chance</a></p>
  </div>
</section>'''

# ---------------------------------------------------------------- blog pages
def build_blog_index(arts):
    key = "blog"
    out_path = out_path_for(key)
    P = prefix(out_path)
    cfg = PAGES[key]
    featured = next((a for a in arts if a.get("featured")), arts[0] if arts else None)
    rest = [a for a in arts if a is not featured]
    present = {a.get("category") for a in arts}

    chips = ['<li><button type="button" class="chip" aria-pressed="true" data-filter="all">All</button></li>']
    for c in CATEGORIES:
        dis = "" if c["slug"] in present else " disabled"
        chips.append(f'<li><button type="button" class="chip" aria-pressed="false" data-filter="{c["slug"]}"{dis}>{esc(c["name"])}</button></li>')

    feat_html = ""
    if featured:
        href = url("article:" + featured["slug"], out_path)
        feat_img = bool((featured.get("hero") or {}).get("src"))
        feat_media = (f'''<a class="feature__media" href="{href}" tabindex="-1" aria-hidden="true">
          <img {img_attrs(featured, out_path, "(max-width: 960px) 100vw, 60vw")} alt="" width="1600" height="900" decoding="async">
        </a>''' if feat_img else "")
        feat_html = f'''<article class="feature{"" if feat_img else " feature--text"} reveal" data-category="{esc(featured.get("category"))}" aria-labelledby="feature-title">
        {feat_media}
        <div class="feature__panel">
          <p class="feature__kicker"><span class="feature__label">Featured</span><span class="post__cat"><span>{esc(CAT_NAME.get(featured.get("category"), ""))}</span>{demo_badge(featured)}</span></p>
          <h3 class="feature__title" id="feature-title"><a href="{href}">{esc(featured["title"])}</a></h3>
          <p class="feature__excerpt">{esc(featured.get("excerpt"))}</p>
          {meta_row(featured)}
          <a class="btn btn--primary feature__cta" href="{href}" aria-label="Read article: {esc(featured["title"])}">Read Article {ICONS["arrow"]}</a>
        </div>
      </article>'''

    lead_html = "\n".join(preview_card(a, out_path, "lead") for a in rest[:2])
    rows_html = "\n".join(preview_card(a, out_path, "row") for a in rest[2:])

    if arts:
        listing = f'''
    <section class="section blog-list" aria-labelledby="latest-title">
      <div class="wrap">
        <div class="blog-filter">
          <h2 class="eyebrow eyebrow--rule" id="latest-title">Latest articles</h2>
          <ul class="chips" aria-label="Filter by category">
            {"".join(chips)}
          </ul>
        </div>
        {feat_html}
        <div class="posts-lead">{lead_html}</div>
        <div class="posts-rows">{rows_html}</div>
        <p class="blog-empty-filter" hidden>No articles in this category yet.</p>
      </div>
    </section>'''
    else:
        listing = f'''
    <section class="section blog-list" aria-labelledby="soon-title">
      <div class="wrap">
        <div class="blog-soon reveal">
          <p class="eyebrow eyebrow--rule">Coming soon</p>
          <h2 class="h2" id="soon-title">The first articles are on the way.</h2>
          <ul class="blog-soon__cats" aria-label="Topics">{"".join(f"<li>{esc(c['name'])}</li>" for c in CATEGORIES)}</ul>
          <a class="btn btn--primary" href="{url("contact", out_path)}">Get Started {ICONS["arrow"]}</a>
        </div>
      </div>
    </section>'''

    demo_note = ""
    if any(a["is_demo"] for a in arts):
        demo_note = '<div class="demo-bar" role="note"><b>Preview build</b> <span class="demo-bar__long">Articles marked “Demo” are placeholders that show the layout. They are excluded from the production build.</span><span class="demo-bar__short">“Demo” articles are layout placeholders.</span></div>'

    head_html = head(out_path, key, cfg["title"], cfg["description"], index=cfg.get("index", True),
                     extra=f'<link rel="stylesheet" href="{P}assets/css/blog.css">\n' + page_jsonld(key, cfg["title"], cfg["description"]))
    page = f'''<!doctype html>
<html lang="en" class="no-js">
<head>
{head_html}
</head>
<body class="blog-page">
{header(out_path, "blog")}
{demo_note}
<main id="main">
  <section class="blog-hero" aria-labelledby="blog-title">
    <div class="blog-hero__bg" aria-hidden="true">
      <img src="{P}assets/img/summit.webp" width="1640" height="661" alt="" decoding="async">
    </div>
    <img class="blog-hero__mark" src="{P}assets/img/logo-icon-lg.webp" width="658" height="653" alt="" aria-hidden="true" decoding="async">
    <div class="wrap">
      <div class="masthead">
        <span>Meridian Performance</span>
        <span class="masthead__topics">{" · ".join(esc(c["name"]) for c in CATEGORIES)}</span>
      </div>
      <div class="blog-hero__grid">
        <div>
          <p class="eyebrow eyebrow--rule">Meridian Insights</p>
          <h1 class="blog-hero__title" id="blog-title"><span class="line"><span class="metal">Train smarter.</span></span><span class="line"><span class="metal-red">Live stronger.</span></span></h1>
        </div>
        <p class="blog-hero__copy">Training, nutrition, mindset and practical strategies to help you make better decisions and keep moving forward.</p>
      </div>
    </div>
  </section>
  {listing}
</main>
{footer(out_path)}
</body>
</html>
'''
    write(out_path, page)


def article_jsonld(a, title, desc):
    """BlogPosting + BreadcrumbList for real published articles (never demos, never without a domain)."""
    if a["is_demo"] or not BASE or PREVIEW:
        return ""
    key = "article:" + a["slug"]
    post = {
        "@type": "BlogPosting", "@id": abs_url(key) + "#article",
        "headline": a["title"], "description": desc,
        "mainEntityOfPage": {"@type": "WebPage", "@id": abs_url(key)},
        "datePublished": a.get("date"), "dateModified": a.get("updated") or a.get("date"),
        "articleSection": CAT_NAME.get(a.get("category")),
        "inLanguage": "en-US",
        "isPartOf": {"@id": abs_url("blog")},
        "publisher": {"@type": "Organization", "@id": biz_id(), "name": BIZ["name"],
                      "logo": {"@type": "ImageObject", "url": abs_asset("assets/img/logo-full.webp")}},
    }
    if a.get("hero", {}).get("src"):
        post["image"] = [abs_asset(a["hero"]["src"])]
    if a.get("author") in AUTHORS:
        au = AUTHORS[a["author"]]
        post["author"] = {"@type": "Person", "@id": person_id(a["author"]), "name": au["name"], "url": abs_url(au.get("about_page", "about"))}
    if a.get("topics"):
        post["keywords"] = ", ".join(a["topics"])
    post = {k: v for k, v in post.items() if v}
    crumbs = {"@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Home", "item": abs_url("home")},
        {"@type": "ListItem", "position": 2, "name": "Blog", "item": abs_url("blog")},
        {"@type": "ListItem", "position": 3, "name": a["title"], "item": abs_url(key)}]}
    return ld({"@context": "https://schema.org", "@graph": [post, crumbs]})


def related_for(a, arts, n=3):
    """Shared topics first, then same category, then most recent."""
    others = [x for x in arts if x is not a]
    topics = set(a.get("topics") or [])
    score = lambda x: (len(topics & set(x.get("topics") or [])), x.get("category") == a.get("category"))
    return sorted(others, key=score, reverse=True)[:n]


def build_article(a, arts):
    key = "article:" + a["slug"]
    out_path = out_path_for(key)
    P = prefix(out_path)
    seo = a.get("seo") or {}
    title = seo.get("title") or f'{a["title"]} | Meridian Insights'
    desc = seo.get("description") or a.get("excerpt", "")
    author = AUTHORS.get(a.get("author"), {"name": "", "role": ""})
    hero = a.get("hero") or {}
    cap = hero.get("caption")
    body = render_markers(a["body"], out_path, key)
    hero_html = ""
    if hero.get("src"):
        hero_html = (f'''<figure class="article-hero">
      <div class="article-hero__frame"><img {img_attrs(a, out_path, "(max-width: 640px) 100vw, 92vw")} alt="{esc(hero.get("alt"))}" width="1600" height="900" fetchpriority="high" decoding="async"></div>
      {f'<figcaption>{esc(cap)}</figcaption>' if cap else ""}
    </figure>''')
    cat = CAT_NAME.get(a.get("category"), "")

    related = related_for(a, arts)
    related_html = ""
    if related:
        related_html = f'''<section class="related" aria-labelledby="related-title">
    <div class="wrap">
      <div class="related__head"><h2 class="eyebrow eyebrow--rule" id="related-title">Keep reading</h2><a class="text-link" href="{url("blog", out_path)}">All articles {ICONS["arrow"]}</a></div>
      <div class="related__grid">{"".join(preview_card(x, out_path, "lead") for x in related)}</div>
    </div>
  </section>'''

    demo_note = ""
    if a["is_demo"]:
        demo_note = '<div class="demo-bar" role="note"><b>Template preview</b> <span class="demo-bar__long">Placeholder content showing the article layout. This is not a published Meridian Performance article.</span><span class="demo-bar__short">Placeholder, not a published article.</span></div>'

    author_name = "Author name" if a["is_demo"] else author.get("name", "")
    author_link = (f'<a href="{url(author.get("about_page", "about"), out_path)}" rel="author">{esc(author_name)}</a>'
                   if not a["is_demo"] and author.get("about_page") else esc(author_name))
    og_src = seo.get("og_image") or hero.get("src")
    og = {"src": og_src, "alt": hero.get("alt") or a["title"]} if og_src else None
    extra = f'<link rel="stylesheet" href="{P}assets/css/blog.css">'
    if a.get("date") and BASE and not a["is_demo"]:
        extra += f'\n<meta property="article:published_time" content="{a["date"]}">'
        if a.get("updated"):
            extra += f'\n<meta property="article:modified_time" content="{a["updated"]}">'
        extra += f'\n<meta property="article:section" content="{esc(cat)}">'
    jl = article_jsonld(a, title, desc)
    if jl:
        extra += "\n" + jl
    head_html = head(out_path, key, title, desc, og_image=og, og_type="article",
                     index=not a["is_demo"], extra=extra)
    page = f'''<!doctype html>
<html lang="en" class="no-js">
<head>
{head_html}
</head>
<body class="blog-page article-page">
<div class="read-progress" aria-hidden="true"><i></i></div>
{header(out_path, "blog")}
{demo_note}
<main id="main">
  <article class="article">
    <header class="article-head">
      <div class="wrap">
        <nav aria-label="Breadcrumb"><p class="crumbs"><a href="{url("blog", out_path)}">Blog</a><span aria-hidden="true">/</span>{esc(cat)}</p></nav>
        <p class="post__cat article-head__cat"><span>{esc(cat)}</span>{demo_badge(a)}</p>
        <h1 class="article-head__title">{esc(a["title"])}</h1>
        {f'<p class="article-head__deck">{esc(a["deck"])}</p>' if a.get("deck") else ""}
        <div class="byline">
          <img class="byline__mark" src="{P}assets/img/logo-icon.webp" width="329" height="326" alt="">
          <div>
            <p class="byline__name">{author_link}</p>
            {meta_row(a)}
          </div>
        </div>
      </div>
    </header>
    {hero_html}
    <div class="prose">
{body}
    </div>
  </article>
  {article_cta(out_path)}
  {related_html}
</main>
{footer(out_path)}
</body>
</html>
'''
    write(out_path, page)

# ---------------------------------------------------------------- sitemap / robots
def write_sitemap_and_robots(arts):
    if PREVIEW:
        # Preview/staging builds are never meant to be indexed. This file only exists in preview/.
        (OUT / "robots.txt").write_text("# PREVIEW BUILD - not for production\nUser-agent: *\nDisallow: /\n")
        return
    robots = "User-agent: *\nAllow: /\n"
    if BASE:
        today = datetime.date.today().isoformat()
        entries = [(abs_url(k), None) for k, cfg in PAGES.items() if cfg.get("index", True) and k != "404"]
        entries += [(abs_url("article:" + a["slug"]), a.get("updated") or a.get("date")) for a in arts if not a["is_demo"]]
        newest = max((a.get("updated") or a.get("date") or "" for a in arts), default="")
        xml = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
        for loc, lastmod in entries:
            if loc == abs_url("blog") and newest:
                lastmod = newest
            xml.append(f"  <url><loc>{esc(loc)}</loc>" + (f"<lastmod>{lastmod}</lastmod>" if lastmod else "") + "</url>")
        xml.append("</urlset>")
        (OUT / "sitemap.xml").write_text("\n".join(xml) + "\n")
        robots += f"\nSitemap: {BASE}/sitemap.xml\n"
    (OUT / "robots.txt").write_text(robots)

# ---------------------------------------------------------------- output
def write(out_path, text):
    p = OUT / out_path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)
    print("built", out_path)


def build():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    shutil.copytree(ROOT / "assets", OUT / "assets",
                    ignore=None if PREVIEW else shutil.ignore_patterns("demo"))
    for key, cfg in PAGES.items():
        if "template" not in cfg:
            continue
        text = (SRC / cfg["template"]).read_text()
        write(out_path_for(key), render_markers(text, out_path_for(key), key, is_home=(key == "home")))
    arts = load_articles()
    build_blog_index(arts)
    for a in arts:
        build_article(a, arts)
    write_sitemap_and_robots(arts)
    if not BASE and not PREVIEW:
        WARNINGS.append("No production domain set (content/site.json base_url or --base-url). Canonical URLs, og:url/og:image, "
                        "structured data and sitemap.xml are skipped until it is set.")
    for k, _, _, u in social_urls():
        if not u and not PREVIEW:
            WARNINGS.append(f"social.{k} is empty in content/site.json: its icon is hidden until a URL is added.")
    for w in WARNINGS:
        print("WARNING:", w)


if __name__ == "__main__":
    build()
