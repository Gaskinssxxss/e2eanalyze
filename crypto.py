#!/usr/bin/env python3
import os, time, base64
from dataclasses import dataclass

def now_ms() -> int:
    return int(time.time() * 1000)

def nonce12() -> bytes:
    return os.urandom(12)

def b64e(b: bytes) -> str:
    return base64.b64encode(b).decode("ascii")

def b64d(s: str) -> bytes:
    return base64.b64decode(s.encode("ascii"))

def _require_crypto():
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM, ChaCha20Poly1305
    return AESGCM, ChaCha20Poly1305

AESGCM, ChaCha20Poly1305 = _require_crypto()

@dataclass
class Box:
    key: bytes
    cipher: str = "aesgcm"
    aad: bytes = b""

    def _aead(self):
        if self.cipher == "aesgcm":
            return AESGCM(self.key)
        if self.cipher == "chacha20poly1305":
            return ChaCha20Poly1305(self.key)
        raise ValueError("cipher harus aesgcm/chacha20poly1305")

    def enc(self, pt: bytes, n: bytes) -> bytes:
        return self._aead().encrypt(n, pt, self.aad)

    def dec(self, ct: bytes, n: bytes) -> bytes:
        return self._aead().decrypt(n, ct, self.aad)
