#!/usr/bin/env python3

import yaml


class FloatConfig:
    CONFIG_FILE = 'snakemake-float.yaml'
    _required_kwargs = ('address', 'username', 'password', 'dataVolume')

    def __init__(self, config_file=CONFIG_FILE):
        self._parameters = {'image': 'cactus', 'cpu': '2', 'mem': '4'}

        with open(config_file) as cf:
            kwargs = yaml.safe_load(cf)

        for kwarg in self._required_kwargs:
            if kwarg not in kwargs:
                raise TypeError(f"{config_file} missing required: '{kwarg}'")

        self._parameters.update(kwargs)

    def parameters(self):
        return self._parameters
