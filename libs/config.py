from ruamel.yaml import YAML

_config = None
yaml = YAML()


def reload_config():
    global _config
    with open("config.yaml") as fp:
        _config = yaml.load(fp)


def save_config():
    with open("config.yaml", "w") as fp:
        yaml.dump(_config, fp)


def config():
    return _config


reload_config()
