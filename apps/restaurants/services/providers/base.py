from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class ProviderRestaurant:
    name: str
    address: str
    cuisine: str
    price_level: int | None
    city: str
    state: str
    country: str
    latitude: str | None
    longitude: str | None
    external_place_id: str
    external_source: str

    def to_response_data(self):
        return asdict(self)

    def to_restaurant_defaults(self):
        data = asdict(self)
        data.pop("external_place_id")
        data.pop("external_source")
        return data


class RestaurantProvider:
    source = ""

    def search(self, query_params):
        raise NotImplementedError

    def get(self, external_place_id):
        raise NotImplementedError
