# Taxonomy

> **LANGUAGE RULE:** This file is in English for technical clarity. All notes, tags, folders, and MOC content in the vault MUST be written in Russian. Always respond and write in Russian.

> **IMMUTABILITY RULE:** You may ONLY append to this file — add new folders, tags, rules. You may NEVER delete or modify existing entries without explicit user permission. If something seems wrong or outdated, ask the user before changing it.

## Initial structure

Starting domains and example topics. This is a guide, not a restriction. New folders and topics should emerge organically as content grows.

### Technology
- Программирование/ — languages, patterns, development practices
- AI/ — artificial intelligence, machine learning, LLM
- DevOps/ — infrastructure, deployment, monitoring
- Безопасность/ — information security, cryptography

### Business & Finance
- Бизнес/ — strategy, management, product
- Финансы/ — investing, economics, crypto
- Маркетинг/ — growth, analytics, channels

### Science & Health
- Наука/ — mathematics, physics, biology
- Здоровье/ — sports, nutrition, mental health

### Other
- Продуктивность/ — systems, habits, thinking tools
- Дизайн/ — UI/UX, visual design, typography

## Organization principles

### Folder creation
- Use existing folders when content fits
- Freely create new subfolders when a topic is independent enough (3+ notes or expected growth)
- Freely create new top-level domains when content doesn't fit existing ones
- Maximum 3 levels of nesting: Domain/Topic/Subtopic
- Folder names in Russian, capitalized
- Don't hesitate to reorganize: if a subtopic has outgrown its parent, promote it
- When creating a new folder, append it to the "Initial structure" section above

### Tags
- Tags in Russian, lowercase
- Hierarchical tags via `/`: `программирование/python`, `ai/llm`, `финансы/крипто`
- This is a starter set, not a closed list — freely create new tags when none of the existing ones fit
- Before creating a new tag, check (via kb_find_related_notes or kb_list_mocs) that a similar one doesn't already exist — avoid duplicates like `ml` and `машинное-обучение`
- Tags must not duplicate each other. If a tag for the concept already exists, use it
- When you create a new tag, append it to the "Content types" table at the bottom of this file so it's tracked
- Tag count per note is unlimited, but every tag must carry meaning — don't add tags for the sake of quantity

### Notes
- Note title = the essence of the concept, not "Article about X"
- One note = one idea/concept (Zettelkasten principle)
- If an article contains 5 different ideas, that's 5 notes, not one
- A note must be self-sufficient — the reader should understand the core idea without opening the source
- Start every note with 1-2 sentences explaining the concept (lead paragraph)
- If a concept has practical application, provide a concrete example

### Content enrichment
- When creating a note, enrich the material with your own knowledge: context, examples, connections to other concepts, practical applications
- You can and should weave your knowledge directly into the note text — clarifications, refinements, examples, analogies
- The foundation of the note is ideas and facts from the source. Extend and expand them, but don't replace them with your own retelling
- NOT allowed: discard the original thesis and write "in my opinion" instead
- Allowed: add a paragraph with context, insert an example, explain a term, develop the author's thought
- For substantial additions (not a couple of words, but a whole paragraph), use a callout:
  ```
  > [!note] Дополнение
  > Clarifications, examples, context not present in the original
  ```
- Don't hesitate to explain complex terms, provide analogies, add "why this matters"
- If the note mentions a tool or concept, briefly explain what it is if not obvious from context
- If you know the backstory or evolution of an idea, add a "Контекст" or "История" section

### Critical assessment
- If the material contains controversial, outdated, or false claims, you must flag them
- Use a callout block with credibility assessment:
  ```
  > [!warning] Спорное утверждение
  > The author claims X, however: [explanation of why it's inaccurate/outdated/false].
  > Current understanding: [correct information with reasoning].
  ```
- For fully debunked claims:
  ```
  > [!danger] Опровергнуто
  > This claim does not hold. [Explanation].
  ```
- For information that was true at the time of writing but has since become outdated:
  ```
  > [!caution] Устарело
  > This information is relevant for [year/version]. Since then: [what changed].
  ```
- Add the corresponding tag (`спорное`, `устарело`, `опровергнуто`) to notes with such callouts
- Do not delete original claims — add your assessment next to or after the statement

### Note quality and maturity
- New notes being incomplete is normal. A brief note now is better than a perfect note never
- Use tag `черновик` for notes that need further work
- When processing new material on the same topic, extend existing notes rather than creating duplicates
- If two notes describe the same thing, merge them

### MOC (Map of Content)
- MOC file lives at the root of the topic folder: `AI/MOC AI.md`, `Финансы/MOC Финансы.md`
- Create a MOC when a topic has >= 3 notes
- Top-level MOC links to subtopic MOCs
- MOC may contain brief annotations and grouping by subtopics
- MOC is not just a list of links but a navigation map: group notes logically, add explanations

### Links
- Wikilinks `[[]]` are placed in note text when mentioning a related concept
- `## Related` section at the end is for connections not mentioned directly in text
- Cross-domain links are encouraged (e.g., `AI/ML/Градиентный спуск` <-> `Наука/Математика/Оптимизация`)
- Links must be meaningful — don't link everything, only what genuinely helps navigation
- If two concepts are contrasted, link them too (e.g., "Монолит" <-> "Микросервисы")

### Language and style
- Notes, tags, and folders are ALWAYS in Russian, regardless of source language
- Technical terms without an established Russian translation stay as-is: "Docker", "transformer", "fine-tuning"
- Write clearly and concretely, avoid filler and vague phrasing
- Prefer active voice over passive

### Writing depth and substance
- Every note must have real substance — write as much as needed to fully cover the topic, but not a word more
- A note should have a lead paragraph explaining the concept, a body developing the idea with details, and examples or practical applications where relevant
- When describing a concept, explain the WHY, not just the WHAT. "X is a pattern" is useless. "X solves the problem of Y by doing Z, which matters because W" is useful
- Use structure: break content into logical sections with headings. A wall of text is hard to navigate
- Include specifics: numbers, names, versions, dates, code snippets, command examples — whatever makes the note concrete rather than abstract
- If the source provides a list of points, don't just copy them — explain each one. "Advantages: speed, reliability" is worthless. Explain WHY it's fast, HOW it's reliable
- Compare and contrast when relevant: "Unlike X, this approach does Y because Z"
- When a concept has multiple perspectives or schools of thought, present them
- Don't pad notes with filler like "this is an important topic" or "many people think" — go straight to the substance
- Imagine the reader is a smart person encountering this concept for the first time. They need enough depth to actually understand and apply it, not just recognize the term

### Processing workflow

When you receive material (URL, PDF, or text), follow this sequence:

1. **Fetch** — `kb_fetch_url` or `kb_extract_pdf` to get raw content
2. **Read taxonomy** — `kb_get_taxonomy` + `kb_get_vault_structure` to understand current organization
3. **Decompose** — identify distinct ideas in the material (see "Idea boundaries" below). One article often contains 3-10 separate concepts
4. **Find existing** — `kb_find_related_notes` and `kb_search_by_tag` for each idea. If a note on this concept already exists, update it instead of creating a duplicate
5. **Create notes** — `kb_save_notes_batch` for new ideas, with proper tags, links, and source attribution
6. **Update MOCs** — `kb_update_moc` for every topic that received new notes
7. **Cross-link** — ensure new notes link to related existing ones, and vice versa via `obsidian_patch_content`

Do NOT skip steps 2-4. Understanding what already exists prevents duplicates and orphans.

### Idea boundaries

How to decide what is a separate note vs part of the same note:

- **Separate note** if the idea can be understood and referenced independently. "Что такое attention mechanism" and "Почему трансформеры заменили RNN" are two notes, not one
- **Same note** if one concept makes no sense without the other. "Как работает Q/K/V в attention" belongs inside the attention note, not separately
- **Rule of thumb**: if you would create a [[wikilink]] to reference this idea from another note, it deserves its own note
- When in doubt, split. It's easier to merge two small notes than to untangle one big one
- A list of items (e.g. "5 principles of X") is ONE note, not 5 — unless each item is a deep concept in its own right
- A comparison ("X vs Y") is one note. Don't split into separate notes for X and Y unless each is independently noteworthy

### Update vs create policy

When new material covers a topic that already has a note:

- **Update existing** when the new info adds depth, examples, or corrections to the same core concept. Use `kb_get_note_sections` + `obsidian_patch_content` to add to a specific section
- **Create new** when the new material presents a genuinely different angle, application, or context. Link to the existing note
- **Merge** (`kb_merge_notes`) when you discover two notes covering the same concept — check with `kb_find_related_notes` before creating
- Never silently overwrite. If updating, preserve the original content and add new material as extensions
- When updating, add the new source to the frontmatter `source` field or add a "Источники" section

### Multiple sources on the same topic

- If sources agree, synthesize into one coherent note. List all sources in a "Источники" section at the bottom
- If sources disagree, present both perspectives with attribution: "По мнению A... В то же время B утверждает..."
- If one source is clearly more authoritative or recent, note this: "Более свежие данные (2025) показывают..."
- Do NOT average conflicting positions into a bland middle. State each clearly and note the tension
- Use `> [!warning] Спорное утверждение` callout when sources directly contradict each other

### Vault maintenance

Periodically (or when the user asks), run maintenance:

- **Orphan check** — `kb_get_orphans` to find unlinked notes. Either link them into the knowledge graph or mark with `черновик` tag
- **Duplicate check** — `kb_find_related_notes` with key terms from new notes. If a near-duplicate exists, merge with `kb_merge_notes`
- **MOC completeness** — `kb_list_mocs` and check that every folder with 3+ notes has a MOC
- **Structure review** — `kb_get_vault_structure` to spot folders with too many notes (>20) that need subfolder splitting, or folders with 1-2 notes that could be merged upward
- **Tag consistency** — when creating notes, always check the Content types table below and existing tags via `kb_search_by_tag` before inventing new ones

### Binary files
- Stored in `_attachments/` inside the topic folder
- Every binary file has a wrapper note alongside it

## Content types

Starter tag set for classification. Create new types when none fit — and append them to this table.

| Tag | Description | Example |
|-----|------------|---------|
| `концепция` | Fundamental idea or principle | "Инверсия зависимостей", "Компаундный процент" |
| `инструмент` | Specific software, library, service | "PyTorch", "Terraform", "Prometheus" |
| `туториал` | Step-by-step guide | "Настройка CI/CD в GitHub Actions" |
| `обзор` | Comparison, analysis of multiple options | "Сравнение ORM в Python" |
| `исследование` | Scientific paper, experiment | "Attention Is All You Need" |
| `персона` | Person and their contribution | "Андрей Карпатый" |
| `кейс` | Real-world experience, story | "Как Discord масштабировал Elixir" |
| `паттерн` | Repeatable approach to solving a problem | "Circuit Breaker", "Event Sourcing" |
| `антипаттерн` | Common mistake to avoid | "Premature Optimization", "God Object" |
| `метрика` | Way of measuring something | "DORA metrics", "P/E ratio" |
| `фреймворк` | Mental model or decision framework | "First Principles Thinking", "Jobs To Be Done" |
| `термин` | Definition of a concept | "Latency vs Throughput", "CAP-теорема" |
| `спорное` | Contains claims requiring critical assessment | Notes with `[!warning]` or `[!danger]` callouts |
| `устарело` | Information was valid before but is now outdated | Notes with `[!caution]` callouts |
| `опровергнуто` | Contains fully false claims | Notes with `[!danger]` callouts |
| `черновик` | Note is incomplete, needs further work | Any note in progress |
