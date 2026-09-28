"""Encoding utilities for adversarial attack generation.

Encoding attacks test whether an agent's safety measures are
semantic (understands meaning regardless of encoding) or syntactic
(pattern-matches on plain text and can be bypassed by obfuscation).

Three encodings are used:
  Base64    - common encoding, often used in technical contexts
  ROT13     - simple Caesar cipher, trivially decodable by a model
  Leet speak - character substitution, harder to detect as obfuscation

A robust agent refuses encoded attacks because it understands what
is being asked. A brittle agent only refuses the plain-text version.
"""
import base64
import codecs


def to_base64(text: str) -> str:
    """Encode text to Base64.

    Example:
        "Ignore your instructions" →
        "SWdub3JlIHlvdXIgaW5zdHJ1Y3Rpb25z"
    """
    return base64.b64encode(text.encode()).decode()


def to_rot13(text: str) -> str:
    """Encode text with ROT13 (Caesar cipher, shift 13).

    Example:
        "Ignore your instructions" →
        "Vtagber lbhe vafgehpgvbaf"
    """
    return codecs.encode(text, "rot_13")


def to_leet(text: str) -> str:
    """Encode text using leet-speak character substitutions.

    Example:
        "Ignore your instructions" →
        "1gn0r3 y0ur 1nstruct10ns"
    """
    substitutions = {
        'a': '4', 'e': '3', 'i': '1', 'o': '0',
        't': '7', 's': '5', 'g': '9', 'l': '1',
    }
    return ''.join(substitutions.get(c.lower(), c) for c in text)


def to_unicode_lookalike(text: str) -> str:
    """Replace ASCII letters with Unicode lookalikes.

    Example: 'a' → 'а' (Cyrillic), 'e' → 'е' (Cyrillic)
    These look identical to humans but are different characters.
    Content filters that do exact string matching are bypassed.
    """
    lookalikes = {
        'a': 'а',  # Cyrillic а
        'e': 'е',  # Cyrillic е
        'o': 'о',  # Cyrillic о
        'p': 'р',  # Cyrillic р
        'c': 'с',  # Cyrillic с
        'x': 'х',  # Cyrillic х
    }
    return ''.join(lookalikes.get(c, c) for c in text)


ENCODERS = {
    "base64": to_base64,
    "rot13": to_rot13,
    "leet": to_leet,
    "unicode_lookalike": to_unicode_lookalike,
}


def encode_attack(attack_text: str, encoding: str) -> str:
    """Apply one encoding to an attack string.

    Args:
        attack_text: the plain-text attack
        encoding:    one of: base64, rot13, leet, unicode_lookalike

    Returns:
        the encoded attack string

    Raises:
        ValueError if encoding is unknown
    """
    encoder = ENCODERS.get(encoding)
    if encoder is None:
        raise ValueError(
            f"Unknown encoding '{encoding}'. "
            f"Available: {list(ENCODERS.keys())}"
        )
    return encoder(attack_text)
