import struct
import zlib

from fastapi.testclient import TestClient

import app as application
from receipts.logos import Logo, Logos


def png(size=32):
    def chunk(kind, body):
        return struct.pack('>I', len(body)) + kind + body + struct.pack('>I', zlib.crc32(kind + body))
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>2I5B', size, size, 8, 2, 0, 0, 0)) + chunk(b'IDAT', zlib.compress((b'\0' + b'\0\xff\0' * size) * size)) + chunk(b'IEND', b'')


def test_unfeatured_issuer_uses_public_assets_and_caches_by_sec_identity():
    calls = []
    def download(url):
        calls.append(url)
        return png()
    service = Logos(None, download=download)
    company = {'ticker': 'PEP', 'cik': 77476}
    first = service.get(company)
    assert first.media_type == 'image/png'
    assert calls == ['https://financialmodelingprep.com/image-stock/PEP.png']
    assert service.get({**company, 'ticker': 'ANOTHER-CLASS'}) is first
    assert len(calls) == 1


def test_second_source_is_used_and_missing_artwork_is_cached_without_inventing_it():
    calls = []
    def download(url):
        calls.append(url)
        return png() if 'companiesmarketcap.com' in url else None
    service = Logos(None, download=download)
    assert service.get({'ticker': 'PEP', 'cik': 77476}).source.endswith('/64/PEP.png')
    assert len(calls) == 2
    missing = Logos(None, download=lambda url: None)
    assert missing.get({'ticker': 'HLSQ', 'cik': 123456}) is None
    assert missing.cache[123456][1] is None


def test_html_svg_tiny_placeholders_and_oversized_images_are_not_served_as_brand_art():
    for body in [b'<html>not an image</html>', b'<svg><script/></svg>', png(1), b'x' * 300_000]:
        service = Logos(None, download=lambda url, body=body: body)
        assert service._image('https://example.com/asset.png') is None


def test_logo_route_rejects_unknown_symbols_without_external_fetch(monkeypatch):
    def unexpected(company):
        raise AssertionError('Unknown company must not reach an external host')
    monkeypatch.setattr(application.logos, 'get', unexpected)
    response = TestClient(application.app).get('/company-logo/NOTREAL123')
    assert response.status_code == 204
    assert response.headers['x-logo-status'] == 'unavailable'


def test_logo_route_serves_cacheable_rasters_with_etags_and_bundled_share_class_marks(monkeypatch):
    logo = Logo(png(), 'image/png', 'https://financialmodelingprep.com/image-stock/PEP.png')
    monkeypatch.setattr(application.logos, 'get', lambda company: logo)
    client = TestClient(application.app)
    response = client.get('/company-logo/PEP')
    assert response.status_code == 200 and response.content == logo.body
    assert response.headers['cache-control'] == 'public, max-age=86400'
    assert client.get('/company-logo/PEP', headers={'If-None-Match': logo.etag}).status_code == 304
    assert client.get('/company-logo/GOOGM').headers['content-type'].startswith('image/')
