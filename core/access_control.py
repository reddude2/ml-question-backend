"""
Access Control Logic
Test type and tier validation
"""

from fastapi import HTTPException, status

SUBJECT_ACCESS_MATRIX = {
    "polri": ["bahasa_inggris", "numerik", "pengetahuan_umum", "wawasan_kebangsaan"],
    "cpns": ["tiu", "wawasan_kebangsaan", "tkp"],
    "campur": ["bahasa_inggris", "numerik", "pengetahuan_umum", "wawasan_kebangsaan", "tiu", "tkp"]
}

def validate_test_type(test_type: str) -> bool:
    """Validate if test_type is valid"""
    valid_types = ["polri", "cpns", "campur"]
    if test_type not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Test type '{test_type}' tidak valid"
        )
    return True

def validate_subject_access(user_test_type: str, subject: str, test_category: str = None) -> bool:
    """Validate if user has access to a specific subject"""
    allowed_subjects = SUBJECT_ACCESS_MATRIX.get(user_test_type, [])
    
    if subject not in allowed_subjects:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User dengan test_type '{user_test_type}' tidak memiliki akses ke subject '{subject}'"
        )
    
    if test_category:
        if user_test_type == "polri" and test_category == "cpns":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User POLRI tidak dapat mengakses soal CPNS"
            )
        if user_test_type == "cpns" and test_category == "polri":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User CPNS tidak dapat mengakses soal POLRI"
            )
    
    return True

def validate_test_category_access(user_test_type: str, test_category: str) -> bool:
    """Validate if user can access a test category"""
    if user_test_type == "campur":
        return True
    
    if user_test_type == "polri" and test_category != "polri":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User POLRI hanya dapat mengakses soal POLRI"
        )
    
    if user_test_type == "cpns" and test_category != "cpns":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User CPNS hanya dapat mengakses soal CPNS"
        )
    
    return True

def get_allowed_subjects(user_test_type: str) -> list:
    """Get list of subjects user can access"""
    return SUBJECT_ACCESS_MATRIX.get(user_test_type, [])

def get_allowed_test_categories(user_test_type: str) -> list:
    """Get list of test categories user can access"""
    if user_test_type == "campur":
        return ["polri", "cpns"]
    return [user_test_type]