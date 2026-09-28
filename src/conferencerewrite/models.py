import uuid

from django.db import models


class RewriteUsage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    model_id = models.CharField(max_length=64)
    input_tokens = models.PositiveIntegerField()
    output_tokens = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.model_id} {self.created_at}"
