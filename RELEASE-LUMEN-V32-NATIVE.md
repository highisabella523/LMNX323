# Lumen V32.4 — Native Xray + Exact Managed Proxies

## Architecture

Client configurations always use the normal Lumen/Railway public address, port, SNI and Host. Managed proxy endpoints never appear in subscription links.

```text
client → Railway edge → native Xray inbound
       → exact per-user loopback SOCKS bridge
       → exact selected HTTP / HTTPS / SOCKS5 proxy
       → destination
```

## Managed proxy repository

Place `proxy.txt` at `/data/proxy.txt`, override with `LUMEN_PROXY_CATALOG_FILE`, or upload it with `PUT /api/proxies/import`.

Canonical lines:

```text
https://4.213.225.50:443#India - 66%
http://user:pass@host:8080#Germany - 40%
socks5://user:pass@host:1080#Peru - 22%
```

The URL scheme is the proxy protocol. Country is catalog metadata. The legacy percentage is parsed for compatibility but never used for routing, weighting, or failover.

The browser receives only stable proxy ID, country, country code and flag. Protocol, endpoint and credentials remain server-side.

## Exact routing guarantees

- User selection stores one exact `proxy_id`.
- The selected endpoint must pass Cloudflare and Google tests before a signed receipt allows a changed selection to be saved.
- Native Xray routes that user's decoded traffic to one dedicated loopback bridge.
- The bridge resolves the exact repository record and speaks its HTTP, HTTPS or SOCKS5 protocol.
- Destination hostnames are sent to the selected proxy; they are not substituted into client configs.
- Missing/dead selected proxies fail closed. No direct fallback and no alternate proxy selection.
- Direct users continue through Xray `freedom`.

## Railway

Deploy the repository root and persist `/data`. Configure `PUBLIC_DOMAIN` (or Railway's public-domain variable), `JWT_SECRET`, and the normal Railway public `PORT`.
