from __future__ import annotations

from hashlib import sha256
from html import escape
import re

from research_os.presentation.artifacts import (
    HtmlPresentationArtifact,
    MarkdownPresentationArtifact,
)
from research_os.presentation.print_css import A4_PRINT_CSS


_TABLE_SEPARATOR = re.compile(r"^:?-{3,}:?$")
_BOLD = re.compile(r"\*\*(.+?)\*\*")
_CODE = re.compile(r"`([^`]+)`")


class ProfessionalHtmlRenderer:
    """Deterministic, presentation-only renderer for Research OS Markdown."""

    version = "professional-html-renderer@1.0.0"

    _SECTION_LAYOUT = {
        "投资决策快照": ("investment-decision-snapshot", "decision-snapshot"),
        "核心投资判断": ("core-investment-judgment", "core-judgment"),
        "财务与经营表现": ("financial-operating", "financial-operating"),
        "资本效率与融资循环": ("capital-funding", "capital-funding"),
        "关键因果链": ("causal-bridge", "causal-bridge"),
        "投资逻辑与反证": ("thesis-debate", "thesis-debate"),
        "市场预期与预测纪律": ("expectation-forecast", "expectation-forecast"),
        "市场预期差": ("expectation-gap", "expectation-gap"),
        "估值方法与适用性": ("valuation-methods", "valuation-methods"),
        "估值与情景": ("valuation", "valuation"),
        "监控与验证": ("monitoring", "monitoring"),
        "财务趋势": ("financial-trends", "financial-trends"),
        "经营证据": ("operating-evidence", "operating-evidence"),
        "现金流质量": ("cash-flow-quality", "cash-flow-quality"),
        "同行与产品线比较": ("peer-comparison", "peer-comparison"),
        "一致预期分布": ("consensus-dispersion", "consensus-dispersion"),
        "敏感性与情景": ("sensitivity-scenarios", "sensitivity-scenarios"),
        "监控规则与验证日历": ("monitoring-calendar", "monitoring-calendar"),
        "上期判断回顾": ("prior-run-review", "prior-run-review"),
        "方法说明": ("methodology-disclosure", "methodology-disclosure"),
        "主张强度与语义边界": ("semantic-claims", "semantic-claims"),
        "状态来源": ("state-provenance", "state-provenance"),
        "研究缺口分类": ("research-gaps", "research-gaps"),
        "关键研究限制": ("material-limitations", "research-gaps"),
        "证据追溯": ("evidence-traceability", "evidence-traceability"),
        "审计附录": ("audit-appendix", "audit-appendix"),
    }

    @staticmethod
    def _inline(text: str) -> str:
        rendered = escape(text.strip(), quote=True).replace("\\|", "|")
        rendered = _BOLD.sub(r"<strong>\1</strong>", rendered)
        return _CODE.sub(r"<code>\1</code>", rendered)

    @staticmethod
    def _split_table_row(line: str) -> list[str]:
        value = line.strip()
        if value.startswith("|"):
            value = value[1:]
        if value.endswith("|") and not value.endswith("\\|"):
            value = value[:-1]
        return [part.strip() for part in re.split(r"(?<!\\)\|", value)]

    @classmethod
    def _is_table(cls, lines: list[str], index: int) -> bool:
        if index + 1 >= len(lines) or "|" not in lines[index]:
            return False
        separators = cls._split_table_row(lines[index + 1])
        headers = cls._split_table_row(lines[index])
        return bool(headers) and len(headers) == len(separators) and all(
            _TABLE_SEPARATOR.fullmatch(item.replace(" ", "")) for item in separators
        )

    @classmethod
    def _render_table(cls, lines: list[str], index: int) -> tuple[list[str], int]:
        headers = cls._split_table_row(lines[index])
        width = len(headers)
        index += 2
        rows: list[list[str]] = []
        while index < len(lines):
            line = lines[index]
            if not line.strip() or "|" not in line:
                break
            cells = cls._split_table_row(line)
            if len(cells) != width:
                break
            rows.append(cells)
            index += 1

        output = ["<div class=\"table-wrap\">", "<table>", "<thead>", "<tr>"]
        output.extend(f"<th>{cls._inline(item)}</th>" for item in headers)
        output.extend(["</tr>", "</thead>", "<tbody>"])
        for row in rows:
            output.append("<tr>")
            output.extend(f"<td>{cls._inline(item)}</td>" for item in row)
            output.append("</tr>")
        output.extend(["</tbody>", "</table>", "</div>"])
        return output, index

    @classmethod
    def _section_attributes(cls, title: str, sequence: int) -> tuple[str, str]:
        section_id, section_class = cls._SECTION_LAYOUT.get(
            title,
            (f"report-section-{sequence}", "standard-section"),
        )
        return section_id, f"report-section {section_class}"

    @classmethod
    def _markdown_body(cls, content: str) -> str:
        lines = content.splitlines()
        output: list[str] = []
        section_open = False
        list_open = False
        section_sequence = 0
        index = 0

        def close_list() -> None:
            nonlocal list_open
            if list_open:
                output.append("</ul>")
                list_open = False

        while index < len(lines):
            line = lines[index]
            stripped = line.strip()
            if not stripped:
                close_list()
                index += 1
                continue

            heading = re.fullmatch(r"(#{1,4})\s+(.+)", stripped)
            if heading:
                close_list()
                level = len(heading.group(1))
                title = heading.group(2).strip()
                if level == 2:
                    if section_open:
                        output.append("</section>")
                    section_sequence += 1
                    section_id, section_class = cls._section_attributes(
                        title, section_sequence
                    )
                    output.append(
                        f'<section id="{section_id}" class="{section_class}">'
                    )
                    section_open = True
                output.append(f"<h{level}>{cls._inline(title)}</h{level}>")
                index += 1
                continue

            if cls._is_table(lines, index):
                close_list()
                table, index = cls._render_table(lines, index)
                output.extend(table)
                continue

            if stripped.startswith("- "):
                if not list_open:
                    output.append("<ul>")
                    list_open = True
                output.append(f"<li>{cls._inline(stripped[2:])}</li>")
                index += 1
                continue

            close_list()
            if stripped == "---":
                output.append("<hr>")
            else:
                output.append(f"<p>{cls._inline(stripped)}</p>")
            index += 1

        close_list()
        if section_open:
            output.append("</section>")
        return "\n".join(output)

    def render(
        self, markdown: MarkdownPresentationArtifact
    ) -> HtmlPresentationArtifact:
        if not isinstance(markdown, MarkdownPresentationArtifact):
            raise TypeError(
                "ProfessionalHtmlRenderer.render requires MarkdownPresentationArtifact"
            )
        body = self._markdown_body(markdown.content)
        style = A4_PRINT_CSS
        style_hash = sha256(style.encode("utf-8")).hexdigest()
        html = "\n".join(
            (
                "<!doctype html>",
                '<html lang="zh-CN">',
                "<head>",
                '<meta charset="utf-8">',
                '<meta name="viewport" content="width=device-width, initial-scale=1">',
                f'<meta name="research-os-renderer" content="{self.version}">',
                f'<meta name="research-os-source-hash" content="{markdown.content_hash}">',
                f'<meta name="research-os-style-hash" content="{style_hash}">',
                "<title>投资研究报告</title>",
                f"<style>{style}</style>",
                "</head>",
                "<body>",
                '<main class="report">',
                body,
                "</main>",
                "</body>",
                "</html>",
                "",
            )
        )
        return HtmlPresentationArtifact.from_markdown(
            markdown=markdown,
            renderer_version=self.version,
            style=style,
            content=html,
        )
