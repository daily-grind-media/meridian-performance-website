# Meridian Performance website (V3)

A static site with no runtime dependencies. A small Python build script (Python 3.8+, standard library only) generates every page, the blog, sitemap.xml, robots.txt and the structured data from the files in `content/` and `src/`.

## Quick reference

| # | Task | Where |
|---|---|---|
| 1 | **Production domain** | `content/site.json` → `"base_url": "https://www.yourdomain.com"` (no trailing slash). Or pass it at build time: `python3 build.py --base-url=https://www.yourdomain.com` |
| 2 | **Facebook URL** | `content/site.json` → `"social"` → `"facebook"` |
| 3 | **Instagram URL** | `content/site.json` → `"social"` → `"instagram"` |
| 4 | **LinkedIn URL** | `content/site.json` → `"social"` → `"linkedin"` |
| 5 | **Add a blog article** | Copy `content/blog/_TEMPLATE/` to `content/blog/<slug>/`, fill in `meta.json` + `body.html`, set `"status": "published"` (details below) |
| 6 | **sitemap.xml** | Generated automatically by the production build (see below) |
| 7 | **robots.txt** | Generated automatically by every build (see below) |
| 8 | **Structured data** | Generated automatically from `content/` (see below) |
| 9 | **Production build** | `python3 build.py` creates `dist/`. Upload the contents of `dist/` to the host. |

`python3 build.py --preview` creates `preview/`: a review copy that includes the demo blog placeholders. It is noindexed and its robots.txt blocks all crawling. **Never upload `preview/` as the live site.**

## Domain (one value)

`base_url` in `content/site.json` fills in everything that needs an absolute URL:

- canonical URLs
- `og:url`, `og:image`, `twitter:image`
- sitemap.xml entries and the robots.txt `Sitemap:` line
- every structured-data URL and `@id`

Until `base_url` is set, the build skips those items (relative versions would be invalid) and prints a warning. Everything else works normally.

## Social links

The social links live in one place, `content/site.json`:

```json
"social": { "facebook": "", "instagram": "", "linkedin": "", "youtube": "" },
"social_order": ["facebook", "instagram", "linkedin"]
```

- Paste the full profile URLs (`https://…`).
- The same values feed the footer icons, the Contact page icons and the structured data (`sameAs`).
- **While a URL is empty, the production build hides that icon and prints a warning.** The site never links to a placeholder. The preview build shows empty ones as dimmed icons so the layout can be reviewed.
- **To add YouTube later:** fill `social.youtube` and add `"youtube"` to `social_order`. The icon already exists.
- Links open in a new tab with `rel="noopener noreferrer"` and an accessible label such as "Instagram (opens in a new tab)".
- Personal profiles for Chance can go in `content/authors.json` → `chance-dyck.social`. Only non-empty values are used.

## Location

The location is set once in `content/site.json` → `business.location_label` (`Del Mar, CA`). The footer, the mobile menu, the Contact page, the About page and the Coaching section all use it through the `{{LOCATION}}` marker, and the structured data uses `business.locality` / `region`.

## Page titles, descriptions and indexing

`content/pages.json` holds every static page's route, `title`, `description` and `index` flag.

- Pages with `"index": false` get `noindex, follow` and are left out of sitemap.xml. Privacy and Terms are set this way until their content exists, and the 404 page always is.
- **Adding a service landing page later** (e.g. `/personal-training/`): add an entry such as `"personal-training": {"template": "personal-training.html", "route": "personal-training/", "title": "...", "description": "...", "index": true}` and create `src/personal-training.html` (copy `src/about.html` as a starting point). It is then routed, linked with `{{U:personal-training}}` and added to the sitemap automatically.

## Adding a blog article

1. Copy `content/blog/_TEMPLATE/` to `content/blog/<article-slug>/`. Use lowercase words and hyphens. The folder name becomes the URL `/blog/<article-slug>/`.
2. Fill in `meta.json`:

| Field | Notes |
|---|---|
| `status` | `draft` (not built), `published` (built + sitemap + structured data), `demo` (preview only) |
| `title`, `deck` | Headline (the page's only H1) and optional subtitle |
| `category` | A slug from `content/categories.json` |
| `topics` | Optional list, e.g. `["fat-loss", "habits"]`. Used to pick related articles and for structured-data keywords. Good for building topic clusters. |
| `excerpt` | 1–2 sentences for the blog index and related articles |
| `date`, `updated` | `YYYY-MM-DD` |
| `author` | Key from `content/authors.json` |
| `hero` | `src` (1600×900 webp), `thumb` (900×600 webp), `alt`, optional `caption`. Store files in `assets/img/blog/<slug>/`. |
| `featured` | `true` puts it in the large featured slot (otherwise the newest article is featured) |
| `seo.title`, `seo.description`, `seo.og_image` | Unique search and share text. Title falls back to the headline, description to the excerpt, and og_image to the hero image. |

3. Write `body.html` with these elements:
   - `<p>`; `<p class="lede">` for the opening paragraph
   - `<h2>` for sections and `<h3>` for subsections
   - `<ul>`, `<ol>`
   - `<blockquote class="pull"><p>…</p></blockquote>`
   - `<figure><img src="{{A}}assets/img/blog/<slug>/x.webp" alt="…" width="1600" height="900" loading="lazy"><figcaption>…</figcaption></figure>`
   - `<aside class="callout"><p class="callout__label">Key takeaway</p><p>…</p></aside>`

   Internal links use markers that always resolve correctly:
   - `{{U:about}}`, `{{U:contact}}`, `{{U:blog}}`
   - `{{U:home}}#coaching`, `{{U:home}}#method`, `{{U:home}}#results`
   - `{{U:article:<other-slug>}}`
4. Run `python3 build.py`. The build automatically adds the index listing, category filter, reading time, related articles, the "Ready to put it into practice?" section (with links to Coaching, Method and About), canonical/OG tags, BlogPosting + Breadcrumb structured data, and the sitemap entry. It warns if a published article is missing a required field.

Delete the `content/blog/demo-*` folders and `assets/img/blog/demo/` once real articles exist. They are never included in production regardless.

## sitemap.xml

The production build writes `dist/sitemap.xml` when `base_url` is set. It lists:

- every page in `content/pages.json` with `"index": true` (Home, About, Contact, Blog)
- every article with `"status": "published"`, with `lastmod` taken from `updated` or `date`

Drafts, demos, Privacy/Terms (while noindexed) and the 404 page are excluded. You never edit it by hand.

## robots.txt

- **Production** (`dist/robots.txt`): `Allow: /`, plus `Sitemap: <base_url>/sitemap.xml` once the domain is set.
- **Preview** (`preview/robots.txt`): `Disallow: /`, and every preview page also carries `noindex, nofollow`.

The blocking rules exist only in the separate `preview/` folder, and every production build is generated fresh into `dist/`. Preview settings therefore can't carry over to the live site.

## Structured data (JSON-LD)

Generated once `base_url` is set, using only facts in `content/`:

| Page | Types |
|---|---|
| Home | `WebSite`, `LocalBusiness` (name, description, Del Mar / CA / US, area served, founder, the three services, social `sameAs`), `Person` (Chance Dyck, Founder) |
| About | `AboutPage` + `Person` + `LocalBusiness` |
| Contact | `ContactPage` |
| Blog | `Blog` |
| Articles | `BlogPosting` (headline, description, image, dates, author, publisher, section) + `BreadcrumbList` |

No street address, phone, hours, coordinates, ratings, prices or credentials are included. Add them to `content/site.json` and `business_node()` in `build.py` only once they are confirmed.

## 404 page

`dist/404.html` uses root-absolute links so it works at any URL depth. Netlify, Vercel, Cloudflare Pages and GitHub Pages serve it automatically. On Apache, add `ErrorDocument 404 /404.html`.

## Before launch

- [ ] Set `base_url`
- [ ] Add the social URLs
- [ ] Paste the GoHighLevel form and calendar embeds into `src/contact.html` (marked with comments)
- [ ] Add the Privacy/Terms content and set `"index": true` for them in `content/pages.json`
- [ ] Run `python3 build.py` and upload `dist/`

## Structure

```
assets/css/site.css    design system + site pages
assets/css/blog.css    blog index + article template
assets/js/site.js      all interactions (no libraries)
assets/fonts/          Russo One, Rajdhani, Inter (supplied files, woff2 subsets + OFL licences)
content/               site.json, pages.json, authors.json, categories.json, blog/
src/                   page templates (index, about, contact, privacy, terms, 404)
build.py               builder
```
