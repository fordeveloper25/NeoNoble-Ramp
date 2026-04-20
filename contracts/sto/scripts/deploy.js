/**
 * NeoNoble STO — full deployment script
 *
 * Ordine di deploy:
 *   1. IdentityRegistry(owner)
 *   2. DefaultCompliance(owner, registry)
 *   3. NenoSecurityToken(name, symbol, owner, registry, compliance)
 *   4. NAVOracle(owner, settlement, initialNav)
 *   5. RedemptionVault(owner, stoToken, navOracle, settlement)
 *   6. RevenueShareVault(owner, stoToken, settlement)
 *   7. Wiring:
 *      - compliance.setToken(stoToken)
 *      - stoToken.setAgent(deployer, true)              // per future mint
 *      - stoToken.setAgent(redemptionVault, true)       // puo` chiamare burn
 *      - registry.addAgent(deployer)                    // per whitelist
 *      - compliance.setMaxHolders, setLockup, setCountryAllowed...
 *      - identityRegistry.registerIdentity(treasury)    // la tesoreria riceve i token dei mint iniziali
 */

const hre = require("hardhat");
require("dotenv").config();

async function main() {
  const [deployer] = await hre.ethers.getSigners();
  const network = hre.network.name;

  console.log("Deployer:", deployer.address);
  console.log("Network :", network);
  console.log("Balance :", (await hre.ethers.provider.getBalance(deployer.address)).toString());

  const {
    STO_TOKEN_NAME,
    STO_TOKEN_SYMBOL,
    INITIAL_NAV,
    MAX_HOLDERS,
    LOCKUP_UNTIL,
    TREASURY_ADDRESS,
  } = process.env;

  const SETTLEMENT = network === "polygon"
    ? process.env.SETTLEMENT_TOKEN_POLYGON
    : process.env.SETTLEMENT_TOKEN_AMOY;

  if (!STO_TOKEN_NAME || !STO_TOKEN_SYMBOL || !INITIAL_NAV || !SETTLEMENT || !TREASURY_ADDRESS) {
    throw new Error("Env vars mancanti. Compila .env secondo .env.example");
  }

  console.log("\n1/6 IdentityRegistry...");
  const IdentityRegistry = await hre.ethers.getContractFactory("IdentityRegistry");
  const registry = await IdentityRegistry.deploy(deployer.address);
  await registry.waitForDeployment();
  console.log("  ", await registry.getAddress());

  console.log("\n2/6 DefaultCompliance...");
  const Compliance = await hre.ethers.getContractFactory("DefaultCompliance");
  const compliance = await Compliance.deploy(deployer.address, await registry.getAddress());
  await compliance.waitForDeployment();
  console.log("  ", await compliance.getAddress());

  console.log("\n3/6 NenoSecurityToken...");
  const Token = await hre.ethers.getContractFactory("NenoSecurityToken");
  const token = await Token.deploy(
    STO_TOKEN_NAME,
    STO_TOKEN_SYMBOL,
    deployer.address,
    await registry.getAddress(),
    await compliance.getAddress()
  );
  await token.waitForDeployment();
  console.log("  ", await token.getAddress());

  console.log("\n4/6 NAVOracle...");
  const Oracle = await hre.ethers.getContractFactory("NAVOracle");
  const oracle = await Oracle.deploy(deployer.address, SETTLEMENT, INITIAL_NAV);
  await oracle.waitForDeployment();
  console.log("  ", await oracle.getAddress());

  console.log("\n5/6 RedemptionVault...");
  const Redemption = await hre.ethers.getContractFactory("RedemptionVault");
  const redemption = await Redemption.deploy(
    deployer.address,
    await token.getAddress(),
    await oracle.getAddress(),
    SETTLEMENT
  );
  await redemption.waitForDeployment();
  console.log("  ", await redemption.getAddress());

  console.log("\n6/6 RevenueShareVault...");
  const RevenueShare = await hre.ethers.getContractFactory("RevenueShareVault");
  const revShare = await RevenueShare.deploy(
    deployer.address,
    await token.getAddress(),
    SETTLEMENT
  );
  await revShare.waitForDeployment();
  console.log("  ", await revShare.getAddress());

  console.log("\n--- WIRING ---");

  // compliance e` autorizzata dal token
  console.log("compliance.setToken(stoToken)");
  await (await compliance.setToken(await token.getAddress())).wait();

  // redemption vault e deployer sono agent sullo STO token (mint + burn)
  console.log("stoToken.setAgent(deployer, true)");
  await (await token.setAgent(deployer.address, true)).wait();
  console.log("stoToken.setAgent(redemptionVault, true)");
  await (await token.setAgent(await redemption.getAddress(), true)).wait();
  console.log("compliance.setExempt(redemptionVault, true)");
  await (await compliance.setExempt(await redemption.getAddress(), true)).wait();
  console.log("compliance.setExempt(revenueShareVault, true)");
  await (await compliance.setExempt(await revShare.getAddress(), true)).wait();

  // deployer e` agent sul registry
  console.log("registry.addAgent(deployer)");
  await (await registry.addAgent(deployer.address)).wait();

  // compliance config
  if (MAX_HOLDERS && MAX_HOLDERS !== "0") {
    console.log(`compliance.setMaxHolders(${MAX_HOLDERS})`);
    await (await compliance.setMaxHolders(MAX_HOLDERS)).wait();
  }
  if (LOCKUP_UNTIL && LOCKUP_UNTIL !== "0") {
    console.log(`compliance.setLockup(${LOCKUP_UNTIL})`);
    await (await compliance.setLockup(LOCKUP_UNTIL)).wait();
  }

  // La tesoreria deve essere verificata per poter ricevere mint
  console.log("registry.registerIdentity(treasury, IT=380)");
  const oneYearFromNow = Math.floor(Date.now() / 1000) + 365 * 24 * 3600;
  await (await registry.registerIdentity(
    TREASURY_ADDRESS,
    380,  // Italy
    oneYearFromNow,
    hre.ethers.id("SUMSUB")
  )).wait();

  console.log("\n✅ Deploy complete.");
  console.log(JSON.stringify({
    network,
    registry: await registry.getAddress(),
    compliance: await compliance.getAddress(),
    token: await token.getAddress(),
    navOracle: await oracle.getAddress(),
    redemptionVault: await redemption.getAddress(),
    revenueShareVault: await revShare.getAddress(),
  }, null, 2));
}

main().catch((e) => { console.error(e); process.exit(1); });
