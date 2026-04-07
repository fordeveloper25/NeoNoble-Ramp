"""
Market Maker Service — NeoNoble Ramp.

Internal Market Maker with:
- Treasury as real counterparty (single source of truth)
- Dynamic Bid/Ask pricing based on inventory skew + volatility
- Inventory management with available/locked tracking
- Internal matching engine (netting before treasury)
- PnL accounting: revenue (spread + fees) separated from inventory changes
- On-chain treasury sync for crypto assets
"""

import os
import uuid
import logging
import asyncio
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional

from database.mongodb import get_database

logger = logging.getLogger(__name__)

# ── Constants ──
BASE_SPREAD_BPS = 50          # 0.50% base spread
MIN_SPREAD_BPS = 20           # 0.20% minimum spread
MAX_SPREAD_BPS = 200          # 2.00% max spread
SKEW_FACTOR = 0.08            # how much inventory imbalance widens spread
VOLATILITY_FACTOR = 0.003     # how much 24h volume widens spread
VOLUME_THRESHOLD = 100.0      # NENO volume considered "high"
TARGET_NENO_INVENTORY = 500.0 # target NENO in treasury

SUPPORTED_TREASURY_ASSETS = [
    "NENO", "EUR", "USDT", "USDC", "BNB", "ETH", "BTC", "MATIC", "USD"
]

NENO_CONTRACT = "0xeF3F5C1892A8d7A3304E4A15959E124402d69974"
USDT_BSC = "0x55d398326f99059fF775485246999027B3197955"
USDC_BSC = "0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d"

TOKEN_CONTRACTS = {
    "NENO": NENO_CONTRACT,
    "USDT": USDT_BSC,
    "USDC": USDC_BSC,
}
TOKEN_DECIMALS = {"NENO": 18, "USDT": 18, "USDC": 18}


class MarketMakerService:
    """Core Market Maker — Treasury-backed counterparty."""

    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ─────────────────────────────────────────────
    #  TREASURY INVENTORY
    # ─────────────────────────────────────────────

    async def get_treasury_inventory(self) -> dict:
        """Get full treasury inventory with available/locked breakdown."""
        db = get_database()
        items = await db.treasury_inventory.find({}, {"_id": 0}).to_list(50)
        inventory = {}
        total_eur = 0
        for item in items:
            asset = item["asset"]
            inventory[asset] = {
                "amount": round(item.get("amount", 0), 8),
                "locked_amount": round(item.get("locked_amount", 0), 8),
                "available_amount": round(item.get("available_amount", 0), 8),
                "source": item.get("source", "internal"),
                "last_synced": item.get("last_synced"),
            }
            total_eur += item.get("value_eur", 0)
        return {
            "assets": inventory,
            "total_value_eur": round(total_eur, 2),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    async def get_asset_inventory(self, asset: str) -> dict:
        """Get inventory for a single asset."""
        db = get_database()
        item = await db.treasury_inventory.find_one(
            {"asset": asset.upper()}, {"_id": 0}
        )
        if not item:
            return {"asset": asset.upper(), "amount": 0, "locked_amount": 0, "available_amount": 0}
        return {
            "asset": item["asset"],
            "amount": round(item.get("amount", 0), 8),
            "locked_amount": round(item.get("locked_amount", 0), 8),
            "available_amount": round(item.get("available_amount", 0), 8),
            "source": item.get("source", "internal"),
            "last_synced": item.get("last_synced"),
        }

    async def update_treasury(
        self, asset: str, delta: float, source: str = "trade",
        price_eur: float = 0, lock_delta: float = 0
    ):
        """
        Update treasury inventory for an asset.
        delta > 0 = treasury receives (e.g. user sells NENO to us)
        delta < 0 = treasury sends (e.g. user buys NENO from us)
        lock_delta: change in locked amount
        """
        db = get_database()
        asset = asset.upper()
        now = datetime.now(timezone.utc).isoformat()

        existing = await db.treasury_inventory.find_one({"asset": asset})
        if existing:
            new_amount = round(existing.get("amount", 0) + delta, 8)
            new_locked = round(existing.get("locked_amount", 0) + lock_delta, 8)
            new_available = round(new_amount - new_locked, 8)
            await db.treasury_inventory.update_one(
                {"asset": asset},
                {"$set": {
                    "amount": new_amount,
                    "locked_amount": max(new_locked, 0),
                    "available_amount": max(new_available, 0),
                    "value_eur": round(new_amount * price_eur, 2) if price_eur > 0 else existing.get("value_eur", 0),
                    "last_synced": now,
                    "updated_at": now,
                }}
            )
        else:
            amount = round(max(delta, 0), 8)
            locked = round(max(lock_delta, 0), 8)
            await db.treasury_inventory.insert_one({
                "_id": str(uuid.uuid4()),
                "asset": asset,
                "amount": amount,
                "locked_amount": locked,
                "available_amount": round(amount - locked, 8),
                "source": source,
                "value_eur": round(amount * price_eur, 2) if price_eur > 0 else 0,
                "last_synced": now,
                "created_at": now,
                "updated_at": now,
            })

        logger.info(f"[TREASURY] {asset}: delta={delta:+.8f} source={source}")

    async def initialize_treasury(self):
        """Bootstrap treasury from on-chain hot wallet balances."""
        db = get_database()
        try:
            from services.execution_engine import ExecutionEngine
            engine = ExecutionEngine.get_instance()
            status = await engine.get_hot_wallet_status()
            if not status.get("available"):
                logger.warning("[TREASURY] Hot wallet not available for sync")
                return

            now = datetime.now(timezone.utc).isoformat()

            # NENO
            neno_bal = status.get("neno_balance", 0)
            await db.treasury_inventory.update_one(
                {"asset": "NENO"},
                {"$set": {
                    "amount": neno_bal, "locked_amount": 0,
                    "available_amount": neno_bal,
                    "source": "on_chain", "last_synced": now,
                    "updated_at": now, "sync_source": "hot_wallet",
                }, "$setOnInsert": {"_id": str(uuid.uuid4()), "asset": "NENO", "created_at": now}},
                upsert=True,
            )

            # BNB (gas)
            bnb_bal = status.get("bnb_balance", 0)
            await db.treasury_inventory.update_one(
                {"asset": "BNB"},
                {"$set": {
                    "amount": bnb_bal, "locked_amount": 0,
                    "available_amount": bnb_bal,
                    "source": "on_chain", "last_synced": now,
                    "updated_at": now, "sync_source": "hot_wallet",
                }, "$setOnInsert": {"_id": str(uuid.uuid4()), "asset": "BNB", "created_at": now}},
                upsert=True,
            )

            # Ensure EUR entry exists (fiat — starts at 0 unless NIUM configured)
            eur_exists = await db.treasury_inventory.find_one({"asset": "EUR"})
            if not eur_exists:
                await db.treasury_inventory.insert_one({
                    "_id": str(uuid.uuid4()), "asset": "EUR",
                    "amount": 0, "locked_amount": 0, "available_amount": 0,
                    "source": "provider", "last_synced": now,
                    "created_at": now, "updated_at": now,
                    "sync_source": "nium" if os.environ.get("NIUM_API_KEY") else "manual",
                })

            # USDT / USDC — read on-chain if possible
            for stable, contract in [("USDT", USDT_BSC), ("USDC", USDC_BSC)]:
                try:
                    w3 = engine._get_web3()
                    if w3 and engine.hot_wallet:
                        from services.execution_engine import ERC20_ABI
                        from web3 import Web3
                        c = w3.eth.contract(address=Web3.to_checksum_address(contract), abi=ERC20_ABI)
                        raw = c.functions.balanceOf(engine.hot_wallet).call()
                        bal = float(Decimal(raw) / Decimal(10 ** 18))
                        await db.treasury_inventory.update_one(
                            {"asset": stable},
                            {"$set": {
                                "amount": bal, "locked_amount": 0, "available_amount": bal,
                                "source": "on_chain", "last_synced": now, "updated_at": now,
                            }, "$setOnInsert": {"_id": str(uuid.uuid4()), "asset": stable, "created_at": now}},
                            upsert=True,
                        )
                except Exception as e:
                    logger.debug(f"[TREASURY] Could not read {stable} balance: {e}")

            logger.info(f"[TREASURY] Initialized: NENO={neno_bal}, BNB={bnb_bal}")
        except Exception as e:
            logger.error(f"[TREASURY] Initialization error: {e}")

    async def sync_onchain_balances(self):
        """Re-sync treasury crypto balances from on-chain state."""
        await self.initialize_treasury()
        return await self.get_treasury_inventory()

    # ─────────────────────────────────────────────
    #  DYNAMIC PRICING ENGINE
    # ─────────────────────────────────────────────

    async def get_pricing(self) -> dict:
        """
        Calculate full bid/ask pricing for NENO.
        Returns mid_price, bid, ask, spread, skew data.
        """
        # 1. Get mid price from existing dynamic pricing
        from routes.neno_exchange_routes import _get_dynamic_neno_price
        pricing = await _get_dynamic_neno_price()
        mid_price = pricing["price"]

        # 2. Get treasury NENO inventory for skew
        neno_inv = await self.get_asset_inventory("NENO")
        neno_amount = neno_inv["available_amount"]

        # 3. Calculate inventory skew
        if TARGET_NENO_INVENTORY > 0:
            inventory_ratio = neno_amount / TARGET_NENO_INVENTORY
        else:
            inventory_ratio = 1.0

        # skew > 0 means treasury is LONG NENO (has too much)
        #   → lower ask to encourage buys from treasury
        #   → raise bid to discourage more sells to treasury
        # skew < 0 means treasury is SHORT NENO
        #   → raise ask to discourage buys
        #   → lower bid to encourage sells to treasury
        raw_skew = (inventory_ratio - 1.0) * SKEW_FACTOR
        skew_bps = max(-MAX_SPREAD_BPS / 2, min(MAX_SPREAD_BPS / 2, raw_skew * 10000))

        # 4. Volatility from 24h volume
        vol_24h = pricing.get("buy_volume_24h", 0) + pricing.get("sell_volume_24h", 0)
        vol_adj_bps = min(vol_24h / max(VOLUME_THRESHOLD, 0.01), 1.0) * VOLATILITY_FACTOR * 10000

        # 5. Total spread
        total_spread_bps = BASE_SPREAD_BPS + abs(skew_bps) + vol_adj_bps
        total_spread_bps = max(MIN_SPREAD_BPS, min(MAX_SPREAD_BPS, total_spread_bps))
        spread_pct = total_spread_bps / 10000

        # 6. Bid / Ask
        # skew_bps > 0 (long): shift both down to sell inventory
        # skew_bps < 0 (short): shift both up to accumulate
        skew_shift = (skew_bps / 10000) * mid_price
        bid = round(mid_price * (1 - spread_pct / 2) + skew_shift, 2)
        ask = round(mid_price * (1 + spread_pct / 2) + skew_shift, 2)

        # Ensure bid < ask
        if bid >= ask:
            bid = round(ask - mid_price * (MIN_SPREAD_BPS / 10000), 2)

        return {
            "mid_price": round(mid_price, 2),
            "bid": bid,
            "ask": ask,
            "spread_bps": round(total_spread_bps, 1),
            "spread_pct": round(spread_pct * 100, 3),
            "spread_eur": round(ask - bid, 2),
            "inventory_skew": round(raw_skew, 6),
            "inventory_ratio": round(inventory_ratio, 4),
            "treasury_neno": round(neno_amount, 4),
            "target_inventory": TARGET_NENO_INVENTORY,
            "volatility_24h_bps": round(vol_adj_bps, 1),
            "volume_24h": round(vol_24h, 4),
            "base_price_data": pricing,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def get_effective_price(self, direction: str, mid: float, bid: float, ask: float) -> float:
        """Get the price the user gets based on direction."""
        if direction == "buy":
            return ask   # user buys at ask (pays more)
        else:
            return bid   # user sells at bid (receives less)

    # ─────────────────────────────────────────────
    #  INTERNAL MATCHING ENGINE
    # ─────────────────────────────────────────────

    async def try_internal_match(
        self, order_type: str, asset: str, neno_amount: float, price_eur: float
    ) -> Optional[dict]:
        """
        Try to match an order against the internal order book.
        Returns match info or None if no match found.
        """
        db = get_database()
        opposite = "sell" if order_type == "buy" else "buy"

        match = await db.mm_order_book.find_one_and_update(
            {
                "type": opposite, "asset": asset.upper(),
                "remaining_amount": {"$gte": neno_amount},
                "status": "pending",
            },
            {
                "$inc": {"remaining_amount": -neno_amount, "filled_amount": neno_amount},
                "$set": {"updated_at": datetime.now(timezone.utc).isoformat()},
            },
            return_document=False,
        )

        if match:
            # Check if fully filled
            new_remaining = match.get("remaining_amount", 0) - neno_amount
            if new_remaining <= 0.00000001:
                await db.mm_order_book.update_one(
                    {"_id": match["_id"]},
                    {"$set": {"status": "filled", "filled_at": datetime.now(timezone.utc).isoformat()}}
                )

            gas_saved = round(neno_amount * price_eur * 0.002, 4)
            logger.info(f"[MATCH] Internal match: {order_type} {neno_amount} NENO vs order {match.get('id','?')}")
            return {
                "matched": True,
                "counterparty_order_id": str(match.get("id", "")),
                "counterparty_user_id": match.get("user_id", ""),
                "matched_amount": neno_amount,
                "internalized": True,
                "gas_saved_eur": gas_saved,
            }
        return None

    async def submit_to_order_book(
        self, user_id: str, order_type: str, asset: str,
        neno_amount: float, price_eur: float
    ) -> str:
        """Submit a resting order to the internal book for future matching."""
        db = get_database()
        order_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        await db.mm_order_book.insert_one({
            "_id": order_id, "id": order_id, "user_id": user_id,
            "type": order_type, "asset": asset.upper(),
            "amount": neno_amount, "remaining_amount": neno_amount,
            "filled_amount": 0, "price_eur": price_eur,
            "status": "pending",
            "created_at": now, "updated_at": now,
            "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat(),
        })
        return order_id

    # ─────────────────────────────────────────────
    #  TREASURY COUNTERPARTY EXECUTION
    # ─────────────────────────────────────────────

    async def execute_as_counterparty(
        self, tx_id: str, user_id: str, direction: str,
        neno_amount: float, counter_asset: str, counter_amount: float,
        fee_amount: float, fee_asset: str,
        effective_price: float, mid_price: float,
    ) -> dict:
        """
        Execute a trade with Treasury as counterparty.
        Updates treasury inventory and records PnL.
        """
        db = get_database()
        now = datetime.now(timezone.utc).isoformat()

        from routes.neno_exchange_routes import MARKET_PRICES_EUR
        neno_price_eur = effective_price
        counter_price_eur = MARKET_PRICES_EUR.get(counter_asset.upper(), 0)
        if counter_asset.upper() == "NENO":
            counter_price_eur = effective_price

        if direction == "buy":
            # User BUYS NENO → Treasury SELLS NENO
            # Treasury: -NENO, +counter_asset
            await self.update_treasury("NENO", -neno_amount, "trade_sell", neno_price_eur)
            await self.update_treasury(counter_asset, counter_amount, "trade_receive", counter_price_eur)
        else:
            # User SELLS NENO → Treasury BUYS NENO
            # Treasury: +NENO, -counter_asset
            await self.update_treasury("NENO", neno_amount, "trade_buy", neno_price_eur)
            await self.update_treasury(counter_asset, -counter_amount, "trade_pay", counter_price_eur)

        # Revenue from spread
        spread_revenue = abs(effective_price - mid_price) * neno_amount
        total_revenue = spread_revenue + (fee_amount * (counter_price_eur if counter_price_eur > 0 else 1))

        # Record PnL entry
        pnl_entry = {
            "_id": str(uuid.uuid4()),
            "tx_id": tx_id,
            "user_id": user_id,
            "direction": direction,
            "neno_amount": neno_amount,
            "counter_asset": counter_asset,
            "counter_amount": counter_amount,
            "effective_price": effective_price,
            "mid_price": mid_price,
            "spread_revenue_eur": round(spread_revenue, 4),
            "fee_revenue_eur": round(fee_amount * (counter_price_eur if counter_price_eur > 0 else 1), 4),
            "total_revenue_eur": round(total_revenue, 4),
            "inventory_change_neno": round(-neno_amount if direction == "buy" else neno_amount, 8),
            "inventory_change_counter": round(counter_amount if direction == "buy" else -counter_amount, 8),
            "created_at": now,
        }
        await db.mm_pnl_ledger.insert_one(pnl_entry)

        logger.info(
            f"[MM] Counterparty trade: {direction} {neno_amount} NENO @ {effective_price} EUR "
            f"| spread_rev={spread_revenue:.4f} fee_rev={fee_amount:.4f} total={total_revenue:.4f}"
        )

        return {
            "counterparty": "treasury",
            "effective_price": effective_price,
            "mid_price": mid_price,
            "spread_revenue_eur": round(spread_revenue, 4),
            "fee_revenue_eur": round(fee_amount * (counter_price_eur if counter_price_eur > 0 else 1), 4),
            "total_revenue_eur": round(total_revenue, 4),
        }

    # ─────────────────────────────────────────────
    #  PNL & ACCOUNTING
    # ─────────────────────────────────────────────

    async def get_pnl_report(self, hours: int = 24) -> dict:
        """Get PnL report for the specified time window."""
        db = get_database()
        since = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()

        pipeline = [
            {"$match": {"created_at": {"$gte": since}}},
            {"$group": {
                "_id": None,
                "total_spread_revenue": {"$sum": "$spread_revenue_eur"},
                "total_fee_revenue": {"$sum": "$fee_revenue_eur"},
                "total_revenue": {"$sum": "$total_revenue_eur"},
                "total_neno_change": {"$sum": "$inventory_change_neno"},
                "trade_count": {"$sum": 1},
                "buy_count": {"$sum": {"$cond": [{"$eq": ["$direction", "buy"]}, 1, 0]}},
                "sell_count": {"$sum": {"$cond": [{"$eq": ["$direction", "sell"]}, 1, 0]}},
            }},
        ]
        results = await db.mm_pnl_ledger.aggregate(pipeline).to_list(1)

        # Also get legacy treasury_fees
        legacy_pipeline = [
            {"$group": {"_id": "$fee_asset", "total": {"$sum": "$fee_amount"}, "count": {"$sum": 1}}}
        ]
        legacy = await db.treasury_fees.aggregate(legacy_pipeline).to_list(50)
        legacy_eur = sum(r["total"] for r in legacy if r["_id"] == "EUR")

        treasury = await self.get_treasury_inventory()

        if results:
            r = results[0]
            return {
                "period_hours": hours,
                "spread_revenue_eur": round(r["total_spread_revenue"], 4),
                "fee_revenue_eur": round(r["total_fee_revenue"], 4),
                "total_revenue_eur": round(r["total_revenue"], 4),
                "legacy_fees_eur": round(legacy_eur, 4),
                "combined_revenue_eur": round(r["total_revenue"] + legacy_eur, 4),
                "inventory_change_neno": round(r["total_neno_change"], 8),
                "trade_count": r["trade_count"],
                "buy_count": r["buy_count"],
                "sell_count": r["sell_count"],
                "treasury": treasury,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        return {
            "period_hours": hours,
            "spread_revenue_eur": 0, "fee_revenue_eur": 0,
            "total_revenue_eur": 0, "legacy_fees_eur": round(legacy_eur, 4),
            "combined_revenue_eur": round(legacy_eur, 4),
            "inventory_change_neno": 0,
            "trade_count": 0, "buy_count": 0, "sell_count": 0,
            "treasury": treasury,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    # ─────────────────────────────────────────────
    #  OFF-RAMP FALLBACK (USDT/USDC)
    # ─────────────────────────────────────────────

    async def execute_stablecoin_offramp(
        self, user_id: str, amount_eur: float, destination_wallet: str,
        preferred_stable: str = "USDT"
    ) -> dict:
        """
        Off-ramp fallback: send USDT or USDC to user's wallet when NIUM is not configured.
        Returns execution result with tx_hash.
        """
        stable = preferred_stable.upper()
        if stable not in ("USDT", "USDC"):
            stable = "USDT"

        # EUR to stablecoin (1 EUR ≈ 1.087 USD, stablecoins ≈ 1 USD)
        stable_amount = round(amount_eur * 1.087, 6)

        # Check treasury has enough stablecoin
        inv = await self.get_asset_inventory(stable)
        if inv["available_amount"] < stable_amount:
            # Try the other stablecoin
            alt = "USDC" if stable == "USDT" else "USDT"
            alt_inv = await self.get_asset_inventory(alt)
            if alt_inv["available_amount"] >= stable_amount:
                stable = alt
            else:
                return {
                    "success": False,
                    "error": f"Treasury {stable}/{alt} insufficiente per off-ramp: necessario {stable_amount}, disponibile {inv['available_amount']}/{alt_inv['available_amount']}",
                }

        # Execute on-chain transfer
        try:
            from services.execution_engine import ExecutionEngine, ERC20_ABI
            engine = ExecutionEngine.get_instance()
            w3 = engine._get_web3()
            if not w3 or not engine._hot_key:
                return {"success": False, "error": "Web3 o chiave privata non disponibile"}

            from web3 import Web3
            contract_addr = TOKEN_CONTRACTS[stable]
            to_addr = Web3.to_checksum_address(destination_wallet)
            contract = w3.eth.contract(
                address=Web3.to_checksum_address(contract_addr), abi=ERC20_ABI
            )
            decimals = TOKEN_DECIMALS.get(stable, 18)
            raw_amount = int(Decimal(str(stable_amount)) * Decimal(10 ** decimals))

            balance = contract.functions.balanceOf(engine.hot_wallet).call()
            if balance < raw_amount:
                return {"success": False, "error": f"Hot wallet {stable} insufficiente on-chain"}

            nonce = w3.eth.get_transaction_count(engine.hot_wallet, "pending")
            tx = contract.functions.transfer(to_addr, raw_amount).build_transaction({
                "chainId": 56, "gas": 100000,
                "gasPrice": w3.eth.gas_price,
                "nonce": nonce, "from": engine.hot_wallet,
            })
            signed = w3.eth.account.sign_transaction(tx, engine._hot_key)
            tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction).hex()
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)

            if receipt["status"] == 1:
                # Update treasury
                await self.update_treasury(stable, -stable_amount, "offramp_external", 0.92)
                return {
                    "success": True,
                    "tx_hash": tx_hash,
                    "stable_asset": stable,
                    "stable_amount": stable_amount,
                    "destination": destination_wallet,
                    "block_number": receipt["blockNumber"],
                    "explorer": f"https://bscscan.com/tx/{tx_hash}",
                    "state": "payout_executed_external",
                }
            else:
                return {"success": False, "error": "Transaction reverted on-chain"}
        except Exception as e:
            logger.error(f"[MM] Stablecoin off-ramp failed: {e}")
            return {"success": False, "error": str(e)}
