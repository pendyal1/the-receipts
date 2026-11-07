"""Bounded, keyless brand-image lookup for any issuer in our SEC directory.

Logo assets identify current issuers; they are never financial evidence. Only
fixed public image hosts are contacted. Missing artwork remains missing.
"""
import hashlib
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from urllib.parse import quote

import httpx

from .config import ROOT
from .sources import bundled_company_directory


class LogoBusy(Exception):
    pass


@dataclass(frozen=True)
class Logo:
    body: bytes
    media_type: str
    source: str

    @property
    def etag(self):
        return '"' + hashlib.sha256(self.body).hexdigest() + '"'


class Logos:
    MAX_BYTES = 256_000
    MAX_CACHE_BYTES = 12_000_000

    def __init__(self, sources, download=None, clock=time.monotonic):
        self.sources = sources
        self.download = download or self._download
        self.clock = clock
        self.cache = OrderedDict()
        self.lock = threading.RLock()
        self.slots = threading.BoundedSemaphore(4)
        self.issuer_locks = [threading.Lock() for _ in range(32)]

    @staticmethod
    def _download(url):
        # No user-controlled destinations, redirect following or SVG execution.
        with httpx.Client(timeout=3, follow_redirects=False) as client:
            with client.stream('GET', url, headers={'User-Agent': 'TheReceipts/1.0 company-brand lookup'}) as response:
                if response.status_code != 200:
                    return None
                body = bytearray()
                for chunk in response.iter_bytes():
                    body.extend(chunk)
                    if len(body) > Logos.MAX_BYTES:
                        return None
                return bytes(body)

    def _image(self, url):
        try:
            body = self.download(url)
        except (httpx.HTTPError, OSError):
            return None
        if not body or len(body) > self.MAX_BYTES:
            return None
        if body.startswith(b'\x89PNG\r\n\x1a\n'):
            if len(body)<24:
                return None
            width,height=int.from_bytes(body[16:20],'big'),int.from_bytes(body[20:24],'big')
            if min(width,height)<8 or width*height>4_000_000:
                return None
            media = 'image/png'
        elif body.startswith(b'\xff\xd8\xff'):
            media = 'image/jpeg'
        elif body.startswith(b'RIFF') and body[8:12] == b'WEBP':
            media = 'image/webp'
        else:
            return None
        return Logo(body, media, url)

    def local_asset(self, company):
        directory = bundled_company_directory()
        for entry in [company, *(c for c in directory.values() if c['cik'] == company['cik'])]:
            asset = entry.get('logo')
            if asset and asset.startswith('/static/logos/'):
                path = ROOT / asset.lstrip('/')
                if path.is_file():
                    return path
        return None

    def get(self, company):
        key = company['cik']
        with self.issuer_locks[key % len(self.issuer_locks)]:
            with self.lock:
                cached = self.cache.get(key)
                if cached and cached[0] > self.clock():
                    self.cache.move_to_end(key)
                    return cached[1]
            if not self.slots.acquire(timeout=1):
                raise LogoBusy()
            try:
                logo = self._find(company)
            finally:
                self.slots.release()
            with self.lock:
                self.cache[key] = (self.clock() + (86400 if logo else 900), logo)
                self.cache.move_to_end(key)
                while len(self.cache) > 512 or sum(len(item[1].body) for item in self.cache.values() if item[1]) > self.MAX_CACHE_BYTES:
                    self.cache.popitem(last=False)
            return logo

    def _find(self, company):
        # Share classes, units and warrants may use a parent issuer's brand.
        related = [company['ticker'], *(c['ticker'] for c in bundled_company_directory().values() if c['cik'] == company['cik'])]
        deadline = self.clock() + 9
        for ticker in list(dict.fromkeys(related))[:3]:
            symbol = quote(ticker, safe='')
            for url in [f'https://financialmodelingprep.com/image-stock/{symbol}.png',
                        f'https://companiesmarketcap.com/img/company-logos/64/{symbol}.png']:
                if self.clock() >= deadline:
                    return None
                logo = self._image(url)
                if logo:
                    return logo
        return None
