from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.models import User
from documents.models import Document, Clause
from django.utils import timezone
from datetime import timedelta, datetime
import logging
from django.db.models import Avg, Count


logger = logging.getLogger(__name__)


def is_admin_user(user):
    """Check if user is admin (staff or superuser)"""
    return user and user.is_authenticated and (user.is_staff or user.is_superuser)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_me(request):
    """
    Check if current user is admin.
    Returns: {is_admin: true/false, username: str}
    """
    user = request.user
    return Response({
        "is_admin": is_admin_user(user),
        "username": user.username,
        "is_staff": user.is_staff,
        "is_superuser": user.is_superuser
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_overview(request):
    """
    GET /api/admin/overview
    Returns aggregated metrics including trends, risk, and usage.
    """
    if not is_admin_user(request.user):
        return Response({"error": "Admin access required"}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        now = timezone.now()
        seven_days_ago = now - timedelta(days=7)
        
        # 1. Basic counts
        total_users = User.objects.count()
        total_documents = Document.objects.count()
        
        # 2. Trends (Last 7 Days vs Previous 7 Days)
        documents_last_7_days = Document.objects.filter(uploaded_at__gte=seven_days_ago).count()
        
        previous_7_days_start = seven_days_ago - timedelta(days=7)
        documents_prev_7_days = Document.objects.filter(
            uploaded_at__gte=previous_7_days_start, 
            uploaded_at__lt=seven_days_ago
        ).count()
        
        users_last_7_days = User.objects.filter(date_joined__gte=seven_days_ago).count()
        
        daily_trends = []
        for i in range(7):
            d = (now - timedelta(days=i)).date()
            count = Document.objects.filter(uploaded_at__date=d).count()
            daily_trends.append({"date": d.strftime("%Y-%m-%d"), "count": count})
        daily_trends.reverse()

        # 3. Usage Insights
        guest_uploads = Document.objects.filter(user__isnull=True).count()
        registered_uploads = Document.objects.filter(user__isnull=False).count()

        # 4. Risk Overview & Processing Metrics
        exposure_counts = {"Low": 0, "Moderate": 0, "Elevated": 0, "High": 0}
        total_processing_seconds = 0
        processed_count_with_time = 0
        
        # Iterate over recent processed docs (limit 500 for performance)
        processed_docs = Document.objects.filter(processed=True).select_related('user').order_by('-uploaded_at')[:500]
        
        for doc in processed_docs:
            # Risk
            if doc.report_cache and isinstance(doc.report_cache, dict):
                level = doc.report_cache.get("exposure_level")
                if level in exposure_counts:
                    exposure_counts[level] += 1
            
            # Processing time
            if doc.summary_generated_at and doc.uploaded_at:
                delta = (doc.summary_generated_at - doc.uploaded_at).total_seconds()
                if 0 < delta < 3600:
                    total_processing_seconds += delta
                    processed_count_with_time += 1
        
        avg_processing_time = round(total_processing_seconds / processed_count_with_time, 1) if processed_count_with_time else 0
        
        # Failed count (Pending > 1 hour)
        failed_count = Document.objects.filter(processed=False, uploaded_at__lt=now - timedelta(hours=1)).count()

        return Response({
            "total_users": total_users,
            "total_documents": total_documents,
            "documents_last_7_days": documents_last_7_days,
            "documents_prev_7_days": documents_prev_7_days,
            "users_last_7_days": users_last_7_days,
            "daily_trends": daily_trends,
            "usage_insights": {
                "guest_uploads": guest_uploads,
                "registered_uploads": registered_uploads,
                "guest_pct": round(guest_uploads / total_documents * 100, 1) if total_documents else 0
            },
            "risk_overview": exposure_counts,
            "processing_metrics": {
                "avg_time_seconds": avg_processing_time,
                "failed_count": failed_count
            }
        })
    except Exception as e:
        logger.error(f"Error in admin_overview: {e}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_document_types(request):
    """
    GET /api/admin/document_types
    Returns document counts by type.
    """
    if not is_admin_user(request.user):
        return Response(
            {"error": "Admin access required"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        # Get counts for each document type
        type_counts = {}
        for type_code, type_name in Document.DOCUMENT_TYPES:
            count = Document.objects.filter(document_type=type_code).count()
            type_counts[type_code] = {
                "name": type_name,
                "count": count
            }
        
        return Response({
            "document_types": type_counts,
            "total": sum(item["count"] for item in type_counts.values())
        })
    except Exception as e:
        logger.error(f"Error in admin_document_types: {e}")
        return Response(
            {"error": "Failed to fetch document type metrics"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_system_health(request):
    """
    GET /api/admin/system_health
    Returns system health status.
    """
    if not is_admin_user(request.user):
        return Response(
            {"error": "Admin access required"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Check Ollama status
    ollama_status = "down"
    try:
        from documents.ollama_utils import OLLAMA_AVAILABLE
        ollama_status = "up" if OLLAMA_AVAILABLE else "down"
    except Exception as e:
        logger.warning(f"Could not check Ollama status: {e}")
        ollama_status = "unknown"
    
    # Check ChromaDB status
    chroma_status = "fail"
    try:
        from documents.vector_utils import get_chroma_client
        client = get_chroma_client()
        # Simple connectivity check
        client.heartbeat()
        chroma_status = "ok"
    except ImportError:
        logger.warning("ChromaDB module not found")
        chroma_status = "unknown"
    except Exception as e:
        logger.warning(f"ChromaDB connection failed: {e}")
        chroma_status = "down"
    
    # Error logging - we don't have an error log table yet
    recent_errors_count = 0  # TODO: Implement error logging table
    
    return Response({
        "ollama_status": ollama_status,
        "chroma_db_status": chroma_status,
        "recent_errors_count": recent_errors_count,
        "note": "Error logging not yet implemented"
    })



@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_recent_documents(request):
    """
    GET /api/admin/recent_documents
    Returns recent documents (metadata only, no text).
    """
    if not is_admin_user(request.user):
        return Response(
            {"error": "Admin access required"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        # Get last 50 documents
        documents = Document.objects.order_by('-uploaded_at')[:50]
        
        doc_list = []
        for doc in documents:
            # Determine file extension/type
            file_type = "Text"
            if doc.input_method == "FILE" and doc.file:
                try:
                    ext = doc.file.name.split('.')[-1].upper()
                    file_type = ext if len(ext) < 6 else "File"
                except:
                    file_type = "File"
            elif doc.input_method == "FILE":
                file_type = "File"

            doc_list.append({
                "id": doc.id,
                "title": doc.title,
                "document_type": doc.document_type,
                "document_type_display": doc.get_document_type_display(),
                "input_method": doc.input_method,
                "file_type": file_type,
                "uploaded_at": doc.uploaded_at,
                "processed": doc.processed,
                "user_id": doc.user_id if doc.user else None,
                "owner_type": "Registered" if doc.user else "Guest",
                # Privacy: NO raw text, NO user email
            })
        
        return Response({
            "documents": doc_list,
            "count": len(doc_list)
        })
    except Exception as e:
        logger.error(f"Error in admin_recent_documents: {e}")
        return Response(
            {"error": "Failed to fetch recent documents"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def admin_delete_document(request, pk):
    if not is_admin_user(request.user):
        return Response({"error": "Admin access required"}, status=status.HTTP_403_FORBIDDEN)
    try:
        doc = Document.objects.get(pk=pk)
        doc.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    except Document.DoesNotExist:
        return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def admin_rerun_analysis(request, pk):
    if not is_admin_user(request.user):
        return Response({"error": "Admin access required"}, status=status.HTTP_403_FORBIDDEN)
    try:
        from documents.risk_utils import build_document_report
        doc = Document.objects.get(pk=pk)
        doc.report_cache = None
        doc.save()
        build_document_report(doc)
        return Response({"status": "Analysis re-run successfully"})
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_users_list(request):
    """
    GET /api/admin/users/?page=1&page_size=25&search=
    Returns list of users with minimal metadata.
    """
    if not is_admin_user(request.user):
        return Response({"error": "Admin access required"}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 25))
        search = request.query_params.get('search', '')
        
        users_qs = User.objects.all().order_by('-date_joined')
        
        if search:
            users_qs = users_qs.filter(username__icontains=search)
            
        total = users_qs.count()
        
        # Pagination
        start = (page - 1) * page_size
        end = start + page_size
        users = users_qs[start:end]
        
        results = []
        for u in users:
            # Manual count for reliability
            doc_count = Document.objects.filter(user=u).count()
            
            results.append({
                "id": u.id,
                "username": u.username,
                "is_staff": u.is_staff,
                "is_superuser": u.is_superuser,
                "date_joined": u.date_joined,
                "last_login": u.last_login,
                "document_count": doc_count,
            })
            
        return Response({
            "results": results,
            "total": total,
            "page": page,
            "page_size": page_size
        })
    except Exception as e:
        logger.error(f"Error in admin_users_list: {e}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
