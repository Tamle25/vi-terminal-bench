import json
import os
import subprocess
import sys
import tarfile
import tempfile
import traceback
import unittest
from collections.abc import Mapping
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scoped_credentials import VARIABLE, CredentialError, credential_scope, sanitize, sanitized_error
from credential_artifacts import ArtifactPolicyError, validate_public_members, validate_native_inputs
from run_native_offline import inputs
from credential_status import status

FAKE = 'sk-fixture-not-a-real-credential-123456'


class ForbiddenEnvironment(Mapping):
    def __iter__(self): raise AssertionError('Do not read environment')
    def __len__(self): raise AssertionError('Do not read environment')
    def __getitem__(self, key): raise AssertionError('Do not read environment')


class CredentialTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.dotenv = self.root / '.env'
        self.dotenv.write_text(VARIABLE + '=' + FAKE + '\n', encoding='utf-8')

    def tearDown(self): self.temp.cleanup()

    def scope(self, **changes):
        args = dict(mode='runtime', target='model-api-client', gate=lambda: True,
                    dotenv_path=self.dotenv, environment={})
        args.update(changes)
        return credential_scope(**args)

    def test_preview_and_dry_run_never_read_sources(self):
        for mode in ['preview', 'dry-run', 'model']:
            with patch.object(Path, 'open', side_effect=AssertionError('No file reads')):
                with self.assertRaisesRegex(CredentialError, 'MODE_DISABLED'):
                    with self.scope(mode=mode, environment=ForbiddenEnvironment()): pass

    def test_denied_targets_never_read_sources(self):
        for target in ['verifier', 'task', 'docker-build', 'container-agent']:
            with patch.object(Path, 'open', side_effect=AssertionError('No file reads')):
                with self.assertRaisesRegex(CredentialError, 'TARGET_DENIED'):
                    with self.scope(target=target, environment=ForbiddenEnvironment()): pass

    def test_failed_gate_before_environment_or_file(self):
        for gate in [None, lambda: False, lambda: {'ready': True}]:
            with patch.object(Path, 'open', side_effect=AssertionError('No file reads')):
                with self.assertRaisesRegex(CredentialError, 'DISPATCH_BLOCKED'):
                    with self.scope(gate=gate, environment=ForbiddenEnvironment()): pass

    def test_gate_exception_message_is_not_chained_or_disclosed(self):
        def gate(): raise RuntimeError(FAKE)
        try:
            with self.scope(gate=gate): pass
        except CredentialError as exc:
            self.assertNotIn(FAKE, ''.join(traceback.format_exception(exc)))
            self.assertIsNone(exc.__context__)
        else: self.fail('Gate exception must block')

    def test_explicit_environment_precedes_dotenv_without_reading_it(self):
        with patch.object(Path, 'open', side_effect=AssertionError('No fallback file read')):
            with self.scope(environment={VARIABLE: 'fixture-environment-value'}) as lease:
                self.assertEqual(lease.sdk_key(), 'fixture-environment-value')
                self.assertEqual(lease.metadata()['source'], 'environment')

    def test_empty_environment_does_not_fall_back(self):
        with patch.object(Path, 'open', side_effect=AssertionError('No fallback file read')):
            with self.assertRaisesRegex(CredentialError, 'CREDENTIAL_EMPTY'):
                with self.scope(environment={VARIABLE: ''}): pass

    def test_utf8_bom_crlf_quotes_and_vietnamese_path(self):
        path = self.root / 'cấu hình có dấu.env'
        for quote in ['', '"', "'"]:
            path.write_bytes(('\ufeff# fixture\r\nOPENAI_API_KEY=' + quote + FAKE + quote + '\r\n').encode('utf-8'))
            with self.scope(dotenv_path=path) as lease:
                self.assertEqual(lease.sdk_key(), FAKE)

    def test_restricted_literal_format_rejects_shell_and_duplicate_entries(self):
        marker = self.root / 'must-not-exist'
        contents = [VARIABLE + '=$(touch ' + str(marker) + ')',
                    VARIABLE + '=' + FAKE + '\n' + VARIABLE + '=' + FAKE,
                    'export ' + VARIABLE + '=' + FAKE,
                    'OTHER_SECRET=' + FAKE, VARIABLE + '=a;b', VARIABLE + '=\"unclosed',
                    VARIABLE + '=space value', VARIABLE + '=']
        for text in contents:
            self.dotenv.write_text(text, encoding='utf-8')
            with self.assertRaises(CredentialError) as error:
                with self.scope(): pass
            self.assertNotIn(FAKE, str(error.exception))
        self.assertFalse(marker.exists())

    def test_missing_invalid_encoding_and_oversized_source_safe_errors(self):
        for content in [b'\xff' + FAKE.encode(), b'a' * 65537]:
            self.dotenv.write_bytes(content)
            try:
                with self.scope(): pass
            except CredentialError as exc:
                self.assertNotIn(FAKE, ''.join(traceback.format_exception(exc)))
                self.assertIsNone(exc.__context__)
            else: self.fail('Invalid source accepted')
        self.dotenv.unlink()
        with self.assertRaises(CredentialError):
            with self.scope(): pass

    def test_global_environment_is_not_modified(self):
        fake_environment = {VARIABLE: FAKE, 'OTHER_SECRET': 'fixture-other-secret'}
        before = dict(fake_environment)
        with patch('scoped_credentials.os.environ', fake_environment):
            with credential_scope(mode='runtime', target='host-agent', gate=lambda: True) as lease:
                self.assertEqual(lease.sdk_key(), FAKE)
                self.assertEqual(fake_environment, before)
        self.assertEqual(fake_environment, before)

    def test_private_repr_and_json_do_not_disclose_value(self):
        with self.scope() as lease:
            env = lease.environment({'PATH': 'fixture-path'})
            for obj in [lease, env]:
                self.assertNotIn(FAKE, str(obj))
                self.assertNotIn(FAKE, repr(obj))
                with self.assertRaises(TypeError): json.dumps(obj)
            self.assertNotIn(FAKE, json.dumps(lease.metadata()))
            self.assertNotIn('length', lease.metadata())

    def test_close_revokes_future_access_even_after_exception(self):
        lease = None; env = None
        with self.assertRaises(RuntimeError):
            with self.scope() as lease:
                env = lease.environment()
                raise RuntimeError('fixture application failure')
        with self.assertRaisesRegex(CredentialError, 'SCOPE_CLOSED'): lease.sdk_key()
        with self.assertRaisesRegex(CredentialError, 'SCOPE_CLOSED'): env[VARIABLE]

    def test_gate_rechecked_before_credential_access(self):
        enabled = [True]
        with self.scope(gate=lambda: enabled[0]) as lease:
            env = lease.environment()
            enabled[0] = False
            with self.assertRaisesRegex(CredentialError, 'DISPATCH_BLOCKED'): env[VARIABLE]
            self.assertNotIn(FAKE, json.dumps(lease.sanitize({'body': FAKE})))

    def test_only_allowlisted_public_fields_and_key_reach_child(self):
        with self.scope() as lease:
            env = lease.environment({'PATH': os.defpath, 'OTHER_SECRET': 'fixture-other', 'OPENAI_ORG_ID': 'fixture-org'})
            code = 'import os,json;print(json.dumps({"key_present":bool(os.environ.get("OPENAI_API_KEY")),"other_present":"OTHER_SECRET" in os.environ,"org_present":"OPENAI_ORG_ID" in os.environ}))'
            child = subprocess.run([sys.executable, '-c', code], env=env, capture_output=True, text=True, timeout=10)
            self.assertEqual(child.returncode, 0, child.stderr)
            self.assertEqual(json.loads(child.stdout), {'key_present': True, 'other_present': False, 'org_present': False})
            self.assertNotIn(FAKE, child.stdout + child.stderr)

    def test_structured_and_string_redaction(self):
        opaque = 'fixtureOpaqueSecretValue'
        payload = {'Authorization': 'Bearer ' + opaque, 'nested': [{'OPENAI_API_KEY': FAKE}],
                   'body': 'sent=' + opaque + ' https://provider.invalid?api_key=unknown&safe=yes',
                   'unknown_token': FAKE, 'credential_env_name': VARIABLE}
        safe = json.dumps(sanitize(payload, [opaque]))
        self.assertNotIn(opaque, safe); self.assertNotIn(FAKE, safe)
        self.assertNotIn('api_key=unknown', safe)
        self.assertIn(VARIABLE, safe)

    def test_private_objects_are_redacted_without_reading_values(self):
        with self.scope() as lease:
            env = lease.environment()
            self.assertEqual(sanitize({'lease': lease, 'environment': env}), {'lease': '[REDACTED]', 'environment': '[REDACTED]'})

    def test_error_reports_never_serialize_sdk_exception_messages(self):
        class Unsafe(Exception):
            def __str__(self): raise AssertionError('Do not inspect SDK error text')
        self.assertEqual(sanitized_error(Unsafe(FAKE))['error'], 'EXECUTION_ERROR')
        self.assertNotIn(FAKE, json.dumps(sanitized_error(CredentialError(FAKE))))


class ArtifactTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.root = Path(self.temp.name)
        for folder in ['scripts', 'configs', 'tasks', 'prompts']: (self.root / folder).mkdir()
        (self.root / 'manifest.jsonl').write_text('', encoding='utf-8')
        (self.root / 'scripts/public.py').write_text('print("public fixture")\n', encoding='utf-8')
        (self.root / '.env').write_text(VARIABLE + '=' + FAKE, encoding='utf-8')

    def tearDown(self): self.temp.cleanup()

    def test_root_secret_excluded_before_native_hashing_or_copy(self):
        safe = validate_native_inputs(self.root)
        hashed = inputs(self.root)
        self.assertNotIn('.env', safe); self.assertNotIn('.env', hashed)
        self.assertEqual(set(safe), set(hashed))

    def test_metadata_status_does_not_read_credential_values(self):
        def git_metadata(command, **kwargs):
            return subprocess.CompletedProcess(command, 0 if 'check-ignore' in command else 1)
        with patch('credential_status.subprocess.run', side_effect=git_metadata), patch.object(Path, 'open', side_effect=AssertionError('Metadata must not read file values')):
            report = status(self.root)
        self.assertTrue(report['file_present']); self.assertTrue(report['git_ignored'])
        self.assertFalse(report['credential_value_read'])
        self.assertNotIn(FAKE, json.dumps(report))

    def test_nested_dotenv_and_case_variants_are_rejected(self):
        for filename in ['.env', '.ENV', '.env.production', '.env.backup']:
            path = self.root / 'configs' / filename
            path.write_text(VARIABLE + '=' + FAKE, encoding='utf-8')
            with self.assertRaises(ArtifactPolicyError): validate_native_inputs(self.root)
            path.unlink()

    def test_explicit_secret_outside_and_nonportable_paths_rejected(self):
        for name in ['.env', '../outside', str(self.root / '.env'), 'configs\\.env']:
            with self.assertRaises(ArtifactPolicyError): validate_public_members(self.root, [name])

    def test_empty_example_allowed_but_nonempty_example_rejected(self):
        path = self.root / '.env.example'
        path.write_text('# fixture\nOPENAI_API_KEY=\n', encoding='utf-8')
        self.assertEqual(validate_public_members(self.root, ['.env.example']), ['.env.example'])
        path.write_text(VARIABLE + '=' + FAKE, encoding='utf-8')
        with self.assertRaises(ArtifactPolicyError): validate_public_members(self.root, ['.env.example'])

    @unittest.skipUnless(os.name == 'posix', 'Linux source symlink policy')
    def test_secret_symlink_is_rejected(self):
        (self.root / 'scripts/alias.py').symlink_to(self.root / '.env')
        with self.assertRaises(ArtifactPolicyError): validate_native_inputs(self.root)

    def test_archive_of_validated_inputs_contains_no_secret(self):
        path = self.root / 'bundle.tar.gz'
        names = validate_native_inputs(self.root)
        with tarfile.open(path, 'w:gz') as handle:
            for name in names: handle.add(self.root / name, arcname=name)
        with tarfile.open(path, 'r:gz') as handle:
            self.assertNotIn('.env', handle.getnames())
            for member in handle.getmembers():
                self.assertNotIn(FAKE.encode(), handle.extractfile(member).read())


if __name__ == '__main__': unittest.main()
