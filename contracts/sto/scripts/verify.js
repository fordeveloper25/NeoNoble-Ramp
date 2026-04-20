/**
 * scripts/verify.js — verifica dei contratti deployati su Polygonscan.
 *
 * Lanciare DOPO deploy.js. Richiede POLYGONSCAN_API_KEY.
 *
 * Uso:
 *   REGISTRY=0x... COMPLIANCE=0x... TOKEN=0x... ORACLE=0x... \
 *     REDEMPTION=0x... REVSHARE=0x... \
 *     npx hardhat run scripts/verify.js --network polygon
 */
const hre = require("hardhat");

async function verify(address, args) {
  try {
    await hre.run("verify:verify", { address, constructorArguments: args });
    console.log("✅", address);
  } catch (e) {
    console.log("skip", address, "—", e.message.split("\n")[0]);
  }
}

async function main() {
  const {
    REGISTRY, COMPLIANCE, TOKEN, ORACLE, REDEMPTION, REVSHARE,
    TREASURY_ADDRESS, STO_TOKEN_NAME, STO_TOKEN_SYMBOL,
    INITIAL_NAV,
  } = process.env;

  const SETTLEMENT = hre.network.name === "polygon"
    ? process.env.SETTLEMENT_TOKEN_POLYGON
    : process.env.SETTLEMENT_TOKEN_AMOY;

  const [deployer] = await hre.ethers.getSigners();
  const owner = deployer.address;

  if (REGISTRY) await verify(REGISTRY, [owner]);
  if (COMPLIANCE) await verify(COMPLIANCE, [owner, REGISTRY]);
  if (TOKEN) await verify(TOKEN, [STO_TOKEN_NAME, STO_TOKEN_SYMBOL, owner, REGISTRY, COMPLIANCE]);
  if (ORACLE) await verify(ORACLE, [owner, SETTLEMENT, INITIAL_NAV]);
  if (REDEMPTION) await verify(REDEMPTION, [owner, TOKEN, ORACLE, SETTLEMENT]);
  if (REVSHARE) await verify(REVSHARE, [owner, TOKEN, SETTLEMENT]);
}
main().catch((e) => { console.error(e); process.exit(1); });
