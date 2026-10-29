"""design_guide.md Appendix A tokens: every colour is a token, every themed token has its dark/light
pair, and the toggle flips the whole page (D-1029-02). Static; no app or browser."""
import re
import unittest
from pathlib import Path
from edgeex_app.pages import scada as pages

ROOT = Path(__file__).resolve().parents[1]
CSS = (ROOT / "assets/scada.css").read_text(encoding="utf-8")
PY = ["edgeex_app/views/scada_view.py", "edgeex_app/components/scada.py", "edgeex_app/pages/scada.py",
      "edgeex_app/edgeex_app.py", "rxconfig.py"]
PAGES = ["overview", "process", "trend", "alarms", "flow", "communication"]

# design_guide.md A.1 verbatim: light on :root, dark overrides. One departure (PL D-1029-02): light
# muted/muted-2 (#7a7a7a/#86868b) darkened in the same hue to reach WCAG AA, see LightContrast.
GUIDE_LIGHT = {
    "page": "#f5f5f7", "card": "#ffffff", "card-2": "#ffffff", "header": "#fafafc", "row": "#fafafc",
    "select": "#ffffff", "console": "#fafafc", "text": "#1d1d1f", "muted": "#636366", "muted-2": "#68686d",
    "faint": "rgba(0,0,0,.3)", "accent": "#0066cc", "accent-press": "#0071e3", "focus": "#0066cc",
    "border": "#e0e0e0", "border-strong": "#e0e0e0", "hairline": "#f0f0f0", "error": "#ef4444",
    "warning": "#f59e0b", "success": "#10b981", "info": "#0066cc", "series-a": "#0066cc",
    "series-violet": "#a855f7", "series-emerald": "#10b981", "series-amber": "#f59e0b",
    "series-alarm": "#ef4444", "grid": "#f0f0f0", "axis": "rgba(29,29,31,.45)",
}
GUIDE_DARK = {
    "page": "#111214", "card": "#18191b", "card-2": "#1e2022", "header": "#18191b", "row": "#151617",
    "select": "#222529", "console": "rgba(0,0,0,.45)", "text": "#ffffff", "muted": "rgba(255,255,255,.6)",
    "muted-2": "rgba(255,255,255,.4)", "faint": "rgba(255,255,255,.3)", "accent": "#2997ff", "info": "#2997ff",
    "border": "rgba(255,255,255,.05)", "border-strong": "rgba(255,255,255,.1)",
    "hairline": "rgba(255,255,255,.05)", "series-a": "#2997ff", "grid": "rgba(255,255,255,.05)",
    "axis": "rgba(255,255,255,.3)",
}
# Same value in both modes per the guide (§1.3 press/focus/CTA, §2 status, §3 series, §4-§6 type,
# geometry, motion, brand, tooltip/spike shadows). Anything else must have a dark value too.
NEUTRAL = {"accent-press", "focus", "cta", "on-accent", "error", "warning", "success", "series-violet",
           "series-emerald", "series-amber", "series-alarm", "r-card", "r-card-2", "r-lg", "r-input", "r-sm",
           "r-pill", "ease", "dur", "font-sans", "font-mono", "brand", "shadow-tooltip", "shadow-spike"}
COLOUR = re.compile(r"#[0-9a-fA-F]{3,8}\b|\brgba?\(|\bhsla?\(|:\s*(white|black)\b")
LIGHT_SEL, DARK_SEL = ":root{", ':root:not(.light),[data-theme="dark"]{'


def block(selector):
    start = CSS.index(selector) + len(selector)
    return CSS[start:CSS.index("}", start)]


def tokens(selector):
    body = re.sub(r"/\*.*?\*/", "", block(selector), flags=re.S)
    return {m.group(1): m.group(2).strip() for m in re.finditer(r"--am-([\w-]+):([^;]+)", body)}


def outside_token_blocks():
    rest = CSS
    for sel in (LIGHT_SEL, DARK_SEL):
        rest = rest.replace(block(sel), "")
    return re.sub(r"/\*.*?\*/", "", rest, flags=re.S)


class Tokens(unittest.TestCase):
    def test_guide_values_verbatim(self):
        light, dark = tokens(LIGHT_SEL), tokens(DARK_SEL)
        for name, value in GUIDE_LIGHT.items():
            with self.subTest(mode="light", token=name):
                self.assertEqual(light.get(name), value)
        for name, value in GUIDE_DARK.items():
            with self.subTest(mode="dark", token=name):
                self.assertEqual(dark.get(name), value)

    def test_every_used_token_is_defined(self):
        defined = set(tokens(LIGHT_SEL))
        used = set(re.findall(r"var\(--am-([\w-]+)\)", CSS))
        for path in PY:
            used |= set(re.findall(r"var\(--am-([\w-]+)\)", (ROOT / path).read_text(encoding="utf-8")))
        self.assertEqual(used - defined, set())

    def test_every_themed_token_has_a_dark_pair(self):
        light, dark = tokens(LIGHT_SEL), tokens(DARK_SEL)
        self.assertEqual(set(light) - set(dark) - NEUTRAL, set())
        self.assertEqual(set(dark) - set(light), set())

    def test_no_colour_outside_token_blocks(self):
        self.assertEqual(COLOUR.findall(outside_token_blocks()), [])
        for path in PY:
            source = (ROOT / path).read_text(encoding="utf-8")
            with self.subTest(path=path):
                self.assertIsNone(COLOUR.search(source))
                self.assertNotIn("color_scheme", source)

    def test_rendered_pages_carry_no_colour_literal(self):
        for name in PAGES:
            with self.subTest(page=name):
                self.assertEqual(re.findall(r"#[0-9a-fA-F]{3,8}\b", str(getattr(pages, name)())), [])


def contrast(fg, bg):
    def lum(hex_):
        c = [int(hex_[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        c = [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
        return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
    hi, lo = sorted([lum(fg), lum(bg)], reverse=True)
    return (hi + 0.05) / (lo + 0.05)


class LightContrast(unittest.TestCase):
    # Light surfaces muted text sits on: card, header/row, page/sub-nav, row hover (black 5% on
    # #ffffff and #fafafc) and the selected row (accent #0066cc 10% on white).
    SURFACES = ["#ffffff", "#fafafc", "#f5f5f7", "#f2f2f2", "#eeeeef", "#e6f0fa"]

    def test_secondary_text_meets_aa(self):
        light = tokens(LIGHT_SEL)
        for name in ("text", "muted", "muted-2"):
            for bg in self.SURFACES:
                with self.subTest(token=name, surface=bg):
                    self.assertGreaterEqual(contrast(light[name], bg), 4.5)

    def test_secondary_text_keeps_the_guide_order(self):
        light = tokens(LIGHT_SEL)
        self.assertGreater(contrast(light["muted"], "#ffffff"), contrast(light["muted-2"], "#ffffff"))


class ThemeSwitch(unittest.TestCase):
    def test_dark_default_and_radix_follows_the_mode(self):
        config = (ROOT / "rxconfig.py").read_text(encoding="utf-8")
        self.assertIn('appearance="inherit"', config)
        self.assertIn('default_color_mode="dark"', config)
        self.assertTrue(CSS.index(DARK_SEL) > CSS.index(LIGHT_SEL))

    def test_every_page_has_the_toggle(self):
        for name in PAGES:
            with self.subTest(page=name):
                self.assertIn("toggleColorMode", str(getattr(pages, name)()))

    def test_no_script_element_in_page_trees(self):
        # React 19 dev logs console.error for a <script> rendered on the client (acceptance #9).
        for name in PAGES:
            with self.subTest(page=name):
                self.assertNotIn('jsx("script"', str(getattr(pages, name)()))


if __name__ == "__main__":
    unittest.main()
