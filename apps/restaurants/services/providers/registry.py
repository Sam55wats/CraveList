from .seed import SeedRestaurantProvider


PROVIDERS = {
    SeedRestaurantProvider.source: SeedRestaurantProvider,
}


def get_restaurant_provider(source="seed"):
    provider_class = PROVIDERS.get(source)

    if provider_class is None:
        return None

    return provider_class()
