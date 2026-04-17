Stage 1 is complete.

Current status:

- Foundation is ready
- CLI structure exists
- schemas are implemented
- Ollama LLM client is implemented

Now implement Stage 2 only.

Use the attached YAML files as the source of truth:

- 01_project.yaml
- 02_agent_and_tools.yaml
- 03_catalog_logic.yaml
- entity_dictionary.yaml
- size_rules.yaml

Goal of Stage 2:
Implement the working agent loop and demo mode.

What to build now:

1. app/agent/runner.py
2. app/agent/prompts.py
3. app/tools/calculator.py
4. app/tools/file_tools.py
5. app/tools/http_fetch.py
6. wire demo mode into app/main.py
7. update README.md with Stage 2 usage examples
8. add minimal tests for demo mode if project structure already supports tests

Required behavior:

- The agent must run in a thought -> action -> observation -> thought loop
- The model must return structured output only
- Parse model output strictly
- If model output is invalid, retry exactly once with a repair prompt
- Enforce max step limits from YAML
- Print step logs to console:
  - step number
  - thought
  - action
  - args
  - short observation summary
- If task is solved, return final_answer
- If max steps are exceeded, fail gracefully with a clear final message

Demo tools to implement:

1. calculator
   - input: arithmetic expression
   - output: result
   - keep implementation safe and simple
   - do not use unsafe raw eval without restrictions

2. read_text_file
   - input: file_path
   - output:
     - content
     - line_count

3. http_get
   - input:
     - url
     - timeout_sec
   - output:
     - status_code
     - text
   - return truncated text if response is very large

Demo scenarios that must work:

1. Calculate (123 + 456) \* 2
2. Read samples/test.txt and tell how many lines it has
3. Make an HTTP request and return the first 300 characters

Implementation rules:

- Keep the code simple and runnable
- Do not implement catalog mode yet
- Do not add database, async workers, queues, or extra infrastructure
- Do not redesign the architecture from Stage 1
- Reuse existing schemas and LLM client
- Stay close to YAML requirements
- No pseudo-code
- No TODO placeholders unless absolutely necessary

Prompting requirements:

- prompts.py should contain a clear system prompt for structured agent behavior
- include available tools in the prompt
- include current task
- include prior steps/history in compact form
- include output format instructions
- include repair prompt for invalid structured output

Runner requirements:

- runner.py should:
  - call the model
  - parse structured output
  - dispatch tools
  - collect observations
  - maintain step history
  - stop on final_answer
  - stop on max steps
- keep the runner modular, not monolithic

CLI requirements:

- main.py must expose a working demo command
- allow passing a free-text task from CLI
- include a few built-in example commands if helpful

Expected output format from you:

1. Briefly summarize the Stage 2 plan
2. Show which files will be created or changed
3. Then generate the full contents of each file one by one
4. Keep each file complete and ready to save

Important:
Implement Stage 2 only.
Do not start Excel tools or catalog processing in this stage.
Stop after Stage 2 files are complete.
