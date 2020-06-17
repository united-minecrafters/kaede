def letter_emoji(a: str):
    if a.isascii() and a.isalpha() and len(a) == 1:
        a = a.upper()
    else:
        return None
    return chr(ord(a[0]) + 0x1f1a5)


def quote(st: str):
    return "\n".join(f"> {n}" for n in st.split("\n"))
