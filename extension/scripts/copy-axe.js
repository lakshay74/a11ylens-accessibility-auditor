const fs = require("node:fs");
const path = require("node:path");

const axeEntry = require.resolve("axe-core");
const packageDirectory = path.dirname(axeEntry);
const destinationDirectory = path.join(__dirname, "..", "vendor");

fs.mkdirSync(destinationDirectory, { recursive: true });
fs.copyFileSync(
  path.join(packageDirectory, "axe.min.js"),
  path.join(destinationDirectory, "axe.min.js")
);
fs.copyFileSync(
  path.join(packageDirectory, "LICENSE"),
  path.join(destinationDirectory, "axe-core-LICENSE.txt")
);
fs.copyFileSync(
  path.join(packageDirectory, "LICENSE-3RD-PARTY.txt"),
  path.join(destinationDirectory, "axe-core-THIRD-PARTY-NOTICES.txt")
);
console.log("Copied axe-core and its license notices into extension/vendor/");
