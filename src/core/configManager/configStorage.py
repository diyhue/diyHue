import json
import os
import logManager
import subprocess
import configManager
from datetime import datetime
from pathlib import Path

logging = logManager.logger.get_logger(__name__)


# TODO: add empty file to config dir and check for it, if found, notify user to mount the config dir to ensure config is not lost

class configStorage:
    core_config = None
    bridge_config = None
    # runtime_config = None # left here for the future as we dont actually want to save the runtime config for now
    projectDir = '/diyhue'  # cwd = os.path.split(os.path.abspath(__file__))[0]
    configDir = '/config'

    def __init__(self):
        if not os.path.exists(self.configDir):
            os.makedirs(self.configDir)
        self.load_core()

    @staticmethod
    def _open_json(path):
        with open(path, 'r', encoding="utf-8") as fp:
            return json.load(fp)

    @staticmethod
    def _write_json(path, contents):
        with open(path, 'w', encoding="utf-8") as fp:
            json.dump(contents, fp, sort_keys=True, indent=4, separators=(',', ': '))

    def get_path(self, file, project=False, config=False):  # defaulting to config for now...
        if project:
            return Path(self.projectDir, file).as_posix()
        else:
            return Path(self.configDir, file).as_posix()

    def _generate_new_config(self):
        self.bridge_config = {}
        # self.runtime_config = {}

    def _update_core_config(self):  # prepares core config for saving
        self.core_config = {"bridge_config": self.bridge_config}
        # self.core_config["runtime_config"] = self.runtime_config

    def _save_core(self):  # saves core config as is, use caution
        self._write_json(self.get_path("config.json", config=True), self.core_config)

    def load_core(self):
        if os.path.exists(self.get_path("config.json", config=True)):
            self.core_config = self._open_json(self.get_path("config.json", config=True))
            logging.info("Core config found")
            try:
                self.bridge_config = self.core_config["bridge_config"]
                # self.runtime_config = self.core_config["runtime_config"]
            except Exception:
                logging.warning("Core config could not be imported, overwriting current config with defaults")
                self.reset_core()
        else:
            logging.info("No configuration file detected, creating new config")
            self._generate_new_config()
            self.save_latest_core()

    def save_latest_core(self, backup=False):
        self._update_core_config()
        if backup: # first backup
            filename = self.backup_data("config.json")
        else:
            filename = "config.json"
        self._save_core() # then save what we have in memory
        return filename

    def reset_core(self):
        """
        Creates 2 backups. Backup 1: original file from disk. Backup 2: config from memory.
        Saves new config generated from default config.
        :return:
        """
        self.save_latest_core(True)  # Make a backup of config on disk, save in-memory config
        filename = self.backup_data("config.json") # Renames in-memory to backup
        self._generate_new_config()
        self.save_latest_core()
        return filename

    def initialize_certificate(self, reset=False):
        # resetting of certificates is never used currently, maybe add to reset core?
        if reset:
            self.backup_data("cert.pem")
        if not os.path.isfile(self.get_path("cert.pem", config=True)):
            self._generate_certificate(configManager.runtimeConfig.arg["MAC"])
        else:
            if not self._validate_certificate(configManager.runtimeConfig.arg["MAC"]):
                logging.warning("Detected need to recreate the certificate. Backing up certificate.")
                self.backup_data("cert.pem")
                self._generate_certificate(configManager.runtimeConfig.arg["MAC"])

    def backup_data(self, orig_filename):
        """
        Rename main file from config dir to backup file. Will additionally prune old backups with maximum from args.
        :param filename: Full filename including extension
        :return:
        """
        file_ext = orig_filename.split(".")[1]
        filename = orig_filename.split(".")[0]
        self.__prune_backups(filename, file_ext)
        backup_name = filename + "--backup-" + datetime.now().strftime("%Y-%m-%d--%H-%M-%S-%f") + "." + file_ext
        os.rename(self.get_path(orig_filename, config=True), self.get_path(backup_name, config=True))
        return backup_name

    def __prune_backups(self, filename, file_ext):
        backup_list = []
        for file in os.listdir(self.configDir):
            if file.startswith(filename + "--") and file.endswith(file_ext):
                backup_list.append(file)
        backup_list.sort()
        if len(backup_list) > configManager.runtimeConfig.arg[filename.upper() + "_BACKUPS"]:
            for backup in backup_list:
                if len(backup_list) > configManager.runtimeConfig.arg[filename.upper() + "_BACKUPS"]:
                    os.remove(self.get_path(backup, config=True))
                else:
                    break

    def _validate_certificate(self, mac):
        """
        Ensures the certificate within the config directory matches the MAC that we were provided during startup.
        If there is a mismatch, return False.
        :param mac: MAC address without ':'. Letters and numbers only.
        :return: boolean
        """
        opnssl_process = subprocess.check_output(["openssl",
                                                  "x509",
                                                  "-in", self.get_path("cert.pem", config=True),
                                                  "-serial",
                                                  "-noout"]
                                                 )
        try:
            output = opnssl_process.decode('utf-8').rstrip().split("=")[1]
            if mac == output:
                return True
            else:
                try:  # If somehow the mac does not match up, check using integer validation
                    mac = int(mac, 16)
                    output = int(output)
                    return mac == output
                except Exception as e:
                    logging.debug("Couldn't parse secondary MAC serial check", e)
        except Exception as e:
            logging.warning(
                "We failed to detect the certificate serial, so we will recreate the certificate just in case.", e)
            return False

    def _generate_certificate(self, mac):
        """
        Generates cert, key combo in the config directory
        :param mac: Host MAC address without ':'. Letters and numbers only.
        :return:
        """
        logging.info("Generating certificate")
        try:
            # generate certificate using openssl
            subprocess.run(["openssl", "req",
                                     "-new",
                                     "-days", "3650",
                                     "-config", "/diyhue/openssl.conf",
                                     "-nodes",
                                     "-x509",
                                     "-newkey", "ec",
                                     "-pkeyopt", "ec_paramgen_curve:P-256",
                                     "-pkeyopt", "ec_param_enc:named_curve",
                                     "-subj", "/C=NL/O=Philips Hue/CN=" + mac,
                                     "-keyout", "/tmp/private.key",
                                     "-out", "/tmp/public.crt",
                                     "-set_serial", str(int(mac, 16))],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.STDOUT
                            )
            tmp_files = ["/tmp/private.key", "/tmp/public.crt"]
            # concatenate certificate and private key
            with open(self.get_path("cert.pem", config=True), 'w') as outfile:
                for file in tmp_files:
                    with open(Path(file).as_posix(), 'r') as readfile:
                        for line in readfile:
                            outfile.write(line)
            # remove temporary key
            for file in tmp_files:
                os.remove(file)
            logging.info("Certificate created")
        except Exception as e:
            logging.critical("Failed creating certificate!", e)
            raise
