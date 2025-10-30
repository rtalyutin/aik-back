"""
Entry point для запуска API сервера.
Используйте: python -m api
"""

import uvicorn
from config import get_config
from logger import setup_logging

if __name__ == "__main__":
    config = get_config()

    setup_logging(config, service_name="api")

    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=config.DEBUG,
        log_config=None,  # Отключаем стандартную конфигурацию uvicorn
        access_log=True,  # Включаем access логи (они пойдут через наш handler)
    )
