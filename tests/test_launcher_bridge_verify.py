"""launcher-bridge.yml signs a launcher release here only after tools/ci/verify_launcher_release.sh accepts it."""
import base64
import hashlib
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools/ci/verify_launcher_release.sh"
ASSET = "sunrise-launcher-linux-x86_64.tar.gz"


@unittest.skipUnless(shutil.which("openssl") and shutil.which("bash") and shutil.which("sha256sum"), "needs bash, OpenSSL and sha256sum")
class LauncherBridgeVerify(unittest.TestCase):
    def setUp(self):
        self.work = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.work)
        self.key = self.work / "key.der"
        subprocess.run(["openssl", "genpkey", "-algorithm", "ed25519", "-outform", "DER", "-out", self.key], check=True)
        public = subprocess.run(["openssl", "pkey", "-inform", "DER", "-in", self.key, "-pubout", "-outform", "DER"],
                                check=True, capture_output=True).stdout[-32:]
        self.keys = self.work / "keys.txt"
        self.keys.write_text("# the launcher's key\n" + base64.b64encode(public).decode() + "\n")
        self.dist = self.work / "dist"
        self.dist.mkdir()
        (self.dist / ASSET).write_bytes(b"launcher")

    def sign(self, prefix: str, tag: str):
        sums = f"{hashlib.sha256((self.dist / ASSET).read_bytes()).hexdigest()}  {ASSET}\n"
        (self.dist / "SHA256SUMS").write_text(sums)
        message = self.work / "message"
        message.write_bytes(f"{prefix} {tag}\n".encode() + sums.encode())
        signature = subprocess.run(["openssl", "pkeyutl", "-sign", "-rawin", "-inkey", self.key, "-keyform", "DER",
                                    "-in", message], check=True, capture_output=True).stdout
        (self.dist / "SHA256SUMS.sig").write_text(base64.b64encode(signature).decode() + "\n")

    def accepts(self, tag: str, keys: Path | None = None) -> bool:
        result = subprocess.run(["bash", SCRIPT, tag, self.dist, keys or self.keys], capture_output=True, text=True)
        return result.returncode == 0

    def test_a_release_the_launcher_signed_is_accepted(self):
        self.sign("sunrise-launcher release", "v1.1.0")
        self.assertTrue(self.accepts("v1.1.0"))

    def test_another_tag_or_the_games_signing_domain_is_refused(self):
        self.sign("sunrise-launcher release", "v1.1.0")
        self.assertFalse(self.accepts("v1.2.0"))
        self.sign("horizon release", "v1.1.0")
        self.assertFalse(self.accepts("v1.1.0"))

    def test_a_changed_file_is_refused(self):
        self.sign("sunrise-launcher release", "v1.1.0")
        (self.dist / ASSET).write_bytes(b"changed")
        self.assertFalse(self.accepts("v1.1.0"))

    def test_without_a_listed_key_nothing_is_bridged(self):
        self.sign("sunrise-launcher release", "v1.1.0")
        self.assertFalse(self.accepts("v1.1.0", ROOT / "tools/ci/launcher-release-keys.txt"))


if __name__ == "__main__":
    unittest.main()
