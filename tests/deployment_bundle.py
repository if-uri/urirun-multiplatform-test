from __future__ import annotations

import hashlib
import json
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ARTIFACT_KIND_BY_SUFFIX = {
    ".whl": ("wheel", "python-any"),
    ".exe": ("windows-exe", "windows"),
    ".deb": ("linux-deb", "linux"),
    ".rpm": ("linux-rpm", "linux"),
    ".pkg": ("macos-pkg", "macos"),
    ".app": ("macos-app", "macos"),
    ".zip": ("archive", "unknown"),
}

FUTURE_PLATFORM_ARTIFACTS = [
    {"kind": "windows-exe", "platform": "windows", "status": "EXTERNAL BLOCKER"},
    {"kind": "linux-deb", "platform": "linux", "status": "EXTERNAL BLOCKER"},
    {"kind": "linux-rpm", "platform": "linux", "status": "EXTERNAL BLOCKER"},
    {"kind": "macos-pkg", "platform": "macos", "status": "EXTERNAL BLOCKER"},
    {"kind": "macos-app", "platform": "macos", "status": "EXTERNAL BLOCKER"},
]


@dataclass(frozen=True)
class ArtifactRecord:
    name: str
    path: str
    size: int
    sha256: str
    kind: str
    platform: str
    status: str = "built"
    url: str | None = None

    def as_manifest_item(self) -> dict[str, Any]:
        item = {
            "name": self.name,
            "path": self.path,
            "size": self.size,
            "sha256": self.sha256,
            "kind": self.kind,
            "platform": self.platform,
            "status": self.status,
        }
        if self.url:
            item["url"] = self.url
        return item


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def classify_artifact(path: Path) -> tuple[str, str]:
    if path.name.endswith(".tar.gz"):
        return "sdist", "source"
    return ARTIFACT_KIND_BY_SUFFIX.get(path.suffix.lower(), (path.suffix.lower().lstrip(".") or "file", "unknown"))


def artifact_record(path: Path, *, status: str = "built", url: str | None = None) -> ArtifactRecord:
    kind, platform = classify_artifact(path)
    return ArtifactRecord(
        name=path.name,
        path=str(path),
        size=path.stat().st_size,
        sha256=sha256_file(path),
        kind=kind,
        platform=platform,
        status=status,
        url=url,
    )


def discover_artifacts(artifact_dir: Path) -> list[ArtifactRecord]:
    records: list[ArtifactRecord] = []
    for path in sorted(artifact_dir.glob("urirun-*")):
        if path.is_file() and path.name != "manifest.json":
            records.append(artifact_record(path))
    return records


def build_manifest(
    *,
    product: str,
    version: str | None,
    repo_url: str | None,
    ref: str | None,
    revision: str | None,
    artifacts: list[ArtifactRecord],
) -> dict[str, Any]:
    checksum_map = {item.name: item.sha256 for item in artifacts}
    present_kinds = {item.kind for item in artifacts}
    future = [item for item in FUTURE_PLATFORM_ARTIFACTS if item["kind"] not in present_kinds]
    return {
        "product": product,
        "version": version,
        "repo_url": repo_url,
        "ref": ref,
        "revision": revision,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "artifacts": [item.as_manifest_item() for item in artifacts],
        "checksums": checksum_map,
        "future_artifacts": future,
        "integration": {
            "get_urirun_com": {
                "manifest_path": "/manifest.json",
                "checksums_path": "/checksums/SHA256SUMS",
                "artifact_url_template": "/artifacts/{name}",
                "status": "PARTIAL",
            }
        },
    }


def write_sha256sums(bundle_dir: Path, artifacts: list[ArtifactRecord]) -> Path:
    checksums_dir = bundle_dir / "checksums"
    checksums_dir.mkdir(parents=True, exist_ok=True)
    lines = [f"{item.sha256}  artifacts/{item.name}" for item in sorted(artifacts, key=lambda item: item.name)]
    path = checksums_dir / "SHA256SUMS"
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return path


def parse_sha256sums(path: Path) -> dict[str, str]:
    checksums: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        checksum, name = line.split(None, 1)
        checksums[name.strip()] = checksum
    return checksums


def validate_sha256sums(bundle_dir: Path) -> list[str]:
    problems: list[str] = []
    sums = parse_sha256sums(bundle_dir / "checksums" / "SHA256SUMS")
    for rel_path, expected in sums.items():
        path = bundle_dir / rel_path
        if not path.exists():
            problems.append(f"missing checksum target: {rel_path}")
            continue
        actual = sha256_file(path)
        if actual != expected:
            problems.append(f"checksum mismatch: {rel_path}")
    return problems


def validate_manifest(manifest: dict[str, Any]) -> list[str]:
    required = ["product", "version", "repo_url", "ref", "revision", "generated_at", "artifacts", "checksums"]
    problems = [f"missing manifest field: {name}" for name in required if name not in manifest]
    for index, artifact in enumerate(manifest.get("artifacts", [])):
        for field in ["name", "size", "sha256", "kind", "platform", "status"]:
            if field not in artifact:
                problems.append(f"artifact[{index}] missing field: {field}")
    return problems


def create_deployment_bundle(
    *,
    artifact_dir: Path,
    bundle_dir: Path,
    manifest: dict[str, Any],
    artifacts: list[ArtifactRecord],
) -> dict[str, Any]:
    if bundle_dir.exists():
        shutil.rmtree(bundle_dir)
    (bundle_dir / "artifacts").mkdir(parents=True, exist_ok=True)
    (bundle_dir / "site").mkdir(parents=True, exist_ok=True)
    copied: list[ArtifactRecord] = []
    for item in artifacts:
        source = Path(item.path)
        target = bundle_dir / "artifacts" / item.name
        shutil.copy2(source, target)
        copied.append(artifact_record(target, status=item.status, url=f"/artifacts/{item.name}"))
    bundle_manifest = {**manifest, "artifacts": [item.as_manifest_item() for item in copied], "checksums": {item.name: item.sha256 for item in copied}}
    (bundle_dir / "manifest.json").write_text(json.dumps(bundle_manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    write_sha256sums(bundle_dir, copied)
    links = "\n".join(f'<li><a href="../artifacts/{item.name}">{item.name}</a></li>' for item in copied)
    (bundle_dir / "site" / "index.html").write_text(
        "<!doctype html><title>urirun deployment bundle</title>"
        "<h1>urirun deployment bundle</h1>"
        '<p><a href="../manifest.json">manifest.json</a></p>'
        '<p><a href="../checksums/SHA256SUMS">SHA256SUMS</a></p>'
        f"<ul>{links}</ul>",
        encoding="utf-8",
    )
    report = validate_bundle(bundle_dir)
    report_path = bundle_dir / "deployment-report.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return report


def validate_bundle(bundle_dir: Path) -> dict[str, Any]:
    required_paths = [
        "manifest.json",
        "artifacts",
        "checksums/SHA256SUMS",
        "site/index.html",
    ]
    problems = [f"missing bundle path: {rel}" for rel in required_paths if not (bundle_dir / rel).exists()]
    manifest: dict[str, Any] = {}
    manifest_path = bundle_dir / "manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        problems.extend(validate_manifest(manifest))
    if (bundle_dir / "checksums" / "SHA256SUMS").exists():
        problems.extend(validate_sha256sums(bundle_dir))
    promotion_candidate = not problems and bool(manifest.get("artifacts"))
    return {
        "bundle_dir": str(bundle_dir),
        "status": "DONE" if promotion_candidate else "PARTIAL",
        "promotion_candidate": promotion_candidate,
        "problems": problems,
        "recommendation": "Promote only from a trusted CI/CD job with signing and deployment credentials." if promotion_candidate else "Fix bundle validation problems before promotion.",
    }


def diff_manifests(local: dict[str, Any], production: dict[str, Any]) -> dict[str, Any]:
    local_artifacts = {item.get("name"): item for item in local.get("artifacts", [])}
    production_artifacts = {item.get("name"): item for item in production.get("artifacts", [])}
    local_names = set(local_artifacts)
    production_names = set(production_artifacts)
    checksum_diffs = []
    for name in sorted(local_names & production_names):
        if local_artifacts[name].get("sha256") != production_artifacts[name].get("sha256"):
            checksum_diffs.append(name)
    return {
        "version": {"local": local.get("version"), "production": production.get("version"), "matches": local.get("version") == production.get("version")},
        "ref": {"local": local.get("ref"), "production": production.get("ref"), "matches": local.get("ref") == production.get("ref")},
        "revision": {"local": local.get("revision"), "production": production.get("revision"), "matches": local.get("revision") == production.get("revision")},
        "missing_in_production": sorted(local_names - production_names),
        "missing_locally": sorted(production_names - local_names),
        "checksum_differences": checksum_diffs,
    }
