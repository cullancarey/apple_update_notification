import pytest
import re
from unittest.mock import patch, MagicMock
from lambdas import apple_web_scrape as aws


# -------------------------------------------------------------------------
# Fixtures and setup
# -------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def set_env(monkeypatch):
    """Set environment variable for DynamoDB table name"""
    monkeypatch.setenv("dynamodb_table_name", "mock_table")


@pytest.fixture
def sample_html():
    """Fake Apple release page content (updated markup)."""
    return """
    <html>
      <body>
        <ul class="list gb-list">
          <li class="gb-list_item">
            <p class="gb-paragraph">The latest version of iOS and iPadOS is 26.0.1.</p>
          </li>
          <li class="gb-list_item">
            <p class="gb-paragraph">The latest version of macOS is 26.0.1.</p>
          </li>
          <li class="gb-list_item">
            <p class="gb-paragraph">The latest version of watchOS is 26.0.2.</p>
          </li>
          <li class="gb-list_item">
            <p class="gb-paragraph">The latest version of tvOS is 26.0.1.</p>
          </li>
          <li class="gb-list_item">
            <p class="gb-paragraph">The latest version of visionOS is 26.0.1.</p>
          </li>
        </ul>
      </body>
    </html>
    """


# -------------------------------------------------------------------------
# fetch_apple_release_page
# -------------------------------------------------------------------------
@patch("apple_web_scrape.urllib3.PoolManager")
def test_fetch_apple_release_page_success(mock_pool):
    mock_http = MagicMock()
    mock_pool.return_value = mock_http
    mock_http.request.return_value.status = 200
    mock_http.request.return_value.data = b"<html></html>"

    result = aws.fetch_apple_release_page("https://mock.url")
    assert isinstance(result, str)
    assert "<html>" in result


@patch("apple_web_scrape.urllib3.PoolManager")
def test_fetch_apple_release_page_failure(mock_pool):
    mock_http = MagicMock()
    mock_pool.return_value = mock_http
    mock_http.request.return_value.status = 404

    result = aws.fetch_apple_release_page("https://mock.url")
    assert result is None


# -------------------------------------------------------------------------
# parse_release_statements
# -------------------------------------------------------------------------
def test_parse_release_statements_success(sample_html):
    result = aws.parse_release_statements(sample_html)
    assert all(d in result for d in aws.DEVICE_LIST)
    assert "iOS" in result
    assert re.search(r"\d+\.\d+", result["iOS"])


def test_parse_release_statements_incomplete():
    html = """
    <ul class="list gb-list">
      <li class="gb-list_item">
        <p class="gb-paragraph">The latest version of macOS is 14.1.</p>
      </li>
    </ul>
    """
    result = aws.parse_release_statements(html)
    # Should still return partial results, not necessarily None
    assert "macOS" in result
    assert isinstance(result, dict)


# -------------------------------------------------------------------------
# extract_release_versions
# -------------------------------------------------------------------------
def test_extract_release_versions_valid():
    input_data = {
        "iOS": "The latest version of iOS is 26.0.1",
        "macOS": "The latest version of macOS is 26.0.1",
        "watchOS": "The latest version of watchOS is 26.0.2",
        "tvOS": "The latest version of tvOS is 26.0.1",
        "visionOS": "The latest version of visionOS is 26.0.1",
    }
    result = aws.extract_release_versions(input_data)
    assert result == {
        "iOS": "26.0.1",
        "macOS": "26.0.1",
        "watchOS": "26.0.2",
        "tvOS": "26.0.1",
        "visionOS": "26.0.1",
    }


def test_extract_release_versions_missing_version():
    result = aws.extract_release_versions({"macOS": "No version info"})
    assert result is None


# -------------------------------------------------------------------------
# get_latest_releases
# -------------------------------------------------------------------------
@patch("apple_web_scrape.fetch_apple_release_page")
@patch("apple_web_scrape.parse_release_statements")
@patch("apple_web_scrape.extract_release_versions")
def test_get_latest_releases_success(mock_extract, mock_parse, mock_fetch):
    mock_fetch.return_value = "<html>content</html>"
    mock_parse.return_value = {
        "iOS": "The latest version of iOS is 26.0.1",
        "macOS": "The latest version of macOS is 26.0.1",
        "watchOS": "The latest version of watchOS is 26.0.2",
        "tvOS": "The latest version of tvOS is 26.0.1",
        "visionOS": "The latest version of visionOS is 26.0.1",
    }
    mock_extract.return_value = {
        "iOS": "26.0.1",
        "macOS": "26.0.1",
        "watchOS": "26.0.2",
        "tvOS": "26.0.1",
        "visionOS": "26.0.1",
    }

    result = aws.get_latest_releases()
    assert "release_statements" in result
    assert all(k in result for k in aws.DEVICE_LIST)


@patch("lambdas.apple_web_scrape.fetch_apple_release_page", return_value=None)
def test_get_latest_releases_fetch_failure(mock_fetch):
    result = aws.get_latest_releases()
    assert result is None


# -------------------------------------------------------------------------
# update_dynamodb
# -------------------------------------------------------------------------
def test_update_dynamodb_success():
    mock_table = MagicMock()
    result = aws.update_dynamodb(mock_table, "iOS", "26.0.1", "Release info")
    assert result is True
    mock_table.update_item.assert_called_once()


def test_update_dynamodb_failure():
    mock_table = MagicMock()
    mock_table.update_item.side_effect = aws.ClientError(
        {"Error": {"Code": "500"}}, "update_item"
    )
    result = aws.update_dynamodb(mock_table, "iOS", "26.0.1", "Release info")
    assert result is False


# -------------------------------------------------------------------------
# compare_and_update_releases
# -------------------------------------------------------------------------
@patch("lambdas.apple_web_scrape.update_dynamodb")
def test_compare_and_update_releases_triggers_update(mock_update):
    latest = {
        "iOS": "26.0.1",
        "macOS": "26.0.1",
        "watchOS": "26.0.2",
        "tvOS": "26.0.1",
        "visionOS": "26.0.1",
        "release_statements": {d: "tweet" for d in aws.DEVICE_LIST},
    }
    dynamo = {"iOS": "25.0.9"}  # different version
    aws.compare_and_update_releases(latest, dynamo, MagicMock())
    mock_update.assert_called()


@patch("lambdas.apple_web_scrape.update_dynamodb")
def test_compare_and_update_releases_no_update(mock_update):
    latest = {
        "iOS": "26.0.1",
        "macOS": "26.0.1",
        "watchOS": "26.0.2",
        "tvOS": "26.0.1",
        "visionOS": "26.0.1",
        "release_statements": {d: "tweet" for d in aws.DEVICE_LIST},
    }
    dynamo = {d: latest[d] for d in aws.DEVICE_LIST}
    aws.compare_and_update_releases(latest, dynamo, MagicMock())
    mock_update.assert_not_called()


# -------------------------------------------------------------------------
# lambda_handler
# -------------------------------------------------------------------------
@patch("lambdas.apple_web_scrape.create_dynamodb_resource")
@patch("lambdas.apple_web_scrape.get_latest_releases")
@patch("lambdas.apple_web_scrape.get_item", return_value={"iOS": "25.0.9"})
@patch("lambdas.apple_web_scrape.compare_and_update_releases")
def test_lambda_handler_success(mock_compare, mock_get, mock_latest, mock_dynamo):
    mock_latest.return_value = {
        "iOS": "26.0.1",
        "macOS": "26.0.1",
        "watchOS": "26.0.2",
        "tvOS": "26.0.1",
        "visionOS": "26.0.1",
        "release_statements": {},
    }
    mock_table = MagicMock()
    mock_dynamo.return_value.Table.return_value = mock_table

    aws.lambda_handler({}, {})
    mock_compare.assert_called_once()


@patch("apple_web_scrape.create_dynamodb_resource")
def test_lambda_handler_missing_env(mock_dynamo, monkeypatch):
    monkeypatch.delenv("dynamodb_table_name", raising=False)
    aws.lambda_handler({}, {})
    mock_dynamo.assert_not_called()
