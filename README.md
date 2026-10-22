```
   (\ (\
   ( -.-)o
   o_(")(")
```

### Hi, I'm Sanhe 👋

**Forward-deployed AI Architect · Builder who sells, seller who builds · Claude Code power user**

> *I build the tool before Anthropic ships the official feature.*

15+ years designing data and AI platforms, formerly a Senior Data Architect at AWS Data Lab. I spend my spare time building developer tools and shipping them as open source: Python libraries, MCP servers, and Claude Code plugins.

[![PyPI downloads](https://img.shields.io/badge/PyPI-10M%2B%20downloads%2Fmonth-3775A9?logo=pypi&logoColor=white)](https://pypi.org/user/machugwu/)
[![PyPI packages](https://img.shields.io/badge/PyPI%20packages-200%2B-3775A9?logo=python&logoColor=white)](https://pypi.org/user/machugwu/)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-50B%2B%20tokens%20in%202026-D97757?logo=claude&logoColor=white)](#-claude-code)
[![ex-AWS](https://img.shields.io/badge/ex--AWS-Senior%20Data%20Architect-FF9900?logo=amazonwebservices&logoColor=white)](https://github.com/aws-samples/s3pathlib-project)
[![GitHub followers](https://img.shields.io/github/followers/MacHu-GWU?label=Followers&logo=github)](https://github.com/MacHu-GWU?tab=followers)

| [📦 200+](https://pypi.org/user/machugwu/) | [📈 10M+](https://pypistats.org/) | [✍️ 4K+](https://github.com/MacHu-GWU) | [🤖 50B+](https://github.com/MacHu-GWU#-claude-code) |
|:---:|:---:|:---:|:---:|
| PyPI packages ↗ | monthly downloads ↗ | commits per year ↗ | Claude tokens in 2026 ↗ |

---

### ⚡ What makes me different

- 🤝 **Forward-deployed and customer-obsessed.** I sit with the customer, find the problem behind the problem, sell the solution, and stay until it runs in production. Dozens of enterprise engagements across 15+ industries: finance, healthcare, insurance, energy, life sciences, and federal.
- 💰 **Customers first, product second.** Most engineers build a product, then go looking for users. I do it the other way around: find the need, win the user over, convert them into a paying customer, and only then build. Building is the fast part for me.
- 🧭 **Founder mindset.** I own outcomes, not tickets. Product, go-to-market, operations, even legal and finance: I've sat in every seat, so I think about the whole business, not just the code.
- 🛠️ **If it doesn't exist, I build it.** I've worked this way since long before AI. When the tool I want isn't out there, I make it, which is why the [tools below](#-shipped-before-the-official-feature) shipped before Anthropic, AWS, Cursor, and the vendors shipped theirs.

---

### 🐍 Popular Python libraries

[boto_session_manager](https://github.com/aws-samples/boto-session-manager-project) and [s3pathlib](https://github.com/aws-samples/s3pathlib-project) started as my official AWS sample SDKs and are used by thousands of engineers.

<!-- BEGIN pypi-downloads -->
- [uszipcode](https://github.com/MacHu-GWU/uszipcode-project): [![](https://img.shields.io/badge/downloads-1.2M%2Fmonth-blue)](https://pypistats.org/packages/uszipcode)
- [pathlib_mate](https://github.com/MacHu-GWU/pathlib_mate-project): [![](https://img.shields.io/badge/downloads-1.8M%2Fmonth-blue)](https://pypistats.org/packages/pathlib-mate)
- [sqlalchemy_mate](https://github.com/MacHu-GWU/sqlalchemy_mate-project): [![](https://img.shields.io/badge/downloads-1.1M%2Fmonth-blue)](https://pypistats.org/packages/sqlalchemy-mate)
- [s3pathlib](https://github.com/MacHu-GWU/s3pathlib-project): [![](https://img.shields.io/badge/downloads-682k%2Fmonth-blue)](https://pypistats.org/packages/s3pathlib)
- [boto_session_manager](https://github.com/MacHu-GWU/boto_session_manager-project): [![](https://img.shields.io/badge/downloads-667k%2Fmonth-blue)](https://pypistats.org/packages/boto-session-manager)
- [iterproxy](https://github.com/MacHu-GWU/iterproxy-project): [![](https://img.shields.io/badge/downloads-656k%2Fmonth-blue)](https://pypistats.org/packages/iterproxy)
- [func_args](https://github.com/MacHu-GWU/func_args-project): [![](https://img.shields.io/badge/downloads-671k%2Fmonth-blue)](https://pypistats.org/packages/func-args)
<!-- END pypi-downloads -->

[See all 200+ packages on PyPI →](https://pypi.org/user/machugwu/)

---

### 🤖 Claude Code

I run Claude Code all day and maintain ~160 custom agents and a set of plugins that keep my workflow grounded and consistent.

![Claude Code usage](./claude-code-usage.svg)

#### My Claude Code plugin marketplace

```
/plugin marketplace add MacHu-GWU/sanhe_claude_code_plugin_marketplace-project
```

**Always-current docs lookup**: answer from the official docs instead of training-cutoff memory.

| Plugin | What it does |
|---|---|
| [coding-agent-docs](https://github.com/MacHu-GWU/shsk_coding_agent_docs-project) | Distills official AI coding agent documentation into Agent Skills for on-demand discovery and learning. |
| [ai-harness-docs](https://github.com/MacHu-GWU/shsk_ai_harness_docs-project) | Grounded documentation lookup for AI agent harness frameworks (Strands Agents, deepagents) via locally cached, description-enriched indexes. |
| [databricks](https://github.com/MacHu-GWU/shsk_databricks-project) | Databricks skills; `databricks-docs` answers Databricks questions from the official docs. |

**Personal workflow and style**: one consistent voice across everything I write and draw.

| Plugin | What it does |
|---|---|
| [dot-claude](https://github.com/MacHu-GWU/shsk_dot_claude-project) | Meta-skills for authoring and maintaining Claude Code skills, subagents, and plugins. |
| [doc-writing-styles](https://github.com/MacHu-GWU/shsk_doc_writing_styles-project) | My documentation writing style conventions. |
| [mermaid-styles](https://github.com/MacHu-GWU/shsk_mermaid_styles-project) | My Mermaid visual grammar: canonical diagram patterns with locked-in shapes, directions, and arrow semantics. |

---

### 🚀 Shipped before the official feature

- **[troposphere_mate](https://github.com/MacHu-GWU/troposphere_mate-project) → [cottonformation](https://cottonformation.readthedocs.io/en/latest/)** (2019): Pythonic infrastructure as code for AWS, with type hints, auto-validation, and real objects instead of hand-written CloudFormation templates. *Released before AWS CDK went GA, and the project that won over my AWS Bar Raiser and got me hired.*
- **[DocPack](https://docpack.readthedocs.io/en/latest/)** (Jan 2023): zero-dependency codebase-to-context tool that packs a whole repo into structurally annotated files any LLM can read, no RAG required. *5 months before Cursor launched.*
- **[Claude Prompt Launcher](https://sanhehu.atlassian.net/wiki/external/ZmNhY2NiMDE4ODcyNGQxYWE1ZjE1Y2U1MDU3MzBhMmY)** (Aug 2024): fuzzy search across 200+ Claude Projects, launching prompts from anywhere on the desktop. *6 months before Claude Code's native slash commands.*
- **[shai_tix](https://shai-tix.readthedocs.io/en/latest/)** (Jul 2025): JIRA-like task management for AI agents. CLI first, filesystem-backed, 100% local, runs via `uvx`. *4 months before Claude Code's native Tasks.*
- **MCP servers**: [Text-to-SQL across 8+ database engines](https://mcp-ohmy-sql.readthedocs.io/en/latest/), Atlassian (JIRA / Confluence), Google Drive / Gmail. *Shipped ahead of the official vendor releases.*
