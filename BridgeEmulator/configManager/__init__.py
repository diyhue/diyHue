from configManager import configHandler
from configManager import argumentHandler

bridgeConfig = configHandler.Config()
runtimeConfig = configHandler.Config()
bridgeConfig.load_config()

# Initialize runtime configuration
runtimeConfig.arg = argumentHandler.parse_arguments()
argumentHandler.process_arguments(bridgeConfig.configDir, runtimeConfig.arg)
runtimeConfig.newLights = {}
runtimeConfig.dxState = {"sensors": {}, "lights": {}, "groups": {}}


# Initialize bridge config
bridgeConfig.generate_security_key()
bridgeConfig.write_args(runtimeConfig.arg)
bridgeConfig.generate_security_key()

