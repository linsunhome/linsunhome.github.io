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


def publication_url(metadata: dict) -> str | None:
    """Prefer a DOI/ACL/arXiv entry over an internal search result."""
    official = metadata.get('officialUrl')
    if official and 'base-search.net' not in official:
        return official
    return metadata.get('paperUrl')


VENUE_NAMES = {
    'ACL': 'Annual Meeting of the Association for Computational Linguistics',
    'EMNLP': 'Conference on Empirical Methods in Natural Language Processing',
    'AAAI': 'AAAI Conference on Artificial Intelligence',
    'ECAI': 'European Conference on Artificial Intelligence',
    'ICASSP': 'IEEE International Conference on Acoustics, Speech, and Signal Processing',
    'NeurIPS': 'Conference on Neural Information Processing Systems',
    'FSKD': 'International Conference on Fuzzy Systems and Knowledge Discovery',
    'ICMLC': 'International Conference on Machine Learning and Cybernetics',
    'SMC': 'IEEE International Conference on Systems, Man, and Cybernetics',
    'Acta Automatica Sinica': 'Acta Automatica Sinica',
    'Expert Systems with Applications': 'Expert Systems with Applications',
}


def venue_key(venue: str) -> str:
    for key in VENUE_NAMES:
        if venue.startswith(key):
            return key
    return 'arXiv' if venue.startswith('arXiv') else venue


def venue_year(venue: str, fallback: object) -> object:
    match = re.search(r'(?<!\d)(?:19|20)\d{2}(?!\d)', venue)
    return match.group(0) if match else fallback


def venue_short(venue: str, year: object) -> str:
    key = venue_key(venue)
    year = venue_year(venue, year)
    label = 'arXiv' if key == 'arXiv' else {'Expert Systems with Applications': 'ESWA', 'Acta Automatica Sinica': 'AAS'}.get(key, key)
    oral = ' oral' if '(oral)' in venue.lower() else ''
    findings = ' findings' if 'findings' in venue.lower() else ''
    return f'{label} {year}{findings}{oral}'.strip()


def venue_full(venue: str, year: object) -> str:
    key = venue_key(venue)
    if key == 'arXiv':
        return re.sub(r'\bpreprint\b\s*', '', venue, flags=re.IGNORECASE).strip()
    year = venue_year(venue, year)
    full = VENUE_NAMES[key]
    tail = venue[len(key):].strip()
    tail = re.sub(r'^(?:19|20)\d{2}\s*', '', tail)
    oral = '(oral)' in tail.lower()
    findings = 'findings' in tail.lower()
    tail = re.sub(r'\(oral\)', '', tail, flags=re.IGNORECASE)
    tail = re.sub(r'\bfindings\b', '', tail, flags=re.IGNORECASE).strip(' ,')
    if findings and key in {'ACL', 'EMNLP'}:
        full = f'Findings of the Association for Computational Linguistics: {key} {year}'
    else:
        full = f'{full} {year}'
    if oral:
        full += ' (oral)'
    if tail:
        full += f' {tail}'
    return full


def author_html(authors: str) -> tuple[str, bool]:
    """Render every supplied author and identify whether Lin Sun is first author."""
    names = [name.strip() for name in authors.split(',') if name.strip()]
    sun_names = {'L Sun', 'S Lin'}
    first_is_sun = bool(names and names[0] in sun_names)
    rendered = []
    for name in names:
        if name in sun_names:
            rendered.append('<strong>Lin Sun</strong>')
        else:
            rendered.append(esc(name))
    return ', '.join(rendered), first_is_sun


def paper_topic(title: str, lang: str) -> str:
    title = title.lower()
    if any(word in title for word in ('safety', 'secure', 'audit', 'alignment')):
        return '安全与对齐' if lang == 'zh' else 'Safety & alignment'
    if any(word in title for word in ('rag', 'retrieval', 'document', 'ocr', 'question-answer')):
        return 'RAG 与文档理解' if lang == 'zh' else 'RAG & document understanding'
    if any(word in title for word in ('reason', 'distillation', 'router', 'long-context', 'harness')):
        return '基础模型与推理' if lang == 'zh' else 'Foundation models & reasoning'
    if any(word in title for word in ('memory', 'agent', 'experience', 'claw')):
        return '记忆与 Agent' if lang == 'zh' else 'Memory & agents'
    return '搜索与知识服务' if lang == 'zh' else 'Search & knowledge services'


def metadata_topic(metadata: dict, title: str, lang: str) -> str:
    labels = {
        'safety': ('安全与对齐', 'Safety & alignment'),
        'knowledge': ('RAG 与知识推理', 'RAG & knowledge reasoning'),
        'foundation': ('基础模型与推理', 'Foundation models & reasoning'),
        'agents': ('记忆与 Agent', 'Memory & agents'),
        'early': ('搜索与知识服务', 'Search & knowledge services'),
    }
    topic = metadata.get('topic')
    return labels.get(topic, (paper_topic(title, 'zh'), paper_topic(title, 'en')))[0 if lang == 'zh' else 1]


def display_tag(tag: str, lang: str) -> str:
    if lang != 'zh':
        return tag
    return {
        'Reasoning': '推理', 'Distillation': '蒸馏', 'Long context': '长上下文',
        'Alignment': '对齐', 'Safety': '安全', 'Evaluation': '评测',
        'RAG': 'RAG', 'Memory': '记忆', 'Agents': 'Agent',
        'Open research': '开放研究', 'Document AI': '文档智能',
        'Evidence reasoning': '证据推理',
    }.get(tag, tag)


def paper_rows(lang: str, limit: int | None = None, titles: list[str] | None = None) -> str:
    rows = papers
    if titles:
        selected = []
        for query in titles:
            selected.extend([p for p in papers if query.lower() in p['title'].lower()])
        rows = selected
    if limit is not None:
        rows = rows[:limit]
    result = []
    for paper in rows:
        year = paper.get('scholarYear', '')
        venue = paper.get('venue', '')
        title = esc(paper['title'])
        authors, _ = author_html(paper.get('authors', ''))
        metadata = publication_metadata.get(paper['title'], {})
        topic_label = metadata_topic(metadata, paper['title'], lang)
        paper_url = publication_url(metadata)
        title_html = f'<a href="{esc(paper_url)}" target="_blank" rel="noopener">{title}</a>' if paper_url else title
        short_venue = venue_short(venue, year)
        full_venue = venue_full(venue, year)
        tags = f'<span class="tag">{esc(topic_label)}</span>'
        role = metadata.get('role')
        role_tag = f' <span class="tag">{esc(role)}</span>' if role else ''
        result.append(f'''<article class="paper-row" data-paper-row data-year="{esc(year)}"><div class="paper-body"><div class="paper-kicker"><span class="paper-short-venue">[{esc(short_venue)}]</span> {tags}{role_tag}</div><div class="paper-title">{title_html}</div><div class="paper-meta paper-authors">{authors}</div><div class="paper-meta paper-venue">{esc(full_venue)}</div></div></article>''')
    return '\n'.join(result)


def paper_year_groups(lang: str) -> str:
    grouped = {}
    for paper in papers:
        grouped.setdefault(str(paper.get('scholarYear', '')), []).append(paper)
    return '\n'.join(
        f'<section class="paper-year-group"><div class="section-kicker">{esc(year)}</div><div class="paper-list">{paper_rows(lang, titles=[p["title"] for p in rows])}</div></section>'
        for year, rows in sorted(grouped.items(), key=lambda item: item[0], reverse=True)
    )


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
        if lang == 'en' and translated.get('en'):
            title = esc(translated['en'])
        title_html = f'<a href="{esc(url)}" target="_blank" rel="noopener">{title} ↗</a>' if url else f'<strong>{title}</strong>'
        result.append(f'<article class="media-item"><div>{title_html}</div><small>{source} · {date}</small></article>')
    return '\n'.join(result)


def talk_rows(lang: str, limit: int | None = None) -> str:
    rows = talks if limit is None else talks[:limit]
    result = []
    for item in rows:
        title = esc(item.get('title', ''))
        event = esc(item.get('event', ''))
        date = esc(item.get('date', ''))
        url = item.get('url')
        title_html = f'<a href="{esc(url)}" target="_blank" rel="noopener">{title} ↗</a>' if url else f'<strong>{title}</strong>'
        result.append(f'<article class="media-item"><div>{title_html}</div><small>{event} · {date}</small></article>')
    return '\n'.join(result)


def recent_updates(lang: str, limit: int | None = None) -> str:
    key = 'zh' if lang == 'zh' else 'en'
    rows = site_content['news'] if limit is None else site_content['news'][:limit]
    result = []
    for item in rows:
        target = item.get('url') or ('/' + ('en/' if lang == 'en' else '') + item['path'])
        result.append(f'<article class="media-item"><div><a href="{esc(target)}">{esc(item["title"][key])} ↗</a></div><small>{esc(item["date"])}</small></article>')
    return '\n'.join(result)


def home(lang: str) -> str:
    zh = lang == 'zh'
    copy = {
        'eyebrow': '个人研究 · 工程 · 管理', 'title': '把基础模型能力，变成可被理解、验证和使用的真实能力。',
        'intro': '孙林，360 算法高级研究员、基础大模型团队负责人。长期从事基础模型、后训练、大模型安全、RAG、记忆与 Agent 系统的研究和工程实践。',
        'about': '了解我', 'papers': '浏览论文', 'section_research': '研究与工程方向',
        'section_projects': '代表项目',
        'section_papers': '精选研究成果',
        'section_media': '近期交流与动态',
    } if zh else {
        'eyebrow': 'RESEARCH · ENGINEERING · LEADERSHIP', 'title': 'Turning foundation-model capability into work people can trust and use.',
        'intro': 'Lin Sun is a senior algorithm researcher and foundation-model team lead at 360. His work spans foundation models, post-training, LLM safety, RAG, memory, and agent systems.',
        'about': 'About me', 'papers': 'View publications', 'section_research': 'Research & engineering',
        'section_projects': 'Selected work',
        'section_papers': 'Selected publications',
        'section_media': 'Recent conversations & updates',
    }
    projects = [('基础模型与后训练' if zh else 'Foundation models & post-training', '长上下文数据、蒸馏、模型融合、推理和高效部署。' if zh else 'Long-context data, distillation, model merging, reasoning, and efficient deployment.', 'TinyR1 · Router Upcycling · 推理' if zh else 'TinyR1 · Router Upcycling · Reasoning'), ('大模型安全与可信生成' if zh else 'LLM safety & trustworthy generation', '动态攻防、安全对齐、在线防护与幻觉治理。' if zh else 'Dynamic attacks, safety alignment, online protection, and hallucination governance.', 'TriPlay-RL · Magic Token · 安全' if zh else 'TriPlay-RL · Magic Token · Safety'), ('RAG、记忆与 Agent' if zh else 'RAG, memory & agents', '文档理解、多文档证据、长期状态、经验复用与 Agent 评测。' if zh else 'Document understanding, multi-document evidence, long-term state, experience reuse, and agent evaluation.', 'BEAR · TextlessRAG · Agent')]
    project_cards = ''.join(f'<article class="card"><span class="number">0{i + 1}</span><h3>{esc(title)}</h3><p>{esc(desc)}</p><div class="tag-row">' + ''.join(f'<span class="tag">{esc(tag.strip())}</span>' for tag in tags.split('·')) + '</div></article>' for i, (title, desc, tags) in enumerate(projects))
    project_cards2 = ''.join(f'<article class="card project-card"><div><div class="project-meta">{esc(item["period"] if zh else item["period"] + " · " + item["id"])}</div><h3 style="margin-top:12px">{esc(item["title"]["zh" if zh else "en"])}</h3><p>{esc(item["summary"]["zh" if zh else "en"])}</p></div><div class="result"><a class="paper-link" href="/{"en/" if not zh else ""}projects/{item["id"]}/">{"查看项目详情" if zh else "Read project details"} ↗</a></div></article>' for item in site_content['projects'])
    overview = ('我先后在腾讯、360、贝壳找房与如视等团队从事推荐系统、搜索问答、数据智能、基础模型和大模型安全工作；目前在 360 负责基础大模型团队，连接研究、工程、团队建设与线上交付。近年来的研究成果发表于 NeurIPS、ACL、EMNLP、AAAI、ECAI、ICASSP 等会议和期刊，并围绕大模型安全、RAG、记忆和 Agent 系统形成持续的公开研究与产业实践，相关团队成果获得北京市科学技术进步二等奖、SafetyAI Bench 连续两次第一和 SuperCLUE-RAG 评测第一等认可。' if zh else 'I have worked across Tencent, 360, Beike and Rushi on recommendation, search and question answering, data intelligence, foundation models, and LLM safety. I currently lead a foundation-model team at 360, connecting research, engineering, team building, and production delivery. Recent work appears across NeurIPS, ACL, EMNLP, AAAI, ECAI, and ICASSP, with a continuing focus on LLM safety, RAG, memory, and agent systems. Related team work has received the Beijing Science and Technology Progress Award and top results in SafetyAI Bench and SuperCLUE-RAG.')
    return f'''<section class="hero"><div class="wrap hero-grid"><div><div class="eyebrow">{copy['eyebrow']}</div><h1>{copy['title']}</h1><p class="hero-copy">{copy['intro']}</p><p class="hero-overview">{overview}</p><div class="hero-actions"><a class="btn primary" href="/{'en/' if not zh else ''}about/">{copy['about']} ↗</a><a class="btn" href="/{'en/' if not zh else ''}publications/">{copy['papers']} ↗</a></div></div><aside class="hero-card"><div class="monogram">LS</div></aside></div></section>
<section><div class="wrap"><div class="section-head"><div><div class="section-kicker">01 / Research</div><h2>{copy['section_research']}</h2></div></div><div class="grid-3">{project_cards}</div></div></section>
<section><div class="wrap"><div class="section-head"><div><div class="section-kicker">02 / Selected work</div><h2>{copy['section_projects']}</h2></div></div><div class="grid-3">{project_cards2}</div><div class="hero-actions"><a class="btn" href="/{'en/' if not zh else ''}research/">{'查看研究与项目详情' if zh else 'Explore research and projects'} ↗</a></div></div></section>
<section><div class="wrap"><div class="section-head"><div><div class="section-kicker">03 / Publications</div><h2>{copy['section_papers']}</h2></div></div><div class="paper-list">{paper_rows(lang, titles=['TriPlay-RL', 'BEAR:', 'Tinyr1-32b-preview', 'Chain-of-thought matters', 'When Good OCR'])}</div><div class="hero-actions"><a class="btn" href="/{'en/' if not zh else ''}publications/">{'查看完整论文库' if zh else 'View all publications'} ↗</a></div></div></section>
<section><div class="wrap"><div class="section-head"><div><div class="section-kicker">04 / {"Media, talks & updates" if not zh else "Media, talks & updates"}</div><h2>{copy['section_media']}</h2></div></div><h3 class="subsection-title">{'公开交流' if zh else 'Public conversations'}</h3><div class="media-list">{media_rows(lang, 3, public_media)}</div><h3 class="subsection-title">{'近期动态' if zh else 'Recent updates'}</h3><div class="media-list recent-update-list">{recent_updates(lang, 3)}</div><div class="hero-actions"><a class="btn" href="/{'en/' if not zh else ''}impact/">{'查看影响与交流' if zh else 'Explore impact and talks'} ↗</a></div></div></section>
<section><div class="wrap"><div class="callout"><div class="eyebrow">{'OPEN CONTACT' if not zh else 'OPEN CONTACT'}</div><h2 style="margin-top:12px">{'联系我' if zh else 'Get in touch'}</h2><p>{'如果你希望交流基础模型、安全、RAG、记忆、Agent 或团队建设，可以通过邮箱联系我。' if zh else 'For conversations around foundation models, safety, RAG, memory, agents, or team building, reach me by email.'}</p><a class="btn" href="mailto:lincharliesun@gmail.com">lincharliesun@gmail.com ↗</a></div></div></section>'''


def about(lang: str) -> str:
    zh = lang == 'zh'
    career = site_content['career']
    career_html = ''.join(f'<article class="timeline-item"><div class="timeline-time">{esc(item["start"])}—{esc(item["end"] or ("至今" if zh else "present"))}</div><div class="timeline-dot"></div><div class="timeline-card"><h3>{esc(item["org"]["zh" if zh else "en"])} · {esc(item["role"]["zh" if zh else "en"])}</h3><p>{esc(item["text"]["zh" if zh else "en"])}</p></div></article>' for item in career)
    profile = site_content['profile']
    return f'''<section class="page-hero"><div class="wrap"><div class="eyebrow">01 / About</div><h1>{'关于我' if zh else 'About me'}</h1></div></section><section><div class="wrap grid-2"><div class="prose"><h2>{'个人简介' if zh else 'Profile'}</h2><p>{esc(profile['intro']['zh' if zh else 'en'])}</p><p>{'我先后在腾讯、360、贝壳找房与如视承担推荐、搜索问答、数据智能、AI 应用和基础模型相关工作，曾负责技术路线、团队建设与产品交付。当前重点关注大模型安全、可信生成、RAG、记忆和 Agent 系统。' if zh else 'My experience spans Tencent, 360, Beike, and Rushi across recommendation, search and question answering, data intelligence, AI applications, and foundation models. I have led technical direction, team building, and product delivery, with a current focus on LLM safety, trustworthy generation, RAG, memory, and agent systems.'}</p></div><div class="card"><div class="eyebrow">CONTACT</div><h3 style="margin-top:14px">lincharliesun@gmail.com</h3><a class="btn" href="mailto:lincharliesun@gmail.com">{'发送邮件' if zh else 'Send an email'} ↗</a></div></div></section><section><div class="wrap"><div class="section-head"><div><div class="section-kicker">02 / Career</div><h2>{'经历与组织交付' if zh else 'Experience & delivery'}</h2></div></div><div class="timeline">{career_html}</div></div></section><section><div class="wrap grid-2"><article class="card"><div class="eyebrow">EDUCATION</div><h3 style="margin-top:14px">{esc(profile['educationDetails']['zh' if zh else 'en'])}</h3></article><article class="card"><div class="eyebrow">LEADERSHIP</div><h3 style="margin-top:14px">{'技术路线与团队建设' if zh else 'Technical direction & teams'}</h3><p>{'跨职能团队覆盖算法、搜索、NLP、知识图谱、语音、大数据、工程、产品与测试。' if zh else 'Cross-functional teams spanning algorithms, search, NLP, knowledge graphs, speech, data, engineering, product, and testing.'}</p></article></div></section><section><div class="wrap"><article class="card"><div class="eyebrow">INDUSTRY SERVICE</div><h2 style="margin-top:14px">{'联合实验室与行业技术服务' if zh else 'Laboratory and industry service'}</h2><p>{'北大–360 大模型联合实验室委员、360 集团技术委员会算法分委会主席；参与大数据协同安全技术国家工程研究中心大模型专委会。' if zh else 'Member of the PKU–360 Joint Laboratory and chair of the algorithm committee of 360’s technology committee; participant in an LLM committee at a national engineering research center.'}</p></article></div></section>'''


def project_by_slug(slug: str):
    for item in site_content['projects']:
        if item['id'] == slug:
            return item
    raise KeyError(slug)


def research(lang: str) -> str:
    zh = lang == 'zh'
    key = 'zh' if zh else 'en'
    areas = site_content['areas']
    area_html = ''.join(f'<article class="card"><div class="eyebrow">{esc(item["title"][key])}</div><h3 style="margin-top:14px">{esc(item["title"][key])}</h3><p>{esc(item["text"][key])}</p><div class="tag-row">' + ''.join(f'<span class="tag">{esc(display_tag(tag, lang))}</span>' for tag in item['tags']) + '</div></article>' for item in areas)
    project_html = ''.join(f'<article class="card project-card"><div><div class="project-meta">{esc(item["period"] if zh else item["period"] + " · " + item["id"])}</div><h3 style="margin-top:12px">{esc(item["title"][key])}</h3><p>{esc(item["summary"][key])}</p></div><div class="result"><a class="paper-link" href="/{"en/" if not zh else ""}projects/{item["id"]}/">{"查看详情" if zh else "Read project details"} ↗</a></div></article>' for item in site_content['projects'])
    stages = [
        ('攻击生成', 'Attack generation', 'llm-safety', '构造不断变化的风险样本，覆盖越狱、提示注入和有害内容。' if zh else 'Construct evolving risk samples across jailbreaks, prompt injection, and harmful content.'),
        ('自动评测', 'Automated evaluation', 'llm-safety', '用可重复的评测协议量化攻击有效性、风险类型和防护边界。' if zh else 'Use repeatable evaluation protocols to quantify attack effectiveness and protection boundaries.'),
        ('安全训练', 'Safety training', 'llm-safety', '以 TriPlay-RL、Magic Token 等工作连接攻击、评测与模型行为控制。' if zh else 'Connect attacks, evaluation, and behavior control through work such as TriPlay-RL and Magic Token.'),
        ('在线防护', 'Online protection', 'llm-safety', '通过检测、策略调度和分层响应把模型安全能力接入线上服务。' if zh else 'Bring safety capabilities into production through detection, policy routing, and layered response.'),
        ('经验回流', 'Experience feedback', 'memory-agents', '将任务反馈、风险样本和复盘经验沉淀为后续训练与治理依据。' if zh else 'Turn task feedback, risk samples, and reviews into inputs for later training and governance.'),
    ]
    thread_html = ''.join(f'<a class="thread-step" href="/{"en/" if not zh else ""}projects/{slug}/"><span class="thread-index">0{i + 1}</span><strong>{zh_title if zh else en_title}</strong><p>{desc}</p><span class="paper-link">{"查看关联项目" if zh else "Open related project"} ↗</span></a>' for i, (zh_title, en_title, slug, desc) in enumerate(stages))
    return f'''<section class="page-hero"><div class="wrap"><div class="eyebrow">02 / Research & Projects</div><h1>{'研究与项目' if zh else 'Research & projects'}</h1></div></section><section><div class="wrap"><div class="grid-3">{area_html}</div></div></section><section><div class="wrap"><div class="section-head"><div><div class="section-kicker">Selected projects</div><h2>{'代表项目' if zh else 'Selected projects'}</h2></div></div><div class="grid-2">{project_html}</div></div></section><section><div class="wrap"><div class="section-head"><div><div class="section-kicker">TECHNICAL THREAD</div><h2>{'从风险发现到持续治理' if zh else 'From risk discovery to continuous governance'}</h2></div></div><div class="thread-grid">{thread_html}</div></div></section>'''


def project_detail(lang: str, slug: str) -> str:
    zh = lang == 'zh'
    item = project_by_slug(slug)
    key = 'zh' if zh else 'en'
    links = ''.join(f'<a class="btn" href="{esc(link["url"])}" target="_blank" rel="noopener">{esc(link["label"][key])} ↗</a>' for link in item['links'])
    related = paper_rows(lang, titles=item.get('paperQueries', []))
    related_media_map = {
        'llm-safety': ['https://news.southcn.com/node_17a07e5926/e1570938be.shtml', 'https://k.sina.com.cn/article_2674405451_9f68304b019015of2.html', 'https://mp.weixin.qq.com/s/Z5HIYQ8fzq9vdlXOQ-OlDw'],
        'rag-knowledge': ['https://mp.weixin.qq.com/s/C9ckNrC1SNWDzAh8KHri-w'],
        'tinyr1': ['https://cs.pku.edu.cn/info/1263/3601.htm', 'https://mp.weixin.qq.com/s/KKUc6AGeizPELOYZayAb5w'],
        'memory-agents': ['https://mp.weixin.qq.com/s/YMqNYmVMEhUgQ5EomtCIog'],
    }
    related_items = [m for m in published_media if m.get('url') in related_media_map.get(slug, [])]
    related_media = media_rows(lang, items=related_items)
    detail_figure = {
        'llm-safety': ('TriPlay-RL 报告攻击有效性提升 20%–50%、防护性能提升 10%–30%；Magic Token 报告攻击条件下性能下降约 3.8%，基线平均下降 21.5%。' if zh else 'TriPlay-RL reports a 20%–50% gain in adversarial effectiveness and a 10%–30% gain in safety performance. Magic Token reports an approximately 3.8% drop under attack versus a 21.5% average drop for baselines.'),
        'rag-knowledge': ('BEAR 在九类评测设置中采用层级语义索引、粗到细证据分配和局部恢复；在 DragonBall 上报告 85.55% Recall、91.86% Completeness，并将最终证据上下文控制在约 4K tokens。OCR 论文覆盖 11 类复杂文档，说明字符级 OCR 指标与下游 RAG 效果之间存在差距。' if zh else 'BEAR uses hierarchical semantic indices, coarse-to-fine evidence allocation, and localized recovery across nine evaluation settings. On DragonBall it reports 85.55% recall and 91.86% completeness with an approximately 4K-token final evidence context. The OCR paper covers 11 challenging document types and shows why character-level OCR scores can miss downstream RAG failures.'),
        'tinyr1': ('TinyR1 技术报告的 Branch-Merge Distillation 分为 Branch 和 Merge 两阶段；相较原始学生模型，报告数学、编程和科学任务分别提升 5.5、4.4 和 2.9 个百分点，并在 AIME 2024 上达到与 DeepSeek-R1 可比的结果。' if zh else 'The TinyR1 technical report separates Branch-Merge Distillation into Branch and Merge phases. It reports gains of 5.5, 4.4, and 2.9 points in mathematics, coding, and science over the original student, with comparable results to DeepSeek-R1 on AIME 2024.'),
        'memory-agents': ('Mem360 将记忆拆分为情景、语义和程序记忆，并结合向量库、图数据库和统一接口支持长期状态管理；相关论文讨论工作流评测、记忆安全和经验服务。' if zh else 'Mem360 separates episodic, semantic, and procedural memory and combines vector storage, graph storage, and a unified interface for long-term state. Related papers cover workflow evaluation, memory security, and experience serving.'),
    }.get(slug, '')
    image_map = {
        'llm-safety': [('assets/projects/llm-safety-overview.png', '大模型安全与可信生成框架' if zh else 'LLM safety and trustworthy generation framework'), ('assets/projects/llm-safety-online.png', '在线防护链路' if zh else 'Online protection pipeline')],
        'rag-knowledge': [('assets/projects/rag-trustworthy-generation.png', '可信生成框架' if zh else 'Trustworthy generation framework'), ('assets/projects/bear-paper-figure2.png', 'BEAR 证据分配' if zh else 'BEAR evidence allocation')],
        'tinyr1': [('assets/projects/tinyr1-paper-figure1.png', 'TinyR1 Branch-Merge Distillation' if zh else 'TinyR1 Branch-Merge Distillation')],
    }
    figures = ''.join(f'<figure class="project-figure"><img src="/{path}" alt="{esc(alt)}"><figcaption>{esc(alt)}</figcaption></figure>' for path, alt in image_map.get(slug, []))
    d = item
    return f'''<section class="page-hero"><div class="wrap"><div class="eyebrow">Research / Project detail</div><h1>{esc(d["title"][key])}</h1><p>{esc(d["summary"][key])}</p><div class="tag-row">{''.join(f'<span class="tag">{esc(tag)} </span>' for tag in d['tags'])}</div></div></section><section><div class="wrap grid-3"><article class="card"><div class="eyebrow">{'问题 / 动机' if zh else 'Problem / motivation'}</div><p>{esc(d['problem'][key])}</p></article><article class="card"><div class="eyebrow">{'个人角色' if zh else 'Personal role'}</div><p>{esc(d['role'][key])}</p></article><article class="card"><div class="eyebrow">{'技术路径' if zh else 'Approach'}</div><p>{esc(d['approach'][key])}</p></article><article class="card"><div class="eyebrow">{'结果' if zh else 'Results'}</div><p>{esc(d['result'][key])}</p></article></div></section><section><div class="wrap"><article class="card feature-note"><div class="eyebrow">{'方案与实验' if zh else 'Method and results'}</div><p>{esc(detail_figure)}</p></article>{figures}</div></section><section><div class="wrap"><div class="section-head"><div><div class="section-kicker">Related publications</div><h2>{'关联论文' if zh else 'Related papers'}</h2></div></div><div class="paper-list">{related}</div></div></section><section><div class="wrap"><div class="section-head"><div><div class="section-kicker">Related coverage</div><h2>{'相关报道' if zh else 'Related coverage'}</h2></div></div><div class="media-list">{related_media}</div><div class="hero-actions">{links}</div></div></section>'''


def publications(lang: str) -> str:
    zh = lang == 'zh'
    return f'''<section class="page-hero"><div class="wrap"><div class="eyebrow">03 / Publications</div><h1>{'论文' if zh else 'Publications'}</h1><div class="hero-actions"><a class="btn" href="https://orcid.org/0009-0008-0471-9131" target="_blank" rel="noopener">{'ORCID ↗'}</a></div></div></section><section><div class="wrap">{paper_year_groups(lang)}</div></section>'''


def impact(lang: str) -> str:
    zh = lang == 'zh'
    key = 'zh' if zh else 'en'
    honors = [('北京市科学技术进步二等奖','Beijing Science and Technology Progress Award'),('中国人工智能学会科技成果鉴定','CAAI technology achievement appraisal'),('SafetyAI Bench 连续两次第一','Two-time SafetyAI Bench first place'),('SuperCLUE-RAG 2024.11 第一','SuperCLUE-RAG first place in 2024.11'),('360 智盾入选未来产业优秀典型案例','360 Zh Dun named a future-industry case'),('TinyR1 开源发布','TinyR1 open-source release')]
    honor_descriptions = {
        '北京市科学技术进步二等奖': '作为项目第二完成人参与“大模型安全关键技术及应用”项目，项目获得 2025 年北京市科学技术进步二等奖。',
        '中国人工智能学会科技成果鉴定': '相关大模型安全技术通过中国人工智能学会科技成果鉴定。',
        'SafetyAI Bench 连续两次第一': '360 大模型安全团队在中国信通院 SafetyAI Bench 测评中连续两个季度取得第一名。',
        'SuperCLUE-RAG 2024.11 第一': '360 智脑 RAG 团队技术方案在 2024 年 11 月 SuperCLUE-RAG 榜单中取得第一名。',
        '360 智盾入选未来产业优秀典型案例': '360 智盾作为公司大模型安全产品入选工信部未来产业优秀典型案例。',
        'TinyR1 开源发布': '参与 TinyR1 系列模型的训练与发布。',
    }
    honor_descriptions_en = {
        '北京市科学技术进步二等奖': 'Contributed as the second project member to the LLM safety project recognized with the 2025 Beijing Science and Technology Progress Award.',
        '中国人工智能学会科技成果鉴定': 'The related LLM safety technology passed a CAAI technology achievement appraisal.',
        'SafetyAI Bench 连续两次第一': 'The 360 LLM safety team ranked first in two consecutive quarterly SafetyAI Bench evaluations.',
        'SuperCLUE-RAG 2024.11 第一': 'The 360 RAG team solution ranked first on the November 2024 SuperCLUE-RAG leaderboard.',
        '360 智盾入选未来产业优秀典型案例': '360 Zh Dun was named a Ministry of Industry and Information Technology future-industry case.',
        'TinyR1 开源发布': 'Contributed to training and releasing the TinyR1 model series.',
    }
    honor_html = ''.join(f'<article class="card"><h3>{esc(item[0] if zh else item[1])}</h3><p>{esc(honor_descriptions[item[0]] if zh else honor_descriptions_en[item[0]])}</p></article>' for item in honors)
    standards = site_content['standards']
    standard_html = ''.join(f'<div class="media-item"><div><strong>{esc(item["kind"][key])}</strong><div class="paper-meta">{esc(item["title"][key])}</div></div></div>' for item in standards)
    patent_html = ''.join(f'<div class="media-item"><div><strong>{esc(item["title"])}</strong></div></div>' for item in site_content['patents'])
    context_html = media_rows(lang, items=context_media)
    return f'''<section class="page-hero"><div class="wrap"><div class="eyebrow">04 / Impact & talks</div><h1>{'影响与交流' if zh else 'Impact & talks'}</h1></div></section><section><div class="wrap"><div class="section-head"><div><div class="section-kicker">Impact</div><h2>{'荣誉与产业影响' if zh else 'Recognition & impact'}</h2></div></div><div class="grid-3">{honor_html}</div></div></section><section><div class="wrap"><div class="section-head"><div><div class="section-kicker">Patents</div><h2>{'代表性专利' if zh else 'Representative patents'}</h2></div></div><div class="media-list">{patent_html}</div></div></section><section><div class="wrap grid-2"><div><div class="section-kicker">Standards & reports</div><h2>{'标准与技术报告' if zh else 'Standards & reports'}</h2></div><div class="media-list">{standard_html}</div></div></section><section id="talks"><div class="wrap"><div class="section-head"><div><div class="section-kicker">Talks</div><h2>{'公开演讲与技术分享' if zh else 'Public talks'}</h2></div></div><div class="media-list">{talk_rows(lang)}</div></div></section><section><div class="wrap"><div class="section-head"><div><div class="section-kicker">Media & technical articles</div><h2>{'媒体报道与技术文章' if zh else 'Media & technical articles'}</h2></div></div><div class="media-list">{context_html}</div></div></section>'''


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')


def main() -> None:
    # Remove generated pages only; source assets and documentation remain untouched.
    for path in [ROOT / 'index.html', ROOT / 'en', ROOT / 'about', ROOT / 'research', ROOT / 'publications', ROOT / 'impact', ROOT / 'projects']:
        if path.is_file(): path.unlink()
        elif path.is_dir(): shutil.rmtree(path)
    pages = {
        'zh': {'': ('首页', '孙林的研究、工程、管理与公开成果。', home), 'about': ('关于我', '孙林的个人简介、经历与团队建设。', about), 'research': ('研究与项目', '孙林的研究方向与代表性项目。', research), 'publications': ('论文', '孙林的论文与研究成果。', publications), 'impact': ('影响与交流', '孙林的荣誉、标准、媒体与公开活动。', impact)},
        'en': {'': ('Home', 'Lin Sun — research, engineering, leadership, and public work.', home), 'about': ('About', 'Lin Sun — profile, experience, and team building.', about), 'research': ('Research & Projects', 'Lin Sun — research areas and selected projects.', research), 'publications': ('Publications', 'Lin Sun — publications and research.', publications), 'impact': ('Impact & Talks', 'Lin Sun — recognition, standards, media, and talks.', impact)},
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
