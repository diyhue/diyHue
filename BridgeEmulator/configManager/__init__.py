from configManager import configHandler
from configManager import argumentHandler
from configManager import runtimeConfigHandler

bridgeConfig = configHandler.Config()
runtimeConfig = runtimeConfigHandler.Config()

# Initialize runtime configuration
runtimeConfig.populate()
argumentHandler.process_arguments(bridgeConfig.configDir, runtimeConfig.arg)

# Restore configuration
bridgeConfig.load_config()

# Initialize bridge config
#bridgeConfig.generate_security_key()
bridgeConfig.write_args(runtimeConfig.arg)
