from datetime import datetime

import cyrtranslit
import scrapy
from scrapy.http import TextResponse

from scraper.items import CommentItem


class MobilniSvet(scrapy.Spider):
	name = "mobilnisvet"
	allowed_domains = ["mobilnisvet.com"]
	start_urls = [
		"https://mobilnisvet.com/mobilni-proizvodjac/Apple/22/2",
		"https://mobilnisvet.com/mobilni-proizvodjac/Honor/83/2",
		"https://mobilnisvet.com/mobilni-proizvodjac/Huawei/35/2",
		"https://mobilnisvet.com/mobilni-proizvodjac/Samsung/6/2",
		"https://mobilnisvet.com/mobilni-proizvodjac/Xiaomi/52/2"
	]

	def __init__(self, *args, **kwargs):
		super(MobilniSvet, self).__init__(*args, **kwargs)
		self.visited_phones = set()

	def parse(self, response: TextResponse):
		brand = response.css("div.order-2::text").get()
		phones = response.css("div.border-green-200 + div.flex.flex-wrap a")
		for phone in phones:
			names = phone.css("div.tracking-tight::text").getall()
			name = "".join(names).strip()
			if name not in self.visited_phones:
				self.visited_phones.add(name)
				link = phone.css("::attr(href)").get()
				if link:
					yield scrapy.Request(
						response.urljoin(link),
						callback=self.parse_phone_init, # type: ignore
						cb_kwargs={"brand": brand, "phone": name}
					)

	def parse_comments(self, response: TextResponse, brand: str | None, phone: str):
		top_level_comments = response.css("div.ml-2.leading-none")
		for top_level_comment in top_level_comments:
			author = top_level_comment.css("div.items-center span.font-bold::text").get()
			date = top_level_comment.css("div.items-center span.font-hairline::text").get()
			comment = top_level_comment.css("div.leading-snug div.commentbluelinks div::text").get()

			if comment and comment.strip():
				if date:
					try:
						cleaned_date = date.strip()
						parsed_date = datetime.strptime(cleaned_date, "%d.%m.%Y %H:%Mh")
					except ValueError as e:
						self.logger.error(f"Error occured while creating Item on {response.url} link", e)
						parsed_date = None
				else:
					parsed_date = None
				
				item = CommentItem(
					url=response.url,
					brand=brand,
					phone=phone,
					author=author.strip() if author else None,
					date=parsed_date,
					comment=cyrtranslit.to_latin(comment.strip(), "sr")
				)

				yield item

	def parse_phone_init(self, response: TextResponse, brand: str | None, phone: str):
		yield from self.parse_comments(response, brand, phone)

		next_page = response.css("div.mx-auto.flex a.bg-blue-500::attr(href)").get()
		if next_page:
			yield scrapy.Request(
				response.urljoin(next_page),
				callback=self.parse_phone_extra, # type: ignore
				cb_kwargs={"brand": brand, "phone": phone}
			)

	def parse_phone_extra(self, response: TextResponse, brand: str | None, phone: str):
		yield from self.parse_comments(response, brand, phone)

		next_page = response.css("div.font-bold.text-blue-600 a.justify-end::attr(href)").get()
		if next_page:
			yield scrapy.Request(
				response.urljoin(next_page),
				callback=self.parse_phone_extra, # type: ignore
				cb_kwargs={"brand": brand, "phone": phone}
			)
