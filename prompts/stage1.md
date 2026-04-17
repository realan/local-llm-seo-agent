Use the attached YAML files as the source of truth:

- 01_project.yaml
- 02_agent_and_tools.yaml
- 03_catalog_logic.yaml
- entity_dictionary.yaml
- size_rules.yaml

Task:
Create the project in stages.

Stage 1 only:

- Read the YAML files
- Output the final project structure
- Output a short implementation plan
- Generate only the following files first:
  - app/main.py
  - app/agent/schemas.py
  - app/llm/ollama_client.py
  - app/tools/base.py
  - README.md

Rules:

- Keep everything aligned with YAML
- Keep code runnable
- Do not add extra architecture
- Do not implement catalog mode yet beyond basic placeholders if needed
- Do not generate pseudo-code

After Stage 1 is complete, stop.
