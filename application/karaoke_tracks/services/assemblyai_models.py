from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field, HttpUrl


class TranscriptStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"


class TranscriptLanguageCode(str, Enum):
    EN = "en"
    EN_AU = "en_au"
    EN_UK = "en_uk"
    EN_US = "en_us"
    ES = "es"
    FR = "fr"
    DE = "de"
    IT = "it"
    PT = "pt"
    NL = "nl"
    AF = "af"
    SQ = "sq"
    AM = "am"
    AR = "ar"
    HY = "hy"
    AS = "as"
    AZ = "az"
    BA = "ba"
    EU = "eu"
    BE = "be"
    BN = "bn"
    BS = "bs"
    BR = "br"
    BG = "bg"
    MY = "my"
    CA = "ca"
    ZH = "zh"
    HR = "hr"
    CS = "cs"
    DA = "da"
    ET = "et"
    FO = "fo"
    FI = "fi"
    GL = "gl"
    KA = "ka"
    EL = "el"
    GU = "gu"
    HT = "ht"
    HA = "ha"
    HAW = "haw"
    HE = "he"
    HI = "hi"
    HU = "hu"
    IS = "is"
    ID = "id"
    JA = "ja"
    JW = "jw"
    KN = "kn"
    KK = "kk"
    KM = "km"
    KO = "ko"
    LO = "lo"
    LA = "la"
    LV = "lv"
    LN = "ln"
    LT = "lt"
    LB = "lb"
    MK = "mk"
    MG = "mg"
    MS = "ms"
    ML = "ml"
    MT = "mt"
    MI = "mi"
    MR = "mr"
    MN = "mn"
    NE = "ne"
    NO = "no"
    NN = "nn"
    OC = "oc"
    PA = "pa"
    PS = "ps"
    FA = "fa"
    PL = "pl"
    RO = "ro"
    RU = "ru"
    SA = "sa"
    SR = "sr"
    SN = "sn"
    SD = "sd"
    SI = "si"
    SK = "sk"
    SL = "sl"
    SO = "so"
    SU = "su"
    SW = "sw"
    SV = "sv"
    TL = "tl"
    TG = "tg"
    TA = "ta"
    TT = "tt"
    TE = "te"
    TH = "th"
    BO = "bo"
    TR = "tr"
    TK = "tk"
    UK = "uk"
    UR = "ur"
    UZ = "uz"
    VI = "vi"
    CY = "cy"
    YI = "yi"
    YO = "yo"


class SpeechModel(str, Enum):
    BEST = "best"
    SLAM_1 = "slam-1"
    UNIVERSAL = "universal"


class EntityType(str, Enum):
    ACCOUNT_NUMBER = "account_number"
    BANKING_INFORMATION = "banking_information"
    BLOOD_TYPE = "blood_type"
    CREDIT_CARD_CVV = "credit_card_cvv"
    CREDIT_CARD_EXPIRATION = "credit_card_expiration"
    CREDIT_CARD_NUMBER = "credit_card_number"
    DATE = "date"
    DATE_INTERVAL = "date_interval"
    DATE_OF_BIRTH = "date_of_birth"
    DRIVERS_LICENSE = "drivers_license"
    DRUG = "drug"
    DURATION = "duration"
    EMAIL_ADDRESS = "email_address"
    EVENT = "event"
    FILENAME = "filename"
    GENDER_SEXUALITY = "gender_sexuality"
    HEALTHCARE_NUMBER = "healthcare_number"
    INJURY = "injury"
    IP_ADDRESS = "ip_address"
    LANGUAGE = "language"
    LOCATION = "location"
    MARITAL_STATUS = "marital_status"
    MEDICAL_CONDITION = "medical_condition"
    MEDICAL_PROCESS = "medical_process"
    MONEY_AMOUNT = "money_amount"
    NATIONALITY = "nationality"
    NUMBER_SEQUENCE = "number_sequence"
    OCCUPATION = "occupation"
    ORGANIZATION = "organization"
    PASSPORT_NUMBER = "passport_number"
    PASSWORD = "password"
    PERSON_AGE = "person_age"
    PERSON_NAME = "person_name"
    PHONE_NUMBER = "phone_number"
    PHYSICAL_ATTRIBUTE = "physical_attribute"
    POLITICAL_AFFILIATION = "political_affiliation"
    RELIGION = "religion"
    STATISTICS = "statistics"
    TIME = "time"
    URL = "url"
    US_SOCIAL_SECURITY_NUMBER = "us_social_security_number"
    USERNAME = "username"
    VEHICLE_ID = "vehicle_id"
    ZODIAC_SIGN = "zodiac_sign"


class TranscriptLanguageDetectionOptions(BaseModel):
    """Опции обнаружения языка"""

    expected_languages: Optional[List[str]] = Field(None, description="Ожидаемые языки")
    fallback_language: Optional[str] = Field(None, description="Резервный язык")
    code_switching: Optional[bool] = Field(None, description="Переключение кода")
    code_switching_confidence_threshold: Optional[float] = Field(
        None, description="Порог уверенности для переключения кода"
    )


class RedactPiiAudioQuality(str, Enum):
    """Качество аудио для редактирования PII"""

    MP3 = "mp3"
    WAV = "wav"


class SubstitutionPolicy(str, Enum):
    """Политика замены для PII"""

    ENTITY_NAME = "entity_name"
    HASH = "hash"


class Sentiment(str, Enum):
    """Тональность"""

    POSITIVE = "POSITIVE"
    NEUTRAL = "NEUTRAL"
    NEGATIVE = "NEGATIVE"


class Word(BaseModel):
    text: str = Field(..., description="Текст слова")
    start: int = Field(..., description="Начало в миллисекундах")
    end: int = Field(..., description="Конец в миллисекундах")
    confidence: float = Field(..., description="Уверенность распознавания")
    speaker: Optional[str] = Field(None, description="Идентификатор говорящего")


class Utterance(BaseModel):
    text: str = Field(..., description="Текст высказывания")
    start: int = Field(..., description="Начало в миллисекундах")
    end: int = Field(..., description="Конец в миллисекундах")
    confidence: float = Field(..., description="Уверенность распознавания")
    speaker: str = Field(..., description="Идентификатор говорящего")
    words: List[Word] = Field(..., description="Слова высказывания")


class Entity(BaseModel):
    entity_type: EntityType = Field(..., description="Тип сущности")
    text: str = Field(..., description="Текст сущности")
    start: int = Field(..., description="Начало в миллисекундах")
    end: int = Field(..., description="Конец в миллисекундах")


class TranslationRequest(BaseModel):
    target_languages: List[str] = Field(..., description="Целевые языки перевода")


class SpeechUnderstandingRequest(BaseModel):
    translation: TranslationRequest = Field(..., description="Запрос перевода")


class SpeechUnderstanding(BaseModel):
    request: SpeechUnderstandingRequest = Field(..., description="Запрос перевода")


class TranscriptParams(BaseModel):
    audio_url: HttpUrl = Field(..., description="URL аудиофайла")
    language_code: Optional[TranscriptLanguageCode] = Field(
        None, description="Код языка"
    )
    speech_model: Optional[SpeechModel] = Field(
        None, description="Модель распознавания"
    )
    punctuate: bool = Field(True, description="Расстановка пунктуации")
    multichannel: bool = Field(True, description="Мультиканальность")
    language_detection: bool = Field(True, description="Определение языка")
    content_safety: bool = Field(True, description="Расстановка пунктуации")
    format_text: bool = Field(True, description="Форматирование текста")
    disfluencies: bool = Field(False, description="Включение дисфлюенций")
    speaker_labels: bool = Field(True, description="Маркировка спикеров")
    speakers_expected: Optional[int] = Field(
        None, description="Ожидаемое число спикеров"
    )
    auto_highlights: bool = Field(
        False, description="Автоматическое выделение ключевых моментов"
    )
    entity_detection: bool = Field(True, description="Обнаружение сущностей")
    sentiment_analysis: bool = Field(False, description="Анализ тональности")
    auto_chapters: bool = Field(False, description="Автоматические главы")
    speech_threshold: Optional[float] = Field(None, description="Пропуск")
    speech_understanding: Optional[SpeechUnderstanding] = Field(
        None, description="Расширенное понимание речи"
    )


class TranscriptResponse(BaseModel):
    id: str = Field(..., description="ID транскрипции")
    status: TranscriptStatus = Field(..., description="Статус транскрипции")
    text: Optional[str] = Field(None, description="Распознанный текст")
    words: Optional[List[Word]] = Field(None, description="Слова")
    utterances: Optional[List[Utterance]] = Field(None, description="Высказывания")
    entities: Optional[List[Entity]] = Field(None, description="Сущности")
    confidence: Optional[float] = Field(None, description="Общая уверенность")
    audio_duration: Optional[float] = Field(None, description="Длительность аудио")
    error: Optional[str] = Field(None, description="Ошибка обработки")
    language_code: Optional[TranscriptLanguageCode] = Field(
        None, description="Код языка"
    )
    language_detection: Optional[bool] = Field(None, description="Определение языка")
    speech_model: Optional[SpeechModel] = Field(
        None, description="Использованная модель"
    )
    auto_highlights_result: Optional[Any] = Field(
        None, description="Результаты авто-выделения"
    )
    content_safety_labels: Optional[Any] = Field(
        None, description="Метки безопасности контента"
    )
    iab_categories_result: Optional[Any] = Field(
        None, description="Результаты IAB категорий"
    )
    chapters: Optional[List[Any]] = Field(None, description="Главы")
    sentiment_analysis_results: Optional[List[Any]] = Field(
        None, description="Результаты анализа тональности"
    )
    summary: Optional[str] = Field(None, description="Суммаризация")


class ApiResponseContext(BaseModel):
    """Контекст API ответа"""

    headers: Dict[str, str]
    body: Dict[str, Any]
    status_code: int


class SubmitTranscriptResponseWithContext(BaseModel):
    """Ответ на создание транскрипции с контекстом"""

    response: TranscriptResponse
    context: ApiResponseContext


class GetTranscriptResponseWithContext(BaseModel):
    """Ответ на получение транскрипции с контекстом"""

    response: TranscriptResponse
    context: ApiResponseContext


class SubtitleFormat(str, Enum):
    SRT = "srt"
    VTT = "vtt"


class SubtitleItem(BaseModel):
    """Модель элемента субтитров"""

    time_start: int = Field(..., description="Время начала в миллисекундах")
    time_end: int = Field(..., description="Время окончания в миллисекундах")
    text: str = Field(..., description="Текст субтитров")

    @classmethod
    def from_vtt_block(cls, vtt_block: str) -> Optional["SubtitleItem"]:
        """
        Парсит блок VTT формата в SubtitleItem
        Формат VTT:
        HH:MM:SS.mmm --> HH:MM:SS.mmm
        Текст субтитров
        """
        lines = vtt_block.strip().split("\n")
        if len(lines) < 2:
            return None

        # Парсим временную метку
        time_line = lines[0]
        if " --> " not in time_line:
            return None

        start_str, end_str = time_line.split(" --> ")

        # Парсим время в миллисекунды
        start_ms = cls._parse_vtt_time(start_str.strip())
        end_ms = cls._parse_vtt_time(end_str.strip())

        # Объединяем текст (может быть многострочным)
        text = "\n".join(lines[1:]).strip()

        return cls(time_start=start_ms, time_end=end_ms, text=text)

    @staticmethod
    def _parse_vtt_time(time_str: str) -> int:
        """
        Парсит VTT время в миллисекунды
        Форматы: HH:MM:SS.mmm или MM:SS.mmm
        """
        try:
            # Убираем возможные пробелы
            time_str = time_str.strip()

            # Разделяем на компоненты времени и миллисекунды
            if "." in time_str:
                time_part, ms_part = time_str.split(".")
                milliseconds = int(ms_part.ljust(3, "0")[:3])  # Обеспечиваем 3 цифры
            else:
                time_part = time_str
                milliseconds = 0

            # Разбираем компоненты времени
            time_components = time_part.split(":")

            if len(time_components) == 3:  # HH:MM:SS
                hours = int(time_components[0])
                minutes = int(time_components[1])
                seconds = int(time_components[2])
            elif len(time_components) == 2:  # MM:SS
                hours = 0
                minutes = int(time_components[0])
                seconds = int(time_components[1])
            else:
                raise ValueError(f"Invalid time format: {time_str}")

            total_ms = (hours * 3600 + minutes * 60 + seconds) * 1000 + milliseconds
            return total_ms

        except (ValueError, IndexError) as e:
            raise ValueError(f"Failed to parse VTT time: {time_str}") from e


class SubtitlesResponse(BaseModel):
    """Ответ с субтитрами"""

    subtitles: List[SubtitleItem] = Field(..., description="Список элементов субтитров")
    format: SubtitleFormat = Field(..., description="Формат субтитров")
    raw_text: str = Field(..., description="Исходный текст субтитров")


class GetSubtitlesResponseWithContext(BaseModel):
    """Ответ на получение субтитров с контекстом"""

    response: SubtitlesResponse
    context: ApiResponseContext
