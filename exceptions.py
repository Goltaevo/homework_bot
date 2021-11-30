class HomeworksKeyException(Exception):
    """Выдает исключение при отсутствии ключа homeworks в словаре."""

    pass


class HomeworksHasNoListException(Exception):
    """Выдает исключение при отсутствии структуры списка в словаре.

    Если словарь не содержит list().
    """

    pass


class HomeworksEmptyValueException(Exception):
    """Выдает исключение при пустом списке в словаре."""

    pass


class HomeworkStatusUndefined(Exception):
    """Выдает исключение при непонятном статусе домашки."""

    pass


class APITimeoutException(Exception):
    """Выдает исключение при таймауте ответа от API."""

    pass


class APIIsNot200StatusException(Exception):
    """Выдает исключение при ответе не HTTP 200 ОК."""

    pass


class NoHomeworkNameKeyException(Exception):
    """Выдает исключение при отсутствии ключа имени домашки."""

    pass


class JSONDecoderException(Exception):
    """Выдает исключение, если ответ API нельзя привести к словар."""

    pass


class GeneralAPIException(Exception):
    """Выдает исключение при какой-либо проблеме с API."""

    pass


class TelegramAuthorizationException(Exception):
    """Выдает исключение при сбое авторизации в телеги."""

    pass


class TelegramChatIdException(Exception):
    """Выдает исключение при ошибке в chat id телеги."""

    pass
