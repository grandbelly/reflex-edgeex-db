"""Static render-tree check: no block element inside <p> on any of the six pages.

React logs `In HTML, <p> cannot be a descendant of <p>` (edge re-acceptance of 10095cc, #9) when a
text component wraps another text or a box. Walking the built component tree catches it
without starting the app or a browser."""
import unittest
from reflex_base.components.component import Component
from edgeex_app.pages import scada as pages

PAGES = ["overview", "trend", "alarms", "flow", "communication"]
BLOCK_TAGS = {"Box", "Flex", "Grid", "div", "p", "Table.Root", "Callout.Root"}


def is_paragraph(comp):
    return comp.tag == "p" or (comp.tag == "Text" and str(getattr(comp, "as_", "")) == '"p"')


def kids(comp):
    for value in vars(comp).values():
        for item in value if isinstance(value, (list, tuple)) else [value]:
            if isinstance(item, Component):
                yield item


def nested_blocks(comp, inside=None, path=()):
    path = path + (comp.tag or type(comp).__name__,)
    if inside is not None and (is_paragraph(comp) or comp.tag in BLOCK_TAGS):
        yield " > ".join(path)
    for child in kids(comp):
        yield from nested_blocks(child, comp if is_paragraph(comp) else inside, path)


class NoBlockInsideParagraph(unittest.TestCase):
    def test_detector_finds_known_bad_shape(self):
        import reflex as rx
        self.assertTrue(list(nested_blocks(rx.text("선택 기간 ", rx.text("1")))))
        self.assertFalse(list(nested_blocks(rx.box(rx.text("1")))))

    def test_six_pages_have_no_block_inside_p(self):
        for name in PAGES:
            with self.subTest(page=name):
                self.assertEqual(list(nested_blocks(getattr(pages, name)())), [])


if __name__ == "__main__":
    unittest.main()
