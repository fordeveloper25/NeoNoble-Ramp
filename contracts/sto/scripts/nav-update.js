/**
 * scripts/nav-update.js — aggiorna il NAV on-chain dopo la certificazione
 * del revisore trimestrale.
 *
 * Uso:
 *   ORACLE_ADDRESS=0x... NEW_NAV=260000000 EFFECTIVE_FROM=1893456000 \
 *     REPORT_HASH=0x... npx hardhat run scripts/nav-update.js --network polygon
 *
 * NEW_NAV = prezzo per 1 token (wei del settlement token; USDC = 6 dec)
 * REPORT_HASH = keccak256 o CID IPFS del report NAV firmato dal revisore
 */
const hre = require("hardhat");

async function main() {
  const { ORACLE_ADDRESS, NEW_NAV, EFFECTIVE_FROM, REPORT_HASH } = process.env;
  if (!ORACLE_ADDRESS || !NEW_NAV || !EFFECTIVE_FROM || !REPORT_HASH) {
    throw new Error("ORACLE_ADDRESS, NEW_NAV, EFFECTIVE_FROM, REPORT_HASH obbligatori");
  }
  const oracle = await hre.ethers.getContractAt("NAVOracle", ORACLE_ADDRESS);
  const tx = await oracle.updateNAV(NEW_NAV, Number(EFFECTIVE_FROM), REPORT_HASH);
  console.log("tx:", tx.hash);
  await tx.wait();
  console.log("✅ NAV aggiornato a", NEW_NAV);
}
main().catch((e) => { console.error(e); process.exit(1); });
