from typing import Optional
from decimal import Decimal
from pydantic import BaseModel

class SwapRequest(BaseModel):
    user_id: str
    from_token: str
    to_token: str
    amount_in: Decimal
    chain: str = "bsc"
    slippage: float = 0.8

class SwapResult(BaseModel):
    success: bool
    tx_hash: Optional[str] = None
    amount_out_min: Optional[Decimal] = None
    error: Optional[str] = None

class SwapEngine:
    def __init__(self):
        pass

    async def execute_swap(self, request):
        # Versione placeholder - restituisce sempre successo per far passare gli import
        return SwapResult(
            success=True,
            tx_hash="0xSIMULATED_SWAP_" + str(hash(request)),
            amount_out_min=request.amount_in * Decimal("0.95"),
            error=None
        )
