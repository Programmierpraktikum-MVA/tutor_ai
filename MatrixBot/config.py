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
        self.user_password = self.get_config(["matrix", "user_password"], required=True)
        self.homeserver_url = self.get_config(["matrix", "homeserver_url"], required=True)

    def get_config(
            self,
            path: List[str],
            default: Any = None,
            required: bool = True,
    ) -> Any:
        #get fitting option
        config = self.config
        for name in path:
            config = config.get(name)
        return config