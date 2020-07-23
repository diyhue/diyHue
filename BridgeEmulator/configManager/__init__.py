from configManager import configHandler
from configManager import argumentHandler

bridgeConfig = configHandler.Config()
runtimeConfig = configHandler.Config()
bridgeConfig.load_config()

# Initialize configuration
runtimeConfig.arg = argumentHandler.parse_arguments()
argumentHandler.process_arguments()
