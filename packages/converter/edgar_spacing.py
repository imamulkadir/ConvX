"""Fit literal CSS2 spacing to source glyph advances in unchanged format runs."""

from converter.html_generator.typography import font_family


def calibrate(runs, context):
    import numpy as np
    from playwright.sync_api import sync_playwright

    requests = []
    for _, span, chars in runs:
        if len(chars) > 4096 or len(requests) >= 20000:
            raise ValueError("Source typography exceeds bounded calibration work")
        requests.append(
            {
                "family": font_family(span.font_name),
                "size": span.font_size_pt,
                "bold": span.bold_hint,
                "italic": span.italic_hint,
                "text": "".join(c.text for c in chars),
            }
        )
    context.check()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, chromium_sandbox=True)
        try:
            session = browser.new_context(java_script_enabled=False, service_workers="block")
            session.route("**/*", lambda r: r.abort())
            page = session.new_page()
            widths = page.evaluate(
                """requests => {
                const context = document.createElement('canvas').getContext('2d');
                return requests.map(r => {
                    context.font = `${r.italic?'italic ':''}${r.bold?'bold ':''}${r.size*4/3}px "${r.family}"`;
                    const chars = Array.from(r.text), widths = [0];
                    for(let i=1;i<chars.length;i++) widths.push(context.measureText(chars.slice(0,i).join('')).width*.75);
                    return widths;
                });
            }""",
                requests,
            )
        finally:
            browser.close()
    for (node, span, chars), natural in zip(runs, widths, strict=True):
        context.check()
        if len(chars) < 2:
            continue
        if len(natural) != len(chars) or any(len(c.text) != 1 for c in chars):
            raise ValueError("Ambiguous source spacing")
        spaces = 0
        design = []
        for i, c in enumerate(chars):
            design.append((i, spaces))
            spaces += c.text.isspace()
        desired = np.array([c.origin[0] - chars[0].origin[0] for c in chars]) - np.array(natural)
        letter, word = np.linalg.lstsq(np.array(design), desired, rcond=None)[0]
        if abs(letter) > span.font_size_pt or abs(word) > span.font_size_pt * 4:
            raise ValueError("Unrepresentable source run spacing")
        letter_value = format(float(letter), ".10f").rstrip("0").rstrip(".") or "0"
        word_value = format(float(word), ".10f").rstrip("0").rstrip(".") or "0"
        node.set("style", node.get("style") + f";letter-spacing:{letter_value}pt;word-spacing:{word_value}pt")
