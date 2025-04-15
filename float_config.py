#!/usr/bin/env python3

import yaml

from snakemake.common import get_container_image

from float_utils import logger


class FloatConfig:
    _CONFIG_FILE = "snakemake-float.yaml"
    _REQUIRED_KWARGS = {"work-dir"}
    _SUPPORTED_KWARGS = _REQUIRED_KWARGS.union(
        {
            "job-prefix",
            "base-image",
            "cpu",
            "mem",
            "max-cpu-factor",
            "max-mem-factor",
            "submit-extra",
        }
    )

    def __init__(self, config_file=_CONFIG_FILE):
        self._parameters = {"base-image": get_container_image()}

        try:
            with open(config_file) as cf:
                kwargs = yaml.safe_load(cf)
        except OSError:
            logger.exception("Cannot open float config file")
            raise
        except yaml.YAMLError:
            logger.exception(f"Cannot load YAML: {self._CONFIG_FILE}")
            raise

        for kwarg in self._REQUIRED_KWARGS:
            if kwarg not in kwargs:
                msg = f"{config_file} missing required argument: '{kwarg}'"
                logger.error(msg)
                raise TypeError(msg)

        for kwarg in kwargs:
            if kwarg not in self._SUPPORTED_KWARGS:
                msg = f"{config_file} has unsupported argument: '{kwarg}'"
                logger.warning(msg)

        self._parameters.update(kwargs)

    def parameters(self):
        return self._parameters

    def max_cpu_factor(self):
        return (
            float(self._parameters["max-cpu-factor"])
            if "max-cpu-factor" in self._parameters
            else 4.0
        )

    def max_mem_factor(self):
        return (
            float(self._parameters["max-mem-factor"])
            if "max-mem-factor" in self._parameters
            else 4.0
        )
