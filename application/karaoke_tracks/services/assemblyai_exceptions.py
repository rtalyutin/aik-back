from core.errors import BaseError


class AssemblyAIError(BaseError):
    """Базовое исключение для ошибок AssemblyAI API"""

    status_code = 502
    code = "assembly_ai_error"
    message = "AssemblyAI service error"


class AssemblyAISubmitError(AssemblyAIError):
    """Ошибка создания транскрипции"""

    code = "assembly_ai_submit_error"
    message = "Failed to submit transcription to AssemblyAI"


class AssemblyAIGetError(AssemblyAIError):
    """Ошибка получения транскрипции"""

    code = "assembly_ai_get_error"
    message = "Failed to get transcription from AssemblyAI"


class AssemblyAITimeoutError(AssemblyAIError):
    """Таймаут операции"""

    status_code = 504
    code = "assembly_ai_timeout_error"
    message = "AssemblyAI operation timeout"


class AssemblyAITranscriptionError(AssemblyAIError):
    """Ошибка во время транскрипции"""

    code = "assembly_ai_transcription_error"
    message = "Transcription failed in AssemblyAI"


class AssemblyAISubtitlesError(AssemblyAIError):
    """Ошибка получения субтитров"""

    code = "assembly_ai_subtitles_error"
    message = "Failed to get subtitles from AssemblyAI"


class AssemblyAISubtitlesParseError(AssemblyAISubtitlesError):
    """Ошибка парсинга субтитров"""

    code = "assembly_ai_subtitles_parse_error"
    message = "Failed to parse subtitles from AssemblyAI"
