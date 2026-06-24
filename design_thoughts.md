What's so bad about it being an agent?When you turn a component into an Agent, you are giving an LLM the freedom to decide how to use its tools. While that autonomy is amazing for open-ended tasks (like the Search phase), it introduces three major problems in a rigid pipeline like matching:
1. **The "Hallucinated Execution"** Problem An agent can simply forget or decide not to call its tool. If the LLM looks at a job and thinks, "Oh, I already know this is a bad match, I don't need to run the normalize_and_score_logic tool," it skips your code entirely. Suddenly, your backend loses deterministic control over how candidates are filtered.
2.**Infinite Loops** and Latency If an agent encounters an unexpected error or an unusual data format from the jobdatalake payload, it might try to fix it by calling its tool over and over again in a loop.The cost: You pay for tokens on every loop.The UX: The user sits watching a loading spinner for 30 seconds while the agent argues with itself behind the scenes.
3. **Redundant State Management** An agent requires an execution framework (like a LangGraph graph state, an agent memory buffer, or system prompts) just to manage its loop. For a step that is fundamentally linear (Take Jobs -> Score Jobs -> Show Jobs), adding an agent loop adds massive structural bloat to your codebase for no functional gain.


deprecated - 
**don't understand if this is valid architecture. that the llm only decides which tools to run and not actual structuring**
It's a legitimate pattern in general — but only when there's **real ambiguity** for the LLM to resolve. The relevant test: does the "decision" the LLM makes actually vary based on interpreting messy input, or is the control flow fixed regardless of what's in the text?

- **Search agent:** passes the test in theory — "keyword vs. semantic, what query string" genuinely depends on interpreting free text, and a human would make that call differently depending on input. It's just executed badly (the bug you found). Worth fixing the decision logic, not removing the LLM from it.
- **Matching agent:** fails the test — the system prompt always says "call normalize_user_profile once, then score_job_against_profile for each job, sort descending." That sequence never changes based on what's in the text. There's no decision being made; it's a fixed loop dressed up as tool calls. When an "agent" always does the same two steps in the same order regardless of input, it's not reasoning, it's just slower, costlier, non-deterministic plumbing around code that already runs the same way every time.

So the architecture isn't invalid as a pattern — LLM-as-router-over-deterministic-tools is standard and often correct. It's invalid here specifically for the matching stage, because nothing about the routing depends on the LLM's judgment. The tradeoff of "fixing" this by removing the LLM wrapper: you lose the theoretical option of the LLM someday adapting that fixed sequence (e.g., skipping scoring if profile extraction fails) — but right now nothing in the prompt actually exploits that flexibility, so you're paying for optionality that isn't used.


design with second agent:
[ USER INPUT ]
          (Free Text, Form Data, or Resume)
                        │
                        ▼
┌──────────────────────────────────────────────┐
│           Orchestrator (Code Base)           │
│  - Captures input state                      │
│  - Feeds data sequentially to LLM Agents     │
└──────────────────────┬───────────────────────┘
                       │
                       │ (Passes User Input)
                       ▼
        ┌──────────────────────────────┐
        │      Search Agent (LLM)      │
        └──────────────┬───────────────┘
                       │
             [ LLM Decision Loop ]
                       │
         Is input raw text or a file?
         /             │            \
  [ File Upload ]  [ Specific Terms ] [ Conceptual Ideas ]
        │              │                    │
        ▼              ▼                    ▼
┌──────────────┐┌──────────────┐    ┌──────────────┐
│ Tool #1:     ││ Tool #2:     │    │ Tool #3:     │
│ Parse & Prep ││ Search by    │    │ Search by    │
│ Resume       ││ Keyword      │    │ Semantic Text│
└──────┬───────┘└──────┬───────┘    └──────┬───────┘
       │               │                   │
       └───────────────┼───────────────────┘
                       │ (Returns Raw JSON Payload from JobDataLake)
                       ▼
┌──────────────────────────────────────────────┐
│           Orchestrator (Code Base)           │
│  - Receives raw, unranked job listings       │
│  - Moves state forward to the Matcher phase  │
└──────────────────────┬───────────────────────┘
                       │
                       │ (Passes Profile Data + Raw Jobs)
                       ▼
        ┌──────────────────────────────┐
        │     Matcher Agent (LLM)      │
        └──────────────┬───────────────┘
                       │
             [ LLM Execution Loop ]
                       │
                       ▼
        ┌──────────────────────────────┐
        │ Tool #1: Score & Normalize   │
        │ (Deterministic Python Code)  │
        └──────────────┬───────────────┘
                       │
          (Returns Sorted Top 5 Jobs)
                       │
                       ▼
        ┌──────────────────────────────┐
        │ LLM Internal Core Process:   │
        │ Synthesizer & Explainer      │
        └──────────────┬───────────────┘
                       │
                       ▼
            [ FINAL CLEAN FEEDBACK ]
         "Here are your top jobs and 
          exactly why you qualify..."


design after dropping second agent:
Gemini:

[ Resume File or Text Input ]
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                  Orchestrator (Code Base)                   │
│  - Parses PDF/Docx into clean text                          │
│  - Saves parsed profile text to pass down the line          │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               │ (Passes Parsed Resume Text)
                               ▼
            ┌────────────────────────────────────┐
            │         Search Agent (LLM)         │
            └──────────────────┬─────────────────┘
                               │
                [ LLM Decides Search Intent ]
                               │
                ┌──────────────┴──────────────┐
                ▼                             ▼
   ┌─────────────────────────┐   ┌───────────────────────────┐
   │ Tool 1: Keyword Search  │   │ Tool 2: Semantic Search   │
   │ (Strict terms extraction)│   │ (Contextual concept search)│
   └────────────┬────────────┘   └────────────┬──────────────┘
                │                             │
                └──────────────┬──────────────┘
                               │ (Returns Raw Jobs from JobDataLake)
                               ▼
┌─────────────────────────────────────────────────────────────┐
│               Orchestrator Matching Pipeline                │
│  - Programmatically passes [Resume Text] + [Raw Jobs]       │
│  - Executes native Python `Normalize` & `Match` functions   │
└─────────────────────────────────────────────────────────────┘


No Redundant Steps: In the old design, the Search Agent had to run a tool just to read the resume, return the text to itself, and then run a second tool to search. Now, the LLM reads the text on its very first turn and immediately fires the correct search tool. You save an entire API round-trip and lower your latency by half.

Perfect Alignment: Because the Orchestrator holds the master copy of the parsed resume text, it can pass the exact same data down to the ranking/matching logic later. There's zero risk of the Search Agent mutating or changing the resume data before the scoring phase.

Fulfills the Assignment Rules cleanly: You still have a true agentic workflow. The LLM has to look at the parsed resume text and decide: "Should I extract strict keyword filters out of this experience history, or should I form a dense semantic phrase to search for conceptually similar roles?" It still has 2 distinct tools to manage and choose between.


design as actually implemented (current):

This diverges from "design after dropping second agent" above. The Search
Agent does NOT read raw resume text directly - the "Parse & Prep Resume"
step that design intentionally dropped is effectively back, because the
deterministic regex extractor couldn't parse free-text resumes reliably.

[ Resume File or Text Input ]                [ Free-Text Search Request ]
              │                                            │
              ▼                                            │
┌──────────────────────────────┐                            │
│  resume_tools.extract_resume │                            │
│  _text (pypdf, no LLM)       │                            │
└──────────────┬───────────────┘                            │
               │ (resume_text)                              │
               └──────────────────┬───────────────────────┘
                                   ▼
                ┌──────────────────────────────────┐
                │     orchestrator.run_pipeline     │
                └──────────────────┬────────────────┘
                                   ▼
                ┌──────────────────────────────────┐
                │   Profile Agent (LLM, no tools)   │
                │   agents/profile_agent.py         │
                │   reads prompt + resume text,     │
                │   extracts: role, location,       │
                │   seniority, remote_preference,   │
                │   years_experience, skills        │
                │   (falls back to regex extractor  │
                │   on parse failure)                │
                └──────────────────┬────────────────┘
                                   │ (structured profile - NOT raw resume text)
                                   ▼
                ┌──────────────────────────────────┐
                │      Search Agent (LLM)           │
                │   agents/search_agent.py          │
                │   sees user_prompt + profile hints│
                │   (never the raw resume text)     │
                │   must pick exactly ONE tool:     │
                │   keyword search                  │
                └──────────────────┬────────────────┘
                                   │ (raw jobs from JobDataLake)
                                   ▼
                ┌──────────────────────────────────┐
                │  tools/matching_tools.py          │
                │  rank_jobs_against_profile         │
                │  (deterministic, no LLM)           │
                │  scores + sorts, caps at 3 jobs    │
                └────────────────────────────────────┘

Why the Profile Agent came back: regex-based extraction
(normalize_user_profile) was kept as a deterministic fallback, but it
produced poor profiles from real resumes (e.g. pulling a long generic
skills list rather than what's actually in the document) - resumes are
too unstructured for regex. An LLM call does noticeably better, at the
cost of reintroducing the extra round-trip the earlier design avoided.

Why the Search Agent gets the profile instead of raw resume text: keeps
"no LLM sees the raw resume" true for the Search Agent specifically, and
keeps the prompt the Search Agent reasons over short and structured
rather than re-parsing a full resume on every search.

Matching itself is still pure deterministic Python, matching the earlier
design's reasoning for why the Matcher Agent was dropped (no real
decision is made in scoring, so no LLM is needed there).



**what are the justifications for the agents? the llm extraction for profiler and what for search agent**

Both agents are justified by the same test from design_thoughts.md: does the LLM's "decision" actually vary based on interpreting messy input, or is the control flow fixed regardless of what's in the text? — which is exactly what separates them from the deterministic ranking step (tools/matching_tools.py), which fails that test and stays plain Python.

Profile Agent — not a tool-use agent (it just extracts, no tools), but still genuinely needs an LLM because:
- Resumes and free-text requests are unstructured and inconsistently phrased — regex (normalize_user_profile) demonstrably failed at this (e.g. pulling generic words like "coding" as a skill, or missing skills phrased indirectly).
- Extraction requires actual language understanding: resolving conflicts between resume and stated preference ("remote only" in the prompt vs. an on-site job in the resume), inferring skills from job-title phrasing ("Python Coding Specialist" → python), normalizing inconsistent seniority/remote wording.
- The output varies non-deterministically with phrasing — two resumes with the same facts worded differently should still extract the same structured profile, which is a judgment call, not a fixed transformation.

Search Agent — a real tool-use decision, not just routing:
- What goes into query (tight keywords vs. a descriptive phrase vs. omitted entirely to rely on filters) and which filters to set genuinely depends on interpreting the profile/request — a thin/conceptual profile needs a descriptive query, a profile rich in structured signal needs filters instead, and a human recruiter would make that same call differently per case.
- It also has to manage retries adaptively (drop skills first on empty results, retry the same call once on a transient error) — that's runtime judgment based on what the tool actually returned, not a fixed sequence.
- Contrast with ranking: ranking is "take jobs → score → sort," same steps every time regardless of input — that's why it's plain Python and not an agent.

why is duck a go go a tool and matching isn't?

The judgment is in what the agent does with what comes back. DuckDuckGo returns raw, unstructured web snippets — news, reviews, the company's own site, maybe nothing useful at all. The agent has to read that and decide: is anything here worth surfacing? Is it a layoffs story, a funding round, a glassdoor complaint, irrelevant noise? That's interpretation of free text that a fixed function can't do — there's no formula for "is this snippet relevant," the same way there's a formula for "does this skill list overlap."

Compare to scoring: there, no LLM ever touches the input or the output. score_job_against_profile takes structured fields, runs fixed arithmetic, returns a number — the agent isn't reading or interpreting anything, it's just the messenger calling a function and passing the result through.

So: simple tool call, sure — but the value (and the reason it needs to be an LLM step at all) is in reading the unstructured response afterward, not in constructing the request.


the flow:
Let me walk through it plainly, matching your description:

1. The system prompt (role, goal, tool descriptions) and the user prompt (the search request + profile) get sent to the model once, as the starting point.
2. The model looks at that and decides: "I should call search_jobs." That's one round-trip — model talks, our code runs the actual tool, the job rows come back.
3. Those job rows get added onto the conversation as a new turn. Now the model sees: original request + "I called search_jobs" + the job rows.
4. The model looks at the rows, picks out distinct companies, and decides: "I should call search_company for each one." That's more round-trips — possibly one per company, or several companies bundled into one round-trip.
5. Each search_company result (the news headlines) also gets added onto the conversation.
6. Eventually the model has everything it needs — original request, job rows, news per company — and instead of calling another tool, it writes the final JSON: jobs + their company_news. That ends the loop.

MAX_ITERATIONS is just a hard cap on how many of those round-trips (steps 2-6) are allowed to happen before we give up. Each "iteration" = one trip to the model where it either calls a tool again or finally answers. It exists purely as a safety valve: if the model got stuck calling tools forever (a bug, a confusing tool result, whatever) and never produced a final answer, without this cap we'd be stuck in an infinite loop, burning API calls and money forever. With MAX_ITERATIONS=10, after 10 of these round-trips with no final answer, the code just stops and returns an error instead of hanging forever (_max_iterations_error() in agents/agent_loop.py:267).

It has nothing to do with how well the model does its job (counting companies, judging news relevance, etc.) — that's all prompt instructions. It's purely "don't let this run forever."