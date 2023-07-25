#!/usr/bin/env python3

import yaml

from snakemake.common import get_container_image

from float_utils import logger


class FloatConfig:
    _CONFIG_FILE = 'snakemake-float.yaml'
    _REQUIRED_KWARGS = ('address', 'username', 'password', 'dataVolume')

    SUBMIT_EXTRA = 'extra'

    def __init__(self, config_file=_CONFIG_FILE):
        self._parameters = {
            'image': get_container_image(),
        }

        try:
            with open(config_file) as cf:
                kwargs = yaml.safe_load(cf)
        except OSError:
            logger.exception('Cannot open float config file')
            raise
        except yaml.YAMLError:
            logger.exception(f"Cannot load YAML: {self._CONFIG_FILE}")
            raise

        for kwarg in self._REQUIRED_KWARGS:
            if kwarg not in kwargs:
                msg = f"{config_file} missing required argument: '{kwarg}'"
                logger.error(msg)
                raise TypeError(msg)

        self._parameters.update(kwargs)

    def parameters(self):
        return self._parameters
