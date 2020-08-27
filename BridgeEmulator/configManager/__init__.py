from configManager import bridgeConfigHandler
from configManager import argumentHandler
from configManager import runtimeConfigHandler
from configManager import configStorage

coreConfig = configStorage.configStorage()

bridgeConfig = bridgeConfigHandler.Config(coreConfig.bridge_config)
runtimeConfig = runtimeConfigHandler.Config()

# Initialize runtime configuration
runtimeConfig.populate()
argumentHandler.process_arguments(runtimeConfig.arg)

# Initialize bridge config
bridgeConfig.generate_security_key()
bridgeConfig.write_args(runtimeConfig.arg)

# Clean and update config
bridgeConfig.sanitizeBridgeScenes()
bridgeConfig.updateConfig()

