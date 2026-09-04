import base64
import os
import re

_ADANI_FONT_CSS_CACHE = None

SEARCH_TEMPLATE_DIRS = [
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "email_templates")),       # server/app/email_templates
    os.path.abspath(os.path.join(os.path.dirname(__file__), "templates")),                          # server/app/helpers/email/templates
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "email_templates")),  # server/email_templates
]
TEMPLATES_DIR = next((d for d in SEARCH_TEMPLATE_DIRS if os.path.exists(d)), SEARCH_TEMPLATE_DIRS[0])


def get_adani_font_css() -> str:
    """Return the @font-face CSS rule with base64-embedded Adani font."""
    global _ADANI_FONT_CSS_CACHE
    if _ADANI_FONT_CSS_CACHE is not None:
        return _ADANI_FONT_CSS_CACHE

    font_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__), "..", "..", "..", "..", "client", "src", "styles", "adani 2.ttf"
        )
    )

    if os.path.exists(font_path):
        try:
            with open(font_path, "rb") as f:
                b64_font = base64.b64encode(f.read()).decode("ascii")
            _ADANI_FONT_CSS_CACHE = f"""@font-face {{
    font-family: 'Adani';
    src: url(data:font/truetype;charset=utf-8;base64,{b64_font}) format('truetype');
    font-weight: normal;
    font-style: normal;
}}"""
        except Exception:
            _ADANI_FONT_CSS_CACHE = ""
    else:
        _ADANI_FONT_CSS_CACHE = ""

    return _ADANI_FONT_CSS_CACHE


def render_template(template_name: str, context: dict) -> str:
    """Load an HTML template from email_templates/ and substitute {{ key }} placeholders."""
    if not template_name.endswith(".html"):
        template_name = f"{template_name}.html"

    file_path = os.path.join(TEMPLATES_DIR, template_name)
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Email template not found: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Automatically add font_css if not explicitly in context
    if "font_css" not in context:
        context["font_css"] = get_adani_font_css()

    # Replace {{ key }}, {{key}}, or /* {{ key }} */ placeholders
    def replace_match(match):
        key = match.group(1).strip()
        val = context.get(key, "")
        return str(val) if val is not None else ""

    rendered = re.sub(r"(?:/\*\s*)?\{\{\s*([a-zA-Z0-9_]+)\s*\}\}(?:\s*\*/)?", replace_match, content)
    return rendered
