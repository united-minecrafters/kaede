from ruamel.yaml import YAML

config = None
yaml = YAML()


def reload_config():
    global config
    with open("config.yaml") as fp:
        config = yaml.load(fp)


def save_config():
    with open("config.yaml", "w") as fp:
        yaml.dump(config, fp)


reload_config()
