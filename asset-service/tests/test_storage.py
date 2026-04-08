from app.storage import AssetStorageService


def test_save_get_delete_asset(tmp_path):
    storage = AssetStorageService(root=tmp_path)

    saved = storage.save_asset(
        category="product-images",
        content=b"png-bytes",
        filename="widget.png",
        content_type="image/png",
    )

    assert saved["asset_key"].endswith(".png")
    fetched = storage.get_asset(
        category="product-images",
        asset_key=saved["asset_key"],
    )
    assert fetched["content"] == b"png-bytes"
    assert fetched["content_type"] == "image/png"
    assert fetched["filename"] == "widget.png"

    assert storage.delete_asset(
        category="product-images",
        asset_key=saved["asset_key"],
    ) is True
    assert storage.get_asset(
        category="product-images",
        asset_key=saved["asset_key"],
    ) is None


def test_save_asset_with_explicit_key_overwrites(tmp_path):
    storage = AssetStorageService(root=tmp_path)

    storage.save_asset(
        category="quote-images",
        asset_key="quote-42",
        content=b"first",
        filename="quote.png",
        content_type="image/png",
    )
    storage.save_asset(
        category="quote-images",
        asset_key="quote-42",
        content=b"second",
        filename="quote-new.png",
        content_type="image/png",
    )

    fetched = storage.get_asset(category="quote-images", asset_key="quote-42")
    assert fetched["content"] == b"second"
    assert fetched["filename"] == "quote-new.png"
