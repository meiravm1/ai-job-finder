# Test Run Retrospective — [Date] — [Tester Name]

## Input
- User prompt: "..."
- Resume uploaded: yes/no

## Search Agent
- Tool(s) called: [search_jobs_by_keyword / search_jobs_by_semantic_query]
- Parameters used: {...}
- Number of jobs returned: N
- What worked:
  -
- What didn't work:
  -

## Matching Agent
- Profile extracted: {...}
- Sample scores produced (top 3):
  1.
  2.
  3.

- What worked:
  -
- What didn't work:
  -

## Overall
- Did the final ranked list seem reasonable for the prompt? (Y/N + notes)
- Any API errors encountered (JobDataLake or Anthropic)?
  - got 429 from gemini-2.5-flash, had to switch to paid
  - getting results takes a long time
  - why did llm choose by keyword and not full text -> tighten system prompt?
  - hard to understand what happens after what. added logging function
  - hard to understand what happens after what. worked with debug and breakpoints
  - limit number of results to save tokens
  - do we need a rule based matcher or would llm do the matching.
  - inconsistent answers?
  - agent entering loop?
- Ideas for next iteration:
  

  prompts that show llm strength:
  python lover a true new yorker loves remote jobs lots of coding skills - new york into locations, decided on semantic query

  problematic prompt and resume:
  counseler. arkansas
  senior citizen was thought of seniority senior

**when using gemini fast it said it could not parse json so added**
  JSON_RETRY_REMINDER = (
    "Your previous reply was not valid JSON. Respond again with ONLY the
"
    "JSON object matching the required schema - no explanations, no prose
, "
    "no markdown code fences."
)

