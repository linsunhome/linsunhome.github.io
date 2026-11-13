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


def author_html(authors: str, corresponding: bool, lang: str) -> str:
    names = [name.strip() for name in authors.split(",") if name.strip()]
    sun_names = {"L Sun", "S Lin"}
    label = "通讯作者" if lang == "zh" else "Corresponding author"
    marker = f'<sup class="corresponding-author" aria-label="{label}">*</sup>' if corresponding else ""
    return ", ".join(f"<strong>Lin Sun</strong>{marker}" if name in sun_names else esc(name) for name in names)


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
          <div class="paper-title">{title}</div><div class="paper-meta paper-authors">{author_html(paper.get('authors', ''), metadata.get('correspondingAuthor', False), lang)}</div>
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
        meta = " · ".join(part for part in [item.get("roleEn" if lang == "en" else "role", ""), item.get("date", "")] if part)
        result.append(f'<article class="media-item talk-item"><div>{external_link(item.get("url"), title)}<span class="talk-event">{esc(event)}</span></div><small>{esc(meta)}</small></article>')
    return "\n".join(result) or '<p class="empty">暂无公开演讲。</p>'


def recent_updates(lang: str, limit: int | None = None) -> str:
    key = "zh" if lang == "zh" else "en"
    rows = list(site_content.get("news", []))
    rows.extend({"title": {"zh": item["title"], "en": media_translations.get(item["url"], {}).get("en", item["title"])},
                 "source": {"zh": item["source"], "en": "Bilibili / 360"},
                 "date": item.get("date"), "url": item["url"]}
                for item in published_media if item.get("kind") in VIDEO_KINDS)
    rows.sort(key=lambda item: item.get("date") or "", reverse=True)
    if limit is not None:
        rows = rows[:limit]
    result = []
    for item in rows:
        target = item.get("url") or ("/" + ("en/" if lang == "en" else "") + item.get("path", "impact/"))
        title = item["title"][key]
        link = external_link(target, title) if target.startswith("http") else f'<a href="{esc(target)}">{esc(title)} ↗</a>'
        source = item.get("source", {}).get(key, "")
        meta = " · ".join(part for part in [source, item.get("date", "")] if part)
        result.append(f'<article class="media-item"><div>{link}</div><small>{esc(meta)}</small></article>')
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


def featured_papers() -> list[dict]:
    selected = []
    for query in site_content.get("featuredPaperQueries", []):
        for paper in papers:
            metadata = publication_metadata.get(paper["title"], {})
            if (query.lower() in paper["title"].lower() and paper not in selected
                    and (metadata.get("role") == "first-author" or metadata.get("correspondingAuthor"))):
                selected.append(paper)
    # Keep editorial order within each publication-status and authorship tier.
    return sorted(selected, key=lambda paper: (
        publication_metadata[paper["title"]].get("status") != "published",
        publication_metadata[paper["title"]].get("role") != "first-author",
    ))


def home(lang: str) -> str:
    zh = lang == "zh"
    prefix = "" if zh else "en/"
    profile = site_content["profile"]
    theme_cards = "".join(
        f'<article class="card"><h3>{esc(item["title"][lang])}</h3><p>{esc(item["text"][lang])}</p></article>'
        for item in site_content["areas"]
    )
    featured = featured_papers()
    summary = "".join(
        f'<p class="{"hero-copy" if index == 0 else "hero-overview"}">{esc(paragraph)}</p>'
        for index, paragraph in enumerate(profile["homeSummary"][lang])
    )
    return f'''<section class="hero"><div class="wrap">
      <div class="eyebrow">{'研究 · 工程 · 管理' if zh else 'RESEARCH · ENGINEERING · LEADERSHIP'}</div>
      <h1>{'孙林 <span class="name-en">Lin Sun</span>' if zh else 'Lin Sun'}</h1>
      {summary}
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
    <section><div class="wrap"><div class="section-head"><div><div class="section-kicker">04 / Updates</div><h2>{'近期动态' if zh else 'Recent updates'}</h2></div>
      <a class="paper-link" href="/{prefix}impact/">{'影响与交流' if zh else 'Impact & talks'} ↗</a></div>
      <div class="media-list">{recent_updates(lang, 6)}</div>
    </div></section>'''

def about(lang: str) -> str:
    zh = lang == "zh"
    prefix = "" if zh else "en/"
    profile = site_content["profile"]
    summary = "".join(f'<p>{esc(paragraph)}</p>' for paragraph in profile["aboutSummary"][lang])
    contributions = "".join(
        f'<article class="leadership-entry"><h3>{esc(item["title"][lang])}</h3><p>{esc(item["text"][lang])}</p></article>'
        for item in profile["contributions"]
    )
    honors = "".join(
        f'<li>{esc(item["title"][lang])}</li>'
        for item in site_content["recognition"] if item["group"] == "personal"
    )
    education = "".join(
        f'<li><strong>{esc(entry["degree"][lang])}</strong><span>{esc(entry["field"][lang])}</span></li>'
        for entry in profile["educationEntries"]
    )
    career = "".join(f'''<article class="timeline-item">
      <div class="timeline-time">{esc(item["start"])}<br>{esc(item["end"] or ("至今" if zh else "present"))}</div>
      <div class="timeline-dot"></div><div class="timeline-card"><h3>{esc(item["org"][lang])}</h3>
      {f'<div class="career-role">{esc(item["role"][lang])}</div>' if item.get('role') else ''}<p>{esc(item["text"][lang])}</p></div></article>'''
      for item in site_content["career"])
    leadership = "".join(
        f'<article class="leadership-entry"><h3>{esc(item["title"][lang])}</h3><p>{esc(item["text"][lang])}</p></article>'
        for item in profile["leadership"]
    )
    services = "".join(
        f'<li>{esc(item["title"][lang])}</li>' for item in profile.get("services", [])
    )
    funded_projects = "".join(f'<li class="funded-project">{esc(item["title"][lang])}</li>' for item in site_content.get("fundedProjects", []))
    return f'''<section class="page-hero"><div class="wrap"><div class="eyebrow">01 / About</div><h1>{'关于我' if zh else 'About me'}</h1></div></section>
    <section><div class="wrap about-intro"><article class="prose"><h2>{'个人简介' if zh else 'Profile'}</h2>
      {summary}
      <div class="inline-links"><a href="mailto:{site_content['email']}">{site_content['email']}</a>{external_link(site_content['scholar'], 'Google Scholar')}</div>
      </article><aside class="education-panel"><div class="section-kicker">{'教育经历' if zh else 'Education'}</div>
      <h3>{esc(profile["education"][lang])}</h3><ul class="education-list">{education}</ul></aside></div></section>
    <section><div class="wrap about-columns"><div><div class="section-head"><div><div class="section-kicker">02 / Career</div><h2>{'职业经历' if zh else 'Career'}</h2></div></div>
      <div class="timeline">{career}</div></div><aside>
      <div class="section-head"><div><div class="section-kicker">03 / Leadership</div><h2>{'团队与组织交付' if zh else 'Teams & delivery'}</h2></div></div>{leadership}
      <div class="section-kicker service-heading">{'学术与行业服务' if zh else 'Academic & industry service'}</div><ul class="service-list">{services}</ul>
      </aside></div></section>
    <section><div class="wrap about-columns"><div><div class="section-head"><div><div class="section-kicker">04 / Contributions</div><h2>{'研究与行业贡献' if zh else 'Research & industry contributions'}</h2></div></div>
      {contributions}<div class="inline-links"><a class="paper-link" href="/{prefix}research/">{'研究与项目' if zh else 'Research & projects'} ↗</a><a class="paper-link" href="/{prefix}publications/">{'全部论文' if zh else 'All publications'} ↗</a><a class="paper-link" href="/{prefix}impact/">{'专利与标准' if zh else 'Patents & standards'} ↗</a></div>
      </div><aside><div class="section-head"><div><div class="section-kicker">05 / Honors</div><h2>{'个人荣誉' if zh else 'Personal honors'}</h2></div></div>
      <ul class="honors-list">{honors}</ul><p class="paper-meta">{'北京市科学技术进步二等奖：项目《大模型安全关键技术及应用》获奖，孙林作为第二完成人参与该项目。' if zh else 'Beijing Science and Technology Progress Award, Second Prize: the project “Key Technologies and Applications of Large-Model Safety” received the award, with Lin Sun as the second project contributor.'}</p>
      <a class="paper-link" href="/{prefix}impact/">{'奖项与行业认可' if zh else 'Awards & recognition'} ↗</a></aside></div></section>
    <section><div class="wrap"><div class="section-head"><div><div class="section-kicker">{'工业和信息化部' if zh else 'Ministry of Industry and Information Technology'}</div><h2>{'参与的部分国拨项目' if zh else 'Selected nationally funded projects'}</h2></div></div><ol class="funded-projects">{funded_projects}</ol></div></section>'''

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

def project_figure(lang: str, figure: dict) -> str:
    path = "/" + figure["path"]
    caption = esc(figure["alt"][lang])
    label = "查看原图" if lang == "zh" else "Open full-size image"
    source = ""
    if figure.get("sourceUrl"):
        source = " · " + external_link(figure["sourceUrl"], figure["sourceLabel"][lang])
    dimensions = f' width="{figure["width"]}" height="{figure["height"]}"' if figure.get("width") and figure.get("height") else ""
    return f'''<figure class="project-figure"><a href="{esc(path)}" target="_blank" rel="noopener" aria-label="{esc(label)}: {caption}">
      <img src="{esc(path)}" alt="{caption}"{dimensions} loading="lazy"></a><figcaption>{caption}{source}</figcaption></figure>'''


def project_results(lang: str, project: dict) -> str:
    panels = []
    for item in project.get("resultSections", []):
        columns = "".join(f'<th scope="col">{esc(value)}</th>' for value in item["columns"][lang])
        rows = "".join(
            '<tr><th scope="row">' + esc(row[0]) + '</th>'
            + "".join(f'<td>{esc(value)}</td>' for value in row[1:]) + '</tr>'
            for row in item["rows"]
        )
        figure = project_figure(lang, item["figure"]) if item.get("figure") else ""
        panels.append(f'''<article class="project-result" id="{esc(item['id'])}"><h3>{esc(item['title'][lang])}</h3>
          <p>{esc(item['text'][lang])}</p><div class="table-scroll" role="region" aria-label="{esc(item['title'][lang])}" tabindex="0">
          <table><caption class="sr-only">{esc(item['title'][lang])}</caption><thead><tr>{columns}</tr></thead><tbody>{rows}</tbody></table></div>
          <p class="result-source">{external_link(item['sourceUrl'], item['sourceLabel'][lang])}</p>{figure}</article>''')
    if not panels:
        return ""
    return f'''<section><div class="wrap"><div class="section-head"><div><div class="section-kicker">Results & evaluation</div>
      <h2>{'结果与评测' if lang == 'zh' else 'Results & evaluation'}</h2></div></div>{''.join(panels)}</div></section>'''


def project_detail(lang: str, slug: str) -> str:
    zh = lang == "zh"
    item = project_by_slug(slug)
    links = "".join(external_link(link["url"], link["label"][lang], css="btn") for link in item.get("links", []))
    related = [paper for paper in papers if any(query.lower() in paper["title"].lower() for query in item.get("paperQueries", []))]
    related_media = [m for m in published_media if m.get("url") in item.get("relatedMedia", [])]
    figures = "".join(project_figure(lang, figure) for figure in item.get("images", []))
    figure_section = f'<section><div class="wrap">{figures}</div></section>' if figures else ""
    return f'''<section class="page-hero"><div class="wrap"><div class="eyebrow">Research / Project detail</div>
      <h1>{esc(item["title"][lang])}</h1><p>{esc(item["summary"][lang])}</p><div class="tag-row">{tag_html(item.get("tags", []))}</div>
      <div class="hero-actions">{links}</div></div></section>
    <section><div class="wrap"><div class="grid-3">
      <article class="card"><div class="eyebrow">{'问题' if zh else 'Problem'}</div><p>{esc(item['problem'][lang])}</p></article>
      <article class="card"><div class="eyebrow">{'方法' if zh else 'Method'}</div><p>{esc(item['approach'][lang])}</p></article>
      <article class="card"><div class="eyebrow">{'成果' if zh else 'Outcomes'}</div><p>{esc(item['result'][lang])}</p></article>
      </div></div></section>{figure_section}{project_results(lang, item)}
    <section><div class="wrap"><div class="section-head"><div><div class="section-kicker">Related publications</div>
      <h2>{'关联论文' if zh else 'Related papers'}</h2></div></div><div class="paper-list">{paper_rows(lang, related)}</div></div></section>
    <section><div class="wrap"><div class="section-head"><div><div class="section-kicker">Related coverage</div>
      <h2>{'相关报道' if zh else 'Related coverage'}</h2></div></div><div class="media-list">{media_rows(lang, related_media)}</div></div></section>'''


def publications(lang: str) -> str:
    zh = lang == "zh"
    return f'''<section class="page-hero"><div class="wrap"><div class="eyebrow">03 / Publications</div><h1>{'论文' if zh else 'Publications'}</h1><div class="hero-actions"><a class="btn" href="{site_content['scholar']}" target="_blank" rel="noopener">Google Scholar ↗</a><a class="btn" href="https://orcid.org/0009-0008-0471-9131" target="_blank" rel="noopener">ORCID ↗</a></div></div></section><section><div class="wrap">{paper_year_groups(lang)}</div></section>'''


def recognition_html(lang: str, group: str) -> str:
    key = "zh" if lang == "zh" else "en"
    return "".join(f'<article class="card"><div class="eyebrow">{esc(item["kind"][key])}</div><h3>{esc(item["title"][key])}</h3><p>{esc(item["detail"][key])}</p></article>' for item in site_content.get("recognition", []) if item["group"] == group)


def patent_html(lang: str) -> str:
    groups = []
    for theme in site_content["patentThemes"]:
        items = [item for item in site_content["patents"] if item["themeId"] == theme["id"]]
        rows = []
        for item in items:
            title = item["title"] if lang == "zh" else item["titleEn"]
            rows.append(f'<li class="patent-entry" data-patent-id="{esc(item["id"])}">{esc(title)}</li>')
        groups.append(f'<section class="patent-group"><h3>{esc(theme["title"][lang])}<span class="group-count">{len(items)}</span></h3><ol class="patent-list">{"".join(rows)}</ol></section>')
    return "".join(groups)

def impact(lang: str) -> str:
    zh = lang == "zh"
    personal_media = [item for item in published_media if item.get("kind") in MEDIA_KINDS]
    videos = [item for item in published_media if item.get("kind") in VIDEO_KINDS][:2]
    team_media = [item for item in published_media if item.get("kind") in TEAM_KINDS]
    standards = []
    for item in site_content["standards"]:
        identifier = item["id"] if item["id"].startswith(("GB/", "SJ/")) else ""
        reference = f'<div class="standard-code">{esc(identifier)}</div>' if identifier else ""
        standards.append(f'''<article class="standard-card"><div class="section-kicker">{esc(item["kind"][lang])}</div>
          <h3>{esc(item["title"][lang])}</h3>{reference}</article>''')
    return f'''<section class="page-hero"><div class="wrap"><div class="eyebrow">04 / Impact & talks</div><h1>{'影响与交流' if zh else 'Impact & talks'}</h1></div></section>
    <section><div class="wrap"><div class="section-head"><div><div class="section-kicker">Recognition</div><h2>{'奖项与行业认可' if zh else 'Awards & recognition'}</h2></div></div>
      <h3 class="subsection-title">{'个人荣誉' if zh else 'Personal honors'}</h3><div class="grid-3 recognition-grid" data-recognition="personal">{recognition_html(lang, 'personal')}</div>
      <h3 class="subsection-title">{'团队工作荣誉与认可' if zh else 'Team achievements & recognition'}</h3><div class="grid-3 recognition-grid" data-recognition="team">{recognition_html(lang, 'team')}</div></div></section>
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
