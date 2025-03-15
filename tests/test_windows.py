def test_windows(download_model):
    """Test Windows compatibility with the downloaded model.
    
    Args:
        download_model: Path to the downloaded model (provided by the fixture in conftest.py)
    """
    model_path = download_model
    # Now you can use model_path in your test
    assert model_path is not None
    print(f"Using model at: {model_path}")
    
    # Your actual model testing logic here
    assert True
