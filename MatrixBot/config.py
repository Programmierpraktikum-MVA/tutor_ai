import os
import yaml
import sys
from typing import List, Any


class Config(object):

    def __init__(self, filepath):
        # Load in the config file at the given filepath
        with open(filepath) as file_stream:
            self.config = yaml.safe_load(file_stream.read())

        #account setup
        self.user_id = self.get_config(["matrix", "user_id"], required=True)
        self.access_token = self.get_config(["matrix", "access_token"], required=True)
        self.homeserver_url = self.get_config(["matrix", "homeserver_url"], required=True)

    def get_config(
        self,
        path: List[str],
        default: Any = None,
        required: bool = False,
    ) -> Any:
        config = self.config
        for name in path:
            if config is None:
                break
            config = config.get(name)

        if required and config is None:
            raise ValueError(f"Missing required config key: {'.'.join(path)}")

        return config if config is not None else default