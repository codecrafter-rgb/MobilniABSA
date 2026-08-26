from enum import Enum


class Category(str, Enum):
	BATTERY = "Baterija"
	CAMERA = "Kamera"
	SCREEN = "Ekran"
	MEMORY = "Memorija"
	SOUND = "Zvučnici"
	DESIGN = "Izgled"
	HARDWARE = "Hardver"
	SOFTWARE = "Softver"
	PERFORMANCE = "Performanse"
	PRICE = "Cena"
	GENERAL = "Opšta ocena"


class Polarity(str, Enum):
	POSITIVE = "Pozitivan"
	NEGATIVE = "Negativan"
	NEUTRAL = "Neutralan"
	CONFLICT = "Konflikt"
