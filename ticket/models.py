from django.db import models

from order.models import Order
from utils.basemodel import BaseModel


class Ticket(BaseModel):
    name = models.CharField(max_length=255)
    token = models.CharField(max_length=255, unique=True)
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="tickets",
        db_index=True,
    )

    class Meta:
        db_table = "ticket"
        indexes = [
            models.Index(fields=["token"]),
            models.Index(fields=["order_id"]),
            models.Index(fields=["created_at"]),
        ]
