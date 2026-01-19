# FastAPI OCR Service

A modern FastAPI service that extracts text from PDF and image files using advanced OCR technologies (pytesseract, pdfplumber, Pillow).

**Поддерживаемые языки / Supported Languages:** English, Русский

---

## Table of Contents

- [English](#english)
- [Русский](#русский)

---

## English

### Overview

This FastAPI service provides two REST API endpoints for optical character recognition (OCR):
- **PDF extraction**: Hybrid extraction using pdfplumber with automatic OCR fallback for scanned documents
- **Image OCR**: Extract text from images with customizable Tesseract settings and preprocessing pipeline

### Features

- **Hybrid PDF Extraction**: Automatically detects scanned PDFs and falls back to OCR
- **Image Preprocessing**: Optional preprocessing pipeline (grayscale, denoise, deskew, binarize, etc.)
- **Multiple PSM Modes**: Compare multiple Tesseract page segmentation modes in a single request
- **OCR Confidence**: Get confidence scores for OCR results
- **Encrypted PDF Support**: Handle password-protected PDFs

### Setup

#### 1. Install Python Dependencies

```bash
pip install -r requirements.txt
```

#### 2. Install System Dependencies

**Ubuntu/Debian:**
```bash
sudo apt-get install tesseract-ocr tesseract-ocr-rus poppler-utils
```

**macOS:**
```bash
brew install tesseract tesseract-lang poppler
```

**Windows:**
- Tesseract: https://github.com/UB-Mannheim/tesseract/wiki
- Poppler: https://github.com/oschwartz10612/poppler-windows/releases

### Running the Service

```bash
python main.py
```

The API will be available at: `http://localhost:8000`

- **Interactive API docs (Swagger UI)**: `http://localhost:8000/docs`
- **Alternative docs (ReDoc)**: `http://localhost:8000/redoc`

### Endpoints

#### POST /pdf

Extract text from a PDF file with hybrid extraction (pdfplumber + OCR fallback).

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `file` | file | required | PDF file to upload |
| `password` | string | null | Password for encrypted PDFs |
| `detect_vertical` | bool | false | Enable vertical text detection |
| `force_ocr` | bool | false | Force OCR extraction instead of pdfplumber |
| `ocr_language` | string | "eng" | OCR language code (e.g., "rus", "eng+rus") |
| `ocr_psm` | int | 3 | OCR Page Segmentation Mode (0-13) |
| `ocr_dpi` | int | 300 | DPI for rendering PDF pages to images |
| `min_chars_threshold` | int | 50 | Chars/page threshold for OCR fallback |
| `ocr_preprocess` | string | null | Preprocessing steps for OCR (comma-separated) |

**Response:**
```json
{
  "status": "success",
  "type": "pdf",
  "filename": "document.pdf",
  "pages": 5,
  "extraction_method": "pdfplumber",
  "ocr_pages": 0,
  "pdfplumber_pages": 5,
  "results": [
    {
      "page": 1,
      "text": "Extracted text...",
      "text_length": 1234,
      "method": "pdfplumber"
    }
  ]
}
```

**OCR Response (when fallback occurs or force_ocr=true):**
```json
{
  "status": "success",
  "type": "pdf",
  "filename": "scanned.pdf",
  "pages": 3,
  "extraction_method": "ocr",
  "ocr_pages": 3,
  "pdfplumber_pages": 0,
  "results": [
    {
      "page": 1,
      "text": "Extracted text...",
      "text_length": 1234,
      "method": "ocr",
      "ocr_confidence": 92.5
    }
  ]
}
```

**Examples:**
```bash
# Basic usage (auto-detects scanned PDFs)
curl -X POST "http://localhost:8000/pdf" \
  -F "file=@document.pdf"

# Force OCR with Russian language
curl -X POST "http://localhost:8000/pdf?force_ocr=true&ocr_language=rus" \
  -F "file=@russian_scan.pdf"

# Force OCR with preprocessing
curl -X POST "http://localhost:8000/pdf?force_ocr=true&ocr_preprocess=grayscale,denoise,binarize" \
  -F "file=@low_quality_scan.pdf"

# Encrypted PDF with password
curl -X POST "http://localhost:8000/pdf" \
  -F "file=@encrypted.pdf" \
  -d "password=secret123"

# Multilingual OCR
curl -X POST "http://localhost:8000/pdf?force_ocr=true&ocr_language=eng+rus" \
  -F "file=@multilingual.pdf"
```

#### POST /image

Extract text from an image using Tesseract OCR with optional preprocessing.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `file` | file | required | Image file (jpg, png, bmp, gif, tiff) |
| `lang` | string | "eng" | Language code (e.g., "eng", "rus", "eng+rus") |
| `psm` | string | "3" | Page Segmentation Mode(s) - single or comma-separated |
| `oem` | int | 3 | OCR Engine Mode (0=legacy, 1=neural, 2=both, 3=auto) |
| `timeout` | int | 0 | Timeout in seconds per PSM (0=no timeout) |
| `preprocess` | string | null | Preprocessing steps (comma-separated) |
| `clahe_clip` | float | 2.0 | CLAHE clip limit |
| `clahe_grid` | int | 8 | CLAHE grid size |
| `denoise_strength` | int | 10 | Denoising strength (1-30) |
| `binarize_method` | string | "otsu" | Binarization method |
| `upscale_min` | int | 1000 | Minimum dimension for upscaling |

**Preprocessing Steps:**
| Step | Description |
|------|-------------|
| `upscale` | Upscale small images to min dimension |
| `grayscale` | Convert to grayscale |
| `contrast` | Histogram equalization |
| `clahe` | Adaptive histogram equalization (better for text) |
| `denoise` | Non-local means denoising |
| `deskew` | Correct rotation/skew angle |
| `binarize` | Otsu or adaptive thresholding |

**Binarization Methods:**
- `otsu` - Otsu's automatic thresholding (default)
- `adaptive_mean` - Adaptive mean thresholding
- `adaptive_gaussian` - Adaptive Gaussian thresholding

**Response:**
```json
{
  "status": "success",
  "type": "image",
  "filename": "receipt.jpg",
  "image_size": [640, 480],
  "image_format": "JPEG",
  "image_mode": "L",
  "preprocessing": ["grayscale", "denoise", "binarize"],
  "ocr_config": {
    "language": "eng",
    "psm_modes": [3],
    "oem": 3,
    "timeout": 0
  },
  "results": [
    {
      "psm": 3,
      "text": "Extracted text from image...",
      "text_length": 456
    }
  ],
  "total_psm_modes": 1
}
```

**Examples:**
```bash
# Basic usage
curl -X POST "http://localhost:8000/image" \
  -F "file=@receipt.jpg"

# Full preprocessing pipeline
curl -X POST "http://localhost:8000/image?preprocess=upscale,grayscale,denoise,clahe,deskew,binarize" \
  -F "file=@low_quality.jpg"

# Denoise + binarize with adaptive Gaussian
curl -X POST "http://localhost:8000/image?preprocess=denoise,binarize&binarize_method=adaptive_gaussian" \
  -F "file=@noisy_form.jpg"

# Compare multiple PSM modes
curl -X POST "http://localhost:8000/image?psm=3,6,11" \
  -F "file=@document.jpg"

# Russian with preprocessing
curl -X POST "http://localhost:8000/image?lang=rus&preprocess=grayscale,binarize" \
  -F "file=@russian_text.jpg"

# Custom CLAHE parameters
curl -X POST "http://localhost:8000/image?preprocess=clahe&clahe_clip=3.0&clahe_grid=16" \
  -F "file=@low_contrast.jpg"
```

#### GET /

Health check endpoint.

**Response:**
```json
{
  "status": "ok",
  "message": "OCR Service is running"
}
```

### Hybrid PDF Extraction

The `/pdf` endpoint uses a hybrid approach:

1. **First attempt**: Extract text using pdfplumber (fast, preserves layout)
2. **Fallback check**: If extraction yields insufficient text:
   - Total characters < 100
   - Average characters per page < threshold (default: 50)
   - More than 50% of pages are empty
3. **OCR fallback**: Render PDF to images and run Tesseract OCR

This ensures optimal results for both text-based PDFs (fast extraction) and scanned documents (OCR with preprocessing).

### Image Preprocessing Pipeline

The preprocessing pipeline processes steps in order. Recommended order for best results:

1. `upscale` - First, ensure sufficient resolution
2. `grayscale` - Convert to single channel
3. `denoise` - Remove noise before other operations
4. `deskew` - Correct rotation
5. `clahe` or `contrast` - Enhance contrast
6. `binarize` - Final thresholding

Example for low-quality scans:
```bash
curl -X POST "http://localhost:8000/image?preprocess=upscale,grayscale,denoise,deskew,clahe,binarize" \
  -F "file=@scan.jpg"
```

### Error Handling

| Status Code | Meaning | Cause |
|---|---|---|
| 400 | Bad Request | Unsupported file format or invalid parameters |
| 500 | Internal Server Error | Processing error (check logs) |
| 504 | Gateway Timeout | OCR processing exceeded timeout |

### Supported Formats

- **PDF**: .pdf (with optional password protection)
- **Images**: .jpg, .jpeg, .png, .bmp, .gif, .tiff

---

## Русский

### Описание

FastAPI сервис предоставляет два REST API эндпоинта для оптического распознавания текста (OCR):
- **Извлечение из PDF**: Гибридное извлечение с использованием pdfplumber и автоматическим OCR fallback для сканов
- **OCR изображений**: Извлечение текста из изображений с настраиваемым preprocessing pipeline

### Возможности

- **Гибридное извлечение PDF**: Автоматически определяет сканы и переключается на OCR
- **Preprocessing изображений**: Опциональный пайплайн обработки (grayscale, denoise, deskew, binarize и др.)
- **Множественные PSM режимы**: Сравнение нескольких режимов сегментации в одном запросе
- **Уверенность OCR**: Получение оценки уверенности для OCR результатов
- **Поддержка зашифрованных PDF**: Работа с защищенными паролем документами

### Установка

#### 1. Установка Python зависимостей

```bash
pip install -r requirements.txt
```

#### 2. Установка системных зависимостей

**Ubuntu/Debian:**
```bash
sudo apt-get install tesseract-ocr tesseract-ocr-rus poppler-utils
```

**macOS:**
```bash
brew install tesseract tesseract-lang poppler
```

**Windows:**
- Tesseract: https://github.com/UB-Mannheim/tesseract/wiki
- Poppler: https://github.com/oschwartz10612/poppler-windows/releases

### Запуск сервиса

```bash
python main.py
```

API будет доступен по адресу: `http://localhost:8000`

- **Интерактивная документация (Swagger UI)**: `http://localhost:8000/docs`
- **Альтернативная документация (ReDoc)**: `http://localhost:8000/redoc`

### Эндпоинты

#### POST /pdf

Извлечение текста из PDF с гибридной экстракцией (pdfplumber + OCR fallback).

**Параметры:**
| Параметр | Тип | По умолчанию | Описание |
|----------|-----|--------------|----------|
| `file` | file | обязательно | PDF файл для загрузки |
| `password` | string | null | Пароль для зашифрованных PDF |
| `detect_vertical` | bool | false | Включить обнаружение вертикального текста |
| `force_ocr` | bool | false | Принудительно использовать OCR |
| `ocr_language` | string | "eng" | Язык OCR (например, "rus", "eng+rus") |
| `ocr_psm` | int | 3 | Режим сегментации страницы (0-13) |
| `ocr_dpi` | int | 300 | DPI для рендеринга страниц PDF |
| `min_chars_threshold` | int | 50 | Порог символов/страница для OCR fallback |
| `ocr_preprocess` | string | null | Шаги preprocessing для OCR (через запятую) |

**Ответ:**
```json
{
  "status": "success",
  "type": "pdf",
  "filename": "document.pdf",
  "pages": 5,
  "extraction_method": "pdfplumber",
  "ocr_pages": 0,
  "pdfplumber_pages": 5,
  "results": [
    {
      "page": 1,
      "text": "Извлеченный текст...",
      "text_length": 1234,
      "method": "pdfplumber"
    }
  ]
}
```

**OCR ответ (при fallback или force_ocr=true):**
```json
{
  "status": "success",
  "type": "pdf",
  "filename": "scanned.pdf",
  "pages": 3,
  "extraction_method": "ocr",
  "ocr_pages": 3,
  "pdfplumber_pages": 0,
  "results": [
    {
      "page": 1,
      "text": "Извлеченный текст...",
      "text_length": 1234,
      "method": "ocr",
      "ocr_confidence": 92.5
    }
  ]
}
```

**Примеры:**
```bash
# Базовое использование (автоопределение сканов)
curl -X POST "http://localhost:8000/pdf" \
  -F "file=@document.pdf"

# Принудительный OCR с русским языком
curl -X POST "http://localhost:8000/pdf?force_ocr=true&ocr_language=rus" \
  -F "file=@russian_scan.pdf"

# Принудительный OCR с preprocessing
curl -X POST "http://localhost:8000/pdf?force_ocr=true&ocr_preprocess=grayscale,denoise,binarize" \
  -F "file=@low_quality_scan.pdf"

# Зашифрованный PDF с паролем
curl -X POST "http://localhost:8000/pdf" \
  -F "file=@encrypted.pdf" \
  -d "password=secret123"
```

#### POST /image

Извлечение текста из изображения с использованием Tesseract OCR и опциональным preprocessing.

**Параметры:**
| Параметр | Тип | По умолчанию | Описание |
|----------|-----|--------------|----------|
| `file` | file | обязательно | Изображение (jpg, png, bmp, gif, tiff) |
| `lang` | string | "eng" | Код языка (например, "rus", "eng+rus") |
| `psm` | string | "3" | Режим сегментации - один или через запятую |
| `oem` | int | 3 | Режим OCR движка (0-3) |
| `timeout` | int | 0 | Таймаут в секундах (0=без таймаута) |
| `preprocess` | string | null | Шаги preprocessing (через запятую) |
| `clahe_clip` | float | 2.0 | CLAHE clip limit |
| `clahe_grid` | int | 8 | CLAHE grid size |
| `denoise_strength` | int | 10 | Сила шумоподавления (1-30) |
| `binarize_method` | string | "otsu" | Метод бинаризации |
| `upscale_min` | int | 1000 | Минимальное измерение для upscale |

**Шаги Preprocessing:**
| Шаг | Описание |
|-----|----------|
| `upscale` | Увеличение маленьких изображений |
| `grayscale` | Конвертация в оттенки серого |
| `contrast` | Выравнивание гистограммы |
| `clahe` | Адаптивное выравнивание (лучше для текста) |
| `denoise` | Шумоподавление |
| `deskew` | Коррекция угла наклона |
| `binarize` | Пороговая бинаризация |

**Методы бинаризации:**
- `otsu` - Автоматический порог по Otsu (по умолчанию)
- `adaptive_mean` - Адаптивный средний порог
- `adaptive_gaussian` - Адаптивный гауссов порог

**Ответ:**
```json
{
  "status": "success",
  "type": "image",
  "filename": "receipt.jpg",
  "image_size": [640, 480],
  "image_format": "JPEG",
  "image_mode": "L",
  "preprocessing": ["grayscale", "denoise", "binarize"],
  "ocr_config": {
    "language": "rus",
    "psm_modes": [3],
    "oem": 3,
    "timeout": 0
  },
  "results": [
    {
      "psm": 3,
      "text": "Извлеченный текст...",
      "text_length": 456
    }
  ],
  "total_psm_modes": 1
}
```

**Примеры:**
```bash
# Базовое использование с русским языком
curl -X POST "http://localhost:8000/image?lang=rus" \
  -F "file=@russian_text.jpg"

# Полный preprocessing пайплайн
curl -X POST "http://localhost:8000/image?preprocess=upscale,grayscale,denoise,clahe,deskew,binarize" \
  -F "file=@low_quality.jpg"

# Шумоподавление + бинаризация
curl -X POST "http://localhost:8000/image?preprocess=denoise,binarize&binarize_method=adaptive_gaussian" \
  -F "file=@noisy_form.jpg"

# Сравнение нескольких PSM режимов
curl -X POST "http://localhost:8000/image?lang=rus&psm=3,6,11" \
  -F "file=@document.jpg"
```

#### GET /

Эндпоинт проверки здоровья сервиса.

**Ответ:**
```json
{
  "status": "ok",
  "message": "OCR Service is running"
}
```

### Гибридное извлечение PDF

Эндпоинт `/pdf` использует гибридный подход:

1. **Первая попытка**: Извлечение текста через pdfplumber (быстро, сохраняет форматирование)
2. **Проверка fallback**: Если извлечено недостаточно текста:
   - Всего символов < 100
   - Среднее символов на страницу < порога (по умолчанию: 50)
   - Более 50% страниц пустые
3. **OCR fallback**: Рендеринг PDF в изображения и запуск Tesseract OCR

Это обеспечивает оптимальные результаты как для текстовых PDF (быстрое извлечение), так и для сканов (OCR с preprocessing).

### Пайплайн preprocessing изображений

Шаги preprocessing выполняются по порядку. Рекомендуемый порядок для лучших результатов:

1. `upscale` - Сначала обеспечить достаточное разрешение
2. `grayscale` - Конвертация в один канал
3. `denoise` - Удаление шума перед другими операциями
4. `deskew` - Коррекция поворота
5. `clahe` или `contrast` - Улучшение контраста
6. `binarize` - Финальная бинаризация

Пример для низкокачественных сканов:
```bash
curl -X POST "http://localhost:8000/image?preprocess=upscale,grayscale,denoise,deskew,clahe,binarize&lang=rus" \
  -F "file=@scan.jpg"
```

### Обработка ошибок

| Код ответа | Значение | Причина |
|---|---|---|
| 400 | Неверный запрос | Неподдерживаемый формат или неверные параметры |
| 500 | Внутренняя ошибка | Ошибка обработки (проверьте логи) |
| 504 | Таймаут шлюза | Обработка OCR превысила таймаут |

### Поддерживаемые форматы

- **PDF**: .pdf (с опциональной защитой паролем)
- **Изображения**: .jpg, .jpeg, .png, .bmp, .gif, .tiff

---

## License

MIT License - see [LICENSE](LICENSE) for details.
