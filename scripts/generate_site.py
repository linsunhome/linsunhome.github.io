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
media = json.loads((DATA / "media-links-2026-11-10.json").read_text())['items']
published_media = [item for item in media if item.get('publish')]


def esc(value: object) -> str:
    return html.escape(str(value or ""), quote=True)


def nav(lang: str, active: str) -> str:
    labels = {
        'zh': [('about', '关于', '/about/'), ('research', '研究与项目', '/research/'), ('publications', '论文', '/publications/'), ('impact', '影响与交流', '/impact/')],
        'en': [('about', 'About', '/en/about/'), ('research', 'Research & Projects', '/en/research/'), ('publications', 'Publications', '/en/publications/'), ('impact', 'Impact & Talks', '/en/impact/')],
    }
    links = ''.join(f'<a href="{href}"' + (' aria-current="page"' if key == active else '') + f'>{label}</a>' for key, label, href in labels[lang])
    switch = '/en/' if lang == 'zh' else '/'
    switch_label = 'EN' if lang == 'zh' else '中文'
    return f'''<header class="site-header"><div class="wrap nav">
      <a class="brand" href="{'/' if lang == 'zh' else '/en/'}"><strong>孙林</strong><span>LIN SUN / AI BUILDER</span></a>
      <button class="menu-toggle" data-menu-toggle aria-expanded="false" aria-label="Menu">☰</button>
      <nav class="nav-links" data-nav>{links}</nav>
      <div class="nav-tools"><a class="lang" href="{switch}">{switch_label}</a></div>
    </div></header>'''


def footer(lang: str) -> str:
    text = '研究 · 工程 · 管理 · 公开交流' if lang == 'zh' else 'RESEARCH · ENGINEERING · LEADERSHIP · OPEN KNOWLEDGE'
    return f'''<footer><div class="wrap footer-grid"><div><strong>孙林 · Lin Sun</strong><p>{text}</p></div><div class="footer-links"><a href="mailto:lincharliesun@gmail.com">lincharliesun@gmail.com</a><a href="https://scholar.google.com/citations?user=b8yMN1MAAAAJ" target="_blank" rel="noopener">Google Scholar</a></div></div></footer>'''


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
        result.append(f'''<article class="paper-row" data-paper-row data-year="{esc(year)}"><div class="paper-year">{esc(year)}</div><div><div class="paper-title">{title}</div><div class="paper-meta">{authors}<br>{venue_text}</div></div><a class="paper-link" href="https://scholar.google.com/scholar?q={html.escape(paper['title'].replace(' ', '+'))}" target="_blank" rel="noopener">Scholar ↗</a></article>''')
    return '\n'.join(result)


def media_rows(lang: str, limit: int | None = None) -> str:
    rows = published_media if limit is None else published_media[:limit]
    result = []
    for item in rows:
        title = esc(item.get('title', ''))
        source = esc(item.get('source', ''))
        date = esc(item.get('date', item.get('year', '')))
        relation = esc(item.get('relation', ''))
        url = item.get('url')
        title_html = f'<a href="{esc(url)}" target="_blank" rel="noopener">{title} ↗</a>' if url else f'<strong>{title}</strong>'
        result.append(f'<article class="media-item"><div>{title_html}<div class="paper-meta">{relation}</div></div><small>{source} · {date}</small></article>')
    return '\n'.join(result)


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
    project_titles = [('大模型安全防护与可信生成', 'Safety & trustworthy generation', 'From attack generation and evaluation to online protection and experience feedback.'), ('RAG 与可信知识服务', 'RAG & knowledge services', 'Retrieval, evidence, and grounded generation for complex information workflows.'), ('TinyR1 开源大模型', 'Open reasoning models', 'Training and releasing compact reasoning models with branch-merge distillation.')]
    project_cards2 = ''.join(f'<article class="card project-card"><div><div class="project-meta">{esc(meta)}</div><h3 style="margin-top:12px">{esc(title)}</h3><p>{esc(desc)}</p></div><div class="result">{("技术路线、模型训练和系统落地" if zh else "Technical direction, model training, and system delivery")}</div></article>' for title, meta, desc in project_titles)
    timeline = [('2010—2012', '腾讯网媒产品技术部', '汽车业务开发与推荐系统。' if zh else 'Automotive product engineering and recommendation systems.'), ('2012—2017', '360 搜索与智能语义', '问答、语义、人机对话与大数据智能。' if zh else 'Search, question answering, semantics, dialogue, and data intelligence.'), ('2017—2023', '贝壳 / 如视', '企业搜索云、数据智能、AI+VR 与 100+ 人跨职能团队。' if zh else 'Enterprise search, data intelligence, AI+VR, and a 100+ person cross-functional team.'), ('2023—至今', '360 基础大模型', '基础模型、安全、RAG、记忆、经验系统与高效推理。' if zh else 'Foundation models, safety, RAG, memory, experience systems, and efficient reasoning.')]
    timeline_html = ''.join(f'<article class="timeline-item"><div class="timeline-time">{esc(year)}</div><div class="timeline-dot"></div><div class="timeline-card"><h3>{esc(role)}</h3><p>{esc(desc)}</p></div></article>' for year, role, desc in timeline)
    return f'''<section class="hero"><div class="wrap hero-grid"><div><div class="eyebrow">{copy['eyebrow']}</div><h1>{copy['title']}</h1><p class="hero-copy">{copy['intro']}</p><div class="hero-actions"><a class="btn primary" href="/{'en/' if not zh else ''}about/">{copy['about']} ↗</a><a class="btn" href="/{'en/' if not zh else ''}publications/">{copy['papers']} ↗</a></div></div><aside class="hero-card"><div class="monogram">LS</div><p>{'研究、工程、管理与产业实践的公开记录。' if zh else 'An open record of research, engineering, leadership, and industry practice.'}</p></aside></div><div class="wrap metric-grid"><div class="metric"><strong>16</strong><span>{'年技术研发与管理' if zh else 'years in research & engineering'}</span></div><div class="metric"><strong>30</strong><span>{'条 Scholar 论文记录' if zh else 'records in the Scholar snapshot'}</span></div><div class="metric"><strong>4</strong><span>{'个职业阶段' if zh else 'career stages'}</span></div><div class="metric"><strong>14</strong><span>{'条已核对公开记录' if zh else 'reviewed public records'}</span></div></div></section>
<section><div class="wrap"><div class="section-head"><div><div class="section-kicker">01 / Research</div><h2>{copy['section_research']}</h2></div><p>{copy['section_research_desc']}</p></div><div class="grid-3">{project_cards}</div></div></section>
<section><div class="wrap"><div class="section-head"><div><div class="section-kicker">02 / Selected work</div><h2>{copy['section_projects']}</h2></div><p>{copy['section_projects_desc']}</p></div><div class="grid-3">{project_cards2}</div><div class="hero-actions"><a class="btn" href="/{'en/' if not zh else ''}research/">{'查看研究与项目详情' if zh else 'Explore research and projects'} ↗</a></div></div></section>
<section><div class="wrap"><div class="section-head"><div><div class="section-kicker">03 / Publications</div><h2>{copy['section_papers']}</h2></div><p>{copy['section_papers_desc']}</p></div><div class="paper-list">{paper_rows(lang, 6)}</div><div class="hero-actions"><a class="btn" href="/{'en/' if not zh else ''}publications/">{'查看完整论文库' if zh else 'View all publications'} ↗</a></div></div></section>
<section><div class="wrap"><div class="section-head"><div><div class="section-kicker">04 / Timeline</div><h2>{copy['section_timeline']}</h2></div><p>{copy['section_timeline_desc']}</p></div><div class="timeline">{timeline_html}</div><div class="hero-actions"><a class="btn" href="/{'en/' if not zh else ''}about/">{'查看完整经历' if zh else 'Read the full profile'} ↗</a></div></div></section>
<section><div class="wrap"><div class="section-head"><div><div class="section-kicker">05 / Media & talks</div><h2>{copy['section_media']}</h2></div><p>{copy['section_media_desc']}</p></div><div class="media-list">{media_rows(lang, 4)}</div><div class="hero-actions"><a class="btn" href="/{'en/' if not zh else ''}impact/">{'查看影响与交流' if zh else 'Explore impact and talks'} ↗</a></div></div></section>
<section><div class="wrap"><div class="callout"><div class="eyebrow">{'OPEN CONTACT' if not zh else 'OPEN CONTACT'}</div><h2 style="margin-top:12px">{'保持交流，分享公开成果。' if zh else 'Open to thoughtful conversations.'}</h2><p>{'如果你希望交流基础模型、安全、RAG、记忆、Agent 或团队建设，可以通过邮箱联系我。' if zh else 'For conversations around foundation models, safety, RAG, memory, agents, or team building, reach me by email.'}</p><a class="btn" href="mailto:lincharliesun@gmail.com">lincharliesun@gmail.com ↗</a></div></div></section>'''


def about(lang: str) -> str:
    zh = lang == 'zh'
    return f'''<section class="page-hero"><div class="wrap"><div class="eyebrow">01 / About</div><h1>{'关于我' if zh else 'About me'}</h1><p>{'研究、工程、团队与长期交付，构成我理解技术工作的四个角度。' if zh else 'Research, engineering, teams, and long-term delivery are four lenses through which I understand technical work.'}</p></div></section><section><div class="wrap grid-2"><div class="prose"><h2>{'个人简介' if zh else 'Profile'}</h2><p>{'我是孙林，现任 360 算法高级研究员、基础大模型团队负责人。我的工作覆盖基础模型、后训练、大模型安全、RAG、记忆与 Agent 系统，关注研究方法如何变成可复用、可交付的系统能力。' if zh else 'I am Lin Sun, a senior algorithm researcher and foundation-model team lead at 360. My work spans foundation models, post-training, LLM safety, RAG, memory, and agent systems, with a focus on turning research methods into reusable and deliverable systems.'}</p><p>{'除技术路线外，我也关注团队建设、跨职能协作和组织交付，让模型能力能够在真实业务中持续运行。' if zh else 'Alongside technical direction, I care about team building, cross-functional collaboration, and organizational delivery so that model capabilities can operate sustainably in real products.'}</p></div><div class="card"><div class="eyebrow">CONTACT</div><h3 style="margin-top:14px">lincharliesun@gmail.com</h3><p>{'公开邮箱，用于研究、工程和产业交流。' if zh else 'A public inbox for research, engineering, and industry conversations.'}</p><a class="btn" href="mailto:lincharliesun@gmail.com">{'发送邮件' if zh else 'Send an email'} ↗</a></div></div></section><section><div class="wrap"><div class="section-head"><div><div class="section-kicker">02 / Career</div><h2>{'经历与组织交付' if zh else 'Experience & delivery'}</h2></div><p>{'时间线同时记录技术方向、职责变化和团队建设。' if zh else 'One timeline for technical direction, responsibility, and team building.'}</p></div><div class="timeline">{''.join(f'<article class="timeline-item"><div class="timeline-time">{esc(y)}</div><div class="timeline-dot"></div><div class="timeline-card"><h3>{esc(r)}</h3><p>{esc(d)}</p></div></article>' for y, r, d in ([('2010.07—2012.08','腾讯网媒产品技术部','汽车业务开发与推荐系统。' if zh else 'Automotive product engineering and recommendation systems.'),('2012.08—2017.08','360 搜索问答与智能语义','问答、语义、人机对话和大数据智能。' if zh else 'Search, question answering, semantics, dialogue, and data intelligence.'),('2017.08—2023.07','贝壳 / 如视','企业搜索云、数据智能、AI+VR 与 100+ 人跨职能团队。' if zh else 'Enterprise search, data intelligence, AI+VR, and a 100+ person cross-functional team.'),('2023.07—至今','360 基础大模型','基础模型、大模型安全、RAG、记忆、经验系统与高效推理。' if zh else 'Foundation models, LLM safety, RAG, memory, experience systems, and efficient reasoning.')]))}</div></div></section><section><div class="wrap grid-2"><article class="card"><div class="eyebrow">EDUCATION</div><h3 style="margin-top:14px">哈尔滨工业大学</h3><p>{'教育背景、实验室经历与行业工作共同构成长期技术积累。' if zh else 'Education, laboratory experience, and industry work form a continuous technical practice.'}</p></article><article class="card"><div class="eyebrow">LEADERSHIP</div><h3 style="margin-top:14px">{'技术路线与团队建设' if zh else 'Technical direction & teams'}</h3><p>{'公开材料中的团队规模、职责和成果按具体来源分别说明，不用单一人数替代管理经历。' if zh else 'Team size, responsibility, and outcomes are described with their evidence; a single headcount never substitutes for the management story.'}</p></article></div></section>'''


def research(lang: str) -> str:
    zh = lang == 'zh'
    areas = [('Foundation Models & Post-Training','预训练数据、长上下文、SFT、强化学习、蒸馏、模型融合与推理能力增强。' if zh else 'Long-context data, SFT, reinforcement learning, distillation, model merging, and reasoning.'),('LLM Safety & Trustworthy Generation','动态攻防、自动评测、安全对齐、在线防护、经验回流与幻觉治理。' if zh else 'Dynamic attacks, evaluation, safety alignment, online protection, experience feedback, and hallucination governance.'),('RAG, Memory & Agent','企业知识、多文档证据分配、视觉文档、长期状态、经验复用与 Agent 评测。' if zh else 'Enterprise knowledge, multi-document evidence, visual documents, long-term state, experience reuse, and agent evaluation.')]
    area_html = ''.join(f'<article class="card"><div class="eyebrow">{esc(a)}</div><h3 style="margin-top:14px">{esc(b.split("。")[0] if zh else a)}</h3><p>{esc(b)}</p></article>' for a,b in areas)
    projects = [('大模型安全防护与可信生成','TriPlay-RL · Magic Token · online protection','覆盖攻击生成、自动评测、安全训练、在线防护、动态运营和经验回流。' if zh else 'A chain from attack generation and evaluation to safety training, online protection, operations, and experience feedback.'),('RAG 与可信知识服务','BEAR · InduOCRBench · TextlessRAG','围绕检索增强、证据分配、OCR 鲁棒性和可信生成建立评测与系统能力。' if zh else 'Evaluation and systems for retrieval augmentation, evidence allocation, OCR robustness, and grounded generation.'),('TinyR1 与高效推理','Branch-Merge Distillation · Router Upcycling','探索小参数量推理模型、蒸馏、路由和推理能力增强。' if zh else 'Compact reasoning models, distillation, routing, and efficient reasoning.')]
    phtml = ''.join(f'<article class="card project-card"><div><div class="project-meta">{esc(meta)}</div><h3 style="margin-top:12px">{esc(title)}</h3><p>{esc(desc)}</p></div><div class="result">{("公开证据、个人角色和结果在项目详情中逐条核验。" if zh else "Public evidence, personal role, and results are verified item by item in the project details.")}</div></article>' for title,meta,desc in projects)
    return f'''<section class="page-hero"><div class="wrap"><div class="eyebrow">02 / Research & Projects</div><h1>{'研究与项目' if zh else 'Research & projects'}</h1><p>{'研究方法、系统工程与组织交付在项目中连接起来。' if zh else 'Research methods, systems engineering, and organizational delivery meet in the work.'}</p></div></section><section><div class="wrap"><div class="grid-3">{area_html}</div></div></section><section><div class="wrap"><div class="section-head"><div><div class="section-kicker">Selected projects</div><h2>{'代表项目' if zh else 'Selected projects'}</h2></div><p>{'每个项目都说明问题、个人角色、结果和公开证据。' if zh else 'Each project explains the problem, personal role, result, and public evidence.'}</p></div><div class="grid-3">{phtml}</div></div></section><section><div class="wrap"><div class="card"><div class="eyebrow">TECHNICAL THREAD</div><h2 style="margin-top:14px">{'攻击生成 → 自动评测 → 安全训练 → 在线防护 → 经验回流' if zh else 'Attack generation → evaluation → safety training → online protection → experience feedback'}</h2><p>{'这条链路是研究与工程之间的一个代表性连接；具体项目详情只展示可公开的技术信息。' if zh else 'This is one representative connection between research and engineering; project pages disclose only public technical information.'}</p></div></div></section>'''


def publications(lang: str) -> str:
    zh = lang == 'zh'
    years = sorted({str(p.get('scholarYear')) for p in papers if p.get('scholarYear')}, reverse=True)
    options = '<option value="">' + ('全部年份' if zh else 'All years') + '</option>' + ''.join(f'<option value="{y}">{y}</option>' for y in years)
    return f'''<section class="page-hero"><div class="wrap"><div class="eyebrow">03 / Publications</div><h1>{'论文' if zh else 'Publications'}</h1><p>{'最新 Scholar 快照包含 30 条记录。列表保留原始引用标记，发表状态和作者角色在核验后补齐。' if zh else 'The latest Scholar snapshot contains 30 records. Original citation markers are preserved; publication status and author roles are verified separately.'}</p></div></section><section><div class="wrap"><div class="filters"><input data-paper-search type="search" placeholder="{'搜索标题、作者或主题' if zh else 'Search title, author, or topic'}"><select data-paper-year>{options}</select></div><p class="filter-note">{'数据接收日期：2026-11-10 · 空白引用显示“引用未提供”' if zh else 'Snapshot received: 2026-11-10 · Blank citation fields remain unavailable'}</p><div class="paper-list">{paper_rows(lang)}</div><p class="empty" data-paper-empty hidden>{'没有匹配的论文。' if zh else 'No publications match these filters.'}</p></div></section>'''


def impact(lang: str) -> str:
    zh = lang == 'zh'
    honors = ['北京市科学技术进步二等奖', '中国人工智能学会科技成果鉴定', 'SafetyAI Bench 连续两次第一', 'SuperCLUE-RAG 2024.11 第一', '360 智盾入选未来产业优秀典型案例', 'TinyR1 开源发布'] if zh else ['Beijing Science and Technology Progress Award', 'CAAI technology achievement appraisal', 'Two-time SafetyAI Bench first place', 'SuperCLUE-RAG first place in 2024.11', '360 Zh Dun named a future-industry case', 'TinyR1 open-source release']
    honor_html = ''.join(f'<article class="card"><h3>{esc(item)}</h3><p>{"公开材料中的奖项、评测、产品和团队成果分别标注归属与来源。" if zh else "Awards, evaluations, products, and team outcomes are presented with their attribution and evidence."}</p></article>' for item in honors)
    standards = [('国家标准','GB/T 42131-2022《人工智能 知识图谱技术框架》'),('国家标准项目','20231746-T-469《人工智能 大模型 第 2 部分：评测指标与方法》'),('行业标准','SJ/T 11914-2023《虚拟现实从业人员能力要求》'),('技术白皮书','《大模型安全研究报告（2024 年）》')]
    standard_html = ''.join(f'<div class="media-item"><div><strong>{esc(a)}</strong><div class="paper-meta">{esc(b)}</div></div><small>{"角色待发布前核验" if zh else "Role to be verified before publication"}</small></div>' for a,b in standards)
    return f'''<section class="page-hero"><div class="wrap"><div class="eyebrow">04 / Impact & talks</div><h1>{'影响与交流' if zh else 'Impact & talks'}</h1><p>{'产业实践、专业服务、媒体报道和公开分享共同构成长期影响。' if zh else 'Industry practice, professional service, media, and public talks form a long-term record of impact.'}</p></div></section><section><div class="wrap"><div class="section-head"><div><div class="section-kicker">Impact</div><h2>{'荣誉与产业影响' if zh else 'Recognition & impact'}</h2></div><p>{'团队和公司成果不会自动改写成个人独立成果。' if zh else 'Team and company outcomes are never rewritten as individual achievements by default.'}</p></div><div class="grid-3">{honor_html}</div></div></section><section><div class="wrap grid-2"><div><div class="section-kicker">Patents & standards</div><h2>{'专利与标准' if zh else 'Patents & standards'}</h2><p class="paper-meta">{'代表性专利、标准项目和技术白皮书按公开状态和个人角色分别记录。' if zh else 'Representative patents, standards, and technical reports are recorded by public status and personal role.'}</p></div><div class="media-list">{standard_html}</div></div></section><section><div class="wrap"><div class="section-head"><div><div class="section-kicker">Media & talks</div><h2>{'媒体与公开活动' if zh else 'Media & public talks'}</h2></div><p>{'已核对条目公开展示；验证页、未知标题和私有材料留在候选清单。' if zh else 'Verified items are shown publicly; validation pages, unknown titles, and private materials remain out of the public list.'}</p></div><div class="media-list">{media_rows(lang)}</div></div></section>'''


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')


def main() -> None:
    # Remove generated pages only; source assets and documentation remain untouched.
    for path in [ROOT / 'index.html', ROOT / 'en', ROOT / 'about', ROOT / 'research', ROOT / 'publications', ROOT / 'impact']:
        if path.is_file(): path.unlink()
        elif path.is_dir(): shutil.rmtree(path)
    pages = {
        'zh': {'': ('首页', '孙林的研究、工程、管理与公开成果。', home), 'about': ('关于我', '孙林的个人简介、经历与团队建设。', about), 'research': ('研究与项目', '孙林的研究方向与代表性项目。', research), 'publications': ('论文', '孙林的论文与 Google Scholar 公开记录。', publications), 'impact': ('影响与交流', '孙林的荣誉、标准、媒体与公开活动。', impact)},
        'en': {'': ('Home', 'Lin Sun — research, engineering, leadership, and public work.', home), 'about': ('About', 'Lin Sun — profile, experience, and team building.', about), 'research': ('Research & Projects', 'Lin Sun — research areas and selected projects.', research), 'publications': ('Publications', 'Lin Sun — publications and public Scholar records.', publications), 'impact': ('Impact & Talks', 'Lin Sun — recognition, standards, media, and talks.', impact)},
    }
    for lang, entries in pages.items():
        for route, (title, description, renderer) in entries.items():
            path = ROOT / ('en' if lang == 'en' else '') / route / 'index.html' if route else ROOT / ('en/index.html' if lang == 'en' else 'index.html')
            write(path, page(lang, route or 'home', f'{title} | {"Lin Sun" if lang == "en" else "孙林"}', description, renderer(lang)))
    print(f'Generated {sum(len(v) for v in pages.values())} pages from {len(papers)} papers and {len(published_media)} published media items.')


if __name__ == '__main__':
    main()
