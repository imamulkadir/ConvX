from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser


class ScanLimit(Exception):
    pass


@dataclass
class Node:
    number: int
    tag: str
    attrs: dict
    parent: int | None
    ancestors: tuple[str, ...]
    line: int


class SourceScanner(HTMLParser):
    """Observe source tags before a browser/lxml can repair or insert markup."""

    def __init__(self, policy, diagnostic, context):
        super().__init__(convert_charrefs=False)
        self.policy, self.diagnostic, self.context = policy, diagnostic, context
        self.nodes = []
        self.stack = []

    def handle_starttag(self, tag, attrs):
        self.context.check()
        if (
            len(self.nodes) >= self.policy.max_nodes
            or len(self.stack) >= self.policy.max_depth
            or len(attrs) > self.policy.max_attributes
        ):
            raise ScanLimit
        # HTML permits omitted end tags; do not invent an EDGAR proper-nesting requirement.
        if tag in {"td", "th", "tr"}:
            targets = {"td", "th", "tr"} if tag == "tr" else {"td", "th"}
            while self.stack and self.stack[-1].tag in targets:
                self.stack.pop()
        names = [name for name, _ in attrs]
        node = Node(
            len(self.nodes),
            tag,
            dict(attrs),
            self.stack[-1].number if self.stack else None,
            tuple(n.tag for n in self.stack),
            self.getpos()[0],
        )
        self.nodes.append(node)
        if len(names) != len(set(names)):
            self.diagnostic(
                "HTML_DUPLICATE_ATTRIBUTE",
                "Duplicate attributes have ambiguous parser behavior",
                "Remove ambiguity in the source bytes",
                node=node,
                basis="project_policy",
            )
        if tag not in {"br", "hr", "img", "meta", "isindex", "page"}:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                break

    def handle_decl(self, decl):
        self.diagnostic(
            "HTML_DECLARATION_UNSUPPORTED",
            "DOCTYPE/SGML declarations are outside the conservative profile",
            "Omit declarations; retain escaped disclosure",
            section="5.2.2.4",
            basis="confirmed_manual",
        )

    def unknown_decl(self, data):
        self.diagnostic(
            "HTML_DECLARATION_UNSUPPORTED",
            "Unrecognized declaration in HTML source",
            "Remove unsupported declaration",
            basis="project_policy",
        )

    def handle_pi(self, data):
        self.diagnostic(
            "HTML_PROCESSING_INSTRUCTION",
            "Processing instructions are outside this ordinary HTML profile",
            "Use plain HTM without XML processing instructions",
            basis="project_policy",
        )
