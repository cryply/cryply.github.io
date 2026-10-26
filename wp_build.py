#!/usr/bin/env python3
"""Собрать статический сайт borisivanov.com из ОРИГИНАЛЬНОГО бэкапа WordPress.

Это вторая, правильная версия. Первая (build_site.py) собирала сайт из
выскребленных копий web.archive.org — она сработала и дала все 31 статью,
но исходник нашёлся, и он лучше: оригинальная разметка вместо вытащенной
из чужого HTML, полноразмерные картинки, точные даты и 260 комментариев.

Вход:
  --sql   дамп базы (borr_wp_2015.sql)
  --root  распакованный public_html из borisivanov.com.tar.gz
  --out   куда писать сайт

    tar xzf borisivanov.com.tar.gz
    python3 tools/wp_build.py \\
        --sql borisivanov.com/borr_wp_2015.sql \\
        --root borisivanov.com/public_html \\
        --out ~/work/cryply.github.io

Что делает с содержимым:
  * берёт из wp_posts только post_type=post и post_status=publish;
  * ПЕРВЫМ ДЕЛОМ прячет блоки кода [source]/[sourcecode] за плейсхолдеры
    и только потом трогает остальное. Иначе wpautop наставит <p> внутри
    VHDL, а поиск шорткодов найдёт в коде конструкции вида get_ports[...]
    и [i] и примет их за разметку WordPress;
  * повторяет wpautop: пустая строка — абзац, одиночный перевод — <br>;
  * формулы mathtex (картинки с мёртвого Google Chart API) превращает в
    KaTeX — TeX лежит прямо в alt и в параметре chl;
  * ссылки и картинки делает относительными, чтобы сайт открывался и с
    диска, и на домене, и из подкаталога;
  * печатает комментарии: на FPGA-туториалах это живые вопросы читателей
    с ответами автора, и для портфолио они ценнее самих статей.

Адреса статей — /YYYY/MM/slug/, как было на сайте, чтобы старые входящие
ссылки продолжали работать.

Новые заметки (после 2019) живут не в дампе, а в Markdown:
  --notes notes/   каталог с *.md; front matter между строками '---':
      title:   заголовок
      date:    2026-10-26
      section: llm            (ключ из SECTIONS, иначе попадёт в Other)
      summary: одна строка для <meta description> (необязательно)
      license: own | mixed    (по умолчанию own)
      draft:   true           (пропускается, если не передан --drafts)
  Тело — Markdown (python-markdown: fenced_code, tables). Картинки и прочие
  файлы кладутся рядом в src/notes/<slug>/ и копируются в /notes/<slug>/.

  Адреса новых заметок — /notes/<slug>/, НЕ /YYYY/MM/slug/: даты в пути
  принадлежат архиву 2015–2016 и означают «так было на сайте». Свежий
  текст под таким адресом выглядел бы частью архива, а подвал у него
  другой.

  ВАЖНО: исходники держать ВНЕ каталога вывода. --out — корень
  репозитория сайта, и в нём же появляется /notes/<slug>/index.html.
  Если исходный каталог тоже назвать notes/, copytree будет копировать
  src/notes/<slug>/ сам на себя. Поэтому исходники — в src/notes/.
"""

from __future__ import annotations

import argparse
import hashlib
import html as htmllib
import os
import re
import shutil
import sys
import urllib.parse

SITE_TITLE = "Boris Ivanov"
SITE_SUB = "Notes on C++, FPGA and security — an archive, 2015–2016"
CNAME = "borisivanov.com"
LANG = {"c": "cpp", "cpp": "cpp", "c++": "cpp", "vhdl": "vhdl",
        "verilog": "verilog", "python": "python", "bash": "bash"}

SECTIONS = [
    ("Local LLMs", "llm",
     "Running open-weight models on a DGX Spark-class box: what fits, how fast, "
     "and whether the code they write actually compiles."),
    ("FPGA", "electronics",
     "Step-by-step walkthroughs on a Digilent Zybo board "
     "(Xilinx Zynq-7010) with Vivado 2015. Project sources included."),
    ("C++ design patterns", "programming",
     "A run through the Gang of Four catalogue: what each pattern is for, "
     "a diagram, trade-offs, and working C++."),
    ("Security", "security", "Cryptography, worked through by hand."),
    ("Other", None, ""),
]

ELSEWHERE = [
    ("LinkedIn", "https://www.linkedin.com/in/borisivanov2025"),
    ("GitHub", "https://github.com/cryply"),
    ("Stack Overflow", "https://stackoverflow.com/users/711654/boris-ivanov"),
]

KATEX = (
    '<link rel="stylesheet" '
    'href="https://cdnjs.cloudflare.com/ajax/libs/KaTeX/0.16.9/katex.min.css">\n'
    '<script defer '
    'src="https://cdnjs.cloudflare.com/ajax/libs/KaTeX/0.16.9/katex.min.js"></script>\n'
    '<script defer '
    'src="https://cdnjs.cloudflare.com/ajax/libs/KaTeX/0.16.9/contrib/auto-render.min.js" '
    'onload="renderMathInElement(document.body,{delimiters:['
    '{left:String.fromCharCode(92)+String.fromCharCode(40),'
    'right:String.fromCharCode(92)+String.fromCharCode(41),display:false}],'
    'throwOnError:false})"></script>\n'
)

CSS = """\
:root { --fg:#1b1b1b; --muted:#666; --bg:#fdfdfc; --accent:#8a3324; --line:#e3e0da;
        --code-bg:#f5f3ef; }
@media (prefers-color-scheme: dark) { :root {
  --fg:#e6e4e0; --muted:#9a968e; --bg:#16161a; --accent:#d98b6a; --line:#2e2e34;
  --code-bg:#1e1e24; } }
* { box-sizing:border-box; }
/* Кегль и ширина подобраны под широкий монитор: Georgia мелкая в своём
   кегле, и 16px в колонке на 46rem читались тяжело. Теперь базовый
   размер плавает от 17px на телефоне до 22px на большом экране, а
   колонка — 52rem, то есть растёт вместе со шрифтом.
   КРУТИТЬ ЗДЕСЬ, если захочется иначе: верхняя граница в clamp() —
   размер текста, max-width — ширина колонки. Больше 56rem при таком
   кегле строка становится длинной и глаз начинает терять начало. */
body { margin:0 auto; padding:3rem 1.2rem 6rem; max-width:52rem; background:var(--bg);
  color:var(--fg);
  font:clamp(17px, 0.95rem + 0.45vw, 22px)/1.7 Georgia,"Iowan Old Style",serif;
  -webkit-text-size-adjust:100%; }
a { color:var(--accent); }
header.site h1 { margin:0 0 .25rem; font-size:1.8rem; letter-spacing:-.01em; }
header.site { margin-bottom:2.5rem; }
header.site p { margin:0; color:var(--muted); font-size:1rem; }
header.site p.elsewhere { margin-top:.7rem; font-size:.95rem; }
nav.back { margin-bottom:1.5rem; font-size:.95rem; }
section.group { margin:0 0 2.5rem; }
section.group h2 { font-size:1.25rem; margin:0 0 .35rem; }
section.group > p { margin:0 0 1.1rem; color:var(--muted); font-size:.97rem; }
ul.posts { list-style:none; margin:0; padding:0; }
ul.posts li { display:flex; gap:1rem; padding:.5rem 0; border-bottom:1px solid var(--line); }
ul.posts time { flex:0 0 6.4rem; color:var(--muted); font-size:.88rem;
  font-family:ui-monospace,SFMono-Regular,Menlo,monospace; padding-top:.2rem; }
article h1 { font-size:1.75rem; line-height:1.25; margin:0 0 .35rem; }
article h3 { font-size:1.2rem; margin:2.2rem 0 .6rem; }
.meta { color:var(--muted); font-size:.88rem; margin:0 0 2.2rem;
  font-family:ui-monospace,SFMono-Regular,Menlo,monospace; }
article img { max-width:100%; height:auto; display:block; margin:1.2rem 0;
  border:1px solid var(--line); border-radius:3px; }
pre { background:var(--code-bg); border:1px solid var(--line); border-radius:4px;
  padding:1rem 1.1rem; overflow-x:auto; font-size:.86rem; line-height:1.55; }
pre code { font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; }
:not(pre) > code { background:var(--code-bg); padding:.1em .35em; border-radius:3px;
  font-size:.88em; }
blockquote { margin:1.2rem 0; padding-left:1rem; border-left:3px solid var(--line);
  color:var(--muted); }
footer.site { margin-top:4rem; padding-top:1.2rem; border-top:1px solid var(--line);
  color:var(--muted); font-size:.9rem; line-height:1.55; }
.note { background:var(--code-bg); border:1px solid var(--line); border-radius:4px;
  padding:.9rem 1.1rem; font-size:.95rem; color:var(--muted); margin:0 0 2.2rem; }
.comments { margin-top:3.5rem; border-top:1px solid var(--line); padding-top:1.5rem; }
.comments h2 { font-size:1.2rem; margin:0 0 1rem; }
.comment { margin:0 0 1.3rem; font-size:1rem; }
.comment.reply { margin-left:1.5rem; padding-left:1rem; border-left:2px solid var(--line); }
.comment .who { font-size:.85rem; color:var(--muted);
  font-family:ui-monospace,SFMono-Regular,Menlo,monospace; }
.comment p { margin:.3rem 0 0; }
article table { border-collapse:collapse; margin:1.2rem 0; font-size:.88rem; width:100%;
  display:block; overflow-x:auto; }
article th, article td { border-bottom:1px solid var(--line); padding:.35rem .7rem;
  text-align:left; white-space:nowrap; }
article th { color:var(--muted); font-weight:normal;
  font-family:ui-monospace,SFMono-Regular,Menlo,monospace; }
article td.num, article th.num { text-align:right; font-variant-numeric:tabular-nums; }
"""

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<meta name="author" content="Boris Ivanov">
<link rel="stylesheet" href="{root}style.css?v={cssver}">
{head_extra}</head>
<body>
{content}
<footer class="site">{footer}</footer>
</body>
</html>
"""


# ───────────────────────────── разбор дампа ─────────────────────────────

def sql_rows(sql: str, table: str):
    """Строки из INSERT INTO `table`. Без mysql — потоковый токенайзер."""
    for m in re.finditer(r"INSERT INTO `" + table + r"` \(([^)]*)\) VALUES\s*", sql):
        cols = [c.strip(" `") for c in m.group(1).split(",")]
        i = m.end()
        while i < len(sql) and sql[i] == "(":
            i += 1
            vals, cur, inq, esc = [], [], False, False
            while i < len(sql):
                ch = sql[i]
                if inq:
                    if esc:
                        cur.append({"n": "\n", "t": "\t", "r": "\r",
                                    "0": "\0"}.get(ch, ch))
                        esc = False
                    elif ch == "\\":
                        esc = True
                    elif ch == "'":
                        inq = False
                    else:
                        cur.append(ch)
                else:
                    if ch == "'":
                        inq = True
                    elif ch == ",":
                        vals.append("".join(cur)); cur = []
                    elif ch == ")":
                        vals.append("".join(cur)); i += 1; break
                    elif not ch.isspace():
                        cur.append(ch)
                i += 1
            yield dict(zip(cols, vals))
            while i < len(sql) and sql[i] in " \n\r\t,":
                i += 1


# ──────────────────────────── рендер контента ───────────────────────────

# Блочные теги — список тот же, что в wpautop() самого WordPress.
BLOCK = (r"table|thead|tfoot|caption|col|colgroup|tbody|tr|td|th|div|dl|dd|dt"
         r"|ul|ol|li|pre|form|map|area|blockquote|address|style|p|h[1-6]|hr"
         r"|fieldset|legend|section|article|aside|hgroup|header|footer|nav"
         r"|figure|figcaption|details|menu|summary")


def wpautop(text: str) -> str:
    """Повторяет wpautop() из WordPress.

    Важно не просто резать по пустым строкам: в постах сплошь и рядом
    встречается `</h3>\\nтекст\\n<h3>` без единой пустой строки, и если
    резать только по ним, текст между заголовками останется голым, без
    <p>. WordPress поэтому сначала САМ расставляет пустые строки вокруг
    блочных тегов, и только потом делит. Делаем так же.
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"<(" + BLOCK + r")\b([^>]*)>", r"\n\n<\1\2>", text, flags=re.I)
    text = re.sub(r"</(" + BLOCK + r")>", r"</\1>\n\n", text, flags=re.I)
    text = re.sub(r"(<(?:hr|br)\s*/?>)", r"\n\n\1\n\n", text, flags=re.I)

    out = []
    for b in re.split(r"\n\s*\n", text):
        b = b.strip()
        if not b:
            continue
        if re.match(r"^<(?:" + BLOCK + r"|/)", b, re.I):
            out.append(b)
        else:
            out.append("<p>" + b.replace("\n", "<br />\n") + "</p>")
    return "\n".join(out)


def render(content: str, prefix: str) -> str:
    """post_content -> готовый HTML."""
    stash: list[str] = []

    def keep(html: str) -> str:
        stash.append(html)
        return f"\x00CODE{len(stash) - 1}\x00"

    # 1. Код прячем ПЕРВЫМ. Внутри VHDL и C полно конструкций вида
    #    get_ports[...] и [i], которые иначе будут приняты за шорткоды.
    def code(m: re.Match) -> str:
        lang = (m.group("lang") or "").strip().lower()
        cls = f' class="language-{LANG.get(lang, lang)}"' if lang else ""
        body = m.group("body")
        body = htmllib.unescape(body).strip("\n")
        return keep(f"<pre><code{cls}>{htmllib.escape(body)}</code></pre>")

    content = re.sub(
        r"\[(?P<tag>source|sourcecode)(?:[^\]]*?language=[\"'](?P<lang>[^\"']+)[\"'])?"
        r"[^\]]*\](?P<body>.*?)\[/(?P=tag)\]",
        code, content, flags=re.S | re.I)

    # 2. [caption ...]<img>подпись[/caption] -> figure
    def caption(m: re.Match) -> str:
        inner = m.group(1).strip()
        im = re.search(r"<img[^>]*>", inner)
        cap = re.sub(r"<img[^>]*>", "", inner).strip()
        return ("<figure>" + (im.group(0) if im else "") +
                (f"<figcaption>{cap}</figcaption>" if cap else "") + "</figure>")

    content = re.sub(r"\[caption[^\]]*\](.*?)\[/caption\]", caption, content, flags=re.S)
    content = re.sub(r"\[/?embed[^\]]*\]", "", content)

    # 3. Абзацы
    content = wpautop(content)
    # Плейсхолдер кода для wpautop — обычный текст, поэтому он успевает
    # завернуться в <p>. А <pre> внутри <p> — невалидная разметка, браузер
    # закроет абзац сам и вёрстка поедет. Снимаем обёртку.
    content = re.sub(r"<p>\s*(\x00CODE\d+\x00)\s*</p>", r"\1", content)

    # 4. Формулы: картинки мёртвого Google Chart API -> KaTeX
    def math(m: re.Match) -> str:
        tag = m.group(0)
        a = re.search(r'alt="([^"]*)"', tag)
        tex = htmllib.unescape(a.group(1)) if a else ""
        if not tex:
            u = re.search(r"[?&]chl=([^\"&]*)", htmllib.unescape(tag))
            tex = urllib.parse.unquote_plus(u.group(1)) if u else ""
        return ('<span class="math">\\(' + htmllib.escape(tex, quote=False) +
                "\\)</span>") if tex else tag

    content = re.sub(r"<img[^>]*chart\.apis\.google\.com[^>]*>", math, content)

    # 5. Ссылки и картинки -> относительные
    content = re.sub(r"https?://(?:www\.)?borisivanov\.com/?", "/", content)
    content = re.sub(r"/index\.php/(\d{4})/(\d{2})/\d{2}/", r"/\1/\2/", content)
    content = re.sub(r'((?:href|src)=")/(?!/)', lambda m: m.group(1) + prefix, content)
    content = re.sub(r"\s*onclick=\"__gaTracker\([^\"]*\)[^\"]*\"", "", content)
    content = re.sub(r'\s(?:width|height)="\d+"', "", content)

    # 6. Возвращаем код на место
    for n, html in enumerate(stash):
        content = content.replace(f"\x00CODE{n}\x00", html)
    return content


def text_of(h: str) -> str:
    t = re.sub(r"<script.*?</script>|<style.*?</style>", " ", h, flags=re.S | re.I)
    return re.sub(r"\s+", " ", htmllib.unescape(re.sub(r"<[^>]+>", " ", t))).strip()


def esc(s: str) -> str:
    return htmllib.escape(s, quote=True)


# ─────────────────────────── заметки в Markdown ──────────────────────────

def load_notes(notes_dir: str, drafts: bool) -> list[dict]:
    """notes/*.md -> список словарей того же вида, что и посты из дампа."""
    if not notes_dir or not os.path.isdir(notes_dir):
        return []
    try:
        import markdown  # python-markdown; нужен только для новых заметок
    except ImportError:
        print("нет пакета markdown: pip install markdown", file=sys.stderr)
        raise
    out = []
    for fn in sorted(os.listdir(notes_dir)):
        if not fn.endswith(".md"):
            continue
        raw = open(os.path.join(notes_dir, fn), encoding="utf-8").read()
        m = re.match(r"---\n(.*?)\n---\n(.*)", raw, re.S)
        if not m:
            print(f"  {fn}: нет front matter — пропускаю", file=sys.stderr)
            continue
        meta = {}
        for line in m.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip().strip('"').strip("'")
        if meta.get("draft", "").lower() == "true" and not drafts:
            print(f"  {fn}: черновик — пропускаю (--drafts, чтобы включить)")
            continue
        slug = meta.get("slug") or re.sub(r"^\d{4}-\d{2}(-\d{2})?-", "", fn[:-3])
        body = markdown.markdown(m.group(2), extensions=["fenced_code", "tables"],
                                 output_format="html5")
        out.append({"title": meta["title"], "date": meta["date"], "slug": slug,
                    "section": meta.get("section", ""),
                    "summary": meta.get("summary", ""),
                    "license": meta.get("license", "own"),
                    "assets": os.path.join(notes_dir, slug), "html": body})
    return out


# ──────────────────────────────── сборка ────────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sql", required=True)
    ap.add_argument("--root", required=True, help="распакованный public_html")
    ap.add_argument("--out", required=True)
    ap.add_argument("--no-comments", action="store_true")
    ap.add_argument("--notes", help="каталог с новыми заметками *.md")
    ap.add_argument("--drafts", action="store_true", help="включить draft: true")
    a = ap.parse_args()

    sql = open(a.sql, encoding="utf-8", errors="replace").read()

    posts = [p for p in sql_rows(sql, "wp_posts")
             if p.get("post_type") == "post" and p.get("post_status") == "publish"]
    if not posts:
        print("В дампе нет опубликованных постов.", file=sys.stderr)
        return 1

    terms = {t["term_id"]: t for t in sql_rows(sql, "wp_terms")}
    tax = {t["term_taxonomy_id"]: t for t in sql_rows(sql, "wp_term_taxonomy")}
    rel: dict[str, list[str]] = {}
    for r in sql_rows(sql, "wp_term_relationships"):
        tt = tax.get(r["term_taxonomy_id"])
        if not tt:
            continue
        term = terms.get(tt["term_id"])
        if term:
            rel.setdefault(r["object_id"], []).append(
                f'{tt["taxonomy"]}:{term["slug"]}')

    comments: dict[str, list[dict]] = {}
    if not a.no_comments:
        for c in sql_rows(sql, "wp_comments"):
            if c.get("comment_approved") != "1" or c.get("comment_type"):
                continue
            comments.setdefault(c["comment_post_ID"], []).append(c)

    os.makedirs(a.out, exist_ok=True)
    # Отпечаток таблицы стилей в адресе: GitHub Pages отдаёт css с
    # кэшированием, и после правки стилей браузер ещё долго показывает
    # старый файл. Меняется содержимое — меняется адрес — кэш не при чём.
    cssver = hashlib.sha256(CSS.encode()).hexdigest()[:8]
    posts.sort(key=lambda p: p["post_date"])
    # Лицензия считается ПО СТАТЬЯМ, а не одной фразой на весь сайт.
    # Проверено по дампу: у трёх FPGA-разборов ноль внешних картинок и
    # ноль ссылок на чужие источники — они целиком авторские. В части
    # заметок по паттернам чужое есть и подписано на месте (cs.unc.edu,
    # patterns.pl, cpp-reference.ru, sourcemaking.com, Викимедиа).
    # Поэтому страница, где всё своё, говорит это прямо, а страница с
    # заимствованиями — оговаривает их. Общая фраза «всё моё под CC BY»
    # на витрине для технарей хуже, чем её отсутствие.
    ARCHIVE_NOTE = ('Written 2015–2016. Republished as a static archive — '
                    'text, dates and comments unchanged.')
    CC = ('<a href="https://creativecommons.org/licenses/by/4.0/" '
          'rel="license">CC&nbsp;BY&nbsp;4.0</a>')
    LIC_OWN = (f'© 2015–2026 Boris Ivanov. Entirely my own work — text, code '
               f'and screenshots. Reuse with attribution under {CC}.')
    LIC_MIXED = (f'© 2015–2026 Boris Ivanov. My own text and code: reuse with '
                 f'attribution under {CC}. Third-party code and diagrams '
                 f'remain with their authors and are credited where they '
                 f'appear.')
    foot = f"{ARCHIVE_NOTE}<br>{LIC_MIXED}"
    arts = []

    for p in posts:
        date = p["post_date"]
        y, mth = date[:4], date[5:7]
        slug = p["post_name"]
        up = "../../../"
        raw = p["post_content"]
        # chart.apis.google.com не считается чужим: это сервис, который
        # рендерил ЕГО собственный TeX картинкой. Формулы теперь KaTeX.
        ext_img = [u for u in re.findall(r'<img[^>]+src="(https?://[^"]+)"', raw)
                   if "borisivanov.com" not in u
                   and "chart.apis.google.com" not in u]
        credited = re.search(r"(?:From|[Ss]ource:)\s*https?://", raw)
        page_foot = (f"{ARCHIVE_NOTE}<br>"
                     f"{LIC_MIXED if (ext_img or credited) else LIC_OWN}")
        body = render(raw, up)
        cats = [t.split(":", 1)[1] for t in rel.get(p["ID"], [])
                if t.startswith("category:")]

        cm = sorted(comments.get(p["ID"], []), key=lambda c: c["comment_date"])
        cm_html = ""
        if cm:
            items = []
            for c in cm:
                who = esc(c.get("comment_author") or "anonymous")
                when = c["comment_date"][:10]
                cls = "comment reply" if c.get("comment_parent", "0") != "0" else "comment"
                txt = wpautop(htmllib.escape(c["comment_content"]))
                items.append(f'<div class="{cls}"><div class="who">{who} · {when}'
                             f"</div>{txt}</div>")
            cm_html = ('\n<section class="comments">\n'
                       f"<h2>Comments ({len(cm)})</h2>\n" + "\n".join(items) +
                       "\n</section>")

        content = (f'<nav class="back"><a href="{up}">← Index</a></nav>\n'
                   f'<article>\n<h1>{esc(p["post_title"])}</h1>\n'
                   f'<p class="meta">Originally published {date[:10]} · '
                   f"Boris Ivanov</p>\n{body}\n</article>{cm_html}")

        d = os.path.join(a.out, y, mth, slug)
        os.makedirs(d, exist_ok=True)
        open(os.path.join(d, "index.html"), "w", encoding="utf-8").write(
            PAGE.format(title=esc(p["post_title"]) + " · " + SITE_TITLE,
                        desc=esc(text_of(body)[:160]), root=up,
                        content=content, footer=page_foot, cssver=cssver,
                        head_extra=KATEX if 'class="math"' in body else ""))

        arts.append({"url": f"{y}/{mth}/{slug}/", "slug": slug,
                     "title": p["post_title"], "date": date, "cats": cats,
                     "n_comments": len(cm)})

    # новые заметки из Markdown — адрес /notes/<slug>/, см. шапку файла
    notes = load_notes(a.notes, a.drafts)
    for n in notes:
        y = n["date"][:4]
        up = "../../"
        lic = LIC_MIXED if n["license"] == "mixed" else LIC_OWN
        content = (f'<nav class="back"><a href="{up}">← Index</a></nav>\n'
                   f'<article>\n<h1>{esc(n["title"])}</h1>\n'
                   f'<p class="meta">{n["date"][:10]} · Boris Ivanov</p>\n'
                   f'{n["html"]}\n</article>')
        d = os.path.join(a.out, "notes", n["slug"])
        if os.path.isdir(n["assets"]) and os.path.realpath(n["assets"]) == os.path.realpath(d):
            print(f"  {n['slug']}: исходники лежат в каталоге вывода — перенеси в src/notes/",
                  file=sys.stderr)
            return 1
        os.makedirs(d, exist_ok=True)
        if os.path.isdir(n["assets"]):
            shutil.copytree(n["assets"], d, dirs_exist_ok=True)
        desc = n["summary"] or text_of(n["html"])[:160]
        open(os.path.join(d, "index.html"), "w", encoding="utf-8").write(
            PAGE.format(title=esc(n["title"]) + " · " + SITE_TITLE,
                        desc=esc(desc), root=up, content=content,
                        footer=f"© {y} Boris Ivanov. {lic.split('. ', 1)[1]}",
                        cssver=cssver, head_extra=""))
        arts.append({"url": f"notes/{n['slug']}/", "slug": n["slug"],
                     "title": n["title"], "date": n["date"],
                     "cats": [n["section"]], "n_comments": 0})

    # индекс: внутри секции — новые сверху только для свежих заметок
    arts.sort(key=lambda x: x["date"])
    used, blocks = set(), []
    for name, cat, blurb in SECTIONS:
        grp = [x for x in arts if x["slug"] not in used
               and (cat is None or cat in x["cats"])]
        if not grp:
            continue
        used.update(x["slug"] for x in grp)
        items = "\n".join(
            f'  <li><time>{x["date"][:10]}</time>'
            f'<a href="{x["url"]}">{esc(x["title"])}</a></li>'
            for x in grp)
        bl = f"<p>{esc(blurb)}</p>\n" if blurb else ""
        blocks.append(f'<section class="group">\n<h2>{esc(name)}</h2>\n'
                      f'{bl}<ul class="posts">\n{items}\n</ul>\n</section>')

    links = " · ".join(f'<a href="{u}">{n}</a>' for n, u in ELSEWHERE)
    sub = SITE_SUB if not notes else "Notes on C++, FPGA, security and local LLMs"
    note = ('These notes were written in 2015 and 2016 and are '
            'republished here unchanged, with their original dates and the '
            'comments they drew at the time. The newest work is elsewhere; '
            'this is kept because it is still useful.') if not notes else (
            'The C++, FPGA and security notes were written in 2015–2016 and are '
            'republished unchanged, with their original dates and comments. '
            'Newer notes are dated as written.')
    index = (f'<header class="site">\n<h1>{SITE_TITLE}</h1>\n<p>{sub}</p>\n'
             f'<p class="elsewhere">{links}</p>\n</header>\n'
             f'<p class="note">{note}</p>\n' + "\n".join(blocks))
    open(os.path.join(a.out, "index.html"), "w", encoding="utf-8").write(
        PAGE.format(title=SITE_TITLE, desc=esc(sub), root="",
                    content=index, footer=foot, cssver=cssver, head_extra=""))

    open(os.path.join(a.out, "style.css"), "w", encoding="utf-8").write(CSS)
    open(os.path.join(a.out, "CNAME"), "w", encoding="utf-8").write(CNAME + "\n")
    open(os.path.join(a.out, ".nojekyll"), "w", encoding="utf-8").write("")

    # ресурсы: картинки, исходники проектов Vivado, PDF-версии
    copied = 0
    for sub in ("wp-content/uploads", "files", "fpga"):
        s_dir = os.path.join(a.root, sub)
        if not os.path.isdir(s_dir):
            print(f"  нет каталога {sub} — пропускаю", file=sys.stderr)
            continue
        d_dir = os.path.join(a.out, sub)
        ignore = shutil.ignore_patterns("mathtex", "js", "*.bak", "*.php")
        shutil.copytree(s_dir, d_dir, dirs_exist_ok=True, ignore=ignore)
        copied += sum(len(f) for _r, _d, f in os.walk(d_dir))

    # битые внутренние ссылки
    missing = set()
    for r, _d, fs in os.walk(a.out):
        for f in fs:
            if not f.endswith(".html"):
                continue
            t = open(os.path.join(r, f), encoding="utf-8").read()
            for href in re.findall(r'(?:href|src)="((?:\.\./)+[^"]+)"', t):
                tgt = os.path.normpath(os.path.join(
                    r, urllib.parse.unquote(href.split("?")[0])))
                if not (os.path.exists(tgt)
                        or os.path.exists(os.path.join(tgt, "index.html"))):
                    missing.add(href)

    total_cm = sum(x["n_comments"] for x in arts)
    print(f"новых заметок: {len(notes)}")
    print(f"статей: {len(arts)}  комментариев: {total_cm}  файлов скопировано: {copied}")
    print(f"готово: {os.path.abspath(a.out)}")
    if missing:
        print(f"\nбитые внутренние ссылки ({len(missing)}):")
        for h in sorted(missing)[:20]:
            print("  ", h)
    return 0


if __name__ == "__main__":
    sys.exit(main())
