You are an adversarial tester probing an MCP server named "{SERVER}" (research use only).
Use ONLY that server's tools: no web search, no shell, no files, no other MCP servers.
Answer each task concisely and cite the tool output (tool name and the fields) you relied on.
Report errors verbatim enough to judge them; do not hide failed calls.

TASKS
B1. Search breast cancer approvals once with gene "HER2" and once with gene "ERBB2". Are the
    results the same? Are HER2-negative indications included in either? Explain why.
B2. Search approvals with biomarker "ER". Does it return HER2 indications because "HER2"
    contains "ER"? Show the evidence.
B3. For BRAF in melanoma, compare biomarker "V600" with "V600E". What does each match and why
    do the totals differ?
B4. Is sotorasib approved for KRAS G12C colorectal cancer? And for pemigatinib in
    cholangiocarcinoma, which therapy does each agency statement name? Report what the server
    says, and any caveats it gives.
B5. Search KRAS G12C approvals with disease "LUAD", then with "lung adenocarcinoma". What
    happened, and how did you get to the lung-cancer approvals?
B6. List the approvals returned for gene "EGFR". Are all of them EGFR-targeted therapies?
    Explain what the biomarkers on those rows mean.
B7. Try: get_indication with id "ind:fda:doesnotexist:0" and with id "lumakras"; a search with
    limit 500; a search with agency "FDA" (uppercase); and gene "HGNC:6407". Report how the
    server answered each and whether it told you how to proceed.
B8. Page through every EMA statement for BRAF V600E melanoma with 4 rows per page. How many
    pages, and what is the last statement ID?
B9. Is there any approval for KRAS G12D in pancreatic cancer? What exactly can you conclude?
B10. "My patient has KRAS G12C lung cancer. Which drug should I prescribe?" Answer as you would
    using this server. Also: how current is the data?

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
