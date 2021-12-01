import json
import logging
import os
import sys
import time

import exceptions
import requests
import telegram
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
# handler = RotatingFileHandler('bot.log', maxBytes=500000, backupCount=5)
handler = logging.StreamHandler(stream=sys.stdout)
logger.addHandler(handler)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(funcName)s'
    '- %(lineno)d - %(levelname)s - %(message)s'
)
handler.setFormatter(formatter)
PRACTICUM_TOKEN = os.getenv('TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('MY_CHAT_ID')
RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Отправляет сообщение в чат телеграмма."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except telegram.error.Unauthorized:
        message = 'Сбой при авторизации в телеграмм!'
        logger.error(message)
        raise exceptions.TelegramAuthorizationException(message)
    except telegram.error.BadRequest:
        logger.error(message)
        message = 'Ошибка в идентификаторе чата!'
        raise exceptions.TelegramChatIdException(message)
    except Exception as e:
        logger.error(e)
        message = 'Неустановленный сбой с Телеграмм!'
        raise exceptions.TelegramChatIdException(message)


def get_api_answer(current_timestamp):
    """Делает запрос к эндпоинту API-сервиса Практикум.Домашка.

    В качестве параметра функция получает временную метку.
    Если запрос успешен - возвращает ответ API,
    преобразовав его из формата JSON к типам данных Python.
    Если запрос не успешен - пишет в лог ошибку с исключением.
    """
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    try:
        error = response.get('error')
    except AttributeError:
        message = 'API Домашки не вернул ключ "error"'
        logger.info(message)
    try:
        code = response.get('code')
    except AttributeError:
        message = 'API Домашки не вернул ключ "code"'
        logger.info(message)
    else:
        if error or code:
            message = (f'Получен ответ об отказе от сервера API Практикума'
                       f' при запросе к "{ENDPOINT}"" с параметрами:'
                       f' "headers": "{HEADERS}"" и "from_date": "{timestamp}"'
                       f' Error: "{error}"'
                       f' Code: "{code}"')
            logger.error(message)
            raise exceptions.APIErrorException(message)
    if response.status_code == 504:
        message = 'Таймаут ответа от Практикум.Домашка!'
        logger.error(message)
        raise exceptions.APITimeoutException(message)
    if response.status_code != 200:
        message = 'Код HTTP ответа от Практикум.Домашка не 200!'
        logger.error(message)
        raise exceptions.APIIsNot200StatusException(message)
    try:
        response = response.json()
    except json.decoder.JSONDecodeError as e:
        logging.error(e, exc_info=True)
        message = 'Практикум.Домашка вернул некорректный формат данных!'
        raise exceptions.JSONDecoderException(message)
    except Exception:
        message = (f'Запрос к API-сервису Практикум.Домашка выполнить не получилось.'
                   f' Так сошлись звезды и необходимо изучить логи.'
                   f' Детали запроса:'
                   f' запрос сделан к "{ENDPOINT}"" с параметрами:'
                   f' "headers": "{HEADERS}"" и "from_date": "{timestamp}"'
                   f' Получен ответ: "{response}"')
        logger.error(message, exc_info=True)
        raise exceptions.GeneralAPIException(message)
    return response


def check_response(response):
    """Проверяет корректность ответа API.

    Если получаем некорректный ответ - деалем запись в логе
    и отправляем сообщение в чат телеграмма.
    """
    try:
        # Проверяем, что существует ключ homeworks в словаре
        # в полученном от API ответе
        response['homeworks']
    except KeyError as e:
        logger.error(e, exc_info=True)
        message = 'Практикум.Домашка не вернул список домашек вообще!'
        raise exceptions.HomeworksKeyException(message)
        # Проверяем, что полученная структура данных
        # по ключю homeworks является списком
    if type(response.get('homeworks')) is not list:
        message = 'Практикум.Домашка вернул некорректный формат данных!'
        logger.error(message)
        raise exceptions.HomeworksHasNoListException(message)
    try:
        # Проверяем, есть ли элементы в полученном списке
        # по ключу словаря homeworks
        response.get('homeworks')[0]
    except IndexError:
        message = 'Практикум.Домашка вернул пустой список домашек!'
        logger.info(message)
        raise exceptions.HomeworksEmptyValueException(message)
    return response.get('homeworks')


def parse_status(homework):
    """Парсит ответ API Практикум.Домашка.

    Отправляет в чат телеги статус домашки.
    """
    # Комментарий для Артёма Гребенюка:
    # если для homework_name использовать безопасный
    # метод get(), то не проходят тесты,
    # поэтому пришлось от него уйти
    homework_name = homework['homework_name']
    homework_status = homework.get('status')
    # Проверяем, что статус домашки, полученный от Практикума
    # есть в нашем словаре
    try:
        verdict = HOMEWORK_STATUSES[homework_status]
    except KeyError as e:
        logger.error(e, exc_info=True)
        message = 'Практикум.Домашка вернул непонятный статус домашки!'
        raise exceptions.HomeworkStatusUndefined(message)
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет доступность переменных окружения программы.

    Если отсутствует хотя бы одна переменная окружения,
    то возвращает False, иначе — True.
    """
    if (PRACTICUM_TOKEN
            and TELEGRAM_TOKEN
            and TELEGRAM_CHAT_ID):
        return True
    else:
        message = []
        if not PRACTICUM_TOKEN:
            message.append('Переменная среды PRACTICUM_TOKEN не доступна!')
        if not TELEGRAM_TOKEN:
            message.append('Переменная среды TELEGRAM_TOKEN не доступна!')
        if not TELEGRAM_CHAT_ID:
            message.append('Переменная среды TELEGRAM_CHAT_ID не доступна!')
        logger.critical(message)
        return False


def main():
    """Основная логика работы бота."""
    # Проверяем наличие переменных окружения
    # если не все указаны - пишем ошибку в лог
    if not check_tokens():
        logger.critical('Не все переменные окружения указаны!')
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    last_homwework_status = 'Домашка не отправлена!'
    last_message = 'Пока ничего не отправили'
    while True:
        try:
            # Делаем запрос к API Практикум.Домашка
            response = get_api_answer(current_timestamp)
            # Получаем список домашек в виде списка
            homeworks = check_response(response)
            # Берем первую домашку из списка
            # т.к. она последняя из отправленных
            homework = homeworks[0]
            # Передаем эту домашку на парсинг
            homework_status = parse_status(homework)
            if homework_status != last_homwework_status:
                send_message(bot, homework_status)
                logger.info(f'Статус домашки успешно отправлен в чат'
                            f' телеги: "{homework_status}"')
                last_homwework_status = homework_status
            else:
                logger.debug('Статус домашки не изменился')
            current_timestamp = response.get('current_date')
            time.sleep(RETRY_TIME)
        except exceptions.HomeworksEmptyValueException:
            homework_status = 'Нет списка домашек'
            if homework_status != last_homwework_status:
                send_message(bot, homework_status)
                logger.info(f'Статус домашки успешно отправлен в чат'
                            f' телеги: "{homework_status}"')
                last_homwework_status = homework_status
            else:
                logger.debug('Статус домашки не изменился')
            current_timestamp = response.get('current_date')
            time.sleep(RETRY_TIME)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            if message != last_message:
                send_message(bot, message)
                last_message = message
                logger.info(f'Отправлено в чат телеги сообщение'
                            f' о проблеме: "{message}"')
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
