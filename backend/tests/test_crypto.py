from app.core.crypto import decrypt, encrypt


def test_roundtrip():
    text = "Болит голова, плохо спала"
    assert decrypt(encrypt(text)) == text


def test_ciphertext_differs_each_time():
    """AES-GCM со случайным nonce: одинаковый текст даёт разный шифротекст."""
    assert encrypt("тест") != encrypt("тест")


def test_plaintext_not_visible():
    assert "голова" not in encrypt("Болит голова")
