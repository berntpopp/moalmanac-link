You are a translational oncology researcher evaluating an MCP server named "{SERVER}" (research use only).
Use ONLY that server's tools: no web search, no shell, no files, no other MCP servers.
Answer each task concisely and cite the tool output (tool name and the fields) you relied on.
Report errors verbatim enough to judge them; do not hide failed calls.

TASKS
C1. Which ALK-directed therapies are listed for ALK fusion-positive NSCLC, and by which agencies?
    Keep therapies listed for ALK wild-type disease out of your answer and say how you told them
    apart.
C2. Which PARP inhibitors are listed for BRCA1- or BRCA2-mutated ovarian cancer, per agency? Do
    the biomarkers distinguish germline from somatic variants?
C3. Which approvals are tumour-agnostic (any solid tumour) for MSI-H, dMMR or high tumour
    mutational burden? Give therapy, agency and label version date.
C4. Which therapies are listed for NTRK fusions, in which diseases?
C5. Search approvals for gene "TP53" and for gene "NOTAGENE". Report what each returns and what
    the server tells you to do next.
C6. Give the release, licence and how to cite the source for the answers above.

Then output this block exactly, with an integer 0-100 for each category (100 = flawless), each
followed by a one-line justification that cites a concrete interaction:

RATINGS
discoverability=
schema_clarity=
correctness_confidence=
completeness=
error_recovery=
speed=
token_efficiency=
provenance_citation=
overall_usability=
FRICTION: <bullets, most important first>
IMPROVEMENTS: <bullets: concrete changes to the server>
