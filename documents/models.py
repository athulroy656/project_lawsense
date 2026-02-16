from django.db import models
from django.contrib.auth.models import User

class Document(models.Model):
    DOCUMENT_TYPES = [
        ("NDA_MUTUAL", "NDA (Mutual)"),
        ("NDA_ONEWAY", "NDA (One-way)"),
        ("SERVICE_AGREEMENT", "Service Agreement"),
        ("PRIVACY_POLICY", "Privacy Policy"),
        ("TERMS_CONDITIONS", "Terms & Conditions"),
        ("EMPLOYMENT_AGREEMENT", "Employment Agreement"),
        ("OTHER", "Other/Unknown"),
    ]

    INPUT_METHODS = [
        ("FILE", "File Upload"),
        ("TEXT", "Pasted Text"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)

    title = models.CharField(max_length=255)
    file = models.FileField(upload_to='documents/', null=True, blank=True)
    extracted_text = models.TextField(blank=True)
    document_type = models.CharField(
        max_length=30,
        choices=DOCUMENT_TYPES,
        default="OTHER"
    )
    detected_type_confidence = models.FloatField(default=0.0)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    processed = models.BooleanField(default=False)
    input_method = models.CharField(
        max_length=10,
        choices=INPUT_METHODS,
        default="FILE"
    )
    
    # Report caching fields
    report_cache = models.JSONField(null=True, blank=True)
    report_cached_at = models.DateTimeField(null=True, blank=True)
    report_cache_key = models.CharField(max_length=64, null=True, blank=True)
    
    # Plain-language summary caching fields
    summary_text = models.TextField(null=True, blank=True)
    summary_generated_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.title

    def get_document_type_display(self):
        return dict(self.DOCUMENT_TYPES).get(self.document_type, "Unknown")

class Clause(models.Model):
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name="clauses"
    )
    text = models.TextField()
    label = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.label} clause"


