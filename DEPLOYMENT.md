# Инструкция по развертыванию FastAPI OCR Service

Полное руководство по запуску FastAPI OCR сервиса на сервере с привязкой домена и настройкой SSL сертификата через Certbot.

---

## Содержание

1. [Предварительные требования](#предварительные-требования)
2. [Установка системных зависимостей](#установка-системных-зависимостей)
3. [Установка Python зависимостей](#установка-python-зависимостей)
4. [Запуск сервиса](#запуск-сервиса)
5. [Настройка домена и DNS](#настройка-домена-и-dns)
6. [Получение SSL сертификата через Certbot](#получение-ssl-сертификата-через-certbot)
7. [Настройка Nginx как reverse proxy](#настройка-nginx-как-reverse-proxy)
8. [Система управления процессом (Systemd)](#система-управления-процессом-systemd)
9. [Проверка и мониторинг](#проверка-и-мониторинг)

---

## Предварительные требования

- Ubuntu/Debian сервер с доступом в интернет
- Доступ к root (или sudoers)
- Доменное имя (например, `YOUR_DOMAIN.duckdns.org`) или готовый DuckDNS аккаунт
- Python 3.8+
- Установленные Nginx и Certbot

---

## Установка системных зависимостей

### 1. Обновить систему

```bash
sudo apt-get update
sudo apt-get upgrade -y
```

### 2. Установить Tesseract OCR и поддержку русского языка

```bash
sudo apt-get install -y tesseract-ocr tesseract-ocr-rus tesseract-ocr-eng
```

### 3. Установить Nginx и Certbot

```bash
sudo apt-get install -y nginx certbot python3-certbot-nginx
```

### 4. Установить Python3 и pip

```bash
sudo apt-get install -y python3 python3-pip python3-venv
```

### 5. Установить дополнительные системные зависимости

```bash
# Для работы с PDF
sudo apt-get install -y libpoppler-cpp-dev

# Для работы с изображениями
sudo apt-get install -y libjpeg-dev zlib1g-dev
```

---

## Установка Python зависимостей

### 1. Перейти в каталог проекта

```bash
cd /home/username/fastapi_ocr_service
```

### 2. Создать виртуальное окружение (рекомендуется)

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Обновить pip, setuptools и wheel

```bash
pip install --upgrade pip setuptools wheel
```

### 4. Установить зависимости из requirements.txt

```bash
pip install -r requirements.txt
```

---

## Запуск сервиса

### Локальный тест (перед развертыванием на сервере)

```bash
# Активировать виртуальное окружение
source venv/bin/activate

# Запустить сервис на localhost:8000
python main.py
```

Проверить здоровье сервиса:
```bash
curl http://localhost:8000/
```

Документация API доступна по адресам:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## Настройка домена и DNS

### Для DuckDNS (YOUR_DOMAIN.duckdns.org)

#### 1. Создать аккаунт DuckDNS

- Перейти на https://www.duckdns.org
- Авторизоваться или зарегистрироваться
- Создать домен (например, `YOUR_DOMAIN`)

#### 2. Получить токен DuckDNS

- В личном кабинете DuckDNS скопировать токен
- Сохранить его в безопасном месте

#### 3. Обновить IP адрес DuckDNS

```bash
# Однократное обновление IP
curl "https://www.duckdns.org/update?domains=YOUR_DOMAIN&token=YOUR_TOKEN&ip="

# Проверить, что домен указывает на ваш IP
dig YOUR_DOMAIN.duckdns.org
# или
nslookup YOUR_DOMAIN.duckdns.org
```

#### 4. Автоматическое обновление IP (опционально)

Создать крон-задачу для автоматического обновления IP каждые 5 минут:

```bash
# Открыть crontab
crontab -e

# Добавить строку:
*/5 * * * * curl -s "https://www.duckdns.org/update?domains=YOUR_DOMAIN&token=YOUR_TOKEN&ip=" >> /tmp/duckdns_update.log 2>&1
```

---

## Получение SSL сертификата через Certbot

### 1. Убедиться, что сервер доступен на портах 80 и 443

```bash
# Проверить, слушает ли сервер порт 80
sudo netstat -tulpn | grep :80
```

### 2. Остановить Nginx перед получением сертификата (если нужно)

```bash
# Nginx будет перенастроен Certbot автоматически, можно оставить запущенным
# Но на первый раз рекомендуется остановить:
sudo systemctl stop nginx
```

### 3. Получить сертификат через Certbot (standalone mode)

```bash
sudo certbot certonly --standalone \
  -d YOUR_DOMAIN.duckdns.org \
  --email your-email@example.com \
  --agree-tos \
  --non-interactive \
  --renew-hook "sudo systemctl restart nginx"
```

**Примечание:** Замените `your-email@example.com` на ваш email.

### 4. Проверить, что сертификат получен

```bash
sudo ls -la /etc/letsencrypt/live/YOUR_DOMAIN.duckdns.org/

# Должны быть файлы:
# - cert.pem (сертификат)
# - privkey.pem (приватный ключ)
# - chain.pem (цепочка сертификатов)
# - fullchain.pem (полная цепочка)
```

### 5. Настроить автоматическое обновление сертификата

```bash
# Certbot уже устанавливает timer для автоматического обновления
# Проверить статус:
sudo systemctl status certbot.timer

# Если timer неактивен, включить его:
sudo systemctl enable certbot.timer
sudo systemctl start certbot.timer

# Тестовое обновление (без реального обновления):
sudo certbot renew --dry-run
```

---

## Настройка Nginx как reverse proxy

### 1. Создать конфиг для Nginx

```bash
sudo nano /etc/nginx/sites-available/fastapi_ocr
```

### 2. Добавить следующую конфигурацию

```nginx
# Redirect HTTP to HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name YOUR_DOMAIN.duckdns.org;

    location / {
        return 301 https://$server_name$request_uri;
    }

    # Разрешить Certbot автоматически обновлять сертификат
    location /.well-known/acme-challenge/ {
        alias /var/www/certbot/.well-known/acme-challenge/;
    }
}

# HTTPS конфигурация
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name YOUR_DOMAIN.duckdns.org;

    # SSL сертификаты
    ssl_certificate /etc/letsencrypt/live/YOUR_DOMAIN.duckdns.org/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/YOUR_DOMAIN.duckdns.org/privkey.pem;

    # SSL конфигурация безопасности
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384';
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # HSTS (рекомендуется, но будьте осторожны)
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # Лимиты размера файла
    client_max_body_size 100M;

    # Проксирование запросов на локальный сервис
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;

        # Таймауты для длительной обработки файлов
        proxy_connect_timeout 60s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }

    # Логирование
    access_log /var/log/nginx/fastapi_ocr_access.log;
    error_log /var/log/nginx/fastapi_ocr_error.log;
}
```

### 3. Активировать конфиг Nginx

```bash
# Создать символическую ссылку на sites-enabled
sudo ln -s /etc/nginx/sites-available/fastapi_ocr /etc/nginx/sites-enabled/

# Проверить синтаксис конфигурации
sudo nginx -t

# Если ошибок нет, перезагрузить Nginx
sudo systemctl restart nginx
```

### 4. Проверить статус Nginx

```bash
sudo systemctl status nginx

# Должно быть: Active (running)
```

---

## Система управления процессом (Systemd)

### 1. Создать systemd сервис для FastAPI приложения

```bash
sudo nano /etc/systemd/system/fastapi_ocr.service
```

### 2. Добавить конфигурацию сервиса

```ini
[Unit]
Description=FastAPI OCR Service
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/home/username/fastapi_ocr_service
Environment="PATH=/home/username/fastapi_ocr_service/venv/bin"
ExecStart=/home/username/fastapi_ocr_service/venv/bin/python main.py
Restart=always
RestartSec=10

# Логирование
StandardOutput=journal
StandardError=journal
SyslogIdentifier=fastapi_ocr

[Install]
WantedBy=multi-user.target
```

**Важно:** Замените `/home/username/` на путь вашего проекта!

### 3. Изменить права доступа на каталог проекта (если нужно)

```bash
# Если вы создали проект под другим пользователем, измените владельца:
sudo chown -R www-data:www-data /home/username/fastapi_ocr_service

# Установить права доступа
sudo chmod 755 /home/username/fastapi_ocr_service
sudo chmod 755 /home/username/fastapi_ocr_service/venv/bin/python
```

### 4. Активировать и запустить сервис

```bash
# Перезагрузить конфигурацию systemd
sudo systemctl daemon-reload

# Включить сервис при загрузке системы
sudo systemctl enable fastapi_ocr.service

# Запустить сервис
sudo systemctl start fastapi_ocr.service

# Проверить статус
sudo systemctl status fastapi_ocr.service
```

### 5. Управление сервисом

```bash
# Просмотреть логи сервиса
sudo journalctl -u fastapi_ocr.service -f

# Последние 100 строк логов
sudo journalctl -u fastapi_ocr.service -n 100

# Перезагрузить сервис
sudo systemctl restart fastapi_ocr.service

# Остановить сервис
sudo systemctl stop fastapi_ocr.service

# Запустить сервис
sudo systemctl start fastapi_ocr.service
```

---

## Проверка и мониторинг

### 1. Проверить доступность сервиса через HTTPS

```bash
# Health check
curl -v https://YOUR_DOMAIN.duckdns.org/

# Должен вернуть: {"status":"ok","message":"OCR Service is running"}
```

### 2. Протестировать endpoints

```bash
# Загрузить изображение для OCR
curl -X POST "https://YOUR_DOMAINduckdns.org/image" \
  -F "file=@test_image.jpg"

# Загрузить PDF
curl -X POST "https://YOUR_DOMAIN.duckdns.org/pdf" \
  -F "file=@test_document.pdf"
```

### 3. Проверить статус портов

```bash
# Убедиться, что сервис слушает на порту 8000
sudo netstat -tulpn | grep 8000

# Проверить, что Nginx слушает на портах 80 и 443
sudo netstat -tulpn | grep nginx
```

### 4. Проверить SSL сертификат

```bash
# Информация о сертификате
echo | openssl s_client -servername YOUR_DOMAIN.duckdns.org -connect YOUR_DOMAIN.duckdns.org:443 2>/dev/null | openssl x509 -text

# Срок действия сертификата
sudo certbot certificates
```

### 5. Просмотреть логи

```bash
# Логи Nginx
sudo tail -f /var/log/nginx/fastapi_ocr_access.log
sudo tail -f /var/log/nginx/fastapi_ocr_error.log

# Логи FastAPI сервиса
sudo journalctl -u fastapi_ocr.service -f
```

### 6. Мониторинг нагрузки

```bash
# Проверить использование ресурсов
top

# Проверить процесс Python
ps aux | grep python

# Проверить открытые порты
sudo lsof -i -P -n
```

---

## Решение проблем

### Проблема: Certbot не может получить сертификат

**Решение:**
```bash
# Убедиться, что порт 80 открыт
sudo ufw allow 80
sudo ufw allow 443

# Проверить, что домен разрешается правильно
dig YOUR_DOMAIN.duckdns.org

# Получить сертификат с подробным выводом ошибок
sudo certbot certonly --standalone \
  -d YOUR_DOMAIN.duckdns.org \
  -v
```

### Проблема: Сервис не запускается

**Решение:**
```bash
# Просмотреть логи ошибок
sudo journalctl -u fastapi_ocr.service -n 50 -e

# Проверить, что виртуальное окружение создано
ls -la /home/username/fastapi_ocr_service/venv/bin/python

# Проверить права доступа
ls -la /home/username/fastapi_ocr_service/
```

### Проблема: Nginx возвращает 502 Bad Gateway

**Решение:**
```bash
# Убедиться, что FastAPI сервис запущен
sudo systemctl status fastapi_ocr.service

# Проверить, что сервис слушает на localhost:8000
sudo netstat -tulpn | grep 8000

# Проверить логи Nginx
sudo tail -f /var/log/nginx/fastapi_ocr_error.log

# Увеличить таймаут в Nginx (см. конфиг выше)
```

### Проблема: "Connection refused" при обращении к API

**Решение:**
```bash
# Проверить, что все процессы запущены:
sudo systemctl status nginx
sudo systemctl status fastapi_ocr.service

# Перезагрузить оба сервиса
sudo systemctl restart nginx
sudo systemctl restart fastapi_ocr.service

# Проверить локально
curl http://localhost:8000/
```

---

## Удаление и переинсталляция

### Остановить и удалить сервис

```bash
# Остановить сервис
sudo systemctl stop fastapi_ocr.service

# Отключить автозагрузку
sudo systemctl disable fastapi_ocr.service

# Удалить файл сервиса
sudo rm /etc/systemd/system/fastapi_ocr.service

# Перезагрузить systemd
sudo systemctl daemon-reload
```

### Удалить Nginx конфиг

```bash
# Удалить символическую ссылку
sudo rm /etc/nginx/sites-enabled/fastapi_ocr

# Удалить файл конфигурации
sudo rm /etc/nginx/sites-available/fastapi_ocr

# Перезагрузить Nginx
sudo systemctl restart nginx
```

### Удалить SSL сертификат

```bash
# Удалить сертификат Certbot
sudo certbot delete --cert-name YOUR_DOMAIN.duckdns.org
```

---

## Быстрый старт (TL;DR)

```bash
# 1. Установить зависимости
sudo apt-get update && sudo apt-get install -y nginx certbot python3-certbot-nginx tesseract-ocr tesseract-ocr-rus python3 python3-pip

# 2. Клонировать и подготовить проект
cd /home/username/fastapi_ocr_service
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Настроить DuckDNS и получить сертификат
# - Создать домен на https://www.duckdns.org
# - Обновить IP на сервере
curl "https://www.duckdns.org/update?domains=YOUR_DOMAIN&token=YOUR_TOKEN&ip="

# 4. Получить SSL сертификат
sudo certbot certonly --standalone -d YOUR_DOMAIN.duckdns.org --email your-email@example.com --agree-tos

# 5. Создать Nginx конфиг (см. раздел выше)
sudo nano /etc/nginx/sites-available/fastapi_ocr

# 6. Создать systemd сервис (см. раздел выше)
sudo nano /etc/systemd/system/fastapi_ocr.service

# 7. Запустить всё
sudo systemctl daemon-reload
sudo systemctl enable fastapi_ocr.service
sudo systemctl start fastapi_ocr.service
sudo systemctl restart nginx

# 8. Проверить
curl https://YOUR_DOMAIN.duckdns.org/
```

---

## Полезные ссылки

- [FastAPI документация](https://fastapi.tiangolo.com/)
- [Uvicorn документация](https://www.uvicorn.org/)
- [Nginx документация](https://nginx.org/en/docs/)
- [Certbot документация](https://certbot.eff.org/docs/)
- [DuckDNS](https://www.duckdns.org/)
- [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki)

---

## Контакты и поддержка

Если возникают проблемы при развертывании, проверьте:
1. Логи сервиса: `sudo journalctl -u fastapi_ocr.service -f`
2. Логи Nginx: `sudo tail -f /var/log/nginx/fastapi_ocr_error.log`
3. Статус сервисов: `sudo systemctl status fastapi_ocr nginx`
4. Доступность порта 8000: `sudo netstat -tulpn | grep 8000`

