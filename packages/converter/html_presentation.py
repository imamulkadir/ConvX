"""Readable structural indentation without changing disclosure text runs."""

import re

from lxml import etree

FORMAT = "structural-indent-v1"
CONTAINERS = frozenset({"html", "head", "body", "div", "table", "tbody", "thead", "tfoot", "tr", "td"})


def formatted_document(element):
    root = element.getroottree().getroot()
    return bool(root.xpath('/html/head/meta[@name="convx-html-format" and @content="structural-indent-v1"]'))


def disclosure_text(element):
    formatted = formatted_document(element)

    def visit(node):
        structural = formatted and node.tag in CONTAINERS and len(node) > 0

        def retained(value):
            return value and not (structural and re.fullmatch(r"\n(?:  )*", value))

        if retained(node.text):
            yield node.text
        for child in node:
            if isinstance(child.tag, str):
                yield from visit(child)
            if retained(child.tail):
                yield child.tail

    return "".join(visit(element))


def readable_html(root):
    before = "".join(root.find("body").itertext())
    etree.SubElement(root.find("head"), "meta", name="convx-html-format", content=FORMAT)

    def indent(node, depth):
        if node.tag not in CONTAINERS:
            return  # Inline text/formatting runs must remain byte-for-byte intact.
        for child in node:
            indent(child, depth + 1)
        if len(node) and node.text is None and all(c.tail is None for c in node):
            node.text = "\n" + "  " * (depth + 1)
            for index, child in enumerate(node):
                child.tail = "\n" + "  " * (depth if index == len(node) - 1 else depth + 1)

    indent(root, 0)
    if disclosure_text(root.find("body")) != before:
        raise ValueError("Structural indentation changed disclosure")
    return etree.tostring(root, method="html", encoding="ascii") + b"\n"
