const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("NeoNoble STO — flow end-to-end", function () {
  let owner, treasury, alice, bob, carol;
  let registry, compliance, token, oracle, redemption, revShare, usdc;

  const USDC_DECIMALS = 6;
  const NAV = ethers.parseUnits("250", USDC_DECIMALS); // 250 USDC per token
  const ONE_YEAR = 365 * 24 * 3600;

  beforeEach(async () => {
    [owner, treasury, alice, bob, carol] = await ethers.getSigners();

    // Mock USDC
    const MockERC20 = await ethers.getContractFactory("MockERC20");
    usdc = await MockERC20.deploy("USDC", "USDC", USDC_DECIMALS);

    const IdentityRegistry = await ethers.getContractFactory("IdentityRegistry");
    registry = await IdentityRegistry.deploy(owner.address);

    const DefaultCompliance = await ethers.getContractFactory("DefaultCompliance");
    compliance = await DefaultCompliance.deploy(owner.address, await registry.getAddress());

    const Token = await ethers.getContractFactory("NenoSecurityToken");
    token = await Token.deploy("NNRS", "NNRS", owner.address,
      await registry.getAddress(), await compliance.getAddress());

    await compliance.setToken(await token.getAddress());
    await token.setAgent(owner.address, true);

    const Oracle = await ethers.getContractFactory("NAVOracle");
    oracle = await Oracle.deploy(owner.address, await usdc.getAddress(), NAV);

    const Redemption = await ethers.getContractFactory("RedemptionVault");
    redemption = await Redemption.deploy(
      owner.address, await token.getAddress(),
      await oracle.getAddress(), await usdc.getAddress()
    );
    await token.setAgent(await redemption.getAddress(), true);
    await compliance.setExempt(await redemption.getAddress(), true);

    const RevShare = await ethers.getContractFactory("RevenueShareVault");
    revShare = await RevShare.deploy(
      owner.address, await token.getAddress(), await usdc.getAddress()
    );

    // KYC registrati
    const exp = Math.floor(Date.now() / 1000) + ONE_YEAR;
    await registry.registerIdentity(alice.address, 380, exp, ethers.id("SUMSUB"));
    await registry.registerIdentity(bob.address,   380, exp, ethers.id("SUMSUB"));
    // carol NON verificata
  });

  it("mint funziona solo verso address whitelisted", async () => {
    await token.mint(alice.address, ethers.parseEther("10"));
    expect(await token.balanceOf(alice.address)).to.eq(ethers.parseEther("10"));
    await expect(token.mint(carol.address, ethers.parseEther("1")))
      .to.be.revertedWith("compliance");
  });

  it("transfer blocca destinatari non KYC", async () => {
    await token.mint(alice.address, ethers.parseEther("10"));
    await expect(token.connect(alice).transfer(carol.address, ethers.parseEther("1")))
      .to.be.revertedWith("compliance");
    await token.connect(alice).transfer(bob.address, ethers.parseEther("1"));
    expect(await token.balanceOf(bob.address)).to.eq(ethers.parseEther("1"));
  });

  it("max holders enforced", async () => {
    await compliance.setMaxHolders(1);
    await token.mint(alice.address, ethers.parseEther("10"));
    await expect(token.mint(bob.address, ethers.parseEther("1")))
      .to.be.revertedWith("compliance");
  });

  it("redemption a NAV con riserva", async () => {
    await token.mint(alice.address, ethers.parseEther("4"));  // 4 token
    // tesoreria alimenta la riserva con 1000 USDC
    await usdc.mint(treasury.address, ethers.parseUnits("1000", USDC_DECIMALS));
    await usdc.connect(treasury).approve(await redemption.getAddress(), ethers.parseUnits("1000", USDC_DECIMALS));
    await redemption.connect(treasury).fund(ethers.parseUnits("1000", USDC_DECIMALS));

    // alice chiede redemption di 4 token @ 250 USDC = 1000 USDC
    await token.connect(alice).approve(await redemption.getAddress(), ethers.parseEther("4"));
    await redemption.connect(alice).requestRedemption(ethers.parseEther("4"));

    await redemption.approve(1);
    await redemption.connect(alice).claim(1);

    expect(await usdc.balanceOf(alice.address)).to.eq(ethers.parseUnits("1000", USDC_DECIMALS));
    expect(await token.balanceOf(alice.address)).to.eq(0);
  });

  it("redemption rifiutata se riserva insufficiente", async () => {
    await token.mint(alice.address, ethers.parseEther("10"));
    await token.connect(alice).approve(await redemption.getAddress(), ethers.parseEther("10"));
    await redemption.connect(alice).requestRedemption(ethers.parseEther("10"));
    await expect(redemption.approve(1)).to.be.revertedWith("reserve insufficient");
  });

  it("revenue share pro-rata", async () => {
    await token.mint(alice.address, ethers.parseEther("30"));
    await token.mint(bob.address,   ethers.parseEther("70"));
    // tesoreria distribuisce 100 USDC
    await usdc.mint(owner.address, ethers.parseUnits("100", USDC_DECIMALS));
    await usdc.approve(await revShare.getAddress(), ethers.parseUnits("100", USDC_DECIMALS));
    await revShare.distribute(ethers.parseUnits("100", USDC_DECIMALS));

    await revShare.connect(alice).claim(0);
    await revShare.connect(bob).claim(0);

    expect(await usdc.balanceOf(alice.address)).to.eq(ethers.parseUnits("30", USDC_DECIMALS));
    expect(await usdc.balanceOf(bob.address)).to.eq(ethers.parseUnits("70", USDC_DECIMALS));
  });

  it("forced transfer loggato e soggetto a compliance su destinatario", async () => {
    await token.mint(alice.address, ethers.parseEther("5"));
    // forced transfer alice → carol (non KYC) deve fallire
    await expect(token.forcedTransfer(alice.address, carol.address, ethers.parseEther("5"), "ordine CONSOB"))
      .to.be.revertedWith("compliance");
    // forced alice → bob ok
    await expect(token.forcedTransfer(alice.address, bob.address, ethers.parseEther("5"), "recupero chiavi"))
      .to.emit(token, "ForcedTransfer")
      .withArgs(alice.address, bob.address, ethers.parseEther("5"), "recupero chiavi");
  });

  it("pause blocca tutti i trasferimenti ma non mint/burn agent", async () => {
    await token.mint(alice.address, ethers.parseEther("5"));
    await token.pause();
    await expect(token.connect(alice).transfer(bob.address, ethers.parseEther("1")))
      .to.be.revertedWith("paused");
    // burn by agent NON va in pause check
    await token.burn(alice.address, ethers.parseEther("1"));
    expect(await token.balanceOf(alice.address)).to.eq(ethers.parseEther("4"));
  });

  it("lockup blocca transfer tra investitori ma non mint", async () => {
    const future = Math.floor(Date.now() / 1000) + 3600;
    await compliance.setLockup(future);
    await token.mint(alice.address, ethers.parseEther("5"));
    await expect(token.connect(alice).transfer(bob.address, ethers.parseEther("1")))
      .to.be.revertedWith("compliance");
  });
});
