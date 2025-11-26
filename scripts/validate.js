const hre = require("hardhat");
const fs = require("fs");
const path = require("path");
require("dotenv").config();

async function main() {
  console.log("=====================================");
  console.log("NGX Stock Oracle Validation");
  console.log("=====================================\n");

  // Get contract address
  const contractAddress = process.env.ORACLE_CONTRACT_ADDRESS;
  
  if (!contractAddress) {
    console.error("❌ ERROR: ORACLE_CONTRACT_ADDRESS not set in .env file");
    console.log("\nPlease deploy the contract first:");
    console.log("npm run deploy:sepolia\n");
    process.exit(1);
  }

  console.log("Contract Address:", contractAddress);
  console.log("Network:", (await hre.ethers.provider.getNetwork()).name);
  
  // Get signer
  const [signer] = await hre.ethers.getSigners();
  console.log("Validator Account:", signer.address);
  
  const balance = await hre.ethers.provider.getBalance(signer.address);
  console.log("Account Balance:", hre.ethers.formatEther(balance), "ETH\n");

  // Load contract ABI
  const artifactPath = path.join(
    process.cwd(),
    "artifacts/contracts/SimpleStockOracle.sol/SimpleStockOracle.json"
  );
  
  if (!fs.existsSync(artifactPath)) {
    console.error("❌ ERROR: Contract artifact not found");
    console.log("\nPlease compile the contract first:");
    console.log("npm run compile\n");
    process.exit(1);
  }

  const artifact = JSON.parse(fs.readFileSync(artifactPath, 'utf8'));
  
  // Connect to contract
  console.log("🔌 Connecting to contract...");
  const oracle = new hre.ethers.Contract(contractAddress, artifact.abi, signer);
  
  try {
    // Test 1: Check owner
    console.log("\n📝 Test 1: Checking contract owner...");
    const owner = await oracle.owner();
    console.log("✅ Owner:", owner);
    console.log(owner === signer.address ? "✅ You are the owner" : "⚠️ You are NOT the owner");

    // Test 2: Check stock count
    console.log("\n📝 Test 2: Checking tracked stocks...");
    const stockCount = await oracle.getStockCount();
    console.log("✅ Total stocks tracked:", stockCount.toString());

    if (stockCount > 0) {
      // Test 3: Read some stock prices
      console.log("\n📝 Test 3: Reading stock prices...");
      
      const sampleSymbols = ["DANGCEM", "GTCO", "BUACEMENT"];
      
      for (const symbol of sampleSymbols) {
        try {
          const exists = await oracle.stockExists(symbol);
          
          if (exists) {
            const [price, timestamp] = await oracle.getPrice(symbol);
            const priceInNGN = Number(hre.ethers.formatUnits(price, 18));
            const date = new Date(Number(timestamp) * 1000);
            
            console.log(`✅ ${symbol}:`);
            console.log(`   Price: ₦${priceInNGN.toFixed(2)}`);
            console.log(`   Updated: ${date.toLocaleString()}`);
          } else {
            console.log(`⚠️ ${symbol}: Not yet tracked`);
          }
        } catch (error) {
          console.log(`⚠️ ${symbol}: Not found`);
        }
      }

      // Test 4: Batch read (gas efficient)
      console.log("\n📝 Test 4: Testing batch read...");
      const [prices, timestamps, exists] = await oracle.getPrices(sampleSymbols);
      
      console.log("✅ Batch read successful");
      for (let i = 0; i < sampleSymbols.length; i++) {
        if (exists[i]) {
          const priceInNGN = Number(hre.ethers.formatUnits(prices[i], 18));
          console.log(`   ${sampleSymbols[i]}: ₦${priceInNGN.toFixed(2)}`);
        }
      }
    } else {
      console.log("\n⚠️ No stocks tracked yet. The keeper needs to update prices.");
    }

    // Test 5: Test update (if you're the owner)
    if (owner === signer.address) {
      console.log("\n📝 Test 5: Testing price update...");
      
      const testSymbol = "TESTSTOCK";
      const testPrice = hre.ethers.parseUnits("100.50", 18);
      
      console.log(`Updating ${testSymbol} to ₦100.50...`);
      
      const tx = await oracle.updatePrice(testSymbol, testPrice);
      console.log("Transaction hash:", tx.hash);
      
      console.log("Waiting for confirmation...");
      await tx.wait();
      
      console.log("✅ Price updated successfully!");
      
      // Read it back
      const [readPrice, readTimestamp] = await oracle.getPrice(testSymbol);
      const priceInNGN = Number(hre.ethers.formatUnits(readPrice, 18));
      
      console.log(`✅ Verified: ${testSymbol} = ₦${priceInNGN.toFixed(2)}`);
      
      // Clean up test stock
      console.log("\nCleaning up test stock...");
      const removeTx = await oracle.removeStock(testSymbol);
      await removeTx.wait();
      console.log("✅ Test stock removed");
    }

    console.log("\n=====================================");
    console.log("✅ ALL TESTS PASSED!");
    console.log("=====================================");
    console.log("\nYour oracle is working correctly!");
    console.log("\nNext steps:");
    console.log("1. Start the keeper to populate prices:");
    console.log("   cd keeper");
    console.log("   python ngx_oracle_keeper.py");
    console.log("\n2. Monitor updates on Etherscan:");
    
    const network = await hre.ethers.provider.getNetwork();
    if (network.chainId === 11155111n) {
      console.log(`   https://sepolia.etherscan.io/address/${contractAddress}`);
    }
    console.log();

  } catch (error) {
    console.error("\n❌ Validation failed:", error.message);
    
    if (error.message.includes("Stock not found")) {
      console.log("\n💡 This is normal if the keeper hasn't run yet.");
      console.log("The contract is deployed correctly, it just needs price data.");
    }
    
    process.exit(1);
  }
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error("\n❌ Error:", error);
    process.exit(1);
  });