from configManager import configHandler
from configManager import argumentHandler
from configManager import runtimeConfigHandler

bridgeConfig = configHandler.Config()
runtimeConfig = runtimeConfigHandler.Config()

# Restore configuration
bridgeConfig.load_config()
runtimeConfig.populate()

# Initialize runtime configuration
argumentHandler.process_arguments(bridgeConfig.configDir, runtimeConfig.arg)


# Initialize bridge config
bridgeConfig.generate_security_key()
bridgeConfig.write_args(runtimeConfig.arg)

# Clean and update config
bridgeConfig.sanitizeBridgeScenes()
bridgeConfig.updateConfig()

