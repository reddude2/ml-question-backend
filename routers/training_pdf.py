"""
Training PDF Router (FINAL VERSION - Compatible with existing project)
Endpoint untuk upload dan view PDF program latihan harian
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import FileResponse
from typing import Optional
import os
from datetime import datetime
from supabase import create_client, Client
from middleware.auth import get_current_user
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Initialize Supabase client
_supabase_client = None

def get_supabase_client() -> Client:
    """Get or create Supabase client"""
    global _supabase_client
    if _supabase_client is None:
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise ValueError("Supabase credentials not configured")
        _supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _supabase_client

router = APIRouter(
    prefix="/api/training-pdf",
    tags=["Training PDF"],
    responses={404: {"description": "Not found"}}
)

# Directory untuk simpan PDF
UPLOAD_DIR = "uploads/training_pdfs"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Allowed file types
ALLOWED_EXTENSIONS = {".pdf"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

def validate_pdf_file(file: UploadFile):
    """Validasi file PDF"""
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, "Hanya file PDF yang diperbolehkan")
    
    if file.content_type != "application/pdf":
        raise HTTPException(400, "Tipe file harus PDF")
    
    return True

def check_admin_or_teacher(current_user: dict):
    """Check apakah user adalah admin atau pengajar"""
    user_role = current_user.get("role", "").lower()
    
    admin_keywords = ["admin", "administrator"]
    teacher_keywords = ["pengajar", "teacher", "guru", "instructor", "tutor"]
    
    is_admin = any(keyword in user_role for keyword in admin_keywords)
    is_teacher = any(keyword in user_role for keyword in teacher_keywords)
    
    return is_admin or is_teacher

@router.post("/upload")
async def upload_training_pdf(
    file: UploadFile = File(...),
    title: str = Form(...),
    description: Optional[str] = Form(""),
    current_user: dict = Depends(get_current_user)
):
    """
    Upload PDF Program Latihan (Admin/Pengajar Only)
    """
    
    # Check role
    if not check_admin_or_teacher(current_user):
        raise HTTPException(
            status_code=403,
            detail=f"Hanya admin atau pengajar yang dapat upload PDF. Role Anda: {current_user.get('role', 'unknown')}"
        )
    
    # Validate file
    validate_pdf_file(file)
    
    # Generate unique filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    original_filename = file.filename.replace(" ", "_")
    safe_filename = f"{timestamp}_{original_filename}"
    file_path = os.path.join(UPLOAD_DIR, safe_filename)
    
    # Save file
    try:
        contents = await file.read()
        
        if len(contents) > MAX_FILE_SIZE:
            raise HTTPException(400, f"Ukuran file maksimal {MAX_FILE_SIZE // (1024*1024)}MB")
        
        with open(file_path, "wb") as f:
            f.write(contents)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Gagal menyimpan file: {str(e)}")
    
    # Save metadata to database
    try:
        supabase = get_supabase_client()
        
        pdf_data = {
            "title": title,
            "description": description,
            "filename": safe_filename,
            "original_filename": file.filename,
            "file_size": len(contents),
            "uploaded_by": current_user.get("id"),
            "uploader_username": current_user.get("username", "unknown"),
            "uploader_role": current_user.get("role", "unknown"),
            "created_at": datetime.now().isoformat(),
            "is_active": True
        }
        
        result = supabase.table("training_pdfs").insert(pdf_data).execute()
        
        if not result.data:
            raise Exception("Gagal menyimpan ke database")
        
        inserted_data = result.data[0]
        inserted_data["pdf_url"] = f"/api/training-pdf/download/{safe_filename}"
        
        return {
            "status": "success",
            "message": "PDF berhasil diupload",
            "data": inserted_data
        }
    
    except HTTPException:
        raise
    except Exception as e:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass
        raise HTTPException(500, f"Gagal menyimpan metadata: {str(e)}")

@router.get("/latest")
async def get_latest_pdf(current_user: dict = Depends(get_current_user)):
    """Get Latest PDF Program Latihan (Semua User)"""
    
    try:
        supabase = get_supabase_client()
        
        result = supabase.table("training_pdfs") \
            .select("*") \
            .eq("is_active", True) \
            .order("created_at", desc=True) \
            .limit(1) \
            .execute()
        
        if not result.data or len(result.data) == 0:
            raise HTTPException(404, "Belum ada PDF tersedia")
        
        pdf_data = result.data[0]
        pdf_data["pdf_url"] = f"/api/training-pdf/download/{pdf_data['filename']}"
        
        return {
            "status": "success",
            "data": pdf_data
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Gagal mengambil data PDF: {str(e)}")

@router.get("/list")
async def list_pdfs(
    limit: int = 10,
    current_user: dict = Depends(get_current_user)
):
    """List All PDFs"""
    
    try:
        supabase = get_supabase_client()
        
        result = supabase.table("training_pdfs") \
            .select("*") \
            .eq("is_active", True) \
            .order("created_at", desc=True) \
            .limit(limit) \
            .execute()
        
        for pdf in result.data:
            pdf["pdf_url"] = f"/api/training-pdf/download/{pdf['filename']}"
        
        return {
            "status": "success",
            "count": len(result.data),
            "data": result.data
        }
    
    except Exception as e:
        raise HTTPException(500, f"Gagal mengambil daftar PDF: {str(e)}")

@router.get("/download/{filename}")
async def download_pdf(
    filename: str,
    current_user: dict = Depends(get_current_user)
):
    """Download/View PDF File (Semua User)"""
    
    file_path = os.path.join(UPLOAD_DIR, filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(404, "File tidak ditemukan")
    
    return FileResponse(
        file_path,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"inline; filename={filename}",
            "Cache-Control": "no-cache"
        }
    )

@router.delete("/{pdf_id}")
async def delete_pdf(
    pdf_id: int,
    current_user: dict = Depends(get_current_user)
):
    """Delete PDF (Admin/Pengajar Only)"""
    
    if not check_admin_or_teacher(current_user):
        raise HTTPException(403, "Hanya admin atau pengajar yang dapat menghapus PDF")
    
    try:
        supabase = get_supabase_client()
        
        result = supabase.table("training_pdfs") \
            .update({"is_active": False, "updated_at": datetime.now().isoformat()}) \
            .eq("id", pdf_id) \
            .execute()
        
        if not result.data:
            raise HTTPException(404, "PDF tidak ditemukan")
        
        return {
            "status": "success",
            "message": "PDF berhasil dihapus"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Gagal menghapus PDF: {str(e)}")

@router.get("/stats")
async def get_pdf_stats(current_user: dict = Depends(get_current_user)):
    """Get PDF Statistics (Admin/Pengajar Only)"""
    
    if not check_admin_or_teacher(current_user):
        raise HTTPException(403, "Akses ditolak")
    
    try:
        supabase = get_supabase_client()
        
        all_pdfs = supabase.table("training_pdfs").select("id", count="exact").execute()
        active_pdfs = supabase.table("training_pdfs").select("id", count="exact").eq("is_active", True).execute()
        all_active = supabase.table("training_pdfs").select("file_size").eq("is_active", True).execute()
        
        total_size = sum([pdf.get("file_size", 0) for pdf in all_active.data])
        
        recent = supabase.table("training_pdfs") \
            .select("title, created_at, uploader_username") \
            .eq("is_active", True) \
            .order("created_at", desc=True) \
            .limit(5) \
            .execute()
        
        return {
            "status": "success",
            "data": {
                "total_pdfs": all_pdfs.count if hasattr(all_pdfs, 'count') else len(all_pdfs.data),
                "active_pdfs": active_pdfs.count if hasattr(active_pdfs, 'count') else len(active_pdfs.data),
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "storage_used": f"{round(total_size / (1024 * 1024), 2)} MB",
                "recent_uploads": recent.data
            }
        }
    
    except Exception as e:
        raise HTTPException(500, f"Gagal mengambil statistik: {str(e)}")

@router.get("/health")
async def pdf_health_check():
    """Health check untuk PDF system (No auth required)"""
    return {
        "status": "healthy",
        "service": "training-pdf",
        "upload_dir": UPLOAD_DIR,
        "upload_dir_exists": os.path.exists(UPLOAD_DIR),
        "max_file_size_mb": MAX_FILE_SIZE // (1024 * 1024),
        "allowed_extensions": list(ALLOWED_EXTENSIONS)
    }
