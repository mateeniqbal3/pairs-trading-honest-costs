"""Build paper/writeup.pdf from paper/writeup.md (the single source of the text).

The Markdown file is written to read well on GitHub. This script moves its
title block and abstract into LaTeX metadata, drops the GitHub-only figure
captions (pandoc makes captions from the image alt text), and runs pandoc
with XeLaTeX.

Requirements: pandoc (3.x) and a TeX distribution with xelatex.
Usage (from the repository root):
    python paper/make_figures.py
    python paper/build_pdf.py
"""

import re
import subprocess
import tempfile
from pathlib import Path

PAPER = Path(__file__).resolve().parent
SRC = PAPER / "writeup.md"
OUT = PAPER / "writeup.pdf"

text = SRC.read_text(encoding="utf-8")

# Split off the title block (everything before the first horizontal rule).
head, body = text.split("\n---\n", 1)
title = re.search(r"^# (.+)$", head, re.M).group(1).strip()
head_lines = [ln.strip() for ln in head.splitlines() if ln.strip() and not ln.startswith("# ")]
author = head_lines[0].strip("*")
affiliation, email, version, code = head_lines[1:5]

# Pull out the abstract, keywords and JEL codes (up to the next rule).
abstract_block, body = body.split("\n---\n", 1)
abstract_block = abstract_block.replace("## Abstract", "").strip()
abstract, keywords, jel = [p.strip() for p in abstract_block.split("\n\n")]

# Figure captions are duplicated on GitHub as italic lines; drop them here.
body = re.sub(r"^\*Figure \d+\..*?\*\n", "", body, flags=re.M | re.S)
# Section numbers are written by hand, so promote "## 1. Intro" to level 1.
body = re.sub(r"^## ", "# ", body, flags=re.M)
body = re.sub(r"^### ", "## ", body, flags=re.M)
# Start the appendices on a new page.
body = body.replace("# Appendix A.", "\\newpage\n\n# Appendix A.", 1)
body = body.replace("# Appendix B.", "\\newpage\n\n# Appendix B.", 1)
# Put each 64-character hash on its own line so it fits the text width.
body = re.sub(r": `([0-9a-f]{64})`", r":\\\n  `\1`", body)
# Size figures for the page (GitHub ignores this attribute syntax, so add it here).
body = re.sub(r"^(!\[.*?\]\(.*?\))$", r"\1{width=62%}", body, flags=re.M)


def yaml_str(s: str) -> str:
    return "'" + s.replace("'", "''") + "'"


abstract_md = f"{abstract}\n\n{keywords}\n\n{jel}"
def tex_escape(s: str) -> str:
    return s.replace("&", r"\&").replace("%", r"\%").replace("_", r"\_").replace("#", r"\#")


author, affiliation, email = tex_escape(author), tex_escape(affiliation), tex_escape(email)
repo_url = re.search(r"<(.+?)>", code).group(1)
# Raw LaTeX for the title block (the `...`{=latex} syntax passes it through pandoc).
author_tex = (
    "`" + author + r"\\[2pt] {\normalsize " + affiliation + r"}\\ "
    + r"{\normalsize\ttfamily " + email + "}`{=latex}"
)
date_tex = "`" + version.replace("—", "--") + r"\\[2pt] {\small\url{" + repo_url + "}}`{=latex}"
abstract_yaml = "\n".join("  " + ln for ln in abstract_md.splitlines())

HEADER = r"""
geometry: margin=1in
fontsize: 11pt
fontfamily: fontspec
mainfont: TeX Gyre Pagella
mathfont: Latin Modern Math
linestretch: 1.15
colorlinks: true
linkcolor: blue
urlcolor: blue
header-includes: |
  \usepackage{float}
  \floatplacement{figure}{H}
  \sloppy
  \usepackage{etoolbox}
  \AtBeginEnvironment{longtable}{\small}
  \usepackage{caption}
  \captionsetup{font=small,labelformat=empty}
  \usepackage{fancyhdr}
  \pagestyle{fancy}
  \fancyhf{}
  \fancyhead[L]{\small Pairs Trading with Honest Cost Modeling}
  \fancyhead[R]{\small Working paper, v1.0}
  \fancyfoot[C]{\thepage}
  \renewcommand{\headrulewidth}{0.4pt}
"""

metadata = (
    "---\n"
    f"title: {yaml_str(title)}\n"
    f"author: {yaml_str(author_tex)}\n"
    f"date: {yaml_str(date_tex)}\n"
    f"abstract: |\n{abstract_yaml}\n"
    + HEADER.lstrip("\n")
    + "---\n\n"
)

with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as tmp:
    tmp.write(metadata + body)
    tmp_path = tmp.name

subprocess.run(
    [
        "pandoc", tmp_path,
        "--from", "markdown+tex_math_dollars+pipe_tables+raw_attribute",
        "--pdf-engine", "xelatex",
        "--resource-path", str(PAPER),
        "-o", str(OUT),
    ],
    check=True,
)
print(f"Wrote {OUT.relative_to(PAPER.parent)}")
