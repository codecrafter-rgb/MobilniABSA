# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

from dataclasses import dataclass
from datetime import datetime


@dataclass
class CommentItem:
    url: str
    brand: str | None
    phone: str
    author: str | None
    date: datetime | None
    comment: str
