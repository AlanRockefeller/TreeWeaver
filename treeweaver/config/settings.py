# This module will handle application settings and preferences.

import json
import os
import logging

# Get logger for this module
logger = logging.getLogger(__name__)

class SettingsManager:
    """Manages application settings, loading from and saving to a JSON file."""

    def __init__(self, app_name="TreeWeaver"):
        self.app_name = app_name
        self.config_dir = self._get_config_dir()
        self.config_file_path = os.path.join(self.config_dir, "settings.json")

        self.default_settings = {
            "external_tool_paths": {
                "mafft": "",
                "raxmlng": "",
                "iqtree": "",
                "modeltest-ng": ""
            },
            "external_tool_options": {
                "mafft_threads": 1,
                "raxmlng_threads": 1,
                "iqtree_threads": 1,      # For general IQ-TREE runs, including ModelFinder for now
                "modeltest_ng_threads": 1 # For ModelTest-NG runs
            },
            "visualization": {
                "font_family": "Arial",
                "font_size": 10,
                "line_thickness": 1
            },
            "user_paths": { # For remembering last used directories
                "last_import_dir": os.path.expanduser("~"),
                "last_export_dir": os.path.expanduser("~"),
                "last_settings_tool_path_dir": os.path.expanduser("~") # For tool path browsing
            },
            "debug_mode": False
        }

        self.settings = self.load_settings()
        logger.info(f"Settings initialized. Config path: {self.config_file_path}")

    def _get_config_dir(self):
        """Determines the appropriate configuration directory based on OS."""
        if os.name == 'nt':  # Windows
            config_dir = os.path.join(os.getenv('APPDATA', ''), self.app_name)
        else:  # macOS, Linux, other Unix-like
            config_dir = os.path.join(os.path.expanduser('~'), '.config', self.app_name)

        if not os.path.exists(config_dir):
            try:
                os.makedirs(config_dir, exist_ok=True)
                logger.info(f"Created configuration directory: {config_dir}")
            except OSError as e:
                logger.error(f"Error creating configuration directory {config_dir}: {e}")
                # Fallback to a local directory if user-level config dir fails
                local_fallback_dir = os.path.join(os.getcwd(), f".{self.app_name.lower()}_config")
                if not os.path.exists(local_fallback_dir):
                    try:
                        os.makedirs(local_fallback_dir, exist_ok=True)
                    except OSError as e_local:
                        logger.error(f"Error creating fallback local config directory {local_fallback_dir}: {e_local}")
                        # If all fails, use current directory (not ideal but better than crashing)
                        return os.getcwd()
                return local_fallback_dir
        return config_dir

    def _deep_merge_dicts(self, defaults, loaded):
        """
        Recursively merges the 'loaded' dictionary into 'defaults'.
        'defaults' provides the structure and default values.
        'loaded' can override existing values but won't add new keys not in defaults at the same level.
        """
        merged = defaults.copy() # Start with a copy of defaults to preserve its structure

        for key, value in loaded.items():
            if key in merged:
                if isinstance(merged[key], dict) and isinstance(value, dict):
                    merged[key] = self._deep_merge_dicts(merged[key], value)
                elif isinstance(merged[key], type(value)): # Only overwrite if types are compatible
                    merged[key] = value
                else:
                    logger.warning(f"Type mismatch for key '{key}' in settings. Keeping default.")
            # else: # Do not add keys from loaded that are not in defaults
            #    logger.warning(f"Ignoring unknown key '{key}' from loaded settings.")
        return merged

    def load_settings(self):
        """Loads settings from the JSON file. Returns defaults if file not found or corrupt."""
        if not os.path.exists(self.config_file_path):
            logger.info(f"Settings file not found at {self.config_file_path}. Using default settings and creating file.")
            self.save_settings(self.default_settings) # Save defaults on first run
            return self.default_settings.copy() # Return a copy

        try:
            with open(self.config_file_path, 'r') as f:
                loaded_settings = json.load(f)

            # Merge loaded settings with defaults to ensure all keys are present
            # and to handle new default settings added in newer versions.
            # The default_settings structure is the master structure.
            merged_settings = self._deep_merge_dicts(self.default_settings, loaded_settings)

            # Ensure no keys from loaded_settings that are not in default_settings get added at the top level
            final_settings = {k: merged_settings[k] for k in self.default_settings if k in merged_settings}

            # Check for any missing top-level keys from defaults (shouldn't happen if merge is correct)
            for k in self.default_settings:
                if k not in final_settings:
                    final_settings[k] = self.default_settings[k]
                    logger.warning(f"Missing top-level key '{k}' after merge, restored from defaults.")

            return final_settings

        except FileNotFoundError:
            logger.warning(f"Settings file not found during load attempt (should have been created). Using defaults.")
            return self.default_settings.copy()
        except json.JSONDecodeError:
            logger.error(f"Error decoding JSON from {self.config_file_path}. Using default settings.")
            # Optionally, could back up the corrupted file here
            return self.default_settings.copy()
        except Exception as e:
            logger.error(f"An unexpected error occurred while loading settings: {e}. Using defaults.")
            return self.default_settings.copy()

    def save_settings(self, settings_data=None):
        """Saves the provided settings_data dictionary to the config file as JSON."""
        data_to_save = settings_data if settings_data is not None else self.settings
        if not os.path.exists(self.config_dir):
            try:
                os.makedirs(self.config_dir, exist_ok=True)
                logger.info(f"Created configuration directory during save: {self.config_dir}")
            except OSError as e:
                logger.error(f"Error creating configuration directory {self.config_dir} during save: {e}")
                # If creating the primary config dir fails, don't attempt to save.
                # The constructor should have handled fallback.
                return False

        try:
            with open(self.config_file_path, 'w') as f:
                json.dump(data_to_save, f, indent=4)
            logger.info(f"Settings saved to {self.config_file_path}")
            self.settings = data_to_save # Update in-memory settings
            return True
        except IOError as e:
            logger.error(f"Error writing settings to {self.config_file_path}: {e}")
            return False
        except Exception as e:
            logger.error(f"An unexpected error occurred while saving settings: {e}")
            return False

    def get_setting(self, key_path: str, default_value=None):
        """
        Retrieves a setting using a dot-separated key path (e.g., "visualization.font_size").
        Returns default_value if the key is not found or if any intermediate key is not a dict.
        """
        keys = key_path.split('.')
        current_level = self.settings
        try:
            for key in keys:
                if not isinstance(current_level, dict): # Ensure intermediate levels are dicts
                    logger.warning(f"Intermediate key in '{key_path}' is not a dictionary. Path invalid.")
                    return default_value
                current_level = current_level[key]
            return current_level
        except KeyError: # Key not found at some level
            logger.debug(f"Setting '{key_path}' not found. Returning default: {default_value}")
            return default_value
        except TypeError: # Path tried to index into a non-dict/non-list type (should be caught by isinstance check)
            logger.warning(f"TypeError accessing setting '{key_path}'. Path likely invalid. Returning default: {default_value}")
            return default_value


    def update_setting(self, key_path: str, value):
        """
        Updates or adds a setting using a dot-separated key path.
        e.g., update_setting("visualization.font_size", 12)
        If the path does not exist, it will be created.
        """
        keys = key_path.split('.')
        current_level = self.settings

        for i, key in enumerate(keys[:-1]):
            if key not in current_level or not isinstance(current_level[key], dict):
                # If key doesn't exist or is not a dict, create it
                logger.debug(f"Creating intermediate dictionary for key '{key}' in path '{key_path}'")
                current_level[key] = {}
            current_level = current_level[key]

        # Set the final value
        final_key = keys[-1]
        current_level[final_key] = value
        logger.debug(f"Set setting '{key_path}' to '{value}'")
        # Optionally, auto-save on update, or require explicit save via settings dialog.
        # For now, we assume settings are saved explicitly (e.g., when SettingsDialog is accepted).
        # self.save_settings()


# Global instance of SettingsManager (Singleton-like pattern)
# This makes it easy to access settings from anywhere in the application.
settings_manager = SettingsManager()

if __name__ == "__main__":
    # Example Usage and Testing
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    logger.info("Initial loaded settings:")
    logger.info(json.dumps(settings_manager.settings, indent=2))

    # Test getting settings
    logger.info(f"MAFFT path: {settings_manager.get_setting('external_tool_paths.mafft', 'N/A')}")
    logger.info(f"Font size: {settings_manager.get_setting('visualization.font_size', 'N/A')}")
    logger.info(f"Non-existent key: {settings_manager.get_setting('non.existent.key', 'Not Found')}")

    # Test updating and saving settings
    settings_manager.update_setting('external_tool_paths.mafft', '/usr/local/bin/mafft')
    settings_manager.update_setting('visualization.font_size', 12)
    settings_manager.settings['debug_mode'] = True # Direct update also possible, but update_setting is safer for nested keys

    logger.info("Settings after updates (in memory):")
    logger.info(json.dumps(settings_manager.settings, indent=2))

    if settings_manager.save_settings():
        logger.info("Settings saved successfully.")

        # Reload to verify
        new_settings_manager = SettingsManager()
        logger.info("Settings after reloading from file:")
        logger.info(json.dumps(new_settings_manager.settings, indent=2))

        # Test that mafft path and font size persisted
        assert new_settings_manager.get_setting('external_tool_paths.mafft') == '/usr/local/bin/mafft'
        assert new_settings_manager.get_setting('visualization.font_size') == 12
        assert new_settings_manager.settings['debug_mode'] is True

        # Restore original defaults for next test run if needed (or manually delete the file)
        # new_settings_manager.save_settings(new_settings_manager.default_settings)
        # logger.info("Restored default settings to file.")
    else:
        logger.error("Failed to save settings.")

    # Test loading corrupted file (manual step: corrupt settings.json, then rerun)
    # Test loading file from an older version (manual step: remove a key from settings.json, then rerun)
    # e.g., remove "debug_mode" or a nested key like "line_thickness"
    # settings_manager_test_old_format = SettingsManager()
    # logger.info("Settings after loading potentially older/incomplete format:")
    # logger.info(json.dumps(settings_manager_test_old_format.settings, indent=2))
    # assert "debug_mode" in settings_manager_test_old_format.settings # Should be restored from defaults
    # assert "line_thickness" in settings_manager_test_old_format.get_setting("visualization")

    logger.info(f"Final config file location: {settings_manager.config_file_path}")
