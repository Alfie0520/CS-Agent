"""微信客服回调消息加解密。

基于企业微信回调加解密方案：
- 签名验证：SHA1(sort(token, timestamp, nonce, msg_encrypt))
- 加密：AES-256-CBC，Key 由 EncodingAESKey Base64 解码得到，IV 为 Key 前 16 字节
- 填充：PKCS#7（32 字节块）
- 明文格式：random(16B) + msg_len(4B, network order) + msg + receiveid
"""

from __future__ import annotations

import base64
import hashlib
import os
import socket
import struct
from xml.etree import ElementTree

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.padding import PKCS7


class KfCallbackCrypto:

    def __init__(self, token: str, encoding_aes_key: str, corp_id: str) -> None:
        self._token = token
        self._corp_id = corp_id
        self._aes_key = base64.b64decode(encoding_aes_key + "=")
        self._iv = self._aes_key[:16]

    # ---------- 签名 ----------

    def _signature(self, timestamp: str, nonce: str, encrypt: str) -> str:
        parts = sorted([self._token, timestamp, nonce, encrypt])
        return hashlib.sha1("".join(parts).encode("utf-8")).hexdigest()

    def verify_signature(
        self, msg_signature: str, timestamp: str, nonce: str, encrypt: str
    ) -> bool:
        return self._signature(timestamp, nonce, encrypt) == msg_signature

    # ---------- 解密 ----------

    def _decrypt(self, ciphertext_b64: str) -> bytes:
        ciphertext = base64.b64decode(ciphertext_b64)
        cipher = Cipher(algorithms.AES(self._aes_key), modes.CBC(self._iv))
        decryptor = cipher.decryptor()
        padded = decryptor.update(ciphertext) + decryptor.finalize()
        # PKCS#7 unpad（32 字节块）
        unpadder = PKCS7(256).unpadder()
        plaintext = unpadder.update(padded) + unpadder.finalize()
        return plaintext

    def decrypt_message(
        self,
        msg_signature: str,
        timestamp: str,
        nonce: str,
        encrypt: str,
    ) -> str:
        """验签 + 解密，返回明文 XML/消息字符串。"""
        if not self.verify_signature(msg_signature, timestamp, nonce, encrypt):
            raise ValueError("Invalid message signature")

        plaintext = self._decrypt(encrypt)
        # 明文格式：random(16B) + msg_len(4B) + msg + receiveid
        msg_len = socket.ntohl(struct.unpack("I", plaintext[16:20])[0])
        msg = plaintext[20 : 20 + msg_len]
        return msg.decode("utf-8")

    # ---------- 加密（用于回复验证请求等场景）----------

    def encrypt_message(self, reply_msg: str, timestamp: str, nonce: str) -> str:
        """加密消息并返回签名后的 XML 响应体。"""
        msg_bytes = reply_msg.encode("utf-8")
        receiveid = self._corp_id.encode("utf-8")
        # 拼接明文：random(16B) + msg_len(4B) + msg + receiveid
        random_bytes = os.urandom(16)
        msg_len = struct.pack("I", socket.htonl(len(msg_bytes)))
        plaintext = random_bytes + msg_len + msg_bytes + receiveid
        # PKCS#7 pad（32 字节块）
        padder = PKCS7(256).padder()
        padded = padder.update(plaintext) + padder.finalize()
        # AES 加密
        cipher = Cipher(algorithms.AES(self._aes_key), modes.CBC(self._iv))
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(padded) + encryptor.finalize()
        encrypt_b64 = base64.b64encode(ciphertext).decode("utf-8")
        # 签名
        signature = self._signature(timestamp, nonce, encrypt_b64)
        return (
            "<xml>"
            f"<Encrypt><![CDATA[{encrypt_b64}]]></Encrypt>"
            f"<MsgSignature><![CDATA[{signature}]]></MsgSignature>"
            f"<TimeStamp>{timestamp}</TimeStamp>"
            f"<Nonce><![CDATA[{nonce}]]></Nonce>"
            "</xml>"
        )

    # ---------- 辅助：URL 验证场景解密 echostr ----------

    def decrypt_echostr(
        self, msg_signature: str, timestamp: str, nonce: str, echostr: str
    ) -> str:
        """URL 验证：解密 echostr 并返回明文（需原样返回给微信）。"""
        return self.decrypt_message(msg_signature, timestamp, nonce, echostr)


def parse_encrypted_xml(body: bytes) -> str:
    """从回调 POST body XML 中提取 <Encrypt> 字段。"""
    root = ElementTree.fromstring(body)
    encrypt_node = root.find("Encrypt")
    if encrypt_node is None or not encrypt_node.text:
        raise ValueError("Missing <Encrypt> in callback XML")
    return encrypt_node.text
