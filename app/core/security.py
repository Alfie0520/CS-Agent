import hashlib


def check_signature(signature: str, timestamp: str, nonce: str, token: str) -> bool:
    """验证微信服务器签名，用于 Token 验证和消息合法性校验。"""
    items = sorted([token, timestamp, nonce])
    sha1 = hashlib.sha1("".join(items).encode("utf-8")).hexdigest()
    return sha1 == signature
