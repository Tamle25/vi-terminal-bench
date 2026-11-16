"""Explicit process-scoped credential loading. No SDK, network or global env mutation."""
import os
import re
from collections.abc import Mapping
from contextlib import contextmanager
from pathlib import Path

VARIABLE = 'OPENAI_API_KEY'
ALLOWED_TARGETS = {'host-agent', 'model-api-client'}
PUBLIC_ENV = {'PATH', 'SystemRoot', 'SYSTEMROOT', 'WINDIR', 'COMSPEC', 'PATHEXT',
              'TEMP', 'TMP', 'TMPDIR', 'LANG', 'LC_ALL', 'TZ', 'PYTHONIOENCODING', 'PYTHONUTF8'}
ERRORS = {'CREDENTIAL_MODE_DISABLED', 'CREDENTIAL_TARGET_DENIED', 'DISPATCH_BLOCKED',
          'CREDENTIAL_SOURCE_UNREADABLE', 'CREDENTIAL_SOURCE_INVALID', 'CREDENTIAL_EMPTY',
          'CREDENTIAL_SCOPE_CLOSED', 'CREDENTIAL_ERROR'}


class CredentialError(ValueError):
    def __init__(self, code):
        self.code = code if code in ERRORS else 'CREDENTIAL_ERROR'
        super().__init__(self.code)


def _check_gate(gate):
    passed = False
    try:
        passed = callable(gate) and gate() is True
    except Exception:
        pass
    if not passed:
        raise CredentialError('DISPATCH_BLOCKED')


def _validate(value):
    if not isinstance(value, str) or not value:
        raise CredentialError('CREDENTIAL_EMPTY')
    # A restricted literal token format; this is not API authentication validation.
    if len(value) > 8192 or not re.fullmatch(r'[A-Za-z0-9_-]+', value):
        raise CredentialError('CREDENTIAL_SOURCE_INVALID')
    return value


def _dotenv(path):
    text = None
    try:
        with Path(path).open('rb') as handle:
            data = handle.read(65537)
        if len(data) <= 65536:
            text = data.decode('utf-8-sig')
    except (OSError, UnicodeError):
        pass
    # Raise outside the except block: no raw Unicode/file exception is chained.
    if text is None:
        raise CredentialError('CREDENTIAL_SOURCE_UNREADABLE')
    found = None
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        match = re.fullmatch(r'OPENAI_API_KEY\s*=\s*(.*)', line)
        if not match or found is not None:
            raise CredentialError('CREDENTIAL_SOURCE_INVALID')
        value = match.group(1)
        if value.startswith(('"', "'")):
            if len(value) < 2 or value[-1] != value[0]:
                raise CredentialError('CREDENTIAL_SOURCE_INVALID')
            value = value[1:-1]
        found = _validate(value)
    if found is None:
        raise CredentialError('CREDENTIAL_EMPTY')
    return found


class ProcessEnvironment(Mapping):
    """Values are available to an explicit subprocess sink; repr/JSON do not dump them."""
    __slots__ = ('_lease', '_public')

    def __init__(self, lease, base):
        self._lease = lease
        self._public = {key: base[key] for key in PUBLIC_ENV if key in base}

    def __getitem__(self, key):
        self._lease._active()
        if key == VARIABLE:
            return self._lease._value
        if key not in self._public:
            raise KeyError('ENVIRONMENT_FIELD_UNAVAILABLE')
        return self._public[key]

    def __iter__(self):
        self._lease._active()
        return iter([*self._public, VARIABLE])

    def __len__(self):
        self._lease._active()
        return len(self._public) + 1

    def __repr__(self):
        return '<ProcessEnvironment redacted>'


class CredentialLease:
    __slots__ = ('_value', '_gate', '_closed', 'source', 'target')

    def __init__(self, value, gate, source, target):
        self._value = value; self._gate = gate; self._closed = False
        self.source = source; self.target = target

    def __repr__(self):
        return '<CredentialLease redacted>'

    def _active(self):
        if self._closed:
            raise CredentialError('CREDENTIAL_SCOPE_CLOSED')
        _check_gate(self._gate)

    def environment(self, base=None):
        self._active()
        return ProcessEnvironment(self, base or {})

    def sdk_key(self):
        """Explicit SDK sink only. Callers must never log the returned string."""
        self._active()
        return self._value

    def metadata(self):
        return {'variable': VARIABLE, 'source': self.source, 'target': self.target,
                'scope_open': not self._closed, 'auth_status': 'unverified'}

    def sanitize(self, payload):
        return sanitize(payload, (self._value,) if not self._closed else ())

    def close(self):
        self._value = None; self._closed = True


@contextmanager
def credential_scope(*, mode, target, gate, dotenv_path=None, environment=None):
    """Binding supplies its live gate callback; this is not an authorization service."""
    if mode != 'runtime':
        raise CredentialError('CREDENTIAL_MODE_DISABLED')
    if target not in ALLOWED_TARGETS:
        raise CredentialError('CREDENTIAL_TARGET_DENIED')
    _check_gate(gate)
    current = os.environ if environment is None else environment
    # Explicitly supplied environment wins, including an empty value which fails closed.
    if VARIABLE in current:
        value = _validate(current[VARIABLE]); source = 'environment'
    else:
        if dotenv_path is None:
            raise CredentialError('CREDENTIAL_EMPTY')
        value = _dotenv(dotenv_path); source = 'dotenv'
    lease = CredentialLease(value, gate, source, target)
    try:
        yield lease
    finally:
        lease.close()


SENSITIVE = {'authorization', 'proxy_authorization', 'api_key', 'apikey', 'access_token',
             'refresh_token', 'password', 'secret', 'client_secret', 'cookie', 'set_cookie'}


def sanitize(payload, secrets=()):
    """Supplementary structured redaction, not permission to log arbitrary SDK objects."""
    if isinstance(payload, (CredentialLease, ProcessEnvironment)):
        return '[REDACTED]'
    if isinstance(payload, Mapping):
        result = {}
        for key, value in payload.items():
            if not isinstance(key, str):
                continue
            normalized = key.lower().replace('-', '_')
            safe_key = sanitize(key, secrets)
            result[safe_key] = '[REDACTED]' if normalized in SENSITIVE or normalized.endswith('_api_key') else sanitize(value, secrets)
        return result
    if isinstance(payload, (tuple, list)):
        return [sanitize(item, secrets) for item in payload]
    if isinstance(payload, str):
        result = payload
        for secret in secrets:
            if isinstance(secret, str) and secret:
                result = result.replace(secret, '[REDACTED]')
        result = re.sub(r'(?i)\bBearer\s+[^\s,;"\']+', 'Bearer [REDACTED]', result)
        result = re.sub(r'(?i)(\b(?:api[_-]?key|access[_-]?token|password|secret)=)[^&\s]+', r'\1[REDACTED]', result)
        return re.sub(r'\bsk-[A-Za-z0-9_-]+', '[REDACTED]', result)
    if payload is None or type(payload) in (bool, int, float):
        return payload
    return '[OMITTED]'


def sanitized_error(exc):
    # Never serialize SDK exception messages, traceback locals, headers or response bodies.
    return {'error': exc.code if isinstance(exc, CredentialError) else 'EXECUTION_ERROR',
            'exception_type': 'CredentialError' if isinstance(exc, CredentialError) else 'Exception'}
