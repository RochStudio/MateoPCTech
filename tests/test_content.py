"""Regression checks against the pre-redesign content, without network writes."""
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
import importlib.util
import json
import re
import tempfile
import unittest
from unittest.mock import patch
from contextlib import redirect_stdout
from io import StringIO

ROOT = Path(__file__).resolve().parent.parent
ORIGINAL = json.loads((ROOT / 'tests/fixtures/original-pages.json').read_text(encoding='utf-8'))


class PageContent(HTMLParser):
    def __init__(self, source):
        super().__init__()
        self.in_main = False
        self.in_item = False
        self.text = []
        self.links = []
        self.items = []
        self.item_text = []
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'main':
            self.in_main = True
        if tag == 'a':
            self.links.append(attrs.get('href'))
        if tag == 'li' and self.in_main:
            self.in_item = True
            self.item_text = []

    def handle_endtag(self, tag):
        if tag == 'main':
            self.in_main = False
        if tag == 'li' and self.in_item:
            self.items.append(' '.join(' '.join(self.item_text).split()))
            self.in_item = False

    def handle_data(self, data):
        if self.in_main:
            self.text.append(data)
        if self.in_item:
            self.item_text.append(data)

    @property
    def words(self):
        return Counter(re.findall(r'\w+', ' '.join(self.text).lower()))


def without_generated_regions(source):
    # Remove whole matched regions, not individual titles/URLs that may also
    # occur in immutable copy elsewhere on the page.
    pattern = r'<!-- (?P<marker>LATEST|(?:LATEST3|POPULAR3):[\w-]+):START -->.*?<!-- (?P=marker):END -->'
    return re.sub(pattern, '', source, flags=re.S)


def generated_sections():
    spec = importlib.util.spec_from_file_location('update_videos', ROOT / 'scripts/update_videos.py')
    updater = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(updater)
    data = json.loads((ROOT / 'data/videos.json').read_text(encoding='utf-8'))
    # Match main(): JSON order is newest first; popularity is a stable view sort.
    regions = [('index', 'LATEST', [updater.make_card(data[c['key']][0], f"From {c['label']}")
                                   for c in updater.CHANNELS if data.get(c['key'])])]
    for channel in updater.CHANNELS:
        key = channel['key']
        regions += [
            ('youtube', 'LATEST3:' + key, [updater.make_card(v, eager=(key == updater.CHANNELS[0]['key'])) for v in data[key][:3]]),
            ('youtube', 'POPULAR3:' + key, [updater.make_card(v, updater.format_views(v.get('views', 0)), eager=False)
                                          for v in sorted(data[key], key=lambda v: v.get('views', 0), reverse=True)[:3]]),
        ]
    return updater, regions


class ContentTests(unittest.TestCase):
    def test_every_original_word_and_link_is_retained_on_each_page(self):
        for name, source in ORIGINAL.items():
            with self.subTest(page=name):
                old = PageContent(without_generated_regions(source))
                new = PageContent(without_generated_regions((ROOT / (name + '.html')).read_text(encoding='utf-8')))
                self.assertFalse(old.words - new.words)
                self.assertFalse(set(old.links) - set(new.links))

    def test_recommendations_and_requirement_lists_keep_their_order(self):
        for name, source in ORIGINAL.items():
            with self.subTest(page=name):
                old = PageContent(source)
                new = PageContent((ROOT / (name + '.html')).read_text(encoding='utf-8'))
                self.assertEqual(old.items, new.items)

    def test_existing_seo_metadata_and_structured_data_are_unchanged(self):
        pattern = r'<meta\b[^>]+>|<link rel="canonical"[^>]+>|<script type="application/ld\+json">.*?</script>'
        for name, source in ORIGINAL.items():
            with self.subTest(page=name):
                new = (ROOT / (name + '.html')).read_text(encoding='utf-8')
                self.assertEqual(re.findall(pattern, source, re.S), re.findall(pattern, new, re.S))

    def test_generated_video_regions_match_current_data(self):
        _, regions = generated_sections()
        for name in ORIGINAL:
            with self.subTest(page=name):
                source = (ROOT / (name + '.html')).read_text(encoding='utf-8')
                expected_markers = [(marker, end) for page, marker, _ in regions if page == name for end in ['START', 'END']]
                actual_markers = re.findall(r'<!-- (LATEST|(?:LATEST3|POPULAR3):[\w-]+):(START|END) -->', source)
                self.assertCountEqual(actual_markers, expected_markers)
        for name, marker, cards in regions:
            with self.subTest(page=name, marker=marker):
                source = (ROOT / (name + '.html')).read_text(encoding='utf-8')
                pattern = re.escape(f'<!-- {marker}:START -->') + r'(.*?)' + re.escape(f'<!-- {marker}:END -->')
                match = re.search(pattern, source, re.S)
                self.assertIsNotNone(match)
                expected = '<div class="video-grid">\n' + '\n'.join(cards) + '\n</div>'
                # Ignore formatting whitespace, but check every card, its order,
                # title, both links, image attributes, channel label and view count.
                self.assertEqual(' '.join(match[1].split()), ' '.join(expected.split()))

    def test_video_updater_preserves_layout_outside_each_generated_region(self):
        updater, regions = generated_sections()
        with tempfile.TemporaryDirectory() as temp:
            for name, marker, cards in regions:
                with self.subTest(marker=marker):
                    source = (ROOT / (name + '.html')).read_text(encoding='utf-8')
                    target = Path(temp) / (name + '.html')
                    target.write_text(source, encoding='utf-8')
                    updater.rebuild_section(target, marker, cards)
                    result = target.read_text(encoding='utf-8')
                    pattern = re.escape(f'<!-- {marker}:START -->') + r'.*?' + re.escape(f'<!-- {marker}:END -->')
                    self.assertEqual(re.sub(pattern, '', source, flags=re.S), re.sub(pattern, '', result, flags=re.S))
                    self.assertFalse(updater.rebuild_section(target, marker, cards))
                    self.assertEqual(result.count(f'<!-- {marker}:START -->'), 1)
                    self.assertEqual(result.count(f'<!-- {marker}:END -->'), 1)


class GeneratedContentRegressionTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        for relative in [*(name + '.html' for name in ORIGINAL), 'data/videos.json', 'scripts/update_videos.py']:
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text((ROOT / relative).read_text(encoding='utf-8'), encoding='utf-8')
        self.data = json.loads((self.root / 'data/videos.json').read_text(encoding='utf-8'))
        spec = importlib.util.spec_from_file_location('fixture_updater', self.root / 'scripts/update_videos.py')
        self.updater = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.updater)

    def regenerate(self):
        (self.root / 'data/videos.json').write_text(json.dumps(self.data), encoding='utf-8')
        # Exercise actual selection/rendering, but never fetch RSS or touch live files.
        with patch.object(self.updater, 'fetch_feed', return_value=[]), redirect_stdout(StringIO()):
            self.updater.main()

    def content_result(self):
        suite = unittest.TestLoader().loadTestsFromTestCase(ContentTests)
        result = unittest.TestResult()
        with patch.dict(globals(), ROOT=self.root):
            suite.run(result)
        self.assertGreater(result.testsRun, 0)
        self.assertEqual(result.errors, [])
        return result

    def assert_generated_tampering_rejected(self, tamper):
        self.regenerate()
        pattern = r'<!-- (?P<marker>LATEST|(?:LATEST3|POPULAR3):[\w-]+):START -->.*?<!-- (?P=marker):END -->'
        for name in ['index', 'youtube']:
            target = self.root / (name + '.html')
            source = target.read_text(encoding='utf-8')
            for match in re.finditer(pattern, source, re.S):
                with self.subTest(page=name, marker=match['marker']):
                    changed = tamper(match.group())
                    self.assertNotEqual(changed, match.group())
                    target.write_text(source[:match.start()] + changed + source[match.end():], encoding='utf-8')
                    try:
                        result = self.content_result()
                        self.assertTrue(result.failures, 'Generated data/HTML disagreement was accepted')
                        self.assertTrue(all('test_generated_video_regions_match_current_data' in test.id()
                                            for test, _ in result.failures), result.failures)
                    finally:
                        target.write_text(source, encoding='utf-8')

    def test_tampered_generated_title_is_rejected(self):
        self.assert_generated_tampering_rejected(lambda region: re.sub(
            r'(<div class="info">\s*<a\b[^>]*>)[^<]+', r'\g<1>Tampered title', region, count=1))

    def test_tampered_generated_link_is_rejected(self):
        self.assert_generated_tampering_rejected(lambda region: re.sub(
            r'(<div class="info">\s*<a href=")[^"]+', r'\g<1>https://example.invalid/tampered', region, count=1))

    def test_surrounding_copy_and_links_are_still_protected(self):
        target = self.root / 'youtube.html'
        source = target.read_text(encoding='utf-8')
        for original, replacement in [
            ('Overclocking guides, BIOS tutorials, and benchmarks.', 'Changed introduction.'),
            ('https://www.youtube.com/@MateoPcTech', 'https://example.invalid/changed-channel'),
        ]:
            with self.subTest(content=original):
                self.assertIn(original, source)
                target.write_text(source.replace(original, replacement), encoding='utf-8')
                result = self.content_result()
                self.assertTrue(result.failures, 'Surrounding immutable content change was accepted')
                self.assertTrue(all('test_every_original_word_and_link_is_retained_on_each_page' in test.id()
                                    for test, _ in result.failures), result.failures)

    def test_agreeing_view_count_update_is_accepted(self):
        for videos in self.data.values():
            videos[-1]['views'] = max(v.get('views', 0) for v in videos) + 100_000
        self.regenerate()
        result = self.content_result()
        self.assertTrue(result.wasSuccessful(), result.failures)

    def test_agreeing_new_latest_video_is_accepted(self):
        for index, videos in enumerate(self.data.values()):
            videos.insert(0, {'id': f'newVideo00{index}', 'title': f'New latest {index}: RAM & GPU <comparison>', 'views': 1})
        self.regenerate()
        result = self.content_result()
        self.assertTrue(result.wasSuccessful(), result.failures)


if __name__ == '__main__':
    unittest.main()
