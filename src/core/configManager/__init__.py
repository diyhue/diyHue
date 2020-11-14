from configManager import bridgeConfigHandler
from configManager import argumentHandler
from configManager import runtimeConfigHandler
from configManager import configStorage

coreConfig = configStorage.configStorage()

# Initialize runtime configuration
runtimeConfig = runtimeConfigHandler.Config()
runtimeConfig.populate()
argumentHandler.process_arguments(runtimeConfig.arg)
coreConfig.initialize_certificate()

# Initialize bridge config
bridgeConfig = bridgeConfigHandler.Config(coreConfig.bridge_config)
bridgeConfig.generate_security_key()
bridgeConfig.write_args(runtimeConfig.arg)

# Clean and update config
bridgeConfig.sanitizeBridgeScenes()
bridgeConfig.updateConfig()

