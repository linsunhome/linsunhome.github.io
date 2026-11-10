#!/usr/bin/env python3
"""Generate the static bilingual site from the checked-in content snapshots."""

from __future__ import annotations

import html
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

papers = json.loads((DATA / "scholar-2026-11-10.json").read_text())['papers']
media_data = json.loads((DATA / "media-links-2026-11-10.json").read_text())
site_content = json.loads((DATA / "site-content.json").read_text())
publication_metadata = json.loads((DATA / "publication-metadata.json").read_text())
media = media_data['items']
talks = media_data.get('talks', [])
published_media = [item for item in media if item.get('publish')]
public_media = [item for item in published_media if item.get('kind') in {'media-interview', 'institutional-news', 'talk-transcript', 'talk'}]
context_media = [item for item in published_media if item.get('kind') not in {'media-interview', 'institutional-news', 'talk-transcript', 'talk', 'unclassified'}]
media_translations = {item.get('url'): item for item in site_content.get('media', []) if item.get('url')}



def esc(value: object) -> str:
    return html.escape(str(value or ""), quote=True)


def nav(lang: str, active: str) -> str:
    labels = {
        'zh': [('about', '关于', '/about/'), ('research', '研究与项目', '/research/'), ('publications', '论文', '/publications/'), ('impact', '影响与交流', '/impact/')],
        'en': [('about', 'About', '/en/about/'), ('research', 'Research & Projects', '/en/research/'), ('publications', 'Publications', '/en/publications/'), ('impact', 'Impact & Talks', '/en/impact/')],
    }
    links = ''.join(f'<a href="{href}"' + (' aria-current="page"' if key == active else '') + f'>{label}</a>' for key, label, href in labels[lang])
    switch_routes = {
        'home': ('/', '/en/'),
        'about': ('/about/', '/en/about/'),
        'research': ('/research/', '/en/research/'),
        'publications': ('/publications/', '/en/publications/'),
        'impact': ('/impact/', '/en/impact/'),
    }
    if active.startswith('projects/'):
        project_slug = active.split('/', 1)[1]
        switch = f'/{"en/" if lang == "zh" else ""}projects/{project_slug}/'
    else:
        switch = switch_routes.get(active, switch_routes['home'])[1 if lang == 'zh' else 0]
    switch_label = 'EN' if lang == 'zh' else '中文'
    return f'''<header class="site-header"><div class="wrap nav">
      <a class="brand" href="{'/' if lang == 'zh' else '/en/'}"><strong>{'孙林' if lang == 'zh' else 'Lin Sun'}</strong><span>LIN SUN / AI BUILDER</span></a>
      <button class="menu-toggle" data-menu-toggle aria-expanded="false" aria-label="Menu">☰</button>
      <nav class="nav-links" data-nav>{links}</nav>
      <div class="nav-tools"><a class="lang" href="{switch}">{switch_label}</a></div>
    </div></header>'''


def footer(lang: str) -> str:
    text = '研究 · 工程 · 管理 · 公开交流' if lang == 'zh' else 'RESEARCH · ENGINEERING · LEADERSHIP · OPEN KNOWLEDGE'
    return f'''<footer><div class="wrap footer-grid"><div><strong>{'孙林 · Lin Sun' if lang == 'zh' else 'Lin Sun'}</strong><p>{text}</p></div><div class="footer-links"><a href="mailto:lincharliesun@gmail.com">lincharliesun@gmail.com</a><a href="https://github.com/linsunhome" target="_blank" rel="noopener">GitHub</a><a href="https://scholar.google.com/citations?user=b8yMN1MAAAAJ" target="_blank" rel="noopener">Google Scholar</a></div></div></footer>'''


def page(lang: str, active: str, title: str, description: str, body: str) -> str:
    return f'''<!doctype html>
<html lang="{'zh-CN' if lang == 'zh' else 'en'}">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="{esc(description)}"><title>{esc(title)}</title>
<link rel="stylesheet" href="/assets/styles.css"></head><body>
{nav(lang, active)}<main>{body}</main>{footer(lang)}
<script src="/assets/site.js" defer></script></body></html>'''


def paper_rows(lang: str, limit: int | None = None) -> str:
    rows = papers if limit is None else papers[:limit]
    result = []
    for paper in rows:
        year = paper.get('scholarYear', '')
        venue = paper.get('venue', '')
        citation = paper.get('citationLabel') or ('引用未提供' if lang == 'zh' else 'Citations unavailable')
        title = esc(paper['title'])
        authors = esc(paper.get('authors', ''))
        venue_text = f'{esc(venue)} · {esc(citation)}' if lang == 'zh' else f'{esc(venue)} · {esc(citation)} citations'
        metadata = publication_metadata.get(paper['title'], {})
        topic = paper['title'].lower()
        if any(word in topic for word in ('safety', 'secure', 'audit', 'alignment')):
            topic_label = '安全' if lang == 'zh' else 'Safety'
        elif any(word in topic for word in ('rag', 'retrieval', 'document', 'ocr', 'question-answer')):
            topic_label = 'RAG / 文档' if lang == 'zh' else 'RAG / documents'
        elif any(word in topic for word in ('reason', 'distillation', 'router', 'long-context', 'harness')):
            topic_label = '基础模型 / 推理' if lang == 'zh' else 'Foundation / reasoning'
        else:
            topic_label = '待分类' if lang == 'zh' else 'To classify'
        status = ('预印本' if lang == 'zh' else 'preprint') if metadata.get('status') == 'preprint' else ('发表状态待核验' if lang == 'zh' else 'publication status to verify')
        role = ('作者角色待核验' if lang == 'zh' else 'author role to verify') if not metadata.get('role') else metadata['role']
        paper_url = metadata.get('paperUrl')
        links = f'<a class="paper-link" href="{esc(paper_url)}" target="_blank" rel="noopener">Paper ↗</a>' if paper_url else ''
        scholar = f'<a class="paper-link" href="https://scholar.google.com/scholar?q={html.escape(paper["title"].replace(" ", "+"))}" target="_blank" rel="noopener">Scholar ↗</a>'
        result.append(f'''<article class="paper-row" data-paper-row data-year="{esc(year)}"><div class="paper-year">{esc(year)}</div><div><div class="paper-title">{title}</div><div class="paper-meta">{authors}<br>{venue_text}<br><span class="tag">{esc(topic_label)}</span> <span class="tag">{esc(status)}</span> <span class="tag">{esc(role)}</span></div></div><div>{links} {scholar}</div></article>''')
    return '\n'.join(result)


def media_rows(lang: str, limit: int | None = None, items=None) -> str:
    source = public_media if items is None else items
    rows = source if limit is None else source[:limit]
    result = []
    for item in rows:
        title = esc(item.get('title', ''))
        source = esc(item.get('source', ''))
        date = esc(item.get('date', item.get('year', '')))
        url = item.get('url')
        translated = media_translations.get(url, {})
        relation = esc(item.get('relation', '')) if lang == 'zh' else esc(translated.get('relationEn', 'Public source reviewed; personal and team attribution are kept separate.'))
        if lang == 'en' and translated.get('en'):
            title = esc(translated['en'])
        title_html = f'<a href="{esc(url)}" target="_blank" rel="noopener">{title} ↗</a>' if url else f'<strong>{title}</strong>'
        result.append(f'<article class="media-item"><div>{title_html}<div class="paper-meta">{relation}</div></div><small>{source} · {date}</small></article>')
    return '\n'.join(result)


def talk_rows(lang: str, limit: int | None = None) -> str:
    rows = talks if limit is None else talks[:limit]
    result = []
    for item in rows:
        title = esc(item.get('title', ''))
        event = esc(item.get('event', ''))
        date = esc(item.get('date', ''))
        role = esc(item.get('role', '')) if lang == 'zh' else 'Speaker / guest role recorded in the event materials.'
        url = item.get('url')
        title_html = f'<a href="{esc(url)}" target="_blank" rel="noopener">{title} ↗</a>' if url else f'<strong>{title}</strong>'
        result.append(f'<article class="media-item"><div>{title_html}<div class="paper-meta">{event} · {role}</div></div><small>{date}</small></article>')
    return '\n'.join(result)


def recent_updates(lang: str, limit: int | None = None) -> str:
    key = 'zh' if lang == 'zh' else 'en'
    rows = site_content['news'] if limit is None else site_content['news'][:limit]
    result = []
    for item in rows:
        target = item.get('url') or ('/' + ('en/' if lang == 'en' else '') + item['path'])
        result.append(f'<article class="media-item"><div><a href="{esc(target)}">{esc(item["title"][key])} ↗</a><div class="paper-meta">{esc(item["text"][key])}</div></div><small>{esc(item["date"])}</small></article>')
    return ''.join(result)


def home(lang: str) -> str:
    zh = lang == 'zh'
    copy = {
        'eyebrow': '个人研究 · 工程 · 管理', 'title': '把基础模型能力，变成可被理解、验证和使用的真实能力。',
        'intro': '孙林，360 算法高级研究员、基础大模型团队负责人。长期从事基础模型、后训练、大模型安全、RAG、记忆与 Agent 系统的研究和工程实践。',
        'about': '了解我', 'papers': '浏览论文', 'section_research': '研究与工程方向', 'section_research_desc': '从基础模型与后训练出发，连接安全治理、知识服务、记忆和真实业务。',
        'section_projects': '代表项目', 'section_projects_desc': '用问题、个人角色、结果和公开证据，说明研究如何进入系统和产品。',
        'section_papers': '精选研究成果', 'section_papers_desc': '最新 Scholar 快照包含 30 条记录，完整论文库按主题和年份持续维护。',
        'section_timeline': '经历与组织交付', 'section_timeline_desc': '技术路线、团队建设与业务结果在同一条时间线上展开。',
        'section_media': '近期公开交流', 'section_media_desc': '媒体观点、机构新闻和公开分享按证据和个人角色分别呈现。',
    } if zh else {
        'eyebrow': 'RESEARCH · ENGINEERING · LEADERSHIP', 'title': 'Turning foundation-model capability into work people can trust and use.',
        'intro': 'Lin Sun is a senior algorithm researcher and foundation-model team lead at 360. His work spans foundation models, post-training, LLM safety, RAG, memory, and agent systems.',
        'about': 'About me', 'papers': 'View publications', 'section_research': 'Research & engineering', 'section_research_desc': 'From foundation models and post-training to safety, knowledge services, memory, and real-world systems.',
        'section_projects': 'Selected work', 'section_projects_desc': 'Each project connects the problem, personal role, result, and public evidence.',
        'section_papers': 'Selected publications', 'section_papers_desc': 'The latest Scholar snapshot contains 30 records, maintained by topic and year.',
        'section_timeline': 'Experience & delivery', 'section_timeline_desc': 'Technical direction, team building, and business delivery across one timeline.',
        'section_media': 'Public conversations', 'section_media_desc': 'Media, institutional news, and talks are separated by evidence and personal role.',
    }
    projects = [('Foundation models & post-training', 'Long-context data, distillation, model merging, reasoning and efficient inference.', 'TinyR1 · Router Upcycling · Reasoning'), ('LLM safety & trustworthy generation', 'Dynamic attacks, evaluation, alignment, online protection and hallucination governance.', 'TriPlay-RL · Magic Token · Safety'), ('RAG, memory & agents', 'Evidence allocation, visual documents, long-term state, experience reuse and agent evaluation.', 'BEAR · TextlessRAG · MemAudit')]
    project_cards = ''.join(f'<article class="card"><span class="number">0{i + 1}</span><h3>{esc(title)}</h3><p>{esc(desc)}</p><div class="tag-row">' + ''.join(f'<span class="tag">{esc(tag.strip())}</span>' for tag in tags.split('·')) + '</div></article>' for i, (title, desc, tags) in enumerate(projects))
    project_cards2 = ''.join(f'<article class="card project-card"><div><div class="project-meta">{esc(item["period"])} · {esc(item["id"])}</div><h3 style="margin-top:12px">{esc(item["title"]["zh" if zh else "en"])}</h3><p>{esc(item["summary"]["zh" if zh else "en"])}</p></div><div class="result">{esc(item["result"]["zh" if zh else "en"])}<br><a class="paper-link" href="/{"en/" if not zh else ""}projects/{item["id"]}/">{"查看项目详情" if zh else "Read project details"} ↗</a></div></article>' for item in site_content['projects'])
    timeline = [('2010—2012', '腾讯网媒产品技术部' if zh else 'Tencent online media product technology', '汽车业务开发与推荐系统。' if zh else 'Automotive product engineering and recommendation systems.'), ('2012—2017', '360 搜索与智能语义' if zh else '360 search & intelligent semantics', '问答、语义、人机对话与大数据智能。' if zh else 'Search, question answering, semantics, dialogue, and data intelligence.'), ('2017—2023', '贝壳 / 如视' if zh else 'Beike / Rushi', '企业搜索云、数据智能、AI+VR 与跨职能团队。' if zh else 'Enterprise search, data intelligence, AI+VR, and cross-functional teams.'), ('2023—至今', '360 基础大模型' if zh else '360 foundation models', '基础模型、安全、RAG、记忆、经验系统与高效推理。' if zh else 'Foundation models, safety, RAG, memory, experience systems, and efficient reasoning.')]
    timeline_html = ''.join(f'<article class="timeline-item"><div class="timeline-time">{esc(year)}</div><div class="timeline-dot"></div><div class="timeline-card"><h3>{esc(role)}</h3><p>{esc(desc)}</p></div></article>' for year, role, desc in timeline)
    return f'''<section class="hero"><div class="wrap hero-grid"><div><div class="eyebrow">{copy['eyebrow']}</div><h1>{copy['title']}</h1><p class="hero-copy">{copy['intro']}</p><div class="hero-actions"><a class="btn primary" href="/{'en/' if not zh else ''}about/">{copy['about']} ↗</a><a class="btn" href="/{'en/' if not zh else ''}publications/">{copy['papers']} ↗</a></div></div><aside class="hero-card"><div class="monogram">LS</div><p>{'研究、工程、管理与产业实践的公开记录。' if zh else 'An open record of research, engineering, leadership, and industry practice.'}</p></aside></div><div class="wrap metric-grid"><div class="metric"><strong>16</strong><span>{'年技术研发与管理' if zh else 'years in research & engineering'}</span></div><div class="metric"><strong>30</strong><span>{'条 Scholar 论文记录' if zh else 'records in the Scholar snapshot'}</span></div><div class="metric"><strong>4</strong><span>{'个职业阶段' if zh else 'career stages'}</span></div><div class="metric"><strong>14</strong><span>{'条已核对公开记录' if zh else 'reviewed public records'}</span></div></div><div class="wrap"><p class="filter-note">{'口径：16 年与 4 个阶段来自个人经历材料；30 条来自 Scholar 快照；14 条为公开媒体与团队记录中标记可发布的条目。更新：2026-11-10。' if zh else 'Scope: 16 years and four stages come from the supplied career material; 30 records from the Scholar snapshot; 14 publishable media/team records. Updated 2026-11-10.'}</p></div></section>
<section><div class="wrap"><div class="section-head"><div><div class="section-kicker">01 / Research</div><h2>{copy['section_research']}</h2></div><p>{copy['section_research_desc']}</p></div><div class="grid-3">{project_cards}</div></div></section>
<section><div class="wrap"><div class="section-head"><div><div class="section-kicker">02 / Selected work</div><h2>{copy['section_projects']}</h2></div><p>{copy['section_projects_desc']}</p></div><div class="grid-3">{project_cards2}</div><div class="hero-actions"><a class="btn" href="/{'en/' if not zh else ''}research/">{'查看研究与项目详情' if zh else 'Explore research and projects'} ↗</a></div></div></section>
<section><div class="wrap"><div class="section-head"><div><div class="section-kicker">03 / Publications</div><h2>{copy['section_papers']}</h2></div><p>{copy['section_papers_desc']}</p></div><div class="paper-list">{paper_rows(lang, 6)}</div><div class="hero-actions"><a class="btn" href="/{'en/' if not zh else ''}publications/">{'查看完整论文库' if zh else 'View all publications'} ↗</a></div></div></section>
<section><div class="wrap"><div class="section-head"><div><div class="section-kicker">04 / Timeline</div><h2>{copy['section_timeline']}</h2></div><p>{copy['section_timeline_desc']}</p></div><div class="timeline">{timeline_html}</div><div class="hero-actions"><a class="btn" href="/{'en/' if not zh else ''}about/">{'查看完整经历' if zh else 'Read the full profile'} ↗</a></div></div></section>
<section><div class="wrap"><div class="section-head"><div><div class="section-kicker">05 / Media & talks</div><h2>{copy['section_media']}</h2></div><p>{copy['section_media_desc']}</p></div><div class="media-list">{media_rows(lang, 4, public_media)}</div><div class="hero-actions"><a class="btn" href="/{'en/' if not zh else ''}impact/">{'查看影响与交流' if zh else 'Explore impact and talks'} ↗</a></div></div></section>
<section><div class="wrap"><div class="section-head"><div><div class="section-kicker">06 / Updates</div><h2>{'近期动态' if zh else 'Recent updates'}</h2></div><p>{'只记录有日期、来源或公开活动依据的更新。' if zh else 'Only dated updates with a source or public activity record are included.'}</p></div><div class="media-list">{recent_updates(lang)}</div></div></section>
<section><div class="wrap"><div class="callout"><div class="eyebrow">{'OPEN CONTACT' if not zh else 'OPEN CONTACT'}</div><h2 style="margin-top:12px">{'保持交流，分享公开成果。' if zh else 'Open to thoughtful conversations.'}</h2><p>{'如果你希望交流基础模型、安全、RAG、记忆、Agent 或团队建设，可以通过邮箱联系我。' if zh else 'For conversations around foundation models, safety, RAG, memory, agents, or team building, reach me by email.'}</p><a class="btn" href="mailto:lincharliesun@gmail.com">lincharliesun@gmail.com ↗</a></div></div></section>'''


def about(lang: str) -> str:
    zh = lang == 'zh'
    career = site_content['career']
    career_html = ''.join(f'<article class="timeline-item"><div class="timeline-time">{esc(item["start"])}—{esc(item["end"] or ("至今" if zh else "present"))}</div><div class="timeline-dot"></div><div class="timeline-card"><h3>{esc(item["org"]["zh" if zh else "en"])} · {esc(item["role"]["zh" if zh else "en"])}</h3><p>{esc(item["text"]["zh" if zh else "en"])}</p><p class="paper-meta">{esc(item["management"]["zh" if zh else "en"])}</p></div></article>' for item in career)
    profile = site_content['profile']
    return f'''<section class="page-hero"><div class="wrap"><div class="eyebrow">01 / About</div><h1>{'关于我' if zh else 'About me'}</h1><p>{'研究、工程、团队与长期交付，构成我理解技术工作的四个角度。' if zh else 'Research, engineering, teams, and long-term delivery are four lenses through which I understand technical work.'}</p></div></section><section><div class="wrap grid-2"><div class="prose"><h2>{'个人简介' if zh else 'Profile'}</h2><p>{esc(profile['intro']['zh' if zh else 'en'])}</p><p>{'除技术路线外，我也关注团队建设、跨职能协作和组织交付，让模型能力能够在真实业务中持续运行。' if zh else 'Alongside technical direction, I care about team building, cross-functional collaboration, and organizational delivery so that model capabilities can operate sustainably in real products.'}</p></div><div class="card"><div class="eyebrow">CONTACT</div><h3 style="margin-top:14px">lincharliesun@gmail.com</h3><p>{'公开邮箱，用于研究、工程和产业交流。' if zh else 'A public inbox for research, engineering, and industry conversations.'}</p><a class="btn" href="mailto:lincharliesun@gmail.com">{'发送邮件' if zh else 'Send an email'} ↗</a></div></div></section><section><div class="wrap"><div class="section-head"><div><div class="section-kicker">02 / Career</div><h2>{'经历与组织交付' if zh else 'Experience & delivery'}</h2></div><p>{'时间线同时记录技术方向、职责变化和团队建设。' if zh else 'One timeline for technical direction, responsibility, and team building.'}</p></div><div class="timeline">{career_html}</div></div></section><section><div class="wrap grid-2"><article class="card"><div class="eyebrow">EDUCATION</div><h3 style="margin-top:14px">{esc(profile['education']['zh' if zh else 'en'])}</h3><p>{'教育背景、实验室经历与行业工作共同构成长期技术积累。' if zh else 'Education, laboratory experience, and industry work form a continuous technical practice.'}</p></article><article class="card"><div class="eyebrow">LEADERSHIP</div><h3 style="margin-top:14px">{'技术路线与团队建设' if zh else 'Technical direction & teams'}</h3><p>{'公开材料中的团队规模、职责和成果按具体来源分别说明，不用单一人数替代管理经历。' if zh else 'Team size, responsibility, and outcomes are described with their evidence; a single headcount never substitutes for the management story.'}</p></article></div></section><section><div class="wrap"><article class="card"><div class="eyebrow">INDUSTRY SERVICE</div><h2 style="margin-top:14px">{'联合实验室与行业技术服务' if zh else 'Laboratory and industry service'}</h2><p>{'材料记录北大–360 大模型联合实验室委员、大数据协同安全技术国家工程研究中心大模型专委会主任等经历；具体任期和公开任命依据发布前继续核验。' if zh else 'The supplied materials record service connected with the PKU–360 joint laboratory and an LLM safety committee at a national engineering research center; tenure and public appointment evidence remain to be verified.'}</p></article></div></section>'''


def project_by_slug(slug: str):
    for item in site_content['projects']:
        if item['id'] == slug:
            return item
    raise KeyError(slug)


def research(lang: str) -> str:
    zh = lang == 'zh'
    key = 'zh' if zh else 'en'
    areas = site_content['areas']
    area_html = ''.join(f'<article class="card"><div class="eyebrow">{esc(item["title"][key])}</div><h3 style="margin-top:14px">{esc(item["title"][key])}</h3><p>{esc(item["text"][key])}</p><div class="tag-row">' + ''.join(f'<span class="tag">{esc(tag)}</span>' for tag in item['tags']) + '</div></article>' for item in areas)
    project_html = ''.join(f'<article class="card project-card"><div><div class="project-meta">{esc(item["period"])} · {esc(item["id"])}</div><h3 style="margin-top:12px">{esc(item["title"][key])}</h3><p>{esc(item["summary"][key])}</p></div><div class="result">{esc(item["result"][key])}<br><a class="paper-link" href="/{"en/" if not zh else ""}projects/{item["id"]}/">{"查看详情" if zh else "Read project details"} ↗</a></div></article>' for item in site_content['projects'])
    return f'''<section class="page-hero"><div class="wrap"><div class="eyebrow">02 / Research & Projects</div><h1>{'研究与项目' if zh else 'Research & projects'}</h1><p>{'研究方法、系统工程与组织交付在项目中连接起来。' if zh else 'Research methods, systems engineering, and organizational delivery meet in the work.'}</p></div></section><section><div class="wrap"><div class="grid-3">{area_html}</div></div></section><section><div class="wrap"><div class="section-head"><div><div class="section-kicker">Selected projects</div><h2>{'代表项目' if zh else 'Selected projects'}</h2></div><p>{'每个项目都说明问题、个人角色、结果和公开证据。' if zh else 'Each project explains the problem, personal role, result, and public evidence.'}</p></div><div class="grid-2">{project_html}</div></div></section><section><div class="wrap"><div class="card"><div class="eyebrow">TECHNICAL THREAD</div><h2 style="margin-top:14px">{'攻击生成 → 自动评测 → 安全训练 → 在线防护 → 经验回流' if zh else 'Attack generation → evaluation → safety training → online protection → experience feedback'}</h2><p>{'这条链路是研究与工程之间的一个代表性连接；具体项目详情只展示可公开的技术信息。' if zh else 'This is one representative connection between research and engineering; project pages disclose only public technical information.'}</p></div></div></section>'''


def project_detail(lang: str, slug: str) -> str:
    zh = lang == 'zh'
    item = project_by_slug(slug)
    key = 'zh' if zh else 'en'
    links = ''.join(f'<a class="btn" href="{esc(link["url"])}" target="_blank" rel="noopener">{esc(link["label"][key])} ↗</a>' for link in item['links'])
    d = item
    return f'''<section class="page-hero"><div class="wrap"><div class="eyebrow">Research / Project detail</div><h1>{esc(d["title"][key])}</h1><p>{esc(d["summary"][key])}</p><div class="tag-row">{''.join(f'<span class="tag">{esc(tag)}</span>' for tag in d['tags'])}</div></div></section><section><div class="wrap grid-2"><article class="card"><div class="eyebrow">{'问题' if zh else 'Problem'}</div><p>{esc(d['problem'][key])}</p></article><article class="card"><div class="eyebrow">{'个人角色' if zh else 'Personal role'}</div><p>{esc(d['role'][key])}</p></article><article class="card"><div class="eyebrow">{'技术路径' if zh else 'Approach'}</div><p>{esc(d['approach'][key])}</p></article><article class="card"><div class="eyebrow">{'公开结果' if zh else 'Public result'}</div><p>{esc(d['result'][key])}</p></article></div></section><section><div class="wrap"><div class="section-head"><div><div class="section-kicker">Evidence</div><h2>{'公开链接' if zh else 'Public links'}</h2></div><p>{'链接只作为证据入口，不扩大报道或作者列表能够支持的结论。' if zh else 'Links are evidence entry points and do not support claims beyond the source or author list.'}</p></div><div class="hero-actions">{links}</div></div></section>'''


def publications(lang: str) -> str:
    zh = lang == 'zh'
    years = sorted({str(p.get('scholarYear')) for p in papers if p.get('scholarYear')}, reverse=True)
    options = '<option value="">' + ('全部年份' if zh else 'All years') + '</option>' + ''.join(f'<option value="{y}">{y}</option>' for y in years)
    return f'''<section class="page-hero"><div class="wrap"><div class="eyebrow">03 / Publications</div><h1>{'论文' if zh else 'Publications'}</h1><p>{'最新 Scholar 快照包含 30 条记录。列表保留原始引用标记，发表状态和作者角色在核验后补齐。' if zh else 'The latest Scholar snapshot contains 30 records. Original citation markers are preserved; publication status and author roles are verified separately.'}</p></div></section><section><div class="wrap"><div class="filters"><input data-paper-search type="search" placeholder="{'搜索标题、作者或主题' if zh else 'Search title, author, or topic'}"><select data-paper-year>{options}</select></div><p class="filter-note">{'数据接收日期：2026-11-10 · 空白引用显示“引用未提供”' if zh else 'Snapshot received: 2026-11-10 · Blank citation fields remain unavailable'}</p><div class="paper-list">{paper_rows(lang)}</div><p class="empty" data-paper-empty hidden>{'没有匹配的论文。' if zh else 'No publications match these filters.'}</p></div></section>'''


def impact(lang: str) -> str:
    zh = lang == 'zh'
    key = 'zh' if zh else 'en'
    honors = [('北京市科学技术进步二等奖','Beijing Science and Technology Progress Award'),('中国人工智能学会科技成果鉴定','CAAI technology achievement appraisal'),('SafetyAI Bench 连续两次第一','Two-time SafetyAI Bench first place'),('SuperCLUE-RAG 2024.11 第一','SuperCLUE-RAG first place in 2024.11'),('360 智盾入选未来产业优秀典型案例','360 Zh Dun named a future-industry case'),('TinyR1 开源发布','TinyR1 open-source release')]
    honor_html = ''.join(f'<article class="card"><h3>{esc(item[0] if zh else item[1])}</h3><p>{"资料记录；来源、日期与个人/团队归属在发布前逐项核验。" if zh else "Source record; date and individual/team attribution are verified item by item before publication."}</p><div class="tag-row"><span class="tag">{"待核验" if zh else "To verify"}</span></div></article>' for item in honors)
    standards = site_content['standards']
    standard_html = ''.join(f'<div class="media-item"><div><strong>{esc(item["kind"][key])}</strong><div class="paper-meta">{esc(item["title"][key])}</div></div><small>{esc(item["role"][key])}</small></div>' for item in standards)
    patent_html = ''.join(f'<div class="media-item"><div><strong>{esc(item["title"])}</strong><div class="paper-meta">{"授权发明专利 · 编号、公告日、申请人与发明人顺序待核验" if zh else "Granted invention patent · number, grant date, applicant, and inventor order to verify"}</div></div><small>{"材料条目" if zh else "Source record"}</small></div>' for item in site_content['patents'])
    context_html = media_rows(lang, items=context_media)
    return f'''<section class="page-hero"><div class="wrap"><div class="eyebrow">04 / Impact & talks</div><h1>{'影响与交流' if zh else 'Impact & talks'}</h1><p>{'产业实践、专业服务、媒体报道和公开分享共同构成长期影响。' if zh else 'Industry practice, professional service, media, and public talks form a long-term record of impact.'}</p></div></section><section><div class="wrap"><div class="section-head"><div><div class="section-kicker">Impact</div><h2>{'荣誉与产业影响' if zh else 'Recognition & impact'}</h2></div><p>{'团队和公司成果不会自动改写成个人独立成果。' if zh else 'Team and company outcomes are never rewritten as individual achievements by default.'}</p></div><div class="grid-3">{honor_html}</div></div></section><section><div class="wrap"><div class="section-head"><div><div class="section-kicker">Patents</div><h2>{'代表性专利（18 项）' if zh else 'Representative patents (18)'}</h2></div><p>{'名称来自资料条目；法律编号、授权公告日、申请人和发明人顺序待逐项核验。' if zh else 'Titles come from the supplied records; legal identifiers, grant dates, applicants, and inventor order remain to be verified item by item.'}</p></div><div class="media-list">{patent_html}</div></div></section><section><div class="wrap grid-2"><div><div class="section-kicker">Standards & reports</div><h2>{'标准与技术报告' if zh else 'Standards & reports'}</h2></div><div class="media-list">{standard_html}</div></div></section><section id="talks"><div class="wrap"><div class="section-head"><div><div class="section-kicker">Talks</div><h2>{'公开演讲与技术分享' if zh else 'Public talks'}</h2></div><p>{'没有公开 URL 的活动仍可显示文字摘要，不提供空链接或本地附件下载。' if zh else 'Talks without public URLs remain text-only summaries; no empty links or local attachments are exposed.'}</p></div><div class="media-list">{talk_rows(lang)}</div></div></section><section><div class="wrap"><div class="section-head"><div><div class="section-kicker">Media & team context</div><h2>{'媒体与团队成果背景' if zh else 'Media & team context'}</h2></div><p>{'团队文章、公司新闻和历史项目报道单独标注，不作为个人采访或个人获奖证据。' if zh else 'Team articles, company news, and historical project coverage are separated from personal interviews and awards.'}</p></div><div class="media-list">{context_html}</div></div></section>'''


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')


def main() -> None:
    # Remove generated pages only; source assets and documentation remain untouched.
    for path in [ROOT / 'index.html', ROOT / 'en', ROOT / 'about', ROOT / 'research', ROOT / 'publications', ROOT / 'impact', ROOT / 'projects']:
        if path.is_file(): path.unlink()
        elif path.is_dir(): shutil.rmtree(path)
    pages = {
        'zh': {'': ('首页', '孙林的研究、工程、管理与公开成果。', home), 'about': ('关于我', '孙林的个人简介、经历与团队建设。', about), 'research': ('研究与项目', '孙林的研究方向与代表性项目。', research), 'publications': ('论文', '孙林的论文与 Google Scholar 公开记录。', publications), 'impact': ('影响与交流', '孙林的荣誉、标准、媒体与公开活动。', impact)},
        'en': {'': ('Home', 'Lin Sun — research, engineering, leadership, and public work.', home), 'about': ('About', 'Lin Sun — profile, experience, and team building.', about), 'research': ('Research & Projects', 'Lin Sun — research areas and selected projects.', research), 'publications': ('Publications', 'Lin Sun — publications and public Scholar records.', publications), 'impact': ('Impact & Talks', 'Lin Sun — recognition, standards, media, and talks.', impact)},
    }
    for project in site_content['projects']:
        slug = project['id']
        pages['zh'][f'projects/{slug}'] = (project['title']['zh'], project['summary']['zh'], lambda language, value=slug: project_detail(language, value))
        pages['en'][f'projects/{slug}'] = (project['title']['en'], project['summary']['en'], lambda language, value=slug: project_detail(language, value))
    for lang, entries in pages.items():
        for route, (title, description, renderer) in entries.items():
            path = ROOT / ('en' if lang == 'en' else '') / route / 'index.html' if route else ROOT / ('en/index.html' if lang == 'en' else 'index.html')
            write(path, page(lang, route or 'home', f'{title} | {"Lin Sun" if lang == "en" else "孙林"}', description, renderer(lang)))
    print(f'Generated {sum(len(v) for v in pages.values())} pages from {len(papers)} papers and {len(published_media)} published media items.')


if __name__ == '__main__':
    main()
