"""Client for the OSV.dev open vulnerability database API (https://osv.dev)."""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

OSV_QUERY_URL = "https://api.osv.dev/v1/query"
OSV_BATCH_URL = "https://api.osv.dev/v1/querybatch"


class OSVClient:
    """Client for OSV.dev vulnerability querying with local caching and offline resilience."""

    def __init__(self, timeout: float = 6.0) -> None:
        self.timeout = timeout
        self._cache: dict[tuple[str, str, str], list[dict[str, Any]]] = {}

    def query_sync(self, package_name: str, version: str, ecosystem: str = "PyPI") -> list[dict[str, Any]]:
        """Query OSV.dev synchronously for vulnerabilities affecting a package version."""
        cache_key = (ecosystem.lower(), package_name.lower(), version.strip())
        if cache_key in self._cache:
            return self._cache[cache_key]

        payload = {
            "package": {"name": package_name, "ecosystem": ecosystem},
            "version": version,
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(OSV_QUERY_URL, json=payload)
                if resp.status_code == 200:
                    vulns = resp.json().get("vulns", [])
                    self._cache[cache_key] = vulns
                    return vulns
                logger.warning("OSV API returned status %d for %s@%s", resp.status_code, package_name, version)
        except Exception as exc:
            logger.warning("OSV.dev query failed for %s@%s: %s", package_name, version, exc)

        return []

    async def query_async(self, package_name: str, version: str, ecosystem: str = "PyPI") -> list[dict[str, Any]]:
        """Query OSV.dev asynchronously for vulnerabilities affecting a package version."""
        cache_key = (ecosystem.lower(), package_name.lower(), version.strip())
        if cache_key in self._cache:
            return self._cache[cache_key]

        payload = {
            "package": {"name": package_name, "ecosystem": ecosystem},
            "version": version,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(OSV_QUERY_URL, json=payload)
                if resp.status_code == 200:
                    vulns = resp.json().get("vulns", [])
                    self._cache[cache_key] = vulns
                    return vulns
                logger.warning("OSV API returned status %d for %s@%s", resp.status_code, package_name, version)
        except Exception as exc:
            logger.warning("OSV.dev async query failed for %s@%s: %s", package_name, version, exc)

        return []

    def query_batch_sync(self, items: list[dict[str, str]]) -> dict[tuple[str, str, str], list[dict[str, Any]]]:
        """Query multiple dependencies in a single batch request."""
        results: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
        queries = []
        needed_indices = []

        for _idx, item in enumerate(items):
            pkg = item.get("name", "")
            ver = item.get("version", "")
            eco = item.get("ecosystem", "PyPI")
            ck = (eco.lower(), pkg.lower(), ver.strip())
            if ck in self._cache:
                results[ck] = self._cache[ck]
            else:
                queries.append({"package": {"name": pkg, "ecosystem": eco}, "version": ver})
                needed_indices.append(ck)

        if not queries:
            return results

        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(OSV_BATCH_URL, json={"queries": queries})
                if resp.status_code == 200:
                    batch_results = resp.json().get("results", [])
                    for ck, res in zip(needed_indices, batch_results, strict=False):
                        vulns = res.get("vulns", [])
                        self._cache[ck] = vulns
                        results[ck] = vulns
                    return results
        except Exception as exc:
            logger.warning("OSV batch query failed: %s; falling back to individual queries", exc)

        # Fallback to individual
        for ck in needed_indices:
            results[ck] = self.query_sync(ck[1], ck[2], ck[0])

        return results

    def clear_cache(self) -> None:
        """Clear cached OSV queries."""
        self._cache.clear()


# Default singleton client
default_osv_client = OSVClient()
