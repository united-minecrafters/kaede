from dataclasses import dataclass

from ruamel.yaml import YAML

_config = None
yaml = YAML()


@dataclass
class EmojiList:
    delete: str
    edit: str
    filter: str
    user_join: str
    user_leave: str
    mute: str
    unmute: str
    ban: str
    unban: str
    softban: str
    autokick_on: str
    autokick_off: str


emojis: EmojiList


def reload_config():
    global _config, emojis
    with open("config.yaml") as fp:
        _config = yaml.load(fp)
    emojis = EmojiList(
        **_config["emojis"]
    )


def save_config():
    with open("config.yaml", "w") as fp:
        yaml.dump(_config, fp)


def config():
    return _config


reload_config()
