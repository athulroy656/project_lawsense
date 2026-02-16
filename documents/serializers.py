from rest_framework import serializers
from .models import Document, Clause


class DocumentSerializer(serializers.ModelSerializer):
    document_type_display = serializers.SerializerMethodField()
    input_method_display = serializers.SerializerMethodField()
    
    class Meta:
        model = Document
        fields = [
            'id',
            'title',
            'uploaded_at',
            'processed',
            'document_type',
            'document_type_display',
            'detected_type_confidence',
            'file',
            'input_method',
            'input_method_display',
        ]
    
    def get_document_type_display(self, obj):
        return obj.get_document_type_display()
    
    def get_input_method_display(self, obj):
        return dict(obj.INPUT_METHODS).get(obj.input_method, "Unknown")


class ClauseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Clause
        fields = [
            'id',
            'label',
            'text',
            'document',
        ]
