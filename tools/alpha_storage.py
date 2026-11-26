"""Move exact corresponding sources off Pages and bound OSTree retention.

All work is staged. Persist/deploy is deliberately outside this module.
The data branch's ordinary Git history remains the recovery copy.
"""

import argparse
import base64
import hashlib
import html
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import tarfile
import tempfile
import urllib.request

REPOSITORY = "icfmp/Bible"
SOURCE_TAG = "alpha-source-archives"
KEEP_COMMITS = 10
# GLib.Variant('a{sv}', {'ostree.static-deltas': GLib.Variant('a{sv}', {})}).
# Native index format: OSTree v2024.5, ostree-repo-static-delta-core.c:1345.
# No delta parts are advertised; clients still verify signed loose objects.
EMPTY_DELTA_INDEX = bytes.fromhex(
    "6f73747265652e7374617469632d64656c7461730000000000617b73767d151f"
)


def empty_delta_indexes(repo):
    """Serve a real empty index rather than an optional 404 for retained commits.

    Some static hosts return 503 for an absent percent-encoded '+' path. Older
    OSTree clients abort there instead of falling back to signed loose objects.
    """
    repo = Path(repo)
    created = []
    for commit in sorted((repo / "objects").glob("[0-9a-f][0-9a-f]/*.commit")):
        assert not commit.is_symlink()
        checksum = commit.parent.name + commit.stem
        assert re.fullmatch("[0-9a-f]{64}", checksum)
        encoded = base64.b64encode(bytes.fromhex(checksum)).decode().rstrip("=").replace("/", "_")
        index = repo / "delta-indexes" / encoded[:2] / (encoded[2:] + ".index")
        index.parent.mkdir(parents=True, exist_ok=True)
        index.write_bytes(EMPTY_DELTA_INDEX)
        created.append(str(index.relative_to(repo)))
    return created


def command(*args):
    return subprocess.check_output(list(map(str, args)), text=True).strip()


def api(endpoint):
    return json.loads(command("gh", "api", endpoint))


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def release():
    """Explicit technical storage prerelease; never a numbered application release."""
    return api(f"repos/{REPOSITORY}/releases/tags/{SOURCE_TAG}")


def verify_asset(asset, name, expected_sha, expected_size, *, download=True):
    """Check source-archive publication identity, size and digest, optionally verifying downloaded bytes."""
    assert asset["name"] == name and asset["state"] == "uploaded"
    assert asset["size"] == expected_size
    assert asset.get("digest") == "sha256:" + expected_sha, "Release asset digest mismatch"
    url = f"https://github.com/{REPOSITORY}/releases/download/{SOURCE_TAG}/{name}"
    assert asset["browser_download_url"] == url
    if download:
        digest = hashlib.sha256()
        size = 0
        with urllib.request.urlopen(url, timeout=120) as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
                size += len(block)
        assert size == expected_size and digest.hexdigest() == expected_sha, (
            "Public source download mismatch"
        )
    return url


def source_contents(path):
    """Compare wrapper payloads/permissions, never timestamp/owner metadata.

    The project tar and pinned dependency archives are regular file payloads:
    their bytes must match exactly, including their own internal metadata.
    """
    contents = {}
    expanded = 0
    with tarfile.open(path, "r|gz") as archive:
        for member in archive:
            name = PurePosixPath(member.name)
            assert not name.is_absolute() and ".." not in name.parts and name.parts, (
                "Unsafe source archive path"
            )
            assert str(name) not in contents and len(contents) < 512, (
                "Duplicate or excessive source archive entries"
            )
            expanded += member.size
            assert 0 <= member.size and expanded <= 512 * 1024 * 1024, (
                "Source archive exceeds safe limits"
            )
            if member.isdir():
                assert member.size == 0
                content = ("directory", member.mode)
            else:
                assert member.isfile(), "Source archive links/special files refused"
                with archive.extractfile(member) as stream:
                    content = (
                        "file",
                        member.mode,
                        hashlib.file_digest(stream, "sha256").hexdigest(),
                    )
            contents[str(name)] = content
    return contents


def reuse_source_upload(path, asset):
    """Recover an unrecorded upload only after exact source-payload comparison."""
    assert re.fullmatch(r"sha256:[0-9a-f]{64}", asset.get("digest", "")), (
        "Missing source asset digest"
    )
    assert type(asset["size"]) is int and 0 < asset["size"] <= 512 * 1024 * 1024, (
        "Invalid source asset size"
    )
    url = verify_asset(asset, path.name, asset["digest"][7:], asset["size"], download=False)
    with tempfile.TemporaryDirectory() as temporary:
        original = Path(temporary) / "original.tar.gz"
        received = 0
        with urllib.request.urlopen(url, timeout=60) as response, original.open("xb") as output:
            for block in iter(lambda: response.read(1024 * 1024), b""):
                received += len(block)
                assert received <= asset["size"], "Public source download exceeds declared size"
                output.write(block)
        digest = sha256(original)
        verify_asset(asset, path.name, digest, received, download=False)
        assert source_contents(path) == source_contents(original), (
            "Existing source archive payload differs"
        )
    return digest, received, url


def archive_sources(site):
    """Upload and publicly verify every source BEFORE deleting any staged copy.

    A failure leaves every local archive intact; no asset is overwritten.
    Existing catalogue entries are checked against GitHub's asset IDs/digests.
    """
    alpha = Path(site) / "alpha"
    catalog_path = alpha / "sources.json"
    catalog = (
        json.loads(catalog_path.read_text())
        if catalog_path.exists()
        else {"version": 1, "archives": {}}
    )
    assert catalog["version"] == 1
    remote = release()
    assert not remote["draft"] and remote["prerelease"], "Source storage release must be public"
    assets = {a["name"]: a for a in remote["assets"]}
    for name, record in catalog["archives"].items():
        asset = assets[name]
        assert asset["id"] == record["asset_id"], "Previously verified source asset was replaced"
        assert (
            verify_asset(asset, name, record["sha256"], record["bytes"], download=False)
            == record["url"]
        )
    pending = sorted(alpha.glob("Bible-*-sources.tar.gz"))
    for path in pending:
        match = re.fullmatch(r"Bible-([0-9a-f]{40})-sources\.tar\.gz", path.name)
        assert match, f"Unexpected source archive: {path.name}"
        digest, size = sha256(path), path.stat().st_size
        asset = assets.get(path.name)
        if asset is None:
            subprocess.run(
                ["gh", "release", "upload", SOURCE_TAG, str(path), "--repo", REPOSITORY], check=True
            )
            assets = {a["name"]: a for a in release()["assets"]}
            asset = assets[path.name]
        if path.name not in catalog["archives"] and asset.get("digest") != "sha256:" + digest:
            # An upload may succeed before persisting its receipt fails. A new
            # wrapper can differ only in tar/gzip metadata: reuse original bytes
            # after independently verifying the download and every payload.
            digest, size, url = reuse_source_upload(path, asset)
        else:
            url = verify_asset(asset, path.name, digest, size)
        catalog["archives"][path.name] = dict(
            source_commit=match[1], sha256=digest, bytes=size, asset_id=asset["id"], url=url
        )
    # Only after every public download passed may staging discard originals.
    catalog_path.write_text(json.dumps(catalog, indent=2, sort_keys=True) + "\n")
    provenance_path = alpha / "provenance.json"
    if provenance_path.exists():
        provenance = json.loads(provenance_path.read_text())
        record = catalog["archives"][provenance["source_archive"]]
        assert provenance["source_sha256"] == record["sha256"]
        provenance["source_url"] = record["url"]
        provenance_path.write_text(json.dumps(provenance, indent=2) + "\n")
    for path in pending:
        path.unlink()
    rows = "".join(
        f'<li><a href="{html.escape(r["url"], quote=True)}">{html.escape(n)}</a>'
        f" — SHA-256: <code>{r['sha256']}</code></li>"
        for n, r in sorted(catalog["archives"].items())
    )
    (alpha / "sources.html").write_text(
        '<!doctype html><html lang="en"><meta charset="utf-8">'
        "<title>Bible corresponding sources</title><h1>Corresponding sources</h1>"
        "<p>Archives moved from Pages to GitHub Releases without changing their bytes. "
        "Old direct Pages archive URLs are replaced by the links below.</p><ul>"
        + rows
        + "</ul></html>\n"
    )
    return catalog


def retain_repository(site, keep=KEEP_COMMITS):
    """Keep the current revision plus nine parents; retain every other ref tip.

    OSTree retains shared file objects needed by any retained tree. Old installed
    clients update via full objects when an incremental delta is unavailable.
    """
    assert keep >= 2
    from tools.flatpak_channel import REF, restore_repository_layout

    repo = Path(site) / "alpha/repo"
    restore_repository_layout(repo)
    head = command("ostree", f"--repo={repo}", "rev-parse", REF)
    before = sum(p.stat().st_size for p in repo.rglob("*") if p.is_file())
    # Indexes advertise the derived delta parts. Retaining an index after its
    # parts are removed sends clients to missing URLs instead of signed objects.
    derived = [repo / name for name in ("deltas", "delta-indexes")]
    assert all(not path.is_symlink() for path in derived)
    import shutil

    for path in derived:
        if path.exists():
            shutil.rmtree(path)
    output = command("ostree", f"--repo={repo}", "prune", "--refs-only", f"--depth={keep - 1}")
    command("ostree", f"--repo={repo}", "fsck")
    indexes = empty_delta_indexes(repo)
    assert command("ostree", f"--repo={repo}", "rev-parse", REF) == head
    return dict(
        keep_commits=keep,
        flatpak_commit=head,
        before_bytes=before,
        after_bytes=sum(p.stat().st_size for p in repo.rglob("*") if p.is_file()),
        prune=output,
        empty_delta_indexes=indexes,
    )


def repair_indexes(site):
    """Recover the already-published index-only defect without changing a commit.

    Refuse live delta parts or links; preserve every other public byte, including
    all signatures, history, provenance, source archives and channel descriptors.
    """
    from tools.flatpak_channel import REF, restore_repository_layout

    site = Path(site)
    repo = site / "alpha/repo"
    restore_repository_layout(repo)
    assert not any(path.is_symlink() for path in site.rglob("*")), "Unexpected public-site link"
    provenance = json.loads((site / "alpha/provenance.json").read_text())
    head = command("ostree", f"--repo={repo}", "rev-parse", REF)
    assert provenance["ref"] == REF and provenance["flatpak_commit"] == head
    assert re.fullmatch(r"[0-9a-f]{40}", provenance["source_commit"])
    parts = repo / "deltas"
    indexes = repo / "delta-indexes"
    assert not parts.is_symlink() and not indexes.is_symlink()
    assert not parts.exists() or not any(parts.rglob("*")), (
        "Live delta parts require normal retention, not index-only repair"
    )
    before = {
        str(path.relative_to(site)): sha256(path) for path in site.rglob("*") if path.is_file()
    }
    removed = {
        name: digest
        for name, digest in before.items()
        if name.startswith("alpha/repo/delta-indexes/")
    }
    if indexes.exists():
        import shutil

        shutil.rmtree(indexes)
    created = empty_delta_indexes(repo)
    command("ostree", f"--repo={repo}", "fsck")
    assert command("ostree", f"--repo={repo}", "rev-parse", REF) == head
    after = {
        str(path.relative_to(site)): sha256(path) for path in site.rglob("*") if path.is_file()
    }
    protected = {name: digest for name, digest in before.items() if name not in removed}
    assert {
        name: digest
        for name, digest in after.items()
        if not name.startswith("alpha/repo/delta-indexes/")
    } == protected
    result = dict(
        flatpak_commit=head,
        source_commit=provenance["source_commit"],
        removed_indexes=removed,
        empty_delta_indexes=created,
        every_other_public_file_unchanged=True,
    )
    return result


def migrate(site):
    """Stage existing source archival and repository retention while preserving application/signing provenance.

    Require the resulting site to fit the publishing budget. Deployment and
    data-branch persistence remain separate operations.
    """
    from tools.flatpak_channel import MAX_SITE_BYTES
    from tools.site_render import render

    site = Path(site)
    before = sum(p.stat().st_size for p in site.rglob("*") if p.is_file())
    alpha = site / "alpha"
    original = json.loads((alpha / "provenance.json").read_text())
    protected = {
        name: sha256(alpha / name)
        for name in [
            "Bible.flatpakref",
            "bible-alpha.flatpakrepo",
            "bible-alpha.gpg",
            "repo/summary",
            "repo/summary.sig",
        ]
    }
    catalog = archive_sources(site)
    retention = retain_repository(site)
    provenance = json.loads((alpha / "provenance.json").read_text())
    assert {k: provenance[k] for k in original} == original, "Application provenance changed"
    assert all(sha256(alpha / name) == digest for name, digest in protected.items()), (
        "Signed channel identity changed"
    )
    render(site, provenance)
    after = sum(p.stat().st_size for p in site.rglob("*") if p.is_file())
    assert after < MAX_SITE_BYTES
    report = dict(
        before_bytes=before,
        after_bytes=after,
        source_archives=len(catalog["archives"]),
        source_archive_bytes=sum(a["bytes"] for a in catalog["archives"].values()),
        application_provenance_unchanged=True,
        signed_channel_files_unchanged=True,
        retention=retention,
    )
    Path("storage-plan.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def seed_client(site, base_url, old_commit):
    """Install while the unpruned public server is still live, then select #90."""
    import os
    from tools.check_flatpak_channel import check, verify_data
    from tools.flatpak_channel import APP_ID

    expected = json.loads((Path(site) / "alpha/provenance.json").read_text())
    result = check(base_url, expected, Path("storage-client-before.json").resolve())
    assert re.fullmatch(r"[0-9a-f]{64}", old_commit)
    assert old_commit != expected["flatpak_commit"]
    subprocess.run(
        [
            "flatpak",
            "update",
            "--user",
            "--noninteractive",
            f"--commit={old_commit}",
            APP_ID + "//alpha",
        ],
        check=True,
    )
    assert command("flatpak", "info", "--user", "--show-commit", APP_ID + "//alpha") == old_commit
    verify_data(result["user_data_snapshot"])
    result.update(
        install_commit=old_commit,
        previous_current_commit=expected["flatpak_commit"],
        client_dir=os.environ["FLATPAK_USER_DIR"],
    )
    Path("storage-client-before.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def verify_clients(site, base_url):
    """Verify a real retained-client update and fresh installation against the published staged provenance.

    Require signed installed commits, GTK startup and preservation of the
    seeded user-data receipt; this mutates isolated Flatpak test installations.
    """
    import os
    from tools.check_flatpak_channel import check, verify_data
    from tools.flatpak_channel import APP_ID

    before = json.loads(Path("storage-client-before.json").read_text())
    expected = json.loads((Path(site) / "alpha/provenance.json").read_text())
    # Wait for the new source catalogue to propagate; the app commit is unchanged.
    import time

    for attempt in range(30):
        try:
            with urllib.request.urlopen(
                base_url + "/alpha/sources.json?storage=" + os.environ["GITHUB_RUN_ID"], timeout=30
            ) as response:
                public = json.load(response)
            assert public == json.loads((Path(site) / "alpha/sources.json").read_text())
            with urllib.request.urlopen(
                base_url + "/alpha/provenance.json?storage=" + os.environ["GITHUB_RUN_ID"],
                timeout=30,
            ) as response:
                assert json.load(response) == expected
            break
        except Exception:
            if attempt == 29:
                raise
            time.sleep(10)
    subprocess.run(
        ["flatpak", "update", "--user", "--noninteractive", APP_ID + "//alpha"], check=True
    )
    installed = command("flatpak", "info", "--user", "--show-commit", APP_ID + "//alpha")
    assert installed == expected["flatpak_commit"] != before["install_commit"]
    verify_data(before["user_data_snapshot"])
    old_dir = os.environ["FLATPAK_USER_DIR"]
    try:
        os.environ["FLATPAK_USER_DIR"] = old_dir + "-fresh"
        fresh = check(base_url, expected, Path("storage-fresh-install.json").resolve())
    finally:
        os.environ["FLATPAK_USER_DIR"] = old_dir
    result = dict(
        old_commit=before["install_commit"],
        update_commit=installed,
        old_client_update=True,
        user_data_preserved=True,
        fresh_install=fresh["install_commit"] == installed,
        gpg_commit=fresh["gpg_commit"],
        gpg_summary=fresh["gpg_summary"],
        gtk_startup=fresh["gtk_startup"],
    )
    Path("storage-check.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "action",
        choices=["archive", "retain", "migrate", "repair-indexes", "seed-client", "verify-clients"],
    )
    parser.add_argument("--site", default="public")
    parser.add_argument("--base-url")
    parser.add_argument("--old-commit")
    args = parser.parse_args()
    if args.action == "seed-client":
        result = seed_client(args.site, args.base_url, args.old_commit)
    elif args.action == "verify-clients":
        result = verify_clients(args.site, args.base_url)
    else:
        result = {
            "archive": archive_sources,
            "retain": retain_repository,
            "migrate": migrate,
            "repair-indexes": repair_indexes,
        }[args.action](args.site)
    if args.action == "repair-indexes":
        Path("storage-index-repair.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
