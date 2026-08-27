import logging

import httpx

logger = logging.getLogger(__name__)

BLOCKSCOUT_API = "https://eth.blockscout.com/api"

CHAIN_APIS = {
    "ethereum": "https://eth.blockscout.com/api",
    "base": "https://base.blockscout.com/api",
    "arbitrum": "https://arbitrum.blockscout.com/api",
    "optimism": "https://optimism.blockscout.com/api",
    "polygon": "https://polygon.blockscout.com/api",
    "gnosis": "https://gnosis.blockscout.com/api",
}


async def _get_txs(client: httpx.AsyncClient, api_url: str, address: str) -> list:
    try:
        resp = await client.get(
            f"{api_url}",
            params={"module": "account", "action": "txlist", "address": address,
                     "startblock": 0, "endblock": 99999999, "page": 1, "offset": 50,
                     "sort": "desc"},
            timeout=15,
        )
        if resp.status_code == 200:
            data = resp.json()
            return data.get("result", []) if isinstance(data.get("result"), list) else []
    except Exception as e:
        logger.debug(f"Blockscout request failed: {e}")
    return []


async def get_onchain_data(wallet_address: str) -> dict:
    """Check on-chain activity for a wallet across multiple chains."""
    if not wallet_address:
        return {"has_wallet": False}

    async with httpx.AsyncClient() as client:
        chains_active = []
        total_deploys = 0
        verified_deploys = 0

        for chain_name, api_url in CHAIN_APIS.items():
            txs = await _get_txs(client, api_url, wallet_address)
            if not txs:
                continue

            chain_deploys = 0
            chain_verified = 0

            for tx in txs:
                if tx.get("to") == "" or tx.get("to") is None:
                    chain_deploys += 1

            if chain_deploys > 0:
                chains_active.append(chain_name)
                total_deploys += chain_deploys

            verify_resp = await client.get(
                f"{api_url}",
                params={"module": "contract", "action": "getabi",
                         "address": wallet_address},
                timeout=10,
            )
            if verify_resp.status_code == 200:
                vdata = verify_resp.json()
                if vdata.get("status") == "1":
                    chain_verified += 1

            verified_deploys += chain_verified

        return {
            "has_wallet": True,
            "chains_active": chains_active,
            "chain_count": len(chains_active),
            "total_deploys": total_deploys,
            "verified_deploys": verified_deploys,
            "verification_rate": (verified_deploys / total_deploys) if total_deploys > 0 else 0,
        }
