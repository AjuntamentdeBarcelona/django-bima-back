
from django.contrib import admin
from .models import MyChunkedUpload, PhotoFilter


@admin.register(MyChunkedUpload)
class MyChunkedUploadAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'filename',
        'status',
        'completed_on',
    )


@admin.register(PhotoFilter)
class PhotoFilterAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'username',
        'name'
    )
    search_fields = ('username', )
