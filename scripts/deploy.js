const hre = require("hardhat");
const fs = require("fs");
const path = require("path");

async function main() {
  console.log("=====================================");
  console.log("NGX Stock Oracle Deployment");
  console.log("=====================================\n");

  // Get deployer account
  const [deployer] = await hre.ethers.getSigners();
  console.log("Deploying contracts with account:", deployer.address);

  // Check balance
  const balance = await hre.ethers.provider.getBalance(deployer.address);
  console.log("Account balance:", hre.ethers.formatEther(balance), "ETH\n");

  if (balance === 0n) {
    console.error("ERROR: Account has no ETH for gas!");
    console.log("\nGet Sepolia test ETH from:");
    console.log("- https://sepoliafaucet.com");
    console.log("- https://www.infura.io/faucet/sepolia\n");
    process.exit(1);
  }

  // Deploy contract
  console.log("Deploying SimpleStockOracle contract...");
  const SimpleStockOracle = await hre.ethers.getContractFactory("SimpleStockOracle");
  const oracle = await SimpleStockOracle.deploy();

  await oracle.waitForDeployment();
  const contractAddress = await oracle.getAddress();

  console.log("\nContract deployed successfully!");
  console.log("=====================================");
  console.log("Contract Address:", contractAddress);
  console.log("Owner:", deployer.address);

  const network = await hre.ethers.provider.getNetwork();
  console.log("Network:", network.name);
  console.log("Chain ID:", network.chainId.toString());
  console.log("=====================================\n");

  // === Save deployment info (BigInt-safe) ===
  const blockNumber = await hre.ethers.provider.getBlockNumber();

  const deploymentInfo = {
    contractAddress,
    owner: deployer.address,
    network: network.name,
    chainId: network.chainId.toString(),           // BigInt → string
    deployedAt: new Date().toISOString(),
    blockNumber: blockNumber.toString()             // BigInt → string
  };

  const deploymentPath = path.join(process.cwd(), "deployment-info.json");

  fs.writeFileSync(
    deploymentPath,
    JSON.stringify(
      deploymentInfo,
      (key, value) => (typeof value === "bigint" ? value.toString() : value), // Extra safety
      2
    )
  );

  console.log("Deployment info saved to:", deploymentPath);

  // === Update .env file ===
  const envPath = path.join(process.cwd(), ".env");
  if (fs.existsSync(envPath)) {
    let envContent = fs.readFileSync(envPath, "utf8");

    const newLine = `ORACLE_CONTRACT_ADDRESS=${contractAddress}`;

    if (envContent.includes("ORACLE_CONTRACT_ADDRESS=")) {
      envContent = envContent.replace(/ORACLE_CONTRACT_ADDRESS=.*/g, newLine);
    } else {
      envContent += (envContent.endsWith("\n") ? "" : "\n") + newLine + "\n";
    }

    fs.writeFileSync(envPath, envContent);
    console.log("Updated .env with contract address\n");
  } else {
    console.log(".env file not found – skipping update");
  }

  // === Verify on Etherscan (if API key exists and not local) ===
  if (process.env.ETHERSCAN_API_KEY && network.name !== "hardhat" && network.name !== "localhost") {
    console.log("\nWaiting 30 seconds before verification (to ensure block propagation)...");
    await new Promise((resolve) => setTimeout(resolve, 30000));

    console.log("Verifying contract on Etherscan...");
    try {
      await hre.run("verify:verify", {
        address: contractAddress,
        constructorArguments: [],
      });
      console.log("Contract verified successfully!");
    } catch (error) {
      console.log("Verification failed (this is common on testnets):", error.message);
      console.log(`You can verify manually later:\n  npx hardhat verify --network ${network.name} ${contractAddress}`);
    }
  }

  // === Final success message ===
  console.log("\n=====================================");
  console.log("DEPLOYMENT COMPLETE!");
  console.log("=====================================");
  console.log("\nNext Steps:");
  console.log("1. Contract deployed at:", contractAddress);
  console.log("2. Address saved to .env and deployment-info.json");

  // Explorer link
  let explorerUrl = "";
  if (network.chainId === 11155111n) {
    explorerUrl = `https://sepolia.etherscan.io/address/${contractAddress}`;
  } else if (network.chainId === 137n) {
    explorerUrl = `https://polygonscan.com/address/${contractAddress}`;
  } else if (network.chainId === 1n) {
    explorerUrl = `https://etherscan.io/address/${contractAddress}`;
  } else if (network.chainId === 80001n) {
    explorerUrl = `https://mumbai.polygonscan.com/address/${contractAddress}`;
  }

  if (explorerUrl) {
    console.log("3. View on block explorer:\n   ", explorerUrl);
  }

  console.log("\n4. Start the price keeper:");
  console.log("   cd keeper");
  console.log("   python ngx_oracle_keeper.py");
  console.log("\n5. Validate everything works:");
  console.log("   npm run validate\n");
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error("\nDeployment failed:", error);
    process.exit(1);
  });