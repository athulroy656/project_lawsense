from django.contrib import admin
from django.contrib import admin
from .models import Document
from .models import Document, Clause


# Register your models here.
@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'document_type', 'uploaded_at', 'processed')
    list_filter = ('document_type', 'processed')
    search_fields = ('title',)


@admin.register(Clause)
class ClauseAdmin(admin.ModelAdmin):
    list_display = ('id', 'label', 'document')
    list_filter = ('label',)
    search_fields = ('text',)