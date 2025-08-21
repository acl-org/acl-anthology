# Prompt template: Process an author-page GitHub issue

Purpose
-------
This prompt is for automating the `process-author-page` workflow. Give an LLM (or automation) a full GitHub issue (title, body, labels, comments) and it will extract the data needed to fill out the project's author-page instructions and produce a machine-friendly plan and artifacts (YAML snippet, XML edit hints, branch name, commands, PR text, and clarifying questions).

How to use
----------
- Provide the full issue object as context: `issue.title`, `issue.body`, `issue.labels`, `issue.author`, `issue.comments` (list of {author, body, created_at}).
- Expect a single JSON object output exactly matching the schema in the "Output schema" section.

Prompt (give the following to the LLM as the user/system prompt):

"Process an author-page GitHub issue and produce a complete actionable plan"

Context you will receive (pass this as context):
- issue.title (string)
- issue.body (string)
- issue.labels (list of strings)
- issue.author (string)
- issue.comments (list of {author, body, created_at})
- optional: linked PR / linked commits

Task for the LLM
----------------
1. Parse the issue and comments to extract:
   - canonical_author_name: canonical first/middle/last parts.
   - name_variants mentioned in issue/comments.
   - requester_author_id (if suggested by user).
   - requester_ORCID (if provided).
   - requester_institution (if provided).
   - primary_paper_ids: Anthology paper IDs the requester claims.
   - other_paper_ids: other Anthology IDs referencing the same name.
   - requested_action: one of ["create-id-and-assign","assign-existing-id","split","merge","other"], or "clarify" if ambiguous.
   - whether the user requests a dummy id for other people sharing the name.
   - urgency / labels like "author-page" / "high-priority".

2. Validate and enrich:
   - Validate ORCID format (pattern: 0000-0000-0000-0000).
   - Validate Anthology ID patterns; if missing set papers_to_verify=true.
   - If ambiguous or missing data, populate `clarifying_questions` with concise questions.

3. Produce outputs using the exact JSON schema below. Be concise and machine-parseable. When generating branch names and ids, follow repository conventions described in guidelines.

Output schema (RETURN EXACTLY this JSON object; do not return extra text)
--------------------------------------------------------------------------------
{
  "metadata": {
    "issue_title": string,
    "issue_number": integer_or_null,
    "issue_author": string,
    "labels": [string]
  },

  "extracted": {
    "canonical_name": { "first": string, "middle": string_or_null, "last": string },
    "name_variants": [string],
    "requester": {
      "author_id_proposed": string_or_null,
      "orcid": string_or_null,
      "institution": string_or_null,
      "claim_paper_ids": [string]
    },
    "other_paper_ids": [ { "id": string, "found_in_comment_or_body": string } ],
    "requested_action": "create-id-and-assign" | "assign-existing-id" | "split" | "merge" | "other" | "clarify",
    "wants_dummy_id": boolean,
    "ambiguities": [string]
  },

  "plan": {
    "branch_name": string,
    "name_variants_yaml_snippet": string,
    "xml_edits": [
      { "paper_id": string, "file_hint": string_or_null, "author_xpath_hint": string, "action": "add_id" | "remove_id" | "none", "id_to_set": string }
    ],
    "commands": [ string ],
    "git": {
      "commit_message": string,
      "pr_title": string,
      "pr_body": string
    },
    "validation_commands": [ string ],
    "files_to_edit": [string],
    "notes": [string]
  },

  "edge_cases_and_questions": {
    "clarifying_questions": [string],
    "recommended_dummy_id_format": string,
    "conflict_resolution_policy": string
  }
}

Guidelines and conventions (apply when filling fields)
------------------------------------------------------
- Always use `data/yaml/name_variants.yaml` for new canonical id entries. The YAML snippet must follow existing project structure. Example:

  - canonical: {first: Shashank, last: Gupta}
    id: shashank-gupta-uiuc
    orcid: 0000-0000-0000-0000
    institution: University of Illinois at Urbana-Champaign
    comment: "created from issue #NNN: author-confirmed"

- Shell commands must be repository-root relative and follow this example order:
  - git checkout -b <branch_name>
  - python3 bin/add_author_id.py <author_id> "Last, First" --paper-ids <ids...>
  - git add <files>
  - git commit -m "<commit_message>"
  - git push --set-upstream origin <branch_name>

- Include validation commands: `make check` and `make hugo_data` in `validation_commands`.
- If ambiguous or missing paper IDs, set `requested_action` to "clarify" and include exact clarifying questions for the issue author.

- ID & branch generation policy:
  - Prefer supplied author id. If none supplied, generate `last-first` (lowercase, ascii, hyphenated).
  - If that collides with an existing id, append an institution shortname (e.g., `-uiuc`) or year suffix (e.g., `-2025`).

Edge cases to handle (list these briefly in `edge_cases_and_questions`):
- Issue requests adding an id but provides no Anthology paper IDs.
- Multiple people share the canonical name across years and venues.
- ORCID present but invalid format.
- A user requests merging two existing ids (detect and set `requested_action`="merge").
- Concurrent edits: warn to re-open `data/yaml/name_variants.yaml` before editing to avoid overwrites.

Minimal example (illustrative only; real output must derive from the issue):

{
  "metadata": { "issue_title": "Author page: Shashank Gupta", "issue_number": 3658, "issue_author": "shashank", "labels": ["author-page"] },
  "extracted": {
    "canonical_name": {"first":"Shashank","middle":null,"last":"Gupta"},
    "name_variants": ["Gupta, Shashank"],
    "requester": {"author_id_proposed":"shashank-gupta-uiuc","orcid":"0000-0002-3683-3739","institution":"University of Illinois at Urbana-Champaign","claim_paper_ids":["L18-1086"]},
    "other_paper_ids": [{"id":"2020.semeval-1.56","found_in_comment_or_body":"comment by alice"}],
    "requested_action":"create-id-and-assign",
    "wants_dummy_id": true,
    "ambiguities": []
  },
  "plan": {
    "branch_name":"author-page-shashank-gupta-uiuc",
    "name_variants_yaml_snippet":"- canonical: {first: Shashank, last: Gupta}\\n  id: shashank-gupta-uiuc\\n  orcid: 0000-0002-3683-3739\\n  institution: University of Illinois at Urbana-Champaign\\n  comment: \\\"from issue #3658\\\"",
    "xml_edits": [{"paper_id":"L18-1086","file_hint":"data/xml/L18.xml","author_xpath_hint":"//paper[@id='L18-1086']//author[first='Shashank' and last='Gupta']","action":"add_id","id_to_set":"shashank-gupta-uiuc"}],
    "commands":["git checkout -b author-page-shashank-gupta-uiuc","python3 bin/add_author_id.py shashank-gupta-uiuc \"Gupta, Shashank\" --paper-ids L18-1086","git add data/xml/L18.xml data/yaml/name_variants.yaml","git commit -m \"Author page: add shashank-gupta-uiuc and assign L18-1086\\n\\nCloses #3658\"","git push --set-upstream origin author-page-shashank-gupta-uiuc"],
    "git": {"commit_message":"Author page: add shashank-gupta-uiuc and assign L18-1086\\n\\nCloses #3658","pr_title":"Author page: Shashank Gupta (shashank-gupta-uiuc)","pr_body":"This PR creates author id `shashank-gupta-uiuc` and assigns it to L18-1086. Also adds a `name_variants` YAML entry. See #3658."},
    "validation_commands": ["make check","make hugo_data"],
    "files_to_edit":["data/yaml/name_variants.yaml","data/xml/L18.xml"],
    "notes":["Re-open `data/yaml/name_variants.yaml` before applying the YAML snippet to avoid overwriting manual edits."]
  },
  "edge_cases_and_questions": {
    "clarifying_questions": [],
    "recommended_dummy_id_format":"last-first",
    "conflict_resolution_policy":"If generated id collides, append institution shortname; if still ambiguous, append year suffix and ask the issue author to confirm."
  }
}

Usage notes
-----------
- Feed the full issue (title, body, comments) into this prompt and request exactly one JSON object output.
- If `requested_action` == "clarify", post the `clarifying_questions` as a comment on the issue before making edits.
- Always re-open `data/yaml/name_variants.yaml` to read current contents before applying the `name_variants_yaml_snippet`.
- Run validation commands after edits.

-- end of prompt template
