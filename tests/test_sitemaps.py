from __future__ import division

import glob
import os
import math
import random
import unittest
import tempfile
import datetime

import six
from lxml import etree
try:
    from backports import tempfile
except ImportError:
    pass

from paka import sitemaps
from paka.sitemaps import robots


sitemaps.PER_MAP = sitemaps.PER_INDEX = 5


class ContextTestCase(unittest.TestCase):

    def setUp(self):
        self._fs_root = tempfile.TemporaryDirectory()
        self.fs_root = self._fs_root.name
        self.base_url = "http://example.com/sitemaps/"
        self.ctx = sitemaps.Context(
            fs_root=self.fs_root,
            base_url=self.base_url,
        )

    def tearDown(self):
        self._fs_root.cleanup()


def list_maps(fs_root):
    return glob.glob(os.path.join(fs_root, "s*"))


def get_random_changefreq():
    return random.choice(list(sitemaps.Changefreq))


def _make_kwargs(i):
    kwargs = {"path": "/lalala/{}/".format(i)}
    ds = (
        {},
        {"lastmod": datetime.datetime.utcnow()},
        {"changefreq": get_random_changefreq()},
        {"priority": "{:.1f}".format(random.random())},
    )
    r = random.randint(0, 5)
    if r not in {5, 2}:
        for _ in range(r):
            kwargs.update(random.choice(ds))
    return kwargs


def _make_sgvfcfni_test(i):

    def _test(self):
        for j in range(i):
            self.ctx.add(**_make_kwargs(j))
        self.ctx.close()

        maps = list_maps(self.fs_root)
        indexes = glob.glob(os.path.join(self.fs_root, "i*"))

        # Number of maps = number of items / sitemaps.PER_MAP
        self.assertEqual(math.ceil(i / sitemaps.PER_MAP), len(maps))

        # Number of indexes = number of maps / sitemaps.PER_INDEX
        self.assertEqual(
            math.ceil(i / sitemaps.PER_MAP / sitemaps.PER_INDEX),
            len(indexes)
        )

        urls_count = 0
        unique_urls = set([])
        for fs_path in maps:
            urls = self.check_map(fs_path)
            urls_count += len(urls)
            unique_urls = unique_urls.union(set(urls))
        self.assertEqual(urls_count, i)
        self.assertEqual(urls_count, len(unique_urls))

        urls_count = 0
        unique_urls = set([])
        for fs_path in indexes:
            urls = self.check_index(fs_path)
            urls_count += len(urls)
            unique_urls = unique_urls.union(set(urls))
        self.assertEqual(urls_count, len(maps))
        self.assertEqual(urls_count, len(unique_urls))

    return _test


class ItemsTestCaseMeta(type):
    ARBITRARY_NUMBERS_OF_ITEMS = (
        1,
        9,
        123,
        sitemaps.PER_MAP,
        sitemaps.PER_MAP - 1,
        41432,
        77777,
        sitemaps.PER_MAP * sitemaps.PER_INDEX,
        sitemaps.PER_MAP * sitemaps.PER_INDEX + 1,
        sitemaps.PER_MAP * sitemaps.PER_INDEX + 2,
        sitemaps.PER_MAP * sitemaps.PER_INDEX + 3,
        sitemaps.PER_MAP * sitemaps.PER_INDEX + 4,
        sitemaps.PER_MAP * sitemaps.PER_INDEX + 5,
        sitemaps.PER_MAP * sitemaps.PER_INDEX * 2,
        sitemaps.PER_MAP * sitemaps.PER_INDEX * 2 + 1,
        sitemaps.PER_MAP * sitemaps.PER_INDEX * 2 + 2,
        sitemaps.PER_MAP * sitemaps.PER_INDEX * 2 + 3,
        sitemaps.PER_MAP * sitemaps.PER_INDEX * 3,
        sitemaps.PER_MAP * sitemaps.PER_INDEX * 4,
        sitemaps.PER_MAP * sitemaps.PER_INDEX * 5,
        sitemaps.PER_MAP * sitemaps.PER_INDEX * 10,
        sitemaps.PER_MAP * sitemaps.PER_INDEX * 11)

    def __new__(cls, name, bases, attrs):
        for i in cls.ARBITRARY_NUMBERS_OF_ITEMS:
            attrs[
                (
                    "test_should_generate_valid_files_correctly_for_"
                    "{}_items"
                ).format(i)
            ] = _make_sgvfcfni_test(i)
        return super(ItemsTestCaseMeta, cls).__new__(cls, name, bases, attrs)


@six.add_metaclass(ItemsTestCaseMeta)
class ItemsTestCase(ContextTestCase):
    ns = {"s": sitemaps.XMLNS}

    @classmethod
    def setUpClass(cls):
        test_files_dir_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "files")
        with open(os.path.join(test_files_dir_path, "sitemap.xsd")) as f:
            cls.map_schema = etree.XMLSchema(etree.parse(f))
        with open(os.path.join(test_files_dir_path, "siteindex.xsd")) as f:
            cls.index_schema = etree.XMLSchema(etree.parse(f))

    def check_map(self, fs_path):
        tree = etree.parse(fs_path)
        self.assertTrue(self.map_schema.validate(tree))
        return [
            url.find("s:loc", namespaces=self.ns).text
            for url in tree.findall("s:url", namespaces=self.ns)
        ]

    def check_index(self, fs_path):
        tree = etree.parse(fs_path)
        self.assertTrue(self.index_schema.validate(tree))
        return [
            url.find("s:loc", namespaces=self.ns).text
            for url in tree.findall("s:sitemap", namespaces=self.ns)
        ]

    def add_and_parse(self, name, value):
        self.ctx.add("/some/thing/", **{name: value})
        self.ctx.close()
        fs_path = list_maps(self.fs_root)[0]
        return etree.parse(fs_path).findtext(
            "//s:{}".format(name), namespaces=self.ns)

    def add_with_priority_and_parse(self, priority):
        return self.add_and_parse("priority", priority)

    def add_with_changefreq_and_parse(self, changefreq):
        return self.add_and_parse("changefreq", changefreq)

    def test_string_priority(self):
        priority = self.add_with_priority_and_parse("0.3")
        self.assertEqual(priority, "0.3")

    def test_float_priority(self):
        priority = self.add_with_priority_and_parse(.7)
        self.assertEqual(priority, "0.7")

    def test_zero_float_priority(self):
        priority = self.add_with_priority_and_parse(.0)
        self.assertEqual(priority, "0.0")

    def test_zero_int_priority(self):
        priority = self.add_with_priority_and_parse(0)
        self.assertEqual(priority, "0.0")

    def test_one_int_priority(self):
        priority = self.add_with_priority_and_parse(1)
        self.assertEqual(priority, "1.0")

    def test_random_changefreq_member(self):
        random_freq = get_random_changefreq()
        self.assertIn(random_freq, sitemaps.Changefreq)
        parsed = self.add_with_changefreq_and_parse(random_freq)
        self.assertEqual(random_freq.value, parsed)

    def test_str_changefreq(self):
        freq = "sometimes"
        parsed = self.add_with_changefreq_and_parse(freq)
        self.assertEqual(freq, parsed)


class RobotsTestCase(ContextTestCase):

    _l = lambda self, n: "Sitemap: {}i{}.xml".format(self.base_url, n)

    def test_with_single_sitemap_index(self):
        for i in range(sitemaps.PER_MAP):
            self.ctx.add(path="/something/here/{}/".format(i))
        self.ctx.close()

        indexes = glob.glob(os.path.join(self.fs_root, "i*"))
        self.assertEqual(1, len(indexes))

        self.assertEqual(
            list(robots.gen_sitemap_lines(self.ctx)),
            [self._l(1)],
        )

    def test_with_multiple_sitemap_indexes(self):
        desired_number_of_indexes = 3
        for i in range(
            desired_number_of_indexes * sitemaps.PER_INDEX * sitemaps.PER_MAP
        ):
            self.ctx.add(path="/something/here/{}/".format(i))
        self.ctx.close()

        indexes = glob.glob(os.path.join(self.fs_root, "i*"))
        self.assertEqual(desired_number_of_indexes, len(indexes))

        self.assertEqual(
            list(robots.gen_sitemap_lines(self.ctx)),
            [self._l(1), self._l(2), self._l(3)],
        )
