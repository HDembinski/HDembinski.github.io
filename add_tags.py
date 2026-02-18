from pathlib import Path
from pydantic_ai import Agent, ModelSettings, capture_run_messages
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic import BaseModel
from annotated_types import Gt, Lt
from typing import Annotated
import json
import nbformat
from typing import Literal
import asyncio
import logging
from rich.logging import RichHandler

logging.basicConfig(
    level="INFO",
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)],
)

log = logging.getLogger(__name__)

model = OpenAIChatModel(
    "",
    provider=OpenAIProvider(
        base_url="http://localhost:8080/v1",
    ),
    settings=ModelSettings(temperature=0.5, max_tokens=1000),
)

valid_tags_raw = """
physics: Post is related to physics, especially particle physics.
science: Post is about science other than physics.
programming: The post is primarily about programming, discussing language features or libraries.
high performance computing: Post is about running software efficiently and fast, typically dealing with benchmarks.
statistics: Post is related to statistics.
llm: Post is related to LLMs (Large Language Models) or uses LLMs, for example through agents.
philosophy: Post touches philosophy. 
engineering: Post is about engineering.
opinion: Post expresses opinions.
data analysis: Post is about data analysis.
visualization: Post is primarily about data visualization.
graphical design: Post is about graphical design.
parsing: Post deals with parsing input.
bootstrap: Post is about the bootstrap method in statistics.
uncertainty analysis: Post is about the statistical uncertainty estimation, confidence interval estimation, or uncertainty propagation (uncertainty = error in this context).
sWeights: Posts about sWeights or COWs (custom orthogonal weight functions).
symbolic computation: Post uses symbolic computation with sympy.
simulation: Post is about simulation of statistical or other processes.
neural networks: Post is about (deep) neural networks.
machine learning: Post is about machine learning other than with neural networks.
prompt engineering: Post is about prompt engineering.
web scraping: Post is about web scraping.
environment: Post is about energy consumption and other topics that affect Earth's environment.
"""

valid_tags = {
    v[0]: v[1] for v in (v.split(":") for v in valid_tags_raw.strip().split("\n"))
}


AllowedTags = Literal[*valid_tags]


class TagWithConfidence(BaseModel):
    tag: AllowedTags  # type:ignore
    confidence: Annotated[float, Gt(0), Lt(1)]


tag_agent = Agent(
    model,
    output_type=list[TagWithConfidence],
    system_prompt="Return tags that match the provided post.",
    instructions=f"""
Respond with a list of all tags that match the post.

All valid tags:

{"- ".join(f"{k}: {v}" for (k, v) in valid_tags.items())}

You must use one of these tags, you cannot invent new ones.
""",
)


fn_tag_db = Path("tag_db.json")

if fn_tag_db.exists():
    with fn_tag_db.open(encoding="utf-8") as f:
        tag_db = json.load(f)
else:
    tag_db = {}


async def get_tags(fn: Path) -> set[str]:
    with open(fn, encoding="utf-8") as f:
        if fn.suffix == ".ipynb":
            # We clean the notebook before passing it to the LLM
            nb = nbformat.read(f, as_version=4)
            nb.metadata = {}
            for cell in nb.cells:
                if cell.cell_type == "code":
                    cell.outputs = []
                    cell.execution_count = None
                    cell.metadata = {}
            doc = nbformat.writes(nb)
        elif fn.suffix == ".md":
            doc = f.read()

    tag_input = f"{fn!s}:\n\n{doc}"  # type:ignore

    joined_tags = set()
    for i in range(3):
        # To get a more complete set of tags, we iterate the call.
        with capture_run_messages() as messages:
            try:
                result = await tag_agent.run(tag_input)
                log.info(f"{fn.name} [{i}] {result.output}")
                tags = set(x.tag for x in result.output if x.confidence >= 0.8)
                joined_tags |= tags
                log.debug(messages)
            except Exception:
                # If there is an error (typically a schema validation error),
                # print the messages for debugging.
                log.exception(messages)
                raise
    log.info(f"{fn.name} {joined_tags}")
    return joined_tags


async def main():
    input_files = [Path(fn) for fn in Path("_posts").rglob("*.*")]

    to_process = []
    for fn in input_files:
        if fn.suffix not in (".ipynb", ".md"):
            continue

        # skip files that have been processed already
        if fn.name in tag_db:
            continue

        to_process.append(fn)

    try:
        for fn in sorted(to_process):
            tags = await get_tags(fn)
            if tags:
                # A sorted list is easier to diff if we update tags.
                tag_db[fn.name] = list(sorted(tags))
            else:
                log.error(f"No tags for {fn.name!r}")
            # save after every change, in case something breaks
            with fn_tag_db.open("w", encoding="utf-8") as f:
                json.dump(
                    dict(sorted(tag_db.items(), key=lambda x: x[0].lower())),
                    f,
                    indent=2,
                )

    except Exception:
        log.exception("Fatal error")
        raise SystemExit("Fatal error")


asyncio.run(main())
