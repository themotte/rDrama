'''
A certificate authority for one test session, which the implementation under test is told to trust (SSL_CERT_FILE): the intercepting proxy and the mail capture present certificates it signs for the hosts they stand in for. Certificates are made with the `openssl` command, with the extensions strict X.509 checking requires.
'''
import secrets
import ssl
import subprocess
import threading
from pathlib import Path

_DAYS = "2"


class Authority:
	def __init__(self, directory: Path):
		'''A new authority keeping its keys and certificates in `directory`.'''
		self.dir = directory
		self.dir.mkdir(parents=True, exist_ok=True)
		self.ca_file = str(self.dir / "ca.pem")
		self._key_file = str(self.dir / "ca.key")
		self._contexts: dict[str, ssl.SSLContext] = {}
		self._lock = threading.Lock()
		_openssl(
			"req", "-x509", "-newkey", "ec", "-pkeyopt", "ec_paramgen_curve:prime256v1", "-nodes",
			"-keyout", self._key_file, "-out", self.ca_file, "-days", _DAYS, "-subj", "/CN=Spec harness CA",
			"-addext", "basicConstraints=critical,CA:TRUE",
			"-addext", "keyUsage=critical,keyCertSign,cRLSign",
			"-addext", "subjectKeyIdentifier=hash",
		)

	def server_context(self, host: str) -> ssl.SSLContext:
		'''A TLS server context presenting a certificate for `host` (a name, or an IP address), made on first use.'''
		with self._lock:
			if host not in self._contexts:
				self._contexts[host] = self._make_context(host)
			return self._contexts[host]

	def _make_context(self, host):
		name = secrets.token_hex(8)
		key, cert = str(self.dir / f"{name}.key"), str(self.dir / f"{name}.pem")
		subject_alt_name = f"IP:{host}" if _is_ip(host) else f"DNS:{host}"
		_openssl(
			"req", "-x509", "-newkey", "ec", "-pkeyopt", "ec_paramgen_curve:prime256v1", "-nodes",
			"-CA", self.ca_file, "-CAkey", self._key_file, "-set_serial", str(int(secrets.token_hex(16), 16)),
			"-keyout", key, "-out", cert, "-days", _DAYS, "-subj", f"/CN={host}",
			"-addext", "basicConstraints=critical,CA:FALSE",
			"-addext", "keyUsage=critical,digitalSignature",
			"-addext", "extendedKeyUsage=serverAuth",
			"-addext", f"subjectAltName={subject_alt_name}",
			"-addext", "subjectKeyIdentifier=hash",
			"-addext", "authorityKeyIdentifier=keyid",
		)
		context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
		context.load_cert_chain(cert, key)
		return context


def _is_ip(host):
	return all(part.isdigit() for part in host.split(".")) or ":" in host


def _openssl(*args):
	result = subprocess.run(["openssl", *args], capture_output=True, text=True)
	if result.returncode != 0:
		raise RuntimeError(f"openssl {' '.join(args[:2])} failed: {result.stderr}")
