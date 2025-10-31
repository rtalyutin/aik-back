#!/bin/bash

# Создаем/перезаписываем файл prompt.txt
output_file="prompt.txt"

# Функция для замены специальных символов только в выводе tree
clean_tree_output() {
    sed -e 's/�/ /g' -e 's/\xC2\xA0/ /g' -e 's/\xA0/ /g'
}

# Добавляем вводный текст (перезаписываем файл)
echo "Помогите проанализировать мой проект на fastapi. Вот структура:" > "$output_file"

# Записываем дерево проекта, исключая __pycache__ и все скрытые файлы/директории кроме исключений
tree -I '__pycache__|.*|prompt.txt' --dirsfirst 2>/dev/null | \
sed '1s/^\./project/' | \
clean_tree_output >> "$output_file"

# Добавляем в дерево исключенные скрытые файлы и директории
echo -e "\n.excluded hidden files and directories:" >> "$output_file"
for item in .env.dist .env-ci .dockerignore .gitignore .python-version .github; do
    if [ -f "$item" ] || [ -d "$item" ]; then
        if [ -f "$item" ]; then
            echo "├── $item" >> "$output_file"
        elif [ -d "$item" ]; then
            echo "├── $item/" >> "$output_file"
            # Добавляем содержимое .github директории
            if [ "$item" = ".github" ]; then
                find ".github" -type f | sed 's|^\.github/||' | while read -r github_file; do
                    echo "│   ├── $github_file" >> "$output_file"
                done
            fi
        fi
    fi
done

# Если tree не установлена, используем find с улучшенными условиями исключения
if [ ${PIPESTATUS[0]} -ne 0 ]; then
    # Удаляем предыдущий вывод tree (который пустой из-за ошибки)
    tail -n +2 "$output_file" > temp.txt && mv temp.txt "$output_file"

    echo "project/" >> "$output_file"

    # Исключаем ненужные директории и файлы с помощью улучшенного условия find
    find . -type d \
        \( \
            -name '__pycache__' -o \
            -name 'docs' -o \
            -name '.*' ! -name '.github' \
        \) -prune -o \
        -type f \
        \( \
            -name 'uv.lock' -o \
            -name 'create_promt.sh' -o \
            -name 'prompt.txt' -o \
            -path '*/migrations/README' -o \
            -path '*/migrations/script.py.mako' -o \
            -name '.*' ! \( \
                -name '.env.dist' -o \
                -name '.env-ci' -o \
                -name '.dockerignore' -o \
                -name '.gitignore' -o \
                -name '.python-version' \
            \) \
        \) -prune -o \
        -print | \
    sed -e 's;[^/]*/;|____;g' -e 's;____|; |;g' | \
    clean_tree_output | \
    sort >> "$output_file"

    # Добавляем исключенные скрытые файлы и директории
    echo -e "\n.excluded hidden files and directories:" >> "$output_file"
    for item in .env.dist .env-ci .dockerignore .gitignore .python-version .github; do
        if [ -f "$item" ] || [ -d "$item" ]; then
            if [ -f "$item" ]; then
                echo "├── $item" >> "$output_file"
            elif [ -d "$item" ]; then
                echo "├── $item/" >> "$output_file"
                # Добавляем содержимое .github директории
                if [ "$item" = ".github" ]; then
                    find ".github" -type f | sed 's|^\.github/||' | while read -r github_file; do
                        echo "│   ├── $github_file" >> "$output_file"
                    done
                fi
            fi
        fi
    done
fi

# Обрабатываем все файлы проекта с исключениями
# Используем более простое и надежное условие find
find . -type f | while read -r file; do
    # Пропускаем файлы в исключенных директориях
    case "$file" in
        */__pycache__/*|*/.venv/*|*/.git/*|*/.idea/*|*/.ruff_cache/*|*/docs/*)
            continue
            ;;
    esac

    # Пропускаем исключенные файлы
    case "$file" in
        ./uv.lock|./create_promt.sh|./prompt.txt|*/migrations/README|*/migrations/script.py.mako)
            continue
            ;;
    esac

    # Пропускаем скрытые файлы, кроме исключений
    filename=$(basename "$file")
    case "$filename" in
        .*)
            # Это скрытый файл - проверяем исключения
            case "$filename" in
                .env.dist|.env-ci|.dockerignore|.gitignore|.python-version)
                    # Это исключение - обрабатываем
                    ;;
                *)
                    # Пропускаем все остальные скрытые файлы
                    continue
                    ;;
            esac
            ;;
    esac

    # Пропускаем бинарные файлы
    case "$file" in
        *.pyc|*.pyo|*.pyd|*.so|*.dll|*.exe|*.bin|*.dat|*.db|*.sqlite|*.jpg|*.jpeg|*.png|*.gif|*.ico|*.svg|*.woff|*.woff2|*.ttf|*.eot)
            continue
            ;;
    esac

    echo -e "\n**$file:**" >> "$output_file"

    # Проверяем, является ли файл текстовым
    if file "$file" | grep -q text; then
        # Читаем файл без изменений
        cat "$file" 2>/dev/null >> "$output_file" || echo "[не удалось прочитать файл]" >> "$output_file"
    else
        echo "[бинарный файл]" >> "$output_file"
    fi
done

echo -e "\nТочки запуска проекта api/__main__.py для FastAPI и background/__main__.py для фоновых задач" >> "$output_file"
echo -e "\nОсновные правила работы с проектом:" >> "$output_file"
echo -e "1. Мы ни когда не возвращаем и не принимаем не типизированные данные. То есть если мы получаем данные из пост запроса - это должна быть пайдентик модель (исключение - файлы, их следуем принимать в multipart формате)." >> "$output_file"
echo -e "2. Если мы возвращаем что либо в респонсе - это тоже должна быть пайдентик модель обернутая в BaseDataResponse или BaseListDataResponse. Например BaseDataResponse[TrackCreatingTaskResponse] или BaseListDataResponse[TrackCreatingTaskResponse]. Исключение - получение файлов или стримов." >> "$output_file"
echo -e "3. У нас используется JSON api, тело принимается всегда в нем, если нет исключений, например - файлы, их следуем принимать в multipart формате" >> "$output_file"
echo -e "4. Ошибки мы не транслируем в HTTPException. Если нам нужно выбросить бизнесовую ошибку, то мы просто выбрасываем исключение, которое наследуется от BaseError и дальше обработчик ошибок сам срендерит корректный респонс. Если возникает какая то неожиданная ошибка, то мы опять же в коде роутера и бизнес логики можем просто оставить выбрасывание этой ошибки так как хендлер ошибок ее преобразует в 500." >> "$output_file"
echo -e "5. В миграциях базы данных мы не используем Enum, вместо него используются обычные строки или числа в зависимости от содержимого. Но в моделях SQLAlchemy следует использовать Enum с параметром native_enum=False" >> "$output_file"
echo -e "6. Внутри пайдентик моделей также не следует использовать не структурированные Dict, вместо этого следует сделать вложенную пайдентик модель" >> "$output_file"

echo "Готово! Файл $output_file создан/перезаписан."