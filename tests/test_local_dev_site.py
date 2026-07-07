from __future__ import annotations

import json

from tests.local_dev_site import copy_bundle_into_checkout, detect_dev_server


def test_detect_node_dev_server(tmp_path):
    checkout = tmp_path / "site"
    checkout.mkdir()
    (checkout / "package.json").write_text(json.dumps({"scripts": {"dev": "vite --host 127.0.0.1"}}), encoding="utf-8")
    plan = detect_dev_server(checkout)
    assert plan.status == "detected"
    assert plan.stack == "node-npm"
    assert plan.command[:3] == ["npm", "run", "dev"]
    assert plan.port is not None


def test_detect_static_html_server(tmp_path):
    checkout = tmp_path / "site"
    checkout.mkdir()
    (checkout / "index.html").write_text("<h1>site</h1>", encoding="utf-8")
    plan = detect_dev_server(checkout)
    assert plan.status == "detected"
    assert plan.stack == "static-html"
    assert plan.command is not None


def test_unknown_stack_requires_integration(tmp_path):
    checkout = tmp_path / "site"
    checkout.mkdir()
    plan = detect_dev_server(checkout)
    assert plan.status == "integration_required"
    assert "no package.json" in (plan.reason or "")


def test_copy_bundle_into_checkout(tmp_path):
    bundle = tmp_path / "deployment-bundle"
    (bundle / "artifacts").mkdir(parents=True)
    (bundle / "artifacts" / "urirun-1.whl").write_bytes(b"wheel")
    (bundle / "manifest.json").write_text("{}", encoding="utf-8")
    checkout = tmp_path / "site"
    checkout.mkdir()
    copied = copy_bundle_into_checkout(bundle, checkout)
    assert (checkout / "deployment-bundle" / "manifest.json").exists()
    assert (checkout / "artifacts" / "urirun-1.whl").exists()
    assert copied
