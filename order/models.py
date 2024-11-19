from django.db import models
from user.models import BaseModel, User


class Order(BaseModel):
    name = models.CharField(max_length=255)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="orders",
        db_index=True,
    )

    class Meta:
        db_table = "order"
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["user_id"]),
        ]
