from django.shortcuts import render, get_object_or_404
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
import os
import logging

from .models import Document, Clause
from .serializers import DocumentSerializer, ClauseSerializer
from .risk_utils import risk_summary, build_document_report
from .utils import process_document, store_clauses
from .vector_utils import index_clauses, delete_document_from_index
from .document_type_detector import detect_document_type
from .ollama_utils import generate_executive_summary, explain_risk, suggest_improvements
from .question_suggestions import suggest_questions

logger = logging.getLogger(__name__)


def get_doc_or_404_safe(pk, user):
    """
    Retrieve a document if it belongs to the user OR if it is a guest document (user is None).
    """
    if user.is_authenticated:
        # User can see their own docs OR guest docs (optional decision, let's strictly say their own + guest ones if they created them? No, guest docs are effectively public to anyone with link for now)
        # For simplicity: If auth, look for user match. If not found, check if it's a guest doc? 
        # Actually, let's keep it simple: Access if doc.user == user OR doc.user is None
        doc = get_object_or_404(Document, pk=pk)
        if doc.user and doc.user != user:
             # If doc has a user and it's not the requestor -> 404/403
             # raising Http404 by using filtering logic is better
             raise get_object_or_404(Document, pk=pk, user=user) # This will fail
        return doc
    else:
        # Guest: can only see docs with user=None
        return get_object_or_404(Document, pk=pk, user__isnull=True)


@api_view(['POST'])
@permission_classes([AllowAny])
@parser_classes([MultiPartParser, FormParser])
def upload_document(request):
    file = request.FILES.get('file')
    pasted_text = request.data.get('pasted_text', '')
    title = request.data.get('title', '')
    user_selected_type = request.data.get('document_type', '')
    input_method = request.data.get('input_method', 'FILE').upper()  # Normalize to uppercase

    # Determine user
    user = request.user if request.user.is_authenticated else None

    # Debug logging
    logger.info("=== UPLOAD REQUEST ===")
    logger.info(f"User: {user}")
    logger.info(f"Input method: {input_method}")
    logger.info(f"File present: {file is not None}")
    logger.info(f"Pasted text length: {len(pasted_text) if pasted_text else 0}")
    logger.info(f"Title: {title}")
    logger.info(f"Document type: {user_selected_type}")
    logger.info("=======================")

    # Validation based on input method
    if input_method == 'TEXT':
        if not pasted_text or len(pasted_text.strip()) < 200:
            error_msg = f"Pasted text is too short or empty. Minimum 200 characters required. (Received: {len(pasted_text.strip()) if pasted_text else 0} characters)"
            logger.warning(f"VALIDATION ERROR: {error_msg}")
            return Response(
                {"detail": error_msg},
                status=status.HTTP_400_BAD_REQUEST
            )
        if len(pasted_text) > 25000:
            error_msg = "Pasted text exceeds maximum length of 25,000 characters."
            logger.warning(f"VALIDATION ERROR: {error_msg}")
            return Response(
                {"detail": error_msg},
                status=status.HTTP_400_BAD_REQUEST
            )
    elif input_method == 'FILE':
        if not file:
            error_msg = "File is required for file upload method."
            logger.warning(f"VALIDATION ERROR: {error_msg}")
            return Response(
                {"detail": error_msg},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate File Size (10MB)
        MAX_SIZE = 10 * 1024 * 1024
        if file.size > MAX_SIZE:
             error_msg = f"File too large. Maximum size is 10MB. (Uploaded: {file.size / (1024 * 1024):.2f}MB)"
             logger.warning(f"VALIDATION ERROR: {error_msg}")
             return Response(
                 {"detail": error_msg},
                 status=status.HTTP_400_BAD_REQUEST
             )

        # Validate File Type
        ALLOWED_EXTENSIONS = ['.pdf', '.docx']
        if not any(file.name.lower().endswith(ext) for ext in ALLOWED_EXTENSIONS):
             error_msg = f"Invalid file format. Allowed formats: {', '.join(ALLOWED_EXTENSIONS)}"
             logger.warning(f"VALIDATION ERROR: {error_msg}")
             return Response(
                 {"detail": error_msg},
                 status=status.HTTP_400_BAD_REQUEST
             )

    # Generate title if not provided
    if not title:
        if input_method == 'FILE' and file:
            title = file.name
        else:
            from django.utils import timezone
            title = f"Document {timezone.now().strftime('%Y%m%d_%H%M%S')}"

    # Start with user-selected type or default to OTHER
    initial_type = user_selected_type if user_selected_type else 'OTHER'
    
    # Create document
    doc = Document.objects.create(
        title=title,
        file=file if input_method == 'FILE' else None,
        document_type=initial_type,
        input_method=input_method,
        user=user  # Can be None
    )

    try:
        # For pasted text, directly set extracted_text
        if input_method == 'TEXT':
            doc.extracted_text = pasted_text
            doc.save()
            logger.info(f"Document {doc.id}: Pasted text set, length={len(pasted_text)}")
        
        # Process document (unified pipeline)
        logger.info(f"Document {doc.id}: Starting process_document()")
        process_document(doc)
        logger.info(f"Document {doc.id}: process_document() complete")
        
        # Only auto-detect if user didn't select a type
        if not user_selected_type:
            logger.info(f"Document {doc.id}: Auto-detecting document type...")
            detected_type, confidence, _ = detect_document_type(doc.extracted_text)
            doc.document_type = detected_type
            doc.detected_type_confidence = confidence
            logger.info(f"Document {doc.id}: Detected as {detected_type} with {confidence:.2f} confidence")
        else:
            # User selected type - set high confidence
            doc.document_type = user_selected_type
            doc.detected_type_confidence = 1.0
            logger.info(f"Document {doc.id}: User selected type {user_selected_type}")
        
        doc.save()
        
        # Store clauses - continue even if this has issues
        try:
            logger.info(f"Document {doc.id}: Storing clauses...")
            store_clauses(doc)
            clause_count = doc.clauses.count()
            logger.info(f"Document {doc.id}: Stored {clause_count} clauses")
        except Exception as clause_error:
            logger.error(f"Document {doc.id}: Clause storage error: {clause_error}")
        
        # Index clauses - continue even if this has issues
        try:
            logger.info(f"Document {doc.id}: Indexing clauses...")
            index_clauses(doc)
            logger.info(f"Document {doc.id}: Clauses indexed successfully")
        except Exception as index_error:
            logger.error(f"Document {doc.id}: Clause indexing error: {index_error}")
        
        # Mark as processed regardless of clause issues
        doc.processed = True
        doc.save()
        logger.info(f"Document {doc.id}: Marked as processed")
        
    except Exception as e:
        doc.processed = False
        doc.save()
        logger.error(f"Document processing failed: {str(e)}")
        return Response(
            {"detail": f"Failed to process document: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    serializer = DocumentSerializer(doc)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([AllowAny])
def document_clauses(request, document_id):
    # Ensure document exists and belongs to user OR is guest
    doc = get_doc_or_404_safe(document_id, request.user)
    clauses = Clause.objects.filter(document_id=doc.id)
    serializer = ClauseSerializer(clauses, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def list_documents(request):
    if not request.user.is_authenticated:
        return Response([]) # Guests have no list
    docs = Document.objects.filter(user=request.user).order_by('-uploaded_at')
    serializer = DocumentSerializer(docs, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def document_risk_summary(request, document_id):
    doc = get_doc_or_404_safe(document_id, request.user)

    summary = risk_summary(doc)
    return Response(summary)


@api_view(['GET'])
@permission_classes([AllowAny])
def document_report(request, document_id):
    doc = get_doc_or_404_safe(document_id, request.user)

    # Check for manual document type override
    doc_type_override = request.query_params.get('document_type_override', None)
    
    # Validate override if provided
    valid_types = [choice[0] for choice in doc._meta.get_field('document_type').choices]
    if doc_type_override and doc_type_override not in valid_types:
        doc_type_override = None  # Ignore invalid override
    
    # Build report with optional override
    report = build_document_report(doc, document_type_override=doc_type_override)
    
    # ENHANCEMENT: Add question suggestions
    report['suggested_questions'] = suggest_questions(doc)
    
    # Check if AI summary is requested (default: False for faster response)
    include_ai = request.query_params.get('ai_summary', 'false').lower() == 'true'
    
    if include_ai:
        try:
            # Generate AI executive summary with timeout protection
            from documents.ollama_utils import OLLAMA_AVAILABLE
            
            detailed = request.query_params.get('detailed', 'false').lower() == 'true'
            
            if OLLAMA_AVAILABLE:
                report['ai_summary'] = generate_executive_summary(doc, detailed=detailed)
                
                # Generate explanations for each risk flag
                risk_explanations = []
                risks = report.get('risk_summary', {}).get('risks', [])
                for risk in risks[:3]:  # Limit to 3 risks for performance
                    explanation = explain_risk(risk, doc.extracted_text[:500])
                    risk_explanations.append({
                        "risk": risk,
                        "explanation": explanation
                    })
                report['risk_explanations'] = risk_explanations
                
                # Generate improvement suggestions if there are risks
                if risks:
                    report['ai_suggestions'] = suggest_improvements(doc, risks)
                else:
                    report['ai_suggestions'] = None
            else:
                report['ai_summary'] = None
                report['risk_explanations'] = []
                report['ai_suggestions'] = None
                
        except Exception as e:
            # If AI fails, still return the basic report
            logger.error(f"AI generation error: {str(e)}")
            report['ai_summary'] = None
            report['risk_explanations'] = []
            report['ai_suggestions'] = None
    else:
        # AI features not requested - skip for faster response
        report['ai_summary'] = None
        report['risk_explanations'] = []
        report['ai_suggestions'] = None
    
    return Response(report)


@api_view(['DELETE'])
@permission_classes([AllowAny]) # Allow deleting guest docs if you know the ID? risky but functional for now.
def delete_document(request, document_id):
    doc = get_doc_or_404_safe(document_id, request.user)

    # Save file path before deleting the model (safe access)
    file_path = None
    if doc.file:
        try:
            file_path = doc.file.path
        except (ValueError, AttributeError):
            # File field exists but no actual file
            file_path = None

    # Remove from vector index
    delete_document_from_index(doc)

    # Delete the Document (will cascade to Clause because of on_delete=CASCADE)
    doc.delete()

    # Delete the file from the filesystem (optional but cleaner)
    if file_path and os.path.exists(file_path):
        try:
            os.remove(file_path)
        except OSError as e:
            logger.warning(f"Failed to delete file {file_path}: {e}")

    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['POST'])
@permission_classes([AllowAny])
def ask_question(request):
    question = request.data.get('question')
    document_id = request.data.get('document_id')  # REQUIRED for document-scoped Q&A

    if not question:
        return Response(
            {"error": "Please enter a question before submitting."},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if not document_id:
        return Response(
            {"error": "document_id is required for document-scoped Q&A."},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if len(question) > 1000:
        return Response(
            {"error": "Question is too long. Maximum 1000 characters allowed."},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Verify document exists and user has access
    try:
        doc = get_doc_or_404_safe(document_id, request.user)
    except:
        return Response(
            {"error": "Document not found or access denied."},
            status=status.HTTP_404_NOT_FOUND
        )

    from .qa_utils import answer_question as qa_answer
    
    # Pass document_id and user_id for scoped Q&A
    user_id = request.user.id if request.user.is_authenticated else None
    answer = qa_answer(question, document_id=document_id, user_id=user_id, document_type=doc.document_type)
    
    return Response({
        "question": question,
        "answer": answer,
        "document_id": document_id  # Echo back for confirmation
    })