"""Validate source-bundle paths before hashing/copying; never inspect root .env."""
from pathlib import Path


class ArtifactPolicyError(ValueError): pass


def private_name(name):
    name = name.casefold()
    return name == '.env' or name.startswith('.env.') and name != '.env.example'


def validate_public_members(repo, members):
    root = Path(repo).resolve()
    safe = []
    for name in members:
        relative = Path(name)
        if '\\' in str(name) or relative.is_absolute() or '..' in relative.parts or any(private_name(part) for part in relative.parts):
            raise ArtifactPolicyError('PRIVATE_OR_OUTSIDE_SOURCE_INPUT')
        path = root / relative
        if not path.resolve().is_relative_to(root):
            raise ArtifactPolicyError('PRIVATE_OR_OUTSIDE_SOURCE_INPUT')
        chain = [relative, *relative.parents]
        if any((root / part).is_symlink() for part in chain):
            raise ArtifactPolicyError('SYMLINK_SOURCE_INPUT_DENIED')
        if any(private_name(part) for part in path.resolve().relative_to(root).parts):
            raise ArtifactPolicyError('PRIVATE_OR_OUTSIDE_SOURCE_INPUT')
        if path.name.casefold() == '.env.example':
            # A source template may contain comments or empty assignments only.
            text = None
            try:
                text = path.read_text(encoding='utf-8')
            except (OSError, UnicodeError):
                pass
            if text is None:
                raise ArtifactPolicyError('CREDENTIAL_TEMPLATE_UNREADABLE')
            for line in text.splitlines():
                line = line.strip()
                if line and not line.startswith('#') and ('=' not in line or line.split('=', 1)[1].strip()):
                    raise ArtifactPolicyError('NONEMPTY_CREDENTIAL_TEMPLATE_DENIED')
        if not path.is_file():
            raise ArtifactPolicyError('SOURCE_INPUT_MISSING')
        safe.append(relative.as_posix())
    return safe


def validate_native_inputs(repo):
    """Match the existing native-copy allowlist; validate paths before it reads bytes."""
    repo = Path(repo)
    members = ['manifest.jsonl']
    for directory in ['scripts', 'configs', 'tasks', 'prompts']:
        for path in (repo / directory).rglob('*'):
            if path.is_file() and '__pycache__' not in path.parts and path.suffix != '.pyc':
                members.append(path.relative_to(repo).as_posix())
            elif path.is_symlink():
                raise ArtifactPolicyError('SYMLINK_SOURCE_INPUT_DENIED')
    return validate_public_members(repo, members)
