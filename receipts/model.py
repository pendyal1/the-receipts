"""Gemini via Google's REST endpoint. No third-party model/data API billing."""
import json
import os
import subprocess
import threading
import time

import google.auth
import requests
from google.auth.transport.requests import Request
from .config import MODEL, PROJECT


class ModelError(Exception):
    pass


class Gemini:
    def __init__(self):
        self._credentials = None
        self._lock = threading.Lock()
        self._cli_token = None
        self._cli_expiry = 0

    def token(self):
        with self._lock:
            try:
                if self._credentials is None:
                    self._credentials, _ = google.auth.default(scopes=['https://www.googleapis.com/auth/cloud-platform'])
                if not self._credentials.valid:
                    self._credentials.refresh(Request())
                return self._credentials.token
            except Exception:
                # Local development may reuse the user's existing gcloud sign-in.
                # No credentials are logged, written to the repo, or sent to the browser.
                if os.getenv('K_SERVICE'):
                    raise ModelError('Vertex AI runtime credentials are unavailable.') from None
                if time.monotonic() < self._cli_expiry:
                    return self._cli_token
                try:
                    result = subprocess.run(['gcloud', 'auth', 'print-access-token', '--account=ap4839@columbia.edu'],
                                            capture_output=True, text=True, timeout=20, check=True)
                    self._cli_token = result.stdout.strip()
                    self._cli_expiry = time.monotonic() + 1800
                    return self._cli_token
                except Exception:
                    raise ModelError('Refresh GCP sign-in or application-default credentials to enable AI investigations.') from None

    def generate(self, system, payload, *, json_mode=True, timeout=35, schema=None):
        url = f'https://aiplatform.googleapis.com/v1/projects/{PROJECT}/locations/global/publishers/google/models/{MODEL}:generateContent'
        body = {'contents': [{'role': 'user', 'parts': [{'text': payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False)}]}],
                'generationConfig': {'temperature': .15, 'maxOutputTokens': 5500}}
        if system:
            body['systemInstruction'] = {'parts': [{'text': system}]}
        if json_mode:
            body['generationConfig']['responseMimeType'] = 'application/json'
        if schema:
            body['generationConfig']['responseSchema'] = schema
        try:
            response = requests.post(url, json=body, headers={'Authorization': f'Bearer {self.token()}'}, timeout=timeout)
            if response.status_code != 200:
                raise ModelError(f'Vertex AI returned HTTP {response.status_code}. Check model access, quota and runtime permissions.')
            data = response.json()
            parts = (data.get('candidates') or [{}])[0].get('content', {}).get('parts', [])
            text = ''.join(part.get('text', '') for part in parts if not part.get('thought'))
            if not text:
                raise ModelError('The model returned no answer.')
            if not json_mode:
                return text
            value = json.loads(text)
            if not isinstance(value, dict):
                raise ModelError('The model returned an invalid structured answer.')
            return value
        except ModelError:
            raise
        except (requests.RequestException, ValueError, KeyError) as exc:
            raise ModelError(f'The model request did not complete ({type(exc).__name__}).') from None
