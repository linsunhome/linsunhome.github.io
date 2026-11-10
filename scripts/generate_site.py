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
      <button class="menu-toggle" data-menu-toggle aria-expanded="false" aria-label="Menu">☰</button>
      <nav class="nav-links" data-nav>{links}</nav>
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
        return re.sub(r"\bpreprint\b\s*", "", venue, flags=re.IGNORECASE).strip()
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


def role_label(role: str | None, lang: str) -> str:
    labels = {"first-author": ("第一作者", "First author"), "co-author": ("共同作者", "Co-author"), "corresponding-author": ("通讯作者", "Corresponding author")}
    return labels.get(role, ("作者", "Author"))[0 if lang == "zh" else 1] if role else ""


def status_label(status: str | None, lang: str) -> str:
    # The data keeps the distinction; the public page suppresses the “preprint” badge.
    labels = {"published": ("已发表", "Published"), "accepted": ("已录用", "Accepted"), "technical-report": ("技术报告", "Technical report"), "submitted": ("投稿中", "Submitted")}
    return labels.get(status, ("", ""))[0 if lang == "zh" else 1]


def paper_rows(lang: str, papers_to_render: list[dict] | None = None) -> str:
    rows = papers if papers_to_render is None else papers_to_render
    result = []
    for paper in rows:
        metadata = publication_metadata.get(paper["title"], {})
        year = paper.get("scholarYear", "")
        paper_url = publication_url(metadata)
        title = external_link(paper_url, paper["title"], css="paper-title-link") if paper_url else f'<span class="paper-title-text">{esc(paper["title"])}</span>'
        badges = [f'<span class="tag">{esc(topic_label(metadata.get("topic"), lang))}</span>']
        role = role_label(metadata.get("role"), lang)
        if role:
            badges.append(f'<span class="tag">{esc(role)}</span>')
        status = status_label(metadata.get("status"), lang)
        if status:
            badges.append(f'<span class="tag tag-muted">{esc(status)}</span>')
        result.append(f'''<article class="paper-row" data-paper-row data-year="{esc(year)}">
          <div class="paper-body"><div class="paper-kicker"><span class="paper-short-venue">{esc(venue_short(paper.get('venue', ''), year))}</span>{''.join(badges)}</div>
          <div class="paper-title">{title}</div><div class="paper-meta paper-authors">{author_html(paper.get('authors', ''))}</div>
          <div class="paper-meta paper-venue">{esc(venue_full(paper.get('venue', ''), year))}</div><p class="paper-summary">{esc(metadata.get('summary', {}).get('zh' if lang == 'zh' else 'en', ''))}</p></div></article>''')
    return "\n".join(result)


def paper_groups(lang: str) -> str:
    order = ["safety", "foundation", "knowledge", "agents", "early"]
    labels = {
        "zh": {"safety": "安全与对齐", "foundation": "基础模型与推理", "knowledge": "RAG 与文档智能", "agents": "记忆与 Agent", "early": "早期研究"},
        "en": {"safety": "Safety & Alignment", "foundation": "Foundation Models & Reasoning", "knowledge": "RAG & Document Intelligence", "agents": "Memory & Agents", "early": "Early Research"},
    }
    groups = []
    for topic in order:
        items = [paper for paper in papers if publication_metadata.get(paper["title"], {}).get("topic") == topic]
        if items:
            groups.append(f'<section class="paper-topic-group"><div class="section-kicker">{esc(labels[lang][topic])}</div><div class="paper-list">{paper_rows(lang, items)}</div></section>')
    return "\n".join(groups)


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
    zh = lang == "zh"
    key = "zh" if zh else "en"
    href = f'/{"en/" if not zh else ""}projects/{item["id"]}/'
    detail = f'<a class="paper-link" href="{href}">{"查看项目详情" if zh else "Read project details"} ↗</a>' if item.get("detail", True) else ""
    return f'''<article class="card project-card"><div><div class="project-meta">{esc(item.get("period", ""))}</div><h3 style="margin-top:12px">{esc(item["title"][key])}</h3><p>{esc(item["summary"][key])}</p></div><div class="result">{detail}</div></article>'''


def tag_html(tags: list[str]) -> str:
    return "".join(f'<span class="tag">{esc(tag)}</span>' for tag in tags)


def home(lang: str) -> str:
    zh = lang == "zh"
    key = "zh" if zh else "en"
    profile = site_content["profile"]
    intro = profile["intro"][key]
    role = profile["role"][key]
    hero_copy = f"{role}。{intro}" if zh else f"{role}. {intro}"
    themes = [("基础模型与后训练", "Foundation models & post-training", "从数据工程、蒸馏到高效推理。", "From data engineering and distillation to efficient reasoning."), ("安全与可信生成", "Safety & trustworthy generation", "从动态攻防到闭环治理和可信生成。", "From dynamic attacks to closed-loop governance and trustworthy generation."), ("RAG、记忆与 Agent", "RAG, memory & agents", "从复杂文档证据到长期状态与工作流评测。", "From document evidence to long-term state and workflow evaluation.")]
    theme_cards = "".join(f'<article class="card"><span class="number">0{i + 1}</span><h3>{esc(t[0] if zh else t[1])}</h3><p>{esc(t[2] if zh else t[3])}</p></article>' for i, t in enumerate(themes))
    selected = site_content["projects"]
    scholar_link = "Google Scholar"
    return f'''<section class="hero"><div class="wrap hero-grid"><div><div class="eyebrow">{'个人研究 · 工程 · 管理' if zh else 'RESEARCH · ENGINEERING · LEADERSHIP'}</div><h1>{'把基础模型能力，变成可被理解、验证和使用的真实能力。' if zh else 'Turning foundation-model capability into work people can trust and use.'}</h1><p class="hero-copy">{esc(hero_copy)}</p><p class="hero-overview">{'2010 年起从事 AI 研发与管理；最新 Scholar 快照含 30 条记录，覆盖 2009–2026 年；曾在贝壳/如视承担跨职能团队建设与研究、工程和组织交付。' if zh else 'Working in AI research and management since 2010; the latest Scholar snapshot contains 30 records spanning 2009–2026; led cross-functional research, engineering, and organizational delivery at Beike/Rushi.'}</p><div class="hero-actions"><a class="btn primary" href="/{'en/' if not zh else ''}about/">{'关于我' if zh else 'About me'} ↗</a><a class="btn" href="{site_content['scholar']}" target="_blank" rel="noopener">{scholar_link}</a><a class="btn" href="mailto:{site_content['email']}">{site_content['email']} ↗</a></div></div><aside class="hero-card"><div class="monogram">LS</div></aside></div></section>
<section><div class="wrap"><div class="section-head"><div><div class="section-kicker">01 / Research</div><h2>{'三个研究主题' if zh else 'Three research themes'}</h2></div></div><div class="grid-3">{theme_cards}</div></div></section>
<section><div class="wrap"><div class="section-head"><div><div class="section-kicker">02 / Selected work</div><h2>{'代表项目与阶段工作' if zh else 'Selected projects and period work'}</h2></div></div><div class="grid-3">{''.join(project_card(lang, item) for item in selected)}</div><div class="hero-actions"><a class="btn" href="/{'en/' if not zh else ''}research/">{'查看研究与项目详情' if zh else 'Explore research and projects'} ↗</a></div></div></section>
<section><div class="wrap"><div class="section-head"><div><div class="section-kicker">03 / Publications</div><h2>{'精选研究成果' if zh else 'Selected publications'}</h2></div></div><div class="paper-list">{paper_rows(lang, [p for p in papers if any(q.lower() in p['title'].lower() for q in site_content.get('featuredPaperQueries', []))])}</div><div class="hero-actions"><a class="btn" href="/{'en/' if not zh else ''}publications/">{'查看 30 条论文记录' if zh else 'View all 30 records'} ↗</a></div></div></section>
<section><div class="wrap"><div class="section-head"><div><div class="section-kicker">04 / Media, talks & updates</div><h2>{'公开交流与近期动态' if zh else 'Public conversations and updates'}</h2></div></div><h3 class="subsection-title">{'公开视频' if zh else 'Public videos'}</h3><div class="media-list">{media_rows(lang, [m for m in published_media if m.get('kind') in VIDEO_KINDS], 2)}</div><h3 class="subsection-title">{'近期动态' if zh else 'Recent updates'}</h3><div class="media-list recent-update-list">{recent_updates(lang, 5)}</div><div class="hero-actions"><a class="btn" href="/{'en/' if not zh else ''}impact/">{'查看影响与交流' if zh else 'Explore impact and talks'} ↗</a></div></div></section>
<section><div class="wrap"><div class="callout"><div class="eyebrow">OPEN CONTACT</div><h2 style="margin-top:12px">{'联系我' if zh else 'Get in touch'}</h2><p>{'如果你希望交流基础模型、安全、RAG、记忆、Agent 或团队建设，可以通过邮箱联系我。' if zh else 'For conversations around foundation models, safety, RAG, memory, agents, or team building, reach me by email.'}</p><a class="btn" href="mailto:{site_content['email']}">{site_content['email']} ↗</a></div></div></section>'''


def about(lang: str) -> str:
    zh = lang == "zh"
    key = "zh" if zh else "en"
    profile = site_content["profile"]
    career_html = "".join(f'''<article class="timeline-item"><div class="timeline-time">{esc(item["start"])}—{esc(item["end"] or ("至今" if zh else "present"))}</div><div class="timeline-dot"></div><div class="timeline-card"><h3>{esc(item["org"][key])} · {esc(item["role"][key])}</h3><p>{esc(item["text"][key])}</p><p class="paper-meta">{esc(item["management"][key])}</p></div></article>''' for item in site_content["career"])
    service_cards = []
    for item in profile.get("services", []):
        term = item.get("term") or item.get("status") or {}
        source = item.get("source") or {}
        service_cards.append(f'<article class="card"><h3>{esc(item["title"][key])}</h3><p>{esc(term.get(key, ""))}</p><p class="paper-meta">{esc(source.get(key, ""))}</p></article>')
    service_html = "".join(service_cards)
    return f'''<section class="page-hero"><div class="wrap"><div class="eyebrow">01 / About</div><h1>{'关于我' if zh else 'About me'}</h1></div></section><section><div class="wrap grid-2"><div class="prose"><h2>{'个人简介' if zh else 'Profile'}</h2><p>{esc(profile['intro'][key])}</p><p>{'我的工作同时覆盖研究问题、模型训练、系统工程和线上交付；在贝壳/如视阶段参与企业搜索、数据智能和 AI+VR 场景，并承担跨职能团队建设。' if zh else 'My work spans research questions, model training, systems engineering, and delivery. At Beike/Rushi I worked across enterprise search, data intelligence, and AI+VR while helping build cross-functional teams.'}</p></div><div class="card"><div class="eyebrow">ROLE</div><h3 style="margin-top:14px">{esc(profile['role'][key])}</h3><p>{'研究、工程、管理与公开交流。' if zh else 'Research, engineering, leadership, and public exchange.'}</p></div></div></section><section><div class="wrap"><div class="section-head"><div><div class="section-kicker">02 / Education</div><h2>{'教育经历' if zh else 'Education'}</h2></div></div><article class="card prose"><h3>{esc(profile['education'][key])}</h3><p>{esc(profile['educationDetails'][key])}</p></article></div></section><section><div class="wrap"><div class="section-head"><div><div class="section-kicker">03 / Career</div><h2>{'经历与组织交付' if zh else 'Experience & delivery'}</h2></div></div><div class="timeline">{career_html}</div></div></section><section><div class="wrap"><div class="section-head"><div><div class="section-kicker">04 / Service</div><h2>{'学术与行业服务' if zh else 'Academic and industry service'}</h2></div></div><div class="grid-3">{service_html}</div></div></section><section><div class="wrap"><div class="callout"><div class="eyebrow">CONTACT</div><h2 style="margin-top:12px">{site_content['email']}</h2><p>{'公开联系入口：围绕基础模型、安全、RAG、记忆、Agent 和团队建设交流。' if zh else 'Open contact for conversations around foundation models, safety, RAG, memory, agents, and team building.'}</p><div class="hero-actions"><a class="btn" href="mailto:{site_content['email']}">{'发送邮件' if zh else 'Send an email'} ↗</a>{external_link(site_content['scholar'], 'Google Scholar', css='btn')}</div></div></div></section>'''


def project_by_slug(slug: str) -> dict:
    for item in site_content["projects"]:
        if item["id"] == slug:
            return item
    raise KeyError(slug)


def research(lang: str) -> str:
    zh = lang == "zh"
    key = "zh" if zh else "en"
    area_html = "".join(f'<article class="card"><div class="eyebrow">{esc(item["title"][key])}</div><h3 style="margin-top:14px">{esc(item["title"][key])}</h3><p>{esc(item["text"][key])}</p><div class="tag-row">{tag_html(item.get("tags", []))}</div><p class="paper-meta"><strong>{"关联项目" if zh else "Projects"}:</strong> {esc(", ".join(project_by_slug(slug)["title"][key] for slug in item.get("projects", []) if any(project["id"] == slug for project in site_content["projects"])))}</p><p class="paper-meta"><strong>{"关联论文" if zh else "Papers"}:</strong> {esc(", ".join(item.get("papers", [])) or ("标准、行业服务与团队交付" if zh else "Standards, service, and team delivery"))}</p></article>' for item in site_content["areas"])
    project_html = "".join(project_card(lang, item) for item in site_content["projects"])
    stages = [("基础模型与数据工程", "Foundation models & data", "长上下文数据、Dense/MoE 与继续训练。" if zh else "Long-context data, Dense/MoE systems, and continued training."), ("后训练与推理", "Post-training & reasoning", "SFT、强化学习、蒸馏、推理路径与模型融合。" if zh else "SFT, reinforcement learning, distillation, reasoning paths, and model merging."), ("安全与可信治理", "Safety & governance", "动态攻防、自动评测、闭环训练与在线策略。" if zh else "Dynamic attacks, automated evaluation, closed-loop training, and online policy."), ("RAG、记忆与 Agent", "RAG, memory & agents", "OCR-RAG、证据分配、长期记忆与 Agent 评测。" if zh else "OCR-RAG, evidence allocation, long-term memory, and agent evaluation."), ("业务与组织交付", "Delivery & organization", "线上系统、产品化、团队协同、标准和行业服务。" if zh else "Production systems, productization, team collaboration, standards, and industry service.")]
    thread_html = "".join(f'<a class="thread-step" href="/{"en/" if not zh else ""}research/"><span class="thread-index">0{i + 1}</span><strong>{esc(title if zh else en_title)}</strong><p>{esc(desc)}</p><span class="paper-link">{"查看关联方向" if zh else "Open related area"} ↗</span></a>' for i, (title, en_title, desc) in enumerate(stages))
    return f'''<section class="page-hero"><div class="wrap"><div class="eyebrow">02 / Research & Projects</div><h1>{'研究与项目' if zh else 'Research & projects'}</h1><p>{'从预训练与数据工程，到后训练、安全治理、RAG/记忆/Agent，再到真实系统与组织交付。' if zh else 'From pre-training and data engineering through post-training, safety, RAG/memory/agents, and real-system delivery.'}</p></div></section><section><div class="wrap"><div class="grid-3">{area_html}</div></div></section><section><div class="wrap"><div class="section-head"><div><div class="section-kicker">Selected projects</div><h2>{'代表项目' if zh else 'Selected projects'}</h2></div></div><div class="grid-3">{project_html}</div></div></section><section><div class="wrap"><div class="section-head"><div><div class="section-kicker">TECHNICAL THREAD</div><h2>{'五层技术体系' if zh else 'Five-layer technical system'}</h2></div></div><div class="thread-grid">{thread_html}</div></div></section>'''


def project_detail(lang: str, slug: str) -> str:
    zh = lang == "zh"
    key = "zh" if zh else "en"
    item = project_by_slug(slug)
    links = "".join(f'<a class="btn" href="{esc(link["url"])}" target="_blank" rel="noopener">{esc(link["label"][key])} ↗</a>' for link in item.get("links", []))
    related = [paper for paper in papers if any(query.lower() in paper["title"].lower() for query in item.get("paperQueries", []))]
    related_media = [m for m in published_media if m.get("url") in item.get("relatedMedia", [])]
    figures = "".join(f'<figure class="project-figure"><img src="/{image["path"]}" alt="{esc(image["alt"][key])}"><figcaption>{esc(image["alt"][key])}</figcaption></figure>' for image in item.get("images", []))
    return f'''<section class="page-hero"><div class="wrap"><div class="eyebrow">Research / Project detail</div><h1>{esc(item["title"][key])}</h1><p>{esc(item["summary"][key])}</p><div class="tag-row">{tag_html(item.get("tags", []))}</div></div></section><section><div class="wrap"><div class="grid-2"><article class="card"><div class="eyebrow">{'问题' if zh else 'Problem'}</div><p>{esc(item['problem'][key])}</p></article><article class="card"><div class="eyebrow">{'个人角色' if zh else 'Personal role'}</div><p>{esc(item['role'][key])}</p></article><article class="card"><div class="eyebrow">{'方法' if zh else 'Method'}</div><p>{esc(item['approach'][key])}</p></article><article class="card"><div class="eyebrow">{'结果' if zh else 'Results'}</div><p>{esc(item['result'][key])}</p></article></div></div></section><section><div class="wrap"><div class="grid-2"><article class="card feature-note"><div class="eyebrow">{'证据' if zh else 'Evidence'}</div><p>{esc(item['evidence'][key])}</p></article><article class="card"><div class="eyebrow">{'公开边界' if zh else 'Public boundary'}</div><p>{esc(item['boundary'][key])}</p></article></div>{figures}</div></section><section><div class="wrap"><div class="section-head"><div><div class="section-kicker">Related publications</div><h2>{'关联论文' if zh else 'Related papers'}</h2></div></div><div class="paper-list">{paper_rows(lang, related)}</div></div></section><section><div class="wrap"><div class="section-head"><div><div class="section-kicker">Related coverage</div><h2>{'相关报道' if zh else 'Related coverage'}</h2></div></div><div class="media-list">{media_rows(lang, related_media)}</div><div class="hero-actions">{links}</div></div></section>'''


def publications(lang: str) -> str:
    zh = lang == "zh"
    return f'''<section class="page-hero"><div class="wrap"><div class="eyebrow">03 / Publications</div><h1>{'论文' if zh else 'Publications'}</h1><p>{'最新 Scholar 快照含 30 条记录，按研究主题组织；正式入口优先使用 DOI、会议页面或 arXiv。' if zh else 'The latest Scholar snapshot contains 30 records, organized by research theme; paper links prefer DOI, venue pages, or arXiv.'}</p><div class="hero-actions"><a class="btn" href="{site_content['scholar']}" target="_blank" rel="noopener">Google Scholar ↗</a><a class="btn" href="https://orcid.org/0009-0008-0471-9131" target="_blank" rel="noopener">ORCID ↗</a></div></div></section><section><div class="wrap">{paper_groups(lang)}</div></section>'''


def recognition_html(lang: str) -> str:
    key = "zh" if lang == "zh" else "en"
    return "".join(f'<article class="card"><div class="eyebrow">{esc(item["kind"][key])}</div><h3 style="margin-top:12px">{esc(item["title"][key])}</h3><p>{esc(item["detail"][key])}</p></article>' for item in site_content.get("recognition", []))


def patent_html(lang: str) -> str:
    result = []
    key = "zh" if lang == "zh" else "en"
    for theme_record in site_content.get("patentThemes", []):
        theme = theme_record.get("title", {}).get(key, "")
        items = [item for item in site_content.get("patents", []) if item.get("number") and item.get("themeId") == theme_record.get("id")]
        rows = "".join(f'<tr><td>{esc(item["number"])}</td><td>{esc(item.get("shortTitle", item["title"]))}</td><td>{esc(item.get("inventorOrder"))}</td><td>{esc(item.get("grantDate"))}</td></tr>' for item in items)
        headings = ("专利号", "短标题", "发明人顺序", "授权公告日") if lang == "zh" else ("Patent", "Short title", "Inventor order", "Grant date")
        empty = f'<p class="empty">{"当前没有已核对的代表条目。" if lang == "zh" else "No verified representative entry is listed yet."}</p>' if not items else ''
        table = f'<div class="table-wrap"><table><thead><tr>{"".join(f"<th>{esc(label)}</th>" for label in headings)}</tr></thead><tbody>{rows}</tbody></table></div>' if items else ''
        result.append(f'<details class="patent-group"><summary>{esc(theme)} <span class="paper-meta">({len(items)})</span></summary>{table}{empty}</details>')
    return "".join(result) or '<p class="empty">暂无代表性专利。</p>'


def patent_theme_html(lang: str) -> str:
    key = "zh" if lang == "zh" else "en"
    return "".join(f'<article class="card"><h3>{esc(item["title"][key])}</h3><p>{esc(item["text"][key])}</p></article>' for item in site_content.get("patentThemes", []))


def impact(lang: str) -> str:
    zh = lang == "zh"
    key = "zh" if zh else "en"
    personal_media = [m for m in published_media if m.get("kind") in MEDIA_KINDS][:2]
    videos = [m for m in published_media if m.get("kind") in VIDEO_KINDS][:2]
    team_media = [m for m in published_media if m.get("kind") in TEAM_KINDS][:3]
    project_media = [m for m in published_media if m.get("kind") in PROJECT_KINDS][:1]
    standards = "".join(f'<article class="media-item"><div><strong>{esc(item["id"])}</strong><div class="paper-meta">{esc(item["title"][key])}</div></div><small>{esc(item["role"][key])}</small></article>' for item in site_content["standards"])
    return f'''<section class="page-hero"><div class="wrap"><div class="eyebrow">04 / Impact & talks</div><h1>{'影响与交流' if zh else 'Impact & talks'}</h1><p>{'以公开奖项、研究、标准、专利和交流记录呈现个人负责与团队协作形成的影响。' if zh else 'Public awards, research, standards, patents, and conversations document individual responsibility and team impact.'}</p></div></section><section><div class="wrap"><div class="section-head"><div><div class="section-kicker">Recognition</div><h2>{'奖项、鉴定与行业认可' if zh else 'Awards, appraisal, and recognition'}</h2></div></div><div class="grid-2">{recognition_html(lang)}</div></div></section><section><div class="wrap"><div class="section-head"><div><div class="section-kicker">Patents</div><h2>{'代表性授权发明专利' if zh else 'Representative granted patents'}</h2></div></div><div class="grid-2">{patent_theme_html(lang)}</div>{patent_html(lang)}</div></section><section><div class="wrap grid-2"><div><div class="section-kicker">Standards & reports</div><h2>{'标准与技术报告' if zh else 'Standards & reports'}</h2></div><div class="media-list">{standards}</div></div></section><section id="talks"><div class="wrap"><div class="section-head"><div><div class="section-kicker">Talks</div><h2>{'公开演讲与技术分享' if zh else 'Public talks'}</h2></div></div><div class="media-list">{talk_rows(lang)}</div></div></section><section><div class="wrap"><div class="section-head"><div><div class="section-kicker">Personal media & videos</div><h2>{'个人观点与公开视频' if zh else 'Personal media and videos'}</h2></div></div><div class="media-list">{media_rows(lang, personal_media)}{media_rows(lang, videos)}</div></div></section><section><div class="wrap"><div class="section-head"><div><div class="section-kicker">Team and product context</div><h2>{'团队技术文章与产品背景' if zh else 'Team articles and product context'}</h2></div></div><div class="media-list">{media_rows(lang, team_media)}{media_rows(lang, project_media)}</div></div></section>'''


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
        "zh": {"": ("首页", "孙林的研究、工程、管理与公开成果。", home), "about": ("关于我", "孙林的个人简介、教育、经历与团队建设。", about), "research": ("研究与项目", "孙林的五层技术体系与代表性项目。", research), "publications": ("论文", "孙林按主题组织的 30 条论文记录。", publications), "impact": ("影响与交流", "孙林的荣誉、标准、专利、媒体与公开活动。", impact)},
        "en": {"": ("Home", "Lin Sun — research, engineering, leadership, and public work.", home), "about": ("About", "Lin Sun — profile, education, experience, and team building.", about), "research": ("Research & Projects", "Lin Sun — five-layer technical system and selected projects.", research), "publications": ("Publications", "Lin Sun — 30 publications organized by theme.", publications), "impact": ("Impact & Talks", "Lin Sun — recognition, standards, patents, media, and talks.", impact)},
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
