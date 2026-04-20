/**
 * scripts/whitelist-add.js — aggiunge un investitore all'IdentityRegistry
 *
 * Uso:
 *   REGISTRY_ADDRESS=0x... INVESTOR_ADDRESS=0x... INVESTOR_COUNTRY=380 \
 *     KYC_PROVIDER=SUMSUB EXPIRES_UNIX=1893456000 \
 *     npx hardhat run scripts/whitelist-add.js --network polygon
 */
const hre = require("hardhat");

async function main() {
  const {
    REGISTRY_ADDRESS,
    INVESTOR_ADDRESS,
    INVESTOR_COUNTRY = "380",
    KYC_PROVIDER = "SUMSUB",
    EXPIRES_UNIX,
  } = process.env;

  if (!REGISTRY_ADDRESS || !INVESTOR_ADDRESS || !EXPIRES_UNIX) {
    throw new Error("REGISTRY_ADDRESS, INVESTOR_ADDRESS, EXPIRES_UNIX sono obbligatorie");
  }

  const registry = await hre.ethers.getContractAt("IdentityRegistry", REGISTRY_ADDRESS);
  const tx = await registry.registerIdentity(
    INVESTOR_ADDRESS,
    Number(INVESTOR_COUNTRY),
    Number(EXPIRES_UNIX),
    hre.ethers.id(KYC_PROVIDER)
  );
  console.log("tx:", tx.hash);
  await tx.wait();
  console.log("✅ whitelisted", INVESTOR_ADDRESS);
}
main().catch((e) => { console.error(e); process.exit(1); });
