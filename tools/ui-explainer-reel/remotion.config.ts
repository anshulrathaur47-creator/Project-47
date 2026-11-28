/**
 * Note: When using the Node.JS APIs, the config file
 * doesn't apply. Instead, pass options directly to the APIs.
 *
 * All configuration options: https://remotion.dev/docs/config
 */

import { Config } from "@remotion/cli/config";

Config.setRspack(true);
Config.setChromiumOpenGlRenderer("angle");
Config.setVideoImageFormat("jpeg");
Config.setOverwriteOutput(true);
// Use the preinstalled headless Chromium (Remotion's own browser download host is not reachable here).
if (process.env.REMOTION_BROWSER) {
  Config.setBrowserExecutable(process.env.REMOTION_BROWSER);
}
