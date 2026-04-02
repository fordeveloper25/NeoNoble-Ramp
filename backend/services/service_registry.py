"""
Service Registry — Microservices-ready modular service initialization.

Organizes all service initialization into domain groups:
- Core: Auth, API Keys, Pricing
- Exchange: Trading Engine, NENO Exchange, Advanced Orders
- Wallet: Wallet, Multi-chain, Banking
- Compliance: KYC, AML, Audit
- Infrastructure: Cards, Notifications, Email, TOTP

Each domain can be extracted into its own microservice later.
"""

import logging
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


class ServiceRegistry:
    """Central registry for all platform services."""

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self._services = {}

    def register(self, name: str, service):
        self._services[name] = service

    def get(self, name: str):
        return self._services.get(name)

    async def initialize_all(self):
        """Initialize all registered services."""
        for name, svc in self._services.items():
            if hasattr(svc, 'initialize'):
                try:
                    await svc.initialize()
                    logger.info(f"[Registry] {name} initialized")
                except Exception as e:
                    logger.warning(f"[Registry] {name} initialization failed: {e}")

    def list_services(self) -> dict:
        """List all registered services and their status."""
        return {
            name: {
                "type": type(svc).__name__,
                "initialized": getattr(svc, '_initialized', True),
            }
            for name, svc in self._services.items()
        }


# Domain groups for microservices planning
DOMAIN_GROUPS = {
    "core": {
        "description": "Authentication, API Keys, Pricing",
        "routes": ["auth", "dev_portal", "password"],
        "services": ["AuthService", "PlatformApiKeyService", "PricingService"],
    },
    "exchange": {
        "description": "Trading Engine, NENO Exchange, Advanced Orders, Market Data",
        "routes": ["trading_engine", "neno_exchange", "advanced_orders", "market_data", "price_history"],
        "services": ["ConnectorManager", "DEXService", "BatchExecutor"],
    },
    "wallet": {
        "description": "Wallet, Multi-chain Sync, Banking Rails",
        "routes": ["wallet", "multichain", "banking"],
        "services": ["WalletService", "BlockchainListener", "NiumBankingService"],
    },
    "compliance": {
        "description": "KYC/AML, Audit, Monitoring",
        "routes": ["kyc", "audit", "admin_audit", "monitoring"],
        "services": ["TransactionAuditService", "AuditLogger"],
    },
    "infrastructure": {
        "description": "Cards, Notifications, Email, TOTP, Subscriptions, Tokens",
        "routes": ["card", "notification", "totp", "subscription", "token"],
        "services": ["EmailService", "NiumService"],
    },
    "liquidity": {
        "description": "Treasury, Exposure, Routing, Hedging, Reconciliation",
        "routes": ["liquidity", "por_api", "stripe_payout", "dex"],
        "services": ["TreasuryService", "ExposureService", "HedgingService"],
    },
    "gateway": {
        "description": "API Gateway, Rate Limiting, WebSocket, Public API",
        "routes": ["websocket", "public_api", "export", "nium_onboarding"],
        "services": ["RateLimitMiddleware"],
    },
}


def get_microservice_plan() -> dict:
    """Returns the microservices decomposition plan."""
    return {
        "current_state": "monolith",
        "target_state": "microservices",
        "domains": DOMAIN_GROUPS,
        "migration_steps": [
            "1. Extract Compliance domain (KYC/AML) - lowest coupling",
            "2. Extract Infrastructure domain (Cards/Notifications) - independent services",
            "3. Extract Wallet domain (Multi-chain/Banking) - needs Exchange events",
            "4. Extract Exchange domain (Trading/Orders) - core business logic",
            "5. Extract Core domain (Auth) - shared dependency, extract last",
            "6. Add API Gateway for routing and rate limiting",
        ],
    }
