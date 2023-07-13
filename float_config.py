#!/usr/bin/env python3

import yaml

from snakemake.common import get_container_image


class FloatConfig:
    _CONFIG_FILE = 'snakemake-float.yaml'
    _REQUIRED_KWARGS = ('address', 'username', 'password', 'dataVolume')

    SUBMIT_EXTRA = 'extra'

    def __init__(self, config_file=_CONFIG_FILE):
        self._parameters = {
            'image': get_container_image(),
        }

        with open(config_file) as cf:
            kwargs = yaml.safe_load(cf)

        for kwarg in self._REQUIRED_KWARGS:
            if kwarg not in kwargs:
                raise TypeError(
                    f"{config_file} missing required argument: '{kwarg}'"
                )

        self._parameters.update(kwargs)

    def parameters(self):
        return self._parameters
