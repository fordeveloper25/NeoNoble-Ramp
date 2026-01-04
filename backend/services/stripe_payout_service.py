"""
Stripe SEPA Payout Service for NeoNoble Ramp.

Handles SEPA bank transfers after successful crypto deposits.
"""

import os
import logging
from typing import Optional, Dict, Tuple
from datetime import datetime, timezone
from decimal import Decimal
import stripe
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


class StripePayoutService:
    """
    Stripe integration for SEPA payouts.
    
    Handles creating payouts to the configured IBAN after
    crypto deposits are confirmed on-chain.
    """
    
    # Default payout destination
    DEFAULT_IBAN = "IT22B0200822800000103317304"
    DEFAULT_BENEFICIARY = "Massimo Fornara"
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.payouts_collection = db.stripe_payouts
        self._initialized = False
    
    def _initialize_stripe(self) -> bool:
        """
        Initialize Stripe with API key from environment.
        
        Returns True if initialized successfully, False otherwise.
        """
        if self._initialized:
            return True
        
        api_key = os.environ.get('STRIPE_SECRET_KEY')
        if not api_key:
            logger.warning(
                "STRIPE_SECRET_KEY not set. Stripe payouts will be disabled. "
                "Set this environment variable to enable real payouts."
            )
            return False
        
        stripe.api_key = api_key
        self._initialized = True
        logger.info("Stripe initialized successfully")
        return True
    
    async def initialize(self):
        """Initialize the payout service."""
        # Create indexes
        await self.payouts_collection.create_index("payout_id", unique=True, sparse=True)
        await self.payouts_collection.create_index("quote_id")
        await self.payouts_collection.create_index("transaction_id")
        await self.payouts_collection.create_index("status")
    
    def is_available(self) -> bool:
        """Check if Stripe payouts are available."""
        return self._initialize_stripe()
    
    async def create_payout(
        self,
        quote_id: str,
        transaction_id: str,
        amount_eur: float,
        iban: str = None,
        beneficiary_name: str = None,
        reference: str = None
    ) -> Tuple[Optional[Dict], Optional[str]]:
        """
        Create a SEPA payout via Stripe.
        
        Args:
            quote_id: The quote ID this payout is for
            transaction_id: The transaction ID
            amount_eur: Amount in EUR to payout
            iban: Destination IBAN (defaults to configured IBAN)
            beneficiary_name: Beneficiary name (defaults to configured name)
            reference: Payment reference
            
        Returns:
            Tuple of (payout_info, error_message)
        """
        iban = iban or self.DEFAULT_IBAN
        beneficiary_name = beneficiary_name or self.DEFAULT_BENEFICIARY
        reference = reference or f"NENO-{quote_id[:8]}"
        
        # Check if already processed
        existing = await self.payouts_collection.find_one({
            'quote_id': quote_id,
            'status': {'$in': ['pending', 'paid', 'in_transit']}
        })
        
        if existing:
            logger.warning(f"Payout already exists for quote {quote_id}")
            return existing, None
        
        # Create payout record
        payout_record = {
            'quote_id': quote_id,
            'transaction_id': transaction_id,
            'amount_eur': amount_eur,
            'amount_cents': int(amount_eur * 100),
            'iban': iban,
            'beneficiary_name': beneficiary_name,
            'reference': reference,
            'status': 'pending',
            'created_at': datetime.now(timezone.utc).isoformat(),
            'payout_id': None,
            'stripe_response': None,
            'error': None
        }
        
        # Check if Stripe is available
        if not self._initialize_stripe():
            payout_record['status'] = 'stripe_unavailable'
            payout_record['error'] = 'Stripe API key not configured'
            await self.payouts_collection.insert_one(payout_record)
            
            logger.warning(
                f"Stripe unavailable - payout logged but not executed: "
                f"{amount_eur} EUR to {iban}"
            )
            return payout_record, "Stripe not configured - payout logged for manual processing"
        
        try:
            # For Stripe Connect payouts, we need a connected account
            # For direct SEPA, we use Stripe's Transfer/Payout API
            
            # Option 1: Using Stripe Payouts (requires Stripe balance)
            # This sends from your Stripe balance to a bank account
            
            # First, check if we have a bank account set up
            # In production, you'd have the bank account already added
            
            # Create the payout
            payout = stripe.Payout.create(
                amount=int(amount_eur * 100),  # Amount in cents
                currency='eur',
                description=f"NeoNoble Ramp - {reference}",
                metadata={
                    'quote_id': quote_id,
                    'transaction_id': transaction_id,
                    'iban': iban,
                    'beneficiary': beneficiary_name
                }
            )
            
            payout_record['payout_id'] = payout.id
            payout_record['status'] = payout.status
            payout_record['stripe_response'] = {
                'id': payout.id,
                'status': payout.status,
                'arrival_date': payout.arrival_date,
                'created': payout.created
            }
            
            await self.payouts_collection.insert_one(payout_record)
            
            logger.info(
                f"Stripe payout created: {payout.id} - {amount_eur} EUR to {iban} "
                f"(status: {payout.status})"
            )
            
            return payout_record, None
            
        except stripe.error.InvalidRequestError as e:
            # Handle case where Stripe balance is insufficient or bank not set up
            error_msg = str(e)
            logger.error(f"Stripe payout failed: {error_msg}")
            
            payout_record['status'] = 'failed'
            payout_record['error'] = error_msg
            await self.payouts_collection.insert_one(payout_record)
            
            return payout_record, error_msg
            
        except stripe.error.StripeError as e:
            error_msg = str(e)
            logger.error(f"Stripe error: {error_msg}")
            
            payout_record['status'] = 'failed'
            payout_record['error'] = error_msg
            await self.payouts_collection.insert_one(payout_record)
            
            return payout_record, error_msg
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Unexpected payout error: {error_msg}")
            
            payout_record['status'] = 'failed'
            payout_record['error'] = error_msg
            await self.payouts_collection.insert_one(payout_record)
            
            return payout_record, error_msg
    
    async def create_transfer_to_connected_account(
        self,
        quote_id: str,
        transaction_id: str,
        amount_eur: float,
        connected_account_id: str = None
    ) -> Tuple[Optional[Dict], Optional[str]]:
        """
        Alternative: Create a transfer to a Stripe Connect account.
        
        Use this if you have Stripe Connect set up with a connected account
        that has the destination bank account.
        """
        if not self._initialize_stripe():
            return None, "Stripe not configured"
        
        try:
            transfer = stripe.Transfer.create(
                amount=int(amount_eur * 100),
                currency='eur',
                destination=connected_account_id,
                description=f"NeoNoble Ramp payout - Quote {quote_id}",
                metadata={
                    'quote_id': quote_id,
                    'transaction_id': transaction_id
                }
            )
            
            logger.info(f"Stripe transfer created: {transfer.id}")
            
            return {
                'transfer_id': transfer.id,
                'status': 'succeeded',
                'amount_eur': amount_eur
            }, None
            
        except stripe.error.StripeError as e:
            return None, str(e)
    
    async def get_payout_status(self, payout_id: str) -> Optional[Dict]:
        """Get the status of a payout."""
        if not self._initialize_stripe():
            return None
        
        try:
            payout = stripe.Payout.retrieve(payout_id)
            return {
                'id': payout.id,
                'status': payout.status,
                'amount': payout.amount / 100,
                'arrival_date': payout.arrival_date,
                'failure_message': payout.failure_message
            }
        except stripe.error.StripeError as e:
            logger.error(f"Failed to get payout status: {e}")
            return None
    
    async def get_payout_by_quote(self, quote_id: str) -> Optional[Dict]:
        """Get payout record by quote ID."""
        return await self.payouts_collection.find_one({'quote_id': quote_id})
    
    async def log_payout_for_manual_processing(
        self,
        quote_id: str,
        transaction_id: str,
        amount_eur: float,
        iban: str = None,
        beneficiary_name: str = None
    ) -> Dict:
        """
        Log a payout request for manual processing.
        
        Used when Stripe is not available or as a fallback.
        """
        iban = iban or self.DEFAULT_IBAN
        beneficiary_name = beneficiary_name or self.DEFAULT_BENEFICIARY
        
        payout_record = {
            'quote_id': quote_id,
            'transaction_id': transaction_id,
            'amount_eur': amount_eur,
            'iban': iban,
            'beneficiary_name': beneficiary_name,
            'reference': f"NENO-{quote_id[:8]}",
            'status': 'pending_manual',
            'created_at': datetime.now(timezone.utc).isoformat(),
            'requires_manual_processing': True
        }
        
        await self.payouts_collection.insert_one(payout_record)
        
        logger.info(
            f"Payout logged for manual processing: {amount_eur} EUR to {iban} "
            f"(quote: {quote_id})"
        )
        
        return payout_record
