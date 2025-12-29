from fastapi import FastAPI, APIRouter
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from contextlib import asynccontextmanager

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Validate required environment variables
def validate_env():
    required_vars = ['MONGO_URL', 'DB_NAME']
    missing = [var for var in required_vars if not os.environ.get(var)]
    if missing:
        raise ValueError(f"Missing required environment variables: {missing}")
    
    # Warn about optional but recommended vars
    if not os.environ.get('API_SECRET_ENCRYPTION_KEY'):
        logging.warning(
            "API_SECRET_ENCRYPTION_KEY not set. Platform API keys will not work. "
            "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
        )

validate_env()

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ.get('DB_NAME', 'neonoble_ramp')]

# Import services
from services.auth_service import AuthService
from services.api_key_service import PlatformApiKeyService
from services.ramp_service import RampService
from services.pricing_service import pricing_service

# Import routes
from routes.auth import router as auth_router, set_auth_service
from routes.dev_portal import router as dev_router, set_api_key_service
from routes.ramp_api import router as ramp_api_router, set_services as set_ramp_api_services
from routes.user_ramp import router as user_ramp_router, set_ramp_service

# Initialize services
auth_service = AuthService(db)
api_key_service = PlatformApiKeyService(db)
ramp_service = RampService(db)

# Wire up services to routes
set_auth_service(auth_service)
set_api_key_service(api_key_service)
set_ramp_api_services(ramp_service, api_key_service)
set_ramp_service(ramp_service)

# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logging.info("NeoNoble Ramp API starting up...")
    
    # Create database indexes
    await db.users.create_index("email", unique=True)
    await db.users.create_index("id", unique=True)
    await db.platform_api_keys.create_index("api_key", unique=True)
    await db.platform_api_keys.create_index("id", unique=True)
    await db.platform_api_keys.create_index("user_id")
    await db.transactions.create_index("id", unique=True)
    await db.transactions.create_index("user_id")
    await db.transactions.create_index("reference", unique=True)
    
    logging.info("Database indexes created")
    yield
    
    # Shutdown
    logging.info("NeoNoble Ramp API shutting down...")
    await pricing_service.close()
    client.close()

# Create the main app
app = FastAPI(
    title="NeoNoble Ramp API",
    description="Crypto on/off-ramp platform with HMAC-secured API access",
    version="1.0.0",
    lifespan=lifespan
)

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Root endpoint
@api_router.get("/")
async def root():
    return {
        "message": "Welcome to NeoNoble Ramp API",
        "version": "1.0.0",
        "docs": "/docs"
    }

# Health check
@api_router.get("/health")
async def health():
    return {"status": "healthy", "service": "NeoNoble Ramp"}

# Include all routers
api_router.include_router(auth_router)
api_router.include_router(dev_router)
api_router.include_router(ramp_api_router)
api_router.include_router(user_ramp_router)

# Include the main router
app.include_router(api_router)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
