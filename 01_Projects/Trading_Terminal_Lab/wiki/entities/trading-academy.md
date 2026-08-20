---
title: Trading Academy
author: Hermes Agent
created: 2026-08-20
updated: 2026-08-20
type: entity
tags: [trading-engine, ai-agent, automation, testing, risk-management]
sources: []
confidence: high
---

# Trading Academy

`Trading Academy`-ն `trading-terminal-mcp` նախագծի մշտական, 24/7 աշխատող,
միայն paper/replay ռեժիմով AI ուսուցման համակարգն է։ Այն ունի ութ AI դասախոսական
դեր և prerequisite-ներով տասը ուսումնական մոդուլ։ Դասախոսները իրական մարդկանց
ներկայացումներ չեն. live trading-ի ցանկացած որոշման համար պարտադիր է որակավորված
մարդու անկախ հաստատումը։

## Դասախոսական կազմ

- AI Quantitative Mathematics Professor
- AI Market Microstructure Professor
- AI Systematic Strategy Professor
- AI Derivatives Mathematics Professor
- AI Risk Management Professor
- AI Execution Practicum Coach
- AI Research Methods Professor
- AI Behavioral Finance & Governance Professor

## Ուսուցման ոլորտներ

Համակարգը ծածկում է հավանականություն և վիճակագրություն, շուկայի միկրոկառուցվածք,
technical ու fundamental/macro վերլուծություն, derivatives, risk management,
execution, backtesting/research integrity, behavioral finance և governance։
Յուրաքանչյուր փուլ ունի paper exercise, deterministic assessment, անցողիկ շեմ և
remediation։

## Ճարտարապետություն

SQLite-ը պահում է trainees-ի վիճակը, գնահատականները, փորձերի քանակը և append-only
audit events-ը։ MCP և REST interface-ները տալիս են curriculum, enrollment,
learning-cycle, assessment և progress գործիքներ։ Live/canary execution request-ը
մերժվում և audit է արվում։

Hermes Cron-ի `Trading Academy 24/7 Paper Cycle` job-ը երկու ժամը մեկ գործարկում է
երեք bounded trainee cycle՝ առանց շարունակական LLM ծախսի։ Gateway-ը supervised է
macOS launchd-ի միջոցով։

Ավելացվել են նաև երեք persistent Hermes Bot profile՝ `academyquant`,
`academystrategy`, `academyrisk`։ Յուրաքանչյուրն ունի Nous Portal model pin,
role-specific SOUL, launchd gateway, վեցժամյա continuity routine և least-privilege
MCP allowlist։ `place_order` ու `cancel_order` գործիքները trainee profile-ների համար
անջատված են։ Առաջին grounded replay assessment-ից հետո երեք trainees-ն էլ ստացել
են 100 միավոր և անցել `microstructure` մոդուլ, սակայն `live_eligible`-ը մնում է
false։

## Կապեր

- [[trading-engine]]
- [[mcp-server]]
- [[hermes-agent]]
- [[order-management]]
- [[portfolio-tracking]]
