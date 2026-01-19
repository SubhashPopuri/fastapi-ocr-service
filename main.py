from fastapi import FastAPI, File, UploadFile, HTTPException, Query
from fastapi.responses import JSONResponse
import pytesseract
import pdfplumber
from PIL import Image
import io
import logging
from typing import Optional, List, Tuple
import cv2
import numpy as np
from pdf2image import convert_from_bytes
from deskew import determine_skew

# Configure pytesseract to find tesseract binary
import os
os.environ['TESSERACT_CMD'] = '/usr/bin/tesseract'
pytesseract.pytesseract.pytesseract_cmd = '/usr/bin/tesseract'

app = FastAPI(title="OCR Service", description="Extract text from PDFs and images")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# =============================================================================
# Image Preprocessing Functions
# =============================================================================

def _to_grayscale(image: np.ndarray) -> np.ndarray:
    """Convert image to grayscale."""
    if len(image.shape) == 3:
        return cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    return image


def _enhance_contrast(image: np.ndarray) -> np.ndarray:
    """Apply histogram equalization to enhance contrast."""
    if len(image.shape) == 3:
        image = _to_grayscale(image)
    return cv2.equalizeHist(image)


def _apply_clahe(image: np.ndarray, clip_limit: float = 2.0, grid_size: int = 8) -> np.ndarray:
    """Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)."""
    if len(image.shape) == 3:
        image = _to_grayscale(image)
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(grid_size, grid_size))
    return clahe.apply(image)


def _denoise(image: np.ndarray, strength: int = 10) -> np.ndarray:
    """Apply Non-local Means Denoising."""
    if len(image.shape) == 3:
        return cv2.fastNlMeansDenoisingColored(image, None, strength, strength, 7, 21)
    return cv2.fastNlMeansDenoising(image, None, strength, 7, 21)


def _deskew(image: np.ndarray) -> np.ndarray:
    """Correct skew angle of the image."""
    grayscale = _to_grayscale(image) if len(image.shape) == 3 else image
    angle = determine_skew(grayscale)

    if angle is None or abs(angle) < 0.5:
        return image

    (h, w) = image.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)

    # Use white background for rotation
    border_value = 255 if len(image.shape) == 2 else (255, 255, 255)
    rotated = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC,
                             borderMode=cv2.BORDER_CONSTANT, borderValue=border_value)
    logger.info(f"Deskewed image by {angle:.2f} degrees")
    return rotated


def _binarize(image: np.ndarray, method: str = "otsu") -> np.ndarray:
    """Apply binarization (thresholding) to the image."""
    if len(image.shape) == 3:
        image = _to_grayscale(image)

    if method == "otsu":
        _, binary = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    elif method == "adaptive_mean":
        binary = cv2.adaptiveThreshold(image, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
                                       cv2.THRESH_BINARY, 11, 2)
    elif method == "adaptive_gaussian":
        binary = cv2.adaptiveThreshold(image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                       cv2.THRESH_BINARY, 11, 2)
    else:
        _, binary = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    return binary


def _upscale(image: np.ndarray, min_dimension: int = 1000) -> np.ndarray:
    """Upscale image if it's smaller than min_dimension."""
    h, w = image.shape[:2]
    min_side = min(h, w)

    if min_side >= min_dimension:
        return image

    scale = min_dimension / min_side
    new_w = int(w * scale)
    new_h = int(h * scale)

    upscaled = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
    logger.info(f"Upscaled image from {w}x{h} to {new_w}x{new_h}")
    return upscaled


def preprocess_image(
    pil_image: Image.Image,
    steps: List[str],
    clahe_clip: float = 2.0,
    clahe_grid: int = 8,
    denoise_strength: int = 10,
    binarize_method: str = "otsu",
    upscale_min: int = 1000
) -> Tuple[Image.Image, List[str]]:
    """
    Apply preprocessing steps to an image.

    Args:
        pil_image: Input PIL Image
        steps: List of preprocessing steps to apply
        clahe_clip: CLAHE clip limit
        clahe_grid: CLAHE grid size
        denoise_strength: Denoising strength
        binarize_method: Binarization method (otsu, adaptive_mean, adaptive_gaussian)
        upscale_min: Minimum dimension for upscaling

    Returns:
        Tuple of (processed PIL Image, list of applied steps)
    """
    if not steps:
        return pil_image, []

    # Convert PIL to numpy array (RGB)
    image = np.array(pil_image)
    applied_steps = []

    step_functions = {
        "upscale": lambda img: _upscale(img, upscale_min),
        "grayscale": _to_grayscale,
        "contrast": _enhance_contrast,
        "clahe": lambda img: _apply_clahe(img, clahe_clip, clahe_grid),
        "denoise": lambda img: _denoise(img, denoise_strength),
        "deskew": _deskew,
        "binarize": lambda img: _binarize(img, binarize_method),
    }

    for step in steps:
        step = step.strip().lower()
        if step in step_functions:
            image = step_functions[step](image)
            applied_steps.append(step)
            logger.info(f"Applied preprocessing step: {step}")
        else:
            logger.warning(f"Unknown preprocessing step: {step}")

    # Convert back to PIL Image
    if len(image.shape) == 2:
        # Grayscale
        result = Image.fromarray(image, mode='L')
    else:
        result = Image.fromarray(image)

    return result, applied_steps


# =============================================================================
# PDF OCR Functions
# =============================================================================

def _extract_with_pdfplumber(
    pdf_content: bytes,
    password: Optional[str],
    detect_vertical: bool
) -> Tuple[List[dict], int]:
    """Extract text from PDF using pdfplumber."""
    pdf_file = io.BytesIO(pdf_content)
    results = []

    laparams = {"detect_vertical": True} if detect_vertical else None

    with pdfplumber.open(pdf_file, password=password, laparams=laparams) as pdf:
        page_count = len(pdf.pages)
        for page_num, page in enumerate(pdf.pages, 1):
            try:
                page_text = page.extract_text() or ""
            except Exception as page_error:
                logger.warning(f"Error extracting page {page_num}: {str(page_error)}")
                page_text = ""

            results.append({
                "page": page_num,
                "text": page_text.strip(),
                "text_length": len(page_text),
                "method": "pdfplumber"
            })

    return results, page_count


def _pdf_to_images(pdf_content: bytes, dpi: int = 300, password: Optional[str] = None) -> List[Image.Image]:
    """Convert PDF pages to images using pdf2image (poppler)."""
    kwargs = {"dpi": dpi, "fmt": "RGB"}
    if password:
        kwargs["userpw"] = password

    images = convert_from_bytes(pdf_content, **kwargs)
    return images


def _extract_with_ocr(
    pdf_content: bytes,
    password: Optional[str],
    language: str,
    psm: int,
    dpi: int,
    preprocess_steps: Optional[List[str]] = None,
    preprocess_config: Optional[dict] = None
) -> Tuple[List[dict], int]:
    """Extract text from PDF using OCR (render to images first)."""
    images = _pdf_to_images(pdf_content, dpi, password)
    results = []

    config = f"--oem 3 --psm {psm}"
    preprocess_config = preprocess_config or {}

    for page_num, image in enumerate(images, 1):
        try:
            # Apply preprocessing if specified
            if preprocess_steps:
                image, _ = preprocess_image(image, preprocess_steps, **preprocess_config)

            # Convert to RGB if needed for Tesseract
            if image.mode != 'RGB' and image.mode != 'L':
                image = image.convert('RGB')

            # Get OCR data with confidence
            ocr_data = pytesseract.image_to_data(image, lang=language, config=config, output_type=pytesseract.Output.DICT)

            # Extract text
            text = pytesseract.image_to_string(image, lang=language, config=config)

            # Calculate average confidence (excluding -1 values which indicate no text)
            confidences = [c for c in ocr_data['conf'] if c != -1]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

            results.append({
                "page": page_num,
                "text": text.strip(),
                "text_length": len(text),
                "method": "ocr",
                "ocr_confidence": round(avg_confidence, 2)
            })

            logger.info(f"OCR page {page_num}: {len(text)} chars, confidence: {avg_confidence:.2f}%")

        except Exception as e:
            logger.error(f"OCR error on page {page_num}: {str(e)}")
            results.append({
                "page": page_num,
                "text": f"[OCR Error: {str(e)}]",
                "text_length": 0,
                "method": "ocr",
                "ocr_confidence": 0.0
            })

    return results, len(images)


def _needs_ocr_fallback(results: List[dict], min_chars_threshold: int = 50) -> bool:
    """Determine if OCR fallback is needed based on extraction results."""
    if not results:
        return True

    total_chars = sum(r.get("text_length", 0) for r in results)
    avg_chars = total_chars / len(results)
    empty_pages = sum(1 for r in results if r.get("text_length", 0) < 10)
    empty_ratio = empty_pages / len(results)

    # OCR fallback conditions
    if total_chars < 100:
        logger.info(f"OCR fallback: total chars ({total_chars}) < 100")
        return True
    if avg_chars < min_chars_threshold:
        logger.info(f"OCR fallback: avg chars/page ({avg_chars:.1f}) < {min_chars_threshold}")
        return True
    if empty_ratio > 0.5:
        logger.info(f"OCR fallback: {empty_ratio*100:.0f}% pages are empty")
        return True

    return False


# =============================================================================
# API Endpoints
# =============================================================================

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "ok", "message": "OCR Service is running"}


@app.post("/pdf")
async def extract_from_pdf(
    file: UploadFile = File(..., description="PDF file to extract text from"),
    password: Optional[str] = Query(None, description="Password for encrypted PDFs"),
    detect_vertical: bool = Query(False, description="Enable vertical text detection via laparams"),
    force_ocr: bool = Query(False, description="Force OCR extraction instead of pdfplumber"),
    ocr_language: str = Query("eng", description="OCR language code (e.g., 'eng', 'rus', 'eng+rus')"),
    ocr_psm: int = Query(3, description="OCR Page Segmentation Mode (0-13)"),
    ocr_dpi: int = Query(300, description="DPI for rendering PDF pages to images for OCR"),
    min_chars_threshold: int = Query(50, description="Minimum chars/page threshold for OCR fallback"),
    ocr_preprocess: Optional[str] = Query(None, description="Preprocessing steps for OCR (comma-separated: grayscale,denoise,binarize)")
):
    """
    Extract text from a PDF file with hybrid extraction.

    Uses pdfplumber for text-based PDFs, automatically falls back to OCR for scanned documents.

    Args:
        file: PDF file to extract text from
        password: Optional password for encrypted PDFs
        detect_vertical: Enable layout analysis for vertical text detection
        force_ocr: Force OCR extraction instead of pdfplumber
        ocr_language: OCR language code
        ocr_psm: OCR Page Segmentation Mode
        ocr_dpi: DPI for PDF to image conversion
        min_chars_threshold: Chars/page threshold for OCR fallback
        ocr_preprocess: Preprocessing steps for OCR pages

    Returns:
        JSON with extracted text and metadata
    """
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")

    if not 0 <= ocr_psm <= 13:
        raise HTTPException(status_code=400, detail="ocr_psm must be between 0-13")

    try:
        content = await file.read()

        # Parse preprocessing steps
        preprocess_steps = None
        if ocr_preprocess:
            preprocess_steps = [s.strip() for s in ocr_preprocess.split(',') if s.strip()]

        extraction_method = "ocr" if force_ocr else "pdfplumber"
        ocr_pages = 0
        pdfplumber_pages = 0

        if force_ocr:
            # Force OCR extraction
            logger.info(f"Force OCR mode for {file.filename}")
            results, page_count = _extract_with_ocr(
                content, password, ocr_language, ocr_psm, ocr_dpi, preprocess_steps
            )
            ocr_pages = page_count
        else:
            # Try pdfplumber first
            results, page_count = _extract_with_pdfplumber(content, password, detect_vertical)
            pdfplumber_pages = page_count

            # Check if OCR fallback is needed
            if _needs_ocr_fallback(results, min_chars_threshold):
                logger.info(f"Falling back to OCR for {file.filename}")
                extraction_method = "ocr"
                results, page_count = _extract_with_ocr(
                    content, password, ocr_language, ocr_psm, ocr_dpi, preprocess_steps
                )
                ocr_pages = page_count
                pdfplumber_pages = 0

        logger.info(f"Successfully extracted text from PDF: {file.filename} ({page_count} pages, method: {extraction_method})")

        return JSONResponse({
            "status": "success",
            "type": "pdf",
            "filename": file.filename,
            "pages": page_count,
            "extraction_method": extraction_method,
            "ocr_pages": ocr_pages,
            "pdfplumber_pages": pdfplumber_pages,
            "results": results
        })

    except Exception as e:
        logger.error(f"Error processing PDF: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")
    finally:
        await file.close()


@app.post("/image")
async def extract_from_image(
    file: UploadFile = File(..., description="Image file to extract text from (jpg, png, bmp, gif, tiff)"),
    lang: str = Query("eng", description="Tesseract language code (e.g., 'eng', 'fra', 'eng+fra' for multiple)"),
    psm: str = Query("3", description="Page Segmentation Mode(s). Single: '3' or multiple: '3,6,11' (comma-separated)"),
    oem: int = Query(3, description="OCR Engine Mode (0=legacy, 1=neural, 2=both, 3=auto)"),
    timeout: int = Query(0, description="Timeout in seconds per PSM (0=no timeout)"),
    preprocess: Optional[str] = Query(None, description="Preprocessing steps (comma-separated: upscale,grayscale,denoise,clahe,deskew,binarize)"),
    clahe_clip: float = Query(2.0, description="CLAHE clip limit"),
    clahe_grid: int = Query(8, description="CLAHE grid size"),
    denoise_strength: int = Query(10, description="Denoising strength (1-30)"),
    binarize_method: str = Query("otsu", description="Binarization method: otsu, adaptive_mean, adaptive_gaussian"),
    upscale_min: int = Query(1000, description="Minimum dimension for upscaling")
):
    """
    Extract text from an image file using OCR (Tesseract) with optional preprocessing.

    Supports multiple PSM modes for comparison and image preprocessing pipeline.

    Args:
        file: Image file to extract text from
        lang: Tesseract language code(s)
        psm: Page Segmentation Mode(s) - single or comma-separated
        oem: OCR Engine Mode (0-3)
        timeout: Timeout in seconds per PSM processing
        preprocess: Preprocessing steps (comma-separated)
        clahe_clip: CLAHE clip limit
        clahe_grid: CLAHE grid size
        denoise_strength: Denoising strength
        binarize_method: Binarization method
        upscale_min: Minimum dimension for upscaling

    Returns:
        JSON with extracted text results for each PSM mode
    """
    allowed_formats = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff'}
    file_ext = f".{file.filename.split('.')[-1].lower()}" if '.' in file.filename else ""

    if file_ext not in allowed_formats:
        raise HTTPException(status_code=400, detail=f"File must be an image format. Allowed: {', '.join(allowed_formats)}")

    # Parse PSM values
    try:
        psm_list = [int(p.strip()) for p in psm.split(',')]
        if not all(0 <= p <= 13 for p in psm_list):
            raise ValueError("PSM must be between 0-13")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid PSM value(s): {str(e)}")

    # Parse preprocessing steps
    preprocess_steps = []
    if preprocess:
        preprocess_steps = [s.strip() for s in preprocess.split(',') if s.strip()]

    try:
        content = await file.read()

        # Open image
        image = Image.open(io.BytesIO(content))
        original_format = image.format
        original_size = image.size

        # Convert to RGB if needed
        if image.mode != 'RGB':
            image = image.convert('RGB')
            logger.info(f"Converted image from {image.mode} to RGB for OCR")

        # Apply preprocessing if specified
        applied_preprocessing = []
        if preprocess_steps:
            image, applied_preprocessing = preprocess_image(
                image,
                preprocess_steps,
                clahe_clip=clahe_clip,
                clahe_grid=clahe_grid,
                denoise_strength=denoise_strength,
                binarize_method=binarize_method,
                upscale_min=upscale_min
            )
            logger.info(f"Applied preprocessing: {applied_preprocessing}")

        # Process image with each PSM mode
        results = []
        for current_psm in psm_list:
            try:
                config = f"--oem {oem} --psm {current_psm}"

                try:
                    extracted_text = pytesseract.image_to_string(
                        image,
                        lang=lang,
                        config=config,
                        timeout=timeout if timeout > 0 else None
                    )
                except RuntimeError as timeout_error:
                    logger.error(f"OCR timeout for PSM {current_psm}: {str(timeout_error)}")
                    extracted_text = f"[Timeout - exceeded {timeout}s limit]"

                results.append({
                    "psm": current_psm,
                    "text": extracted_text.strip(),
                    "text_length": len(extracted_text)
                })

                logger.info(f"PSM {current_psm}: Extracted {len(extracted_text)} chars from {file.filename}")

            except Exception as psm_error:
                logger.error(f"Error processing PSM {current_psm}: {str(psm_error)}")
                results.append({
                    "psm": current_psm,
                    "text": f"[Error: {str(psm_error)}]",
                    "text_length": 0
                })

        logger.info(f"Successfully processed image: {file.filename} (lang={lang}, psm_modes={psm_list}, oem={oem})")

        response_data = {
            "status": "success",
            "type": "image",
            "filename": file.filename,
            "image_size": original_size,
            "image_format": original_format,
            "image_mode": image.mode,
            "ocr_config": {
                "language": lang,
                "psm_modes": psm_list,
                "oem": oem,
                "timeout": timeout
            },
            "results": results,
            "total_psm_modes": len(psm_list)
        }

        # Add preprocessing info if applied
        if applied_preprocessing:
            response_data["preprocessing"] = applied_preprocessing

        return JSONResponse(response_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing image: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing image: {str(e)}")
    finally:
        await file.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
