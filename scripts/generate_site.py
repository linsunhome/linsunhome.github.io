#!/usr/bin/env python3
"""Generate the static bilingual site from the checked-in content snapshots."""

from __future__ import annotations

import html
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

papers = json.loads((DATA / "scholar-2026-11-10.json").read_text())["papers"]
media_data = json.loads((DATA / "media-links-2026-11-10.json").read_text())
site_content = json.loads((DATA / "site-content.json").read_text())
publication_metadata = json.loads((DATA / "publication-metadata.json").read_text())
media = media_data["items"]
talks = media_data.get("talks", [])
published_media = [item for item in media if item.get("publish") and item.get("title")]
media_translations = {item.get("url"): item for item in site_content.get("media", []) if item.get("url")}

MEDIA_KINDS = {"media-interview", "institutional-news", "talk-transcript", "talk"}
TEAM_KINDS = {"team-news", "team-technical-article", "company-news"}
PROJECT_KINDS = {"project-background"}
VIDEO_KINDS = {"video"}


def esc(value: object) -> str:
    return html.escape(str(value or ""), quote=True)


def external_link(url: str | None, label: str, *, css: str = "") -> str:
    if not url:
        return f"<strong>{esc(label)}</strong>"
    class_attr = f' class="{esc(css)}"' if css else ""
    return f'<a{class_attr} href="{esc(url)}" target="_blank" rel="noopener">{esc(label)} ↗</a>'


def nav(lang: str, active: str) -> str:
    labels = {
        "zh": [("about", "关于", "/about/"), ("research", "研究与项目", "/research/"), ("publications", "论文", "/publications/"), ("impact", "影响与交流", "/impact/")],
        "en": [("about", "About", "/en/about/"), ("research", "Research & Projects", "/en/research/"), ("publications", "Publications", "/en/publications/"), ("impact", "Impact & Talks", "/en/impact/")],
    }
    links = "".join(
        f'<a href="{href}"' + (" aria-current=\"page\"" if key == active else "") + f">{label}</a>"
        for key, label, href in labels[lang]
    )
    switch_routes = {
        "home": ("/", "/en/"),
        "about": ("/about/", "/en/about/"),
        "research": ("/research/", "/en/research/"),
        "publications": ("/publications/", "/en/publications/"),
        "impact": ("/impact/", "/en/impact/"),
    }
    if active.startswith("projects/"):
        slug = active.split("/", 1)[1]
        switch = f'/{"en/" if lang == "zh" else ""}projects/{slug}/'
    else:
        switch = switch_routes.get(active, switch_routes["home"])[1 if lang == "zh" else 0]
    switch_label = "EN" if lang == "zh" else "中文"
    return f'''<header class="site-header"><div class="wrap nav">
      <a class="brand" href="{'/' if lang == 'zh' else '/en/'}"><strong>{'孙林' if lang == 'zh' else 'Lin Sun'}</strong><span>LIN SUN / AI BUILDER</span></a>
      <button class="menu-toggle" data-menu-toggle aria-controls="main-navigation" aria-expanded="false" aria-label="{'展开导航' if lang == 'zh' else 'Toggle navigation'}">☰</button>
      <nav class="nav-links" id="main-navigation" data-nav>{links}</nav>
      <div class="nav-tools"><a class="lang" href="{switch}">{switch_label}</a></div>
    </div></header>'''


def footer(lang: str) -> str:
    text = "研究 · 工程 · 管理 · 公开交流" if lang == "zh" else "RESEARCH · ENGINEERING · LEADERSHIP · OPEN KNOWLEDGE"
    return f'''<footer><div class="wrap footer-grid"><div><strong>{'孙林 · Lin Sun' if lang == 'zh' else 'Lin Sun'}</strong><p>{text}</p></div><div class="footer-links"><a href="mailto:lincharliesun@gmail.com">lincharliesun@gmail.com</a><a href="https://github.com/linsunhome" target="_blank" rel="noopener">GitHub</a><a href="https://scholar.google.com/citations?user=b8yMN1MAAAAJ" target="_blank" rel="noopener">Google Scholar</a></div></div></footer>'''


def page(lang: str, active: str, title: str, description: str, body: str) -> str:
    return f'''<!doctype html>
<html lang="{'zh-CN' if lang == 'zh' else 'en'}">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="{esc(description)}"><meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(description)}"><meta property="og:type" content="website"><title>{esc(title)}</title>
<link rel="stylesheet" href="/assets/styles.css"></head><body>
{nav(lang, active)}<main>{body}</main>{footer(lang)}
<script src="/assets/site.js" defer></script></body></html>'''


VENUE_NAMES = {
    "ACL": "Annual Meeting of the Association for Computational Linguistics",
    "EMNLP": "Conference on Empirical Methods in Natural Language Processing",
    "AAAI": "AAAI Conference on Artificial Intelligence",
    "ECAI": "European Conference on Artificial Intelligence",
    "ICASSP": "IEEE International Conference on Acoustics, Speech, and Signal Processing",
    "NeurIPS": "Conference on Neural Information Processing Systems",
    "FSKD": "International Conference on Fuzzy Systems and Knowledge Discovery",
    "ICMLC": "International Conference on Machine Learning and Cybernetics",
    "SMC": "IEEE International Conference on Systems, Man, and Cybernetics",
    "Acta Automatica Sinica": "Acta Automatica Sinica",
    "Expert Systems with Applications": "Expert Systems with Applications",
}


def publication_url(metadata: dict) -> str | None:
    official = metadata.get("officialUrl")
    if official and "base-search.net" not in official:
        return official
    return metadata.get("paperUrl")


def venue_key(venue: str) -> str:
    for key in VENUE_NAMES:
        if venue.startswith(key):
            return key
    return "arXiv" if venue.startswith("arXiv") else venue


def venue_year(venue: str, fallback: object) -> object:
    match = re.search(r"(?<!\d)(?:19|20)\d{2}(?!\d)", venue)
    return match.group(0) if match else fallback


def venue_short(venue: str, year: object) -> str:
    key = venue_key(venue)
    label = "arXiv" if key == "arXiv" else {"Expert Systems with Applications": "ESWA", "Acta Automatica Sinica": "AAS"}.get(key, key)
    suffix = []
    if "findings" in venue.lower():
        suffix.append("findings")
    if "oral" in venue.lower():
        suffix.append("oral")
    return " ".join([label, str(venue_year(venue, year)), *suffix]).strip()


def venue_full(venue: str, year: object) -> str:
    key = venue_key(venue)
    if key == "arXiv":
        label = re.sub(r"\bpreprint\b\s*", "", venue, flags=re.IGNORECASE).strip()
        return re.sub(r"^arXiv\s+(?=arXiv:)", "", label, flags=re.IGNORECASE)
    full = VENUE_NAMES[key]
    actual_year = venue_year(venue, year)
    if "findings" in venue.lower() and key in {"ACL", "EMNLP"}:
        full = f"Findings of the Association for Computational Linguistics: {key} {actual_year}"
    else:
        full = f"{full} {actual_year}"
    if "oral" in venue.lower():
        full += " (oral)"
    tail = venue[len(key):].strip()
    tail = re.sub(r"^(?:19|20)\d{2}\s*", "", tail)
    tail = re.sub(r"\(oral\)|\bfindings\b", "", tail, flags=re.IGNORECASE).strip(" ,")
    if tail:
        full += f" {tail}"
    return full


def author_html(authors: str) -> str:
    names = [name.strip() for name in authors.split(",") if name.strip()]
    sun_names = {"L Sun", "S Lin"}
    return ", ".join("<strong>Lin Sun</strong>" if name in sun_names else esc(name) for name in names)


def topic_label(topic: str | None, lang: str) -> str:
    labels = {
        "safety": ("安全与对齐", "Safety & alignment"),
        "knowledge": ("RAG 与文档智能", "RAG & document intelligence"),
        "foundation": ("基础模型与推理", "Foundation models & reasoning"),
        "agents": ("记忆与 Agent", "Memory & agents"),
        "early": ("早期搜索与问答", "Early search & QA"),
    }
    return labels.get(topic, ("研究成果", "Research"))[0 if lang == "zh" else 1]


def paper_rows(lang: str, papers_to_render: list[dict] | None = None) -> str:
    rows = papers if papers_to_render is None else papers_to_render
    result = []
    for paper in rows:
        metadata = publication_metadata.get(paper["title"], {})
        year = paper.get("scholarYear", "")
        paper_url = publication_url(metadata)
        title = external_link(paper_url, paper["title"], css="paper-title-link") if paper_url else f'<span class="paper-title-text">{esc(paper["title"])}</span>'
        badges = [f'<span class="tag">{esc(topic_label(metadata.get("topic"), lang))}</span>']
        result.append(f'''<article class="paper-row" data-paper-row data-year="{esc(year)}">
          <div class="paper-body"><div class="paper-kicker"><span class="paper-short-venue">[{esc(venue_short(paper.get('venue', ''), year))}]</span>{''.join(badges)}</div>
          <div class="paper-title">{title}</div><div class="paper-meta paper-authors">{author_html(paper.get('authors', ''))}</div>
          <div class="paper-meta paper-venue">{esc(venue_full(paper.get('venue', ''), year))}</div></div></article>''')
    return "\n".join(result)


def paper_year_groups(lang: str) -> str:
    grouped = {}
    for paper in papers:
        grouped.setdefault(str(paper.get("scholarYear", "")), []).append(paper)
    return "\n".join(
        f'<section class="paper-year-group"><div class="section-kicker">{esc(year)}</div><div class="paper-list">{paper_rows(lang, rows)}</div></section>'
        for year, rows in sorted(grouped.items(), key=lambda item: item[0], reverse=True)
    )


def media_rows(lang: str, items: list[dict], limit: int | None = None) -> str:
    rows = items if limit is None else items[:limit]
    result = []
    for item in rows:
        translated = media_translations.get(item.get("url"), {})
        title = translated.get("en") if lang == "en" and translated.get("en") else item.get("title", "")
        date = item.get("date") or ""
        meta = " · ".join(part for part in [item.get("source", ""), date] if part)
        result.append(f'<article class="media-item"><div>{external_link(item.get("url"), title)}</div><small>{esc(meta)}</small></article>')
    return "\n".join(result) or '<p class="empty">暂无公开条目。</p>'


def talk_rows(lang: str, limit: int | None = None) -> str:
    rows = talks if limit is None else talks[:limit]
    result = []
    for item in rows:
        title = item.get("en") if lang == "en" and item.get("en") else item.get("title", "")
        event = item.get("eventEn") if lang == "en" and item.get("eventEn") else item.get("event", "")
        meta = " · ".join(part for part in [event, item.get("date", ""), item.get("roleEn" if lang == "en" else "role", "")] if part)
        result.append(f'<article class="media-item"><div>{external_link(item.get("url"), title)}</div><small>{esc(meta)}</small></article>')
    return "\n".join(result) or '<p class="empty">暂无公开演讲。</p>'


def recent_updates(lang: str, limit: int | None = None) -> str:
    key = "zh" if lang == "zh" else "en"
    rows = site_content.get("news", []) if limit is None else site_content.get("news", [])[:limit]
    result = []
    for item in rows:
        target = item.get("url") or ("/" + ("en/" if lang == "en" else "") + item.get("path", "impact/"))
        title = item["title"][key]
        link = external_link(target, title) if target.startswith("http") else f'<a href="{esc(target)}">{esc(title)} ↗</a>'
        result.append(f'<article class="media-item"><div>{link}</div><small>{esc(item.get("date", ""))}</small></article>')
    return "\n".join(result) or '<p class="empty">暂无近期动态。</p>'


def project_card(lang: str, item: dict) -> str:
    key = lang
    if item.get("detail", True):
        href = f'/{"en/" if lang == "en" else ""}projects/{item["id"]}/'
        label = "项目详情" if lang == "zh" else "Project details"
        link = f'<a class="paper-link" href="{href}" aria-label="{esc(item["title"][key] + " · " + label)}">{label} ↗</a>'
    else:
        link = " ".join(external_link(entry["url"], entry["label"][key], css="paper-link") for entry in item.get("links", []))
    return f'''<article class="card project-card" id="{esc(item["id"])}">
      <div class="project-meta">{esc(item.get("period", ""))}</div>
      <h3>{esc(item["title"][key])}</h3><p>{esc(item["summary"][key])}</p>
      <div class="result">{link}</div></article>'''

def tag_html(tags: list[str]) -> str:
    return "".join(f'<span class="tag">{esc(tag)}</span>' for tag in tags)


def home(lang: str) -> str:
    zh = lang == "zh"
    prefix = "" if zh else "en/"
    profile = site_content["profile"]
    theme_cards = "".join(
        f'<article class="card"><h3>{esc(item["title"][lang])}</h3><p>{esc(item["text"][lang])}</p></article>'
        for item in site_content["areas"]
    )
    featured = [paper for paper in papers if any(query.lower() in paper["title"].lower() for query in site_content.get("featuredPaperQueries", []))]
    return f'''<section class="hero"><div class="wrap">
      <div class="eyebrow">{'研究 · 工程 · 管理' if zh else 'RESEARCH · ENGINEERING · LEADERSHIP'}</div>
      <h1>{'孙林 <span class="name-en">Lin Sun</span>' if zh else 'Lin Sun'}</h1>
      <p class="hero-copy">{esc(profile["intro"][lang])}</p>
      <p class="hero-overview">{esc(profile["background"][lang])}</p>
      <div class="hero-actions"><a class="btn primary" href="/{prefix}about/">{'关于我' if zh else 'About me'} ↗</a>
      {external_link(site_content["scholar"], "Google Scholar", css="btn")}
      <a class="btn" href="mailto:{site_content['email']}">{site_content['email']}</a></div>
    </div></section>
    <section><div class="wrap"><div class="section-head"><div><div class="section-kicker">01 / Research</div><h2>{'研究与工程方向' if zh else 'Research & engineering'}</h2></div></div>
      <div class="grid-3 research-overview">{theme_cards}</div></div></section>
    <section><div class="wrap"><div class="section-head"><div><div class="section-kicker">02 / Selected work</div><h2>{'代表项目' if zh else 'Selected work'}</h2></div></div>
      <div class="grid-3">{''.join(project_card(lang, item) for item in site_content['projects'])}</div></div></section>
    <section><div class="wrap"><div class="section-head"><div><div class="section-kicker">03 / Publications</div><h2>{'精选研究成果' if zh else 'Selected publications'}</h2></div>
      <a class="paper-link" href="/{prefix}publications/">{'全部论文' if zh else 'All publications'} ↗</a></div>
      <div class="paper-list">{paper_rows(lang, featured)}</div></div></section>
    <section><div class="wrap"><div class="section-head"><div><div class="section-kicker">04 / Media & updates</div><h2>{'公开交流与近期动态' if zh else 'Conversations & updates'}</h2></div>
      <a class="paper-link" href="/{prefix}impact/">{'影响与交流' if zh else 'Impact & talks'} ↗</a></div>
      <h3 class="subsection-title">{'公开视频' if zh else 'Public videos'}</h3><div class="media-list">{media_rows(lang, [item for item in published_media if item.get('kind') in VIDEO_KINDS], 2)}</div>
      <h3 class="subsection-title">{'近期动态' if zh else 'Recent updates'}</h3><div class="media-list">{recent_updates(lang, 5)}</div>
    </div></section>'''

def about(lang: str) -> str:
    zh = lang == "zh"
    profile = site_content["profile"]
    education = "".join(
        f'<li><strong>{esc(entry["degree"][lang])}</strong><span>{esc(entry["field"][lang])}</span></li>'
        for entry in profile["educationEntries"]
    )
    career = "".join(f'''<article class="timeline-item">
      <div class="timeline-time">{esc(item["start"])}<br>{esc(item["end"] or ("至今" if zh else "present"))}</div>
      <div class="timeline-dot"></div><div class="timeline-card"><h3>{esc(item["org"][lang])}</h3>
      <div class="career-role">{esc(item["role"][lang])}</div><p>{esc(item["text"][lang])}</p></div></article>'''
      for item in site_content["career"])
    leadership = "".join(
        f'<article class="leadership-entry"><h3>{esc(item["title"][lang])}</h3><p>{esc(item["text"][lang])}</p></article>'
        for item in profile["leadership"]
    )
    services = "".join(f'<li>{esc(item["title"][lang])}</li>' for item in profile.get("services", []))
    return f'''<section class="page-hero"><div class="wrap"><div class="eyebrow">01 / About</div><h1>{'关于我' if zh else 'About me'}</h1></div></section>
    <section><div class="wrap about-intro"><article class="prose"><h2>{'个人简介' if zh else 'Profile'}</h2>
      <p>{esc(profile["intro"][lang])}</p><p>{esc(profile["background"][lang])}</p>
      <div class="inline-links"><a href="mailto:{site_content['email']}">{site_content['email']}</a>{external_link(site_content['scholar'], 'Google Scholar')}</div>
      </article><aside class="education-panel"><div class="section-kicker">{'教育经历' if zh else 'Education'}</div>
      <h3>{esc(profile["education"][lang])}</h3><ul class="education-list">{education}</ul></aside></div></section>
    <section><div class="wrap about-columns"><div><div class="section-head"><div><div class="section-kicker">02 / Career</div><h2>{'职业经历' if zh else 'Career'}</h2></div></div>
      <div class="timeline">{career}</div></div><aside>
      <div class="section-head"><div><div class="section-kicker">03 / Leadership</div><h2>{'团队与组织交付' if zh else 'Teams & delivery'}</h2></div></div>{leadership}
      <div class="section-kicker service-heading">{'学术与行业服务' if zh else 'Academic & industry service'}</div><ul class="service-list">{services}</ul>
      </aside></div></section>'''

def project_by_slug(slug: str) -> dict:
    for item in site_content["projects"]:
        if item["id"] == slug:
            return item
    raise KeyError(slug)


def research(lang: str) -> str:
    zh = lang == "zh"
    directions = "".join(f'''<article class="research-direction"><h3>{esc(item["title"][lang])}</h3>
      <p>{esc(item["text"][lang])}</p><div class="tag-row">{tag_html(item["tags"])}</div></article>'''
      for item in site_content["areas"])
    projects = "".join(project_card(lang, item) for item in site_content["projects"])
    return f'''<section class="page-hero"><div class="wrap"><div class="eyebrow">02 / Research & Projects</div><h1>{'研究与项目' if zh else 'Research & projects'}</h1></div></section>
    <section><div class="wrap"><div class="section-head"><div><div class="section-kicker">Research focus</div><h2>{'研究方向' if zh else 'Research focus'}</h2></div></div>
      <div class="research-directions">{directions}</div></div></section>
    <section><div class="wrap"><div class="section-head"><div><div class="section-kicker">Selected work</div><h2>{'项目与工程实践' if zh else 'Projects & engineering'}</h2></div></div>
      <div class="grid-3">{projects}</div></div></section>'''

def project_detail(lang: str, slug: str) -> str:
    zh = lang == "zh"
    key = "zh" if zh else "en"
    item = project_by_slug(slug)
    links = "".join(f'<a class="btn" href="{esc(link["url"])}" target="_blank" rel="noopener">{esc(link["label"][key])} ↗</a>' for link in item.get("links", []))
    related = [paper for paper in papers if any(query.lower() in paper["title"].lower() for query in item.get("paperQueries", []))]
    related_media = [m for m in published_media if m.get("url") in item.get("relatedMedia", [])]
    figures = "".join(f'<figure class="project-figure"><img src="/{image["path"]}" alt="{esc(image["alt"][key])}"><figcaption>{esc(image["alt"][key])}</figcaption></figure>' for image in item.get("images", []))
    figure_section = f'<section><div class="wrap">{figures}</div></section>' if figures else ""
    return f'''<section class="page-hero"><div class="wrap"><div class="eyebrow">Research / Project detail</div><h1>{esc(item["title"][key])}</h1><p>{esc(item["summary"][key])}</p><div class="tag-row">{tag_html(item.get("tags", []))}</div></div></section><section><div class="wrap"><div class="grid-2"><article class="card"><div class="eyebrow">{'问题' if zh else 'Problem'}</div><p>{esc(item['problem'][key])}</p></article><article class="card"><div class="eyebrow">{'个人角色' if zh else 'Personal role'}</div><p>{esc(item['role'][key])}</p></article><article class="card"><div class="eyebrow">{'方法' if zh else 'Method'}</div><p>{esc(item['approach'][key])}</p></article><article class="card"><div class="eyebrow">{'结果' if zh else 'Results'}</div><p>{esc(item['result'][key])}</p></article></div></div></section>{figure_section}<section><div class="wrap"><div class="section-head"><div><div class="section-kicker">Related publications</div><h2>{'关联论文' if zh else 'Related papers'}</h2></div></div><div class="paper-list">{paper_rows(lang, related)}</div></div></section><section><div class="wrap"><div class="section-head"><div><div class="section-kicker">Related coverage</div><h2>{'相关报道' if zh else 'Related coverage'}</h2></div></div><div class="media-list">{media_rows(lang, related_media)}</div><div class="hero-actions">{links}</div></div></section>'''


def publications(lang: str) -> str:
    zh = lang == "zh"
    return f'''<section class="page-hero"><div class="wrap"><div class="eyebrow">03 / Publications</div><h1>{'论文' if zh else 'Publications'}</h1><div class="hero-actions"><a class="btn" href="{site_content['scholar']}" target="_blank" rel="noopener">Google Scholar ↗</a><a class="btn" href="https://orcid.org/0009-0008-0471-9131" target="_blank" rel="noopener">ORCID ↗</a></div></div></section><section><div class="wrap">{paper_year_groups(lang)}</div></section>'''


def recognition_html(lang: str) -> str:
    key = "zh" if lang == "zh" else "en"
    return "".join(f'<article class="card"><div class="eyebrow">{esc(item["kind"][key])}</div><h3 style="margin-top:12px">{esc(item["title"][key])}</h3><p>{esc(item["detail"][key])}</p></article>' for item in site_content.get("recognition", []))


def patent_html(lang: str) -> str:
    groups = []
    for theme in site_content["patentThemes"]:
        items = [item for item in site_content["patents"] if item["themeId"] == theme["id"]]
        rows = []
        for item in items:
            title = item["title"] if lang == "zh" else item["titleEn"]
            metadata = []
            if item.get("number"):
                metadata.append(esc(item["number"]))
            if item.get("inventorOrder"):
                order = item["inventorOrder"] if lang == "zh" else {"第二发明人": "Second inventor", "第三发明人": "Third inventor"}.get(item["inventorOrder"], item["inventorOrder"])
                metadata.append(esc(order))
            if item.get("grantDate"):
                metadata.append(esc(item["grantDate"]))
            detail = f'<div class="paper-meta">{" · ".join(metadata)}</div>' if metadata else ""
            rows.append(f'<li class="patent-entry" data-patent-id="{esc(item["id"])}"><div>{esc(title)}{detail}</div></li>')
        groups.append(f'<section class="patent-group"><h3>{esc(theme["title"][lang])}<span class="group-count">{len(items)}</span></h3><ol class="patent-list">{"".join(rows)}</ol></section>')
    return "".join(groups)

def impact(lang: str) -> str:
    zh = lang == "zh"
    personal_media = [item for item in published_media if item.get("kind") in MEDIA_KINDS][:2]
    videos = [item for item in published_media if item.get("kind") in VIDEO_KINDS][:2]
    team_media = [item for item in published_media if item.get("kind") in TEAM_KINDS]
    standards = []
    for item in site_content["standards"]:
        identifier = item["id"] if item["id"].startswith(("GB/", "SJ/")) else ""
        reference = f'<div class="standard-code">{esc(identifier)}</div>' if identifier else ""
        date = f'<span>{esc(item["date"])}</span>' if item.get("date") else ""
        role = f'<span>{esc(item["role"][lang])}</span>' if item.get("role") else ""
        metadata = f'<div class="standard-meta">{role}{date}</div>' if role or date else ""
        standards.append(f'''<article class="standard-card"><div class="section-kicker">{esc(item["kind"][lang])}</div>
          <h3>{esc(item["title"][lang])}</h3>{reference}{metadata}</article>''')
    return f'''<section class="page-hero"><div class="wrap"><div class="eyebrow">04 / Impact & talks</div><h1>{'影响与交流' if zh else 'Impact & talks'}</h1></div></section>
    <section><div class="wrap"><div class="section-head"><div><div class="section-kicker">Recognition</div><h2>{'奖项与行业认可' if zh else 'Awards & recognition'}</h2></div></div>
      <div class="grid-3 recognition-grid">{recognition_html(lang)}</div></div></section>
    <section><div class="wrap"><div class="section-head"><div><div class="section-kicker">Patents</div><h2>{'发明专利' if zh else 'Patents'}</h2></div></div>
      <div class="patent-groups">{patent_html(lang)}</div></div></section>
    <section><div class="wrap"><div class="section-head"><div><div class="section-kicker">Standards & reports</div><h2>{'标准与技术报告' if zh else 'Standards & reports'}</h2></div></div>
      <div class="grid-2 standards-grid">{"".join(standards)}</div></div></section>
    <section id="talks"><div class="wrap"><div class="section-head"><div><div class="section-kicker">Talks</div><h2>{'公开演讲与技术分享' if zh else 'Public talks'}</h2></div></div>
      <div class="media-list">{talk_rows(lang)}</div></div></section>
    <section><div class="wrap"><div class="section-head"><div><div class="section-kicker">Media & videos</div><h2>{'媒体观点与公开视频' if zh else 'Media & videos'}</h2></div></div>
      <div class="media-list">{media_rows(lang, personal_media)}{media_rows(lang, videos)}</div></div></section>
    <section><div class="wrap"><div class="section-head"><div><div class="section-kicker">Team articles</div><h2>{'团队技术文章与新闻' if zh else 'Team articles & news'}</h2></div></div>
      <div class="media-list">{media_rows(lang, team_media)}</div></div></section>'''

def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main() -> None:
    for path in [ROOT / "index.html", ROOT / "en", ROOT / "about", ROOT / "research", ROOT / "publications", ROOT / "impact", ROOT / "projects"]:
        if path.is_file():
            path.unlink()
        elif path.is_dir():
            shutil.rmtree(path)
    pages = {
        "zh": {"": ("首页", "孙林的研究、工程、管理与公开成果。", home), "about": ("关于我", "孙林的个人简介、教育、经历与团队建设。", about), "research": ("研究与项目", "孙林的研究方向与代表性项目。", research), "publications": ("论文", "孙林的论文与研究成果。", publications), "impact": ("影响与交流", "孙林的荣誉、标准、专利、媒体与公开活动。", impact)},
        "en": {"": ("Home", "Lin Sun — research, engineering, leadership, and public work.", home), "about": ("About", "Lin Sun — profile, education, experience, and team building.", about), "research": ("Research & Projects", "Lin Sun — research focus and selected projects.", research), "publications": ("Publications", "Publications and research by Lin Sun.", publications), "impact": ("Impact & Talks", "Lin Sun — recognition, standards, patents, media, and talks.", impact)},
    }
    for project in site_content["projects"]:
        if not project.get("detail", True):
            continue
        slug = project["id"]
        pages["zh"][f"projects/{slug}"] = (project["title"]["zh"], project["summary"]["zh"], lambda language, value=slug: project_detail(language, value))
        pages["en"][f"projects/{slug}"] = (project["title"]["en"], project["summary"]["en"], lambda language, value=slug: project_detail(language, value))
    for lang, entries in pages.items():
        for route, (title, description, renderer) in entries.items():
            path = ROOT / ("en" if lang == "en" else "") / route / "index.html" if route else ROOT / ("en/index.html" if lang == "en" else "index.html")
            write(path, page(lang, route or "home", f'{title} | {"Lin Sun" if lang == "en" else "孙林"}', description, renderer(lang)))
    write(ROOT / "404.html", page("zh", "home", "页面未找到 | 孙林", "页面未找到。", '<section class="page-hero"><div class="wrap"><div class="eyebrow">404</div><h1>页面未找到</h1><p>请返回首页继续浏览研究、项目与公开交流。</p><div class="hero-actions"><a class="btn primary" href="/">返回首页 ↗</a><a class="btn" href="/en/">English home ↗</a></div></div></section>'))
    print(f"Generated {sum(len(v) for v in pages.values())} pages from {len(papers)} papers and {len(published_media)} published media items.")


if __name__ == "__main__":
    main()
