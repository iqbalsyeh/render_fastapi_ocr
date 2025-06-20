from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
from pdf2image import convert_from_bytes
from PIL import Image
import pytesseract
import re

app = FastAPI()  # ⬅️ Ini HARUS ditulis sebelum route @app.post()

# Pola regex
pola_nomor = re.compile(r"Nomor[.:\s]*([\w/.-]+)", re.IGNORECASE)
pola_tanggal = re.compile(r"Tanggal[.:\s]*([\d]{1,2}[-/][A-Za-z]{3}[-/][\d]{4})", re.IGNORECASE)
pola_nominal = re.compile(r"(?:Total Pembayaran|Nilai SP2D)[\s:]*([\d.,]+)", re.IGNORECASE)
pola_dipa = re.compile(r"DIPA[-\s:]*(\S+)", re.IGNORECASE)
pola_sp2d = re.compile(r"(?:SP2D|Nomor SP2D)[\s:]*([\d]+)", re.IGNORECASE)

def extract_text_from_pdf(file_bytes):
    images = convert_from_bytes(file_bytes)
    full_text = ""
    for img in images:
        text = pytesseract.image_to_string(img)
        full_text += text + "\n"
    return full_text

def temukan(pattern, text):
    hasil = pattern.search(text)
    return hasil.group(1) if hasil else "Tidak ditemukan"

def deteksi_dokumen(text):
    hasil = []

    if "Surat Perintah Membayar" in text:
        hasil.append({
            "jenis": "Surat Perintah Membayar",
            "nomor": temukan(pola_nomor, text),
            "tanggal": temukan(pola_tanggal, text),
            "dipa": temukan(pola_dipa, text),
            "nominal": temukan(pola_nominal, text)
        })

    if "Surat Permintaan Pembayaran" in text:
        hasil.append({
            "jenis": "Surat Permintaan Pembayaran",
            "nomor": temukan(pola_nomor, text),
            "tanggal": temukan(pola_tanggal, text),
            "dipa": temukan(pola_dipa, text),
            "nominal": temukan(pola_nominal, text)
        })

    if "Surat Perintah Pencairan Dana" in text:
        hasil.append({
            "jenis": "Surat Perintah Pencairan Dana",
            "nomor": temukan(pola_sp2d, text),
            "tanggal": temukan(pola_tanggal, text),
            "nominal": temukan(pola_nominal, text)
        })

    return hasil

@app.post("/cek-pdf")
async def cek_pdf(file: UploadFile = File(...)):
    file_bytes = await file.read()
    text = extract_text_from_pdf(file_bytes)
    hasil_deteksi = deteksi_dokumen(text)

    hasil_utama = hasil_deteksi[0] if hasil_deteksi else {}

    return JSONResponse(content={
        "nama_file": file.filename,
        "jenis_dokumen": hasil_utama.get("jenis", ""),
        "tanggal": hasil_utama.get("tanggal", ""),
        "nomor": hasil_utama.get("nomor", ""),
        "nominal": hasil_utama.get("nominal", ""),
        "status_spm": "Ada" if any(d["jenis"] == "Surat Perintah Membayar" for d in hasil_deteksi) else "Tidak Ada",
        "status_sp2d": "Ada" if any(d["jenis"] == "Surat Perintah Pencairan Dana" for d in hasil_deteksi) else "Tidak Ada",
        "status_spp": "Ada" if any(d["jenis"] == "Surat Permintaan Pembayaran" for d in hasil_deteksi) else "Tidak Ada"
    })

@app.get("/")
def root():
    return {"message": "API aktif. Silakan akses /docs untuk Swagger UI"}
