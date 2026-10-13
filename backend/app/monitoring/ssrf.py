import asyncio
import ipaddress
import socket
from urllib.parse import urlparse
from fastapi import HTTPException

async def validate_public_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or parsed.username or parsed.password or not parsed.hostname:
        raise HTTPException(status_code=422, detail="Only public HTTP(S) URLs without embedded credentials are allowed")
    hostname = parsed.hostname.rstrip(".").lower()
    if hostname in {"localhost", "metadata.google.internal"}:
        raise HTTPException(status_code=422, detail="Private or metadata destinations are not allowed")
    try:
        records = await asyncio.to_thread(socket.getaddrinfo, hostname, parsed.port or (443 if parsed.scheme == "https" else 80), type=socket.SOCK_STREAM)
    except socket.gaierror:
        raise HTTPException(status_code=422, detail="The service hostname could not be resolved")
    for record in records:
        address = ipaddress.ip_address(record[4][0])
        if address.is_private or address.is_loopback or address.is_link_local or address.is_multicast or address.is_reserved or address.is_unspecified:
            raise HTTPException(status_code=422, detail="Private or reserved destinations are not allowed")
