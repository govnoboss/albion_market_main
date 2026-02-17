
import pytest
import shutil
import json
import os
import sys
from unittest.mock import MagicMock, patch, Mock
from pathlib import Path
from datetime import datetime, timedelta

# --- Adjust sys.path to ensure we can import from src ---
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# --- Imports from src ---
from src.utils.config import ConfigManager, get_config
from src.utils.price_storage import PriceStorage, get_price_storage
from src.core.updater import check_for_update, _parse_version, CURRENT_VERSION
from src.core.interaction import DropdownSelector

# =================================================================================================
# MODULE 1: ConfigManager Tests
# =================================================================================================

class TestConfigManager:
    @pytest.fixture
    def config_mgr(self, tmp_path):
        """Fixture that returns a fresh ConfigManager instance pointing to a temp file."""
        config_file = tmp_path / "config" / "test_config.json"
        # We instantiate a new ConfigManager directly to avoid singleton side effects
        cm = ConfigManager(str(config_file))
        return cm

    def test_default_config_creation(self, config_mgr):
        """Test that default config is created if file doesn't exist."""
        assert config_mgr.get_setting("price_update_timeout") == 5.0
        assert config_mgr.get_mouse_settings()["speed_pps"] == 1800.0
        # Check that file was created (save is called on init/set?)
        # Actually init loads config, if not exists returns default but doesn't auto-save immediately 
        # unless set_setting is called or we explicit save. 
        # But let's check defaults are returned correctly.
        assert config_mgr._config["settings"]["price_update_timeout"] == 5.0

    def test_save_and_load(self, config_mgr):
        """Test saving settings and reloading them."""
        config_mgr.set_setting("new_setting", 123)
        assert config_mgr.get_setting("new_setting") == 123
        
        # Verify file exists
        assert config_mgr.config_path.exists()
        
        # Reload
        config_mgr._config = {} # clear memory
        config_mgr._config = config_mgr._load_config()
        assert config_mgr.get_setting("new_setting") == 123

    def test_coordinates_operations(self, config_mgr):
        """Test setting and getting coordinates."""
        config_mgr.set_coordinate("test_point", 100, 200)
        coord = config_mgr.get_coordinate("test_point")
        assert coord == (100, 200)
        
        # Test area
        config_mgr.set_coordinate_area("test_area", 10, 20, 30, 40)
        area = config_mgr.get_coordinate_area("test_area")
        assert area == {"x": 10, "y": 20, "w": 30, "h": 40, "type": "area"}

    def test_items_management(self, config_mgr):
        """Test adding, updating, and removing items."""
        config_mgr.clear_items()
        config_mgr.add_item("Item1", 1000, 1)
        items = config_mgr.get_items()
        assert len(items) == 1
        assert items[0]["name"] == "Item1"
        
        # Update
        config_mgr.update_item(0, max_price=2000)
        items = config_mgr.get_items()
        assert items[0]["max_price"] == 2000
        
        # Remove
        config_mgr.remove_item(0)
        assert len(config_mgr.get_items()) == 0

    def test_profiles(self, config_mgr):
        """Test profile saving and loading."""
        # Set some unique state
        config_mgr.set_coordinate("profile_point", 555, 666)
        
        # Save profile
        assert config_mgr.save_profile("test_prof") is True
        
        # Check file exists
        profiles_dir = config_mgr.config_path.parent / "profiles"
        assert (profiles_dir / "test_prof.json").exists()
        
        # Change state
        config_mgr.set_coordinate("profile_point", 0, 0)
        
        # Load profile
        assert config_mgr.load_profile("test_prof") is True
        assert config_mgr.get_coordinate("profile_point") == (555, 666)
        
        # Delete profile
        assert config_mgr.delete_profile("test_prof") is True
        assert not (profiles_dir / "test_prof.json").exists()


# =================================================================================================
# MODULE 2: PriceStorage Tests
# =================================================================================================

class TestPriceStorage:
    @pytest.fixture
    def storage(self, tmp_path):
        """Fixture that patches PRICES_FILE and resets singleton."""
        # Reset Singleton
        PriceStorage._instance = None
        
        # Patch the file path constant where it's used
        test_file = tmp_path / "data" / "prices.json"
        
        # We need to patch 'src.utils.price_storage.PRICES_FILE'
        # BUT since it's imported in the module scope, patching it might be tricky if not done before import.
        # However, PriceStorage reads from attributes or global. 
        # The class methods use global PRICES_FILE.
        
        with patch("src.utils.price_storage.PRICES_FILE", test_file):
            storage = PriceStorage()
            yield storage
            
        # Cleanup
        PriceStorage._instance = None

    def test_singleton(self, storage):
        """Ensure get_price_storage returns the same instance."""
        s2 = get_price_storage()
        assert storage is s2

    def test_save_and_retrieve_price(self, storage):
        """Test saving a price and retrieving it."""
        city = "Thetford"
        item = "T4_BAG"
        
        # Save
        storage.save_price(city, item, 4, 0, 1, 1000)
        
        # Retrieve specific
        price = storage.get_item_price(city, item, 4, 0, 1)
        assert price == 1000
        
        # Verify persistence (reload)
        storage.reload()
        price = storage.get_item_price(city, item, 4, 0, 1)
        assert price == 1000

    def test_get_cities(self, storage):
        """Test getting list of cities."""
        storage.save_price("Lymhurst", "Item1", 4, 0, 1, 100)
        storage.save_price("Martlock", "Item1", 4, 0, 1, 100)
        
        cities = storage.get_cities()
        assert "Lymhurst" in cities
        assert "Martlock" in cities
        assert len(cities) >= 2

    def test_clean_history(self, storage):
        """Test cleaning old history."""
        city = "TestCity"
        item = "TestItem"
        tier = 4
        enchant = 0
        
        # Add old record logic needs mocking datetime.now() or manually inserting data
        # because save_price uses datetime.now()
        
        # Let's manually inject data to control timestamps
        variant_key = f"T{tier}.{enchant}"
        old_time = (datetime.now() - timedelta(minutes=60)).isoformat()
        recent_time = datetime.now().isoformat()
        
        storage._data = {
            city: {
                item: {
                    "OLD": {"price": 100, "updated": old_time}, # This format is wrong based on code, but logic allows variants
                    # Actually code uses variant_key = f"T{tier}.{enchant}"
                    # Let's use two different variants
                    "T4.0": {"price": 100, "updated": old_time},
                    "T4.1": {"price": 200, "updated": recent_time}
                }
            }
        }
        
        # clean_history removes records if gap > gap_minutes
        # It sorts all records by time.
        # Records: T4.1 (now), T4.0 (now-60m). Diff = 60m.
        # If gap=30, T4.0 should be removed via logic?
        # Logic: 
        # all_records sorted: [T4.1, T4.0]
        # diff between T4.1 and T4.0 is 60m.
        # if diff > 30 -> cutoff found. T4.0 and everything after is deleted.
        
        deleted = storage.clean_history(gap_minutes=30)
        assert deleted == 2
        assert "T4.0" not in storage._data[city][item]
        assert "OLD" not in storage._data[city][item]
        assert "T4.1" in storage._data[city][item]


# =================================================================================================
# MODULE 3: Interaction Tests
# =================================================================================================

class TestInteraction:
    @pytest.fixture
    def mock_config(self):
        """Mock config for interaction."""
        with patch("src.core.interaction.get_config") as mock_get:
            config = Mock()
            mock_get.return_value = config
            
            # Setup default behavior
            config.get_coordinate.return_value = (100, 100) # Default anchor
            config._config = {"dropdowns": {"row_height": 20, "list_start_offset": 10}}
            
            yield config

    def test_dropdown_calculation(self, mock_config):
        """Test calculation of dropdown click points."""
        selector = DropdownSelector()
        
        # Test basic calculation
        # Anchor (100, 100). Offset 10. Row 20. Index 0.
        # Y = 100 + 10 + (0 * 20) = 110. X = 100.
        point = selector.get_dropdown_click_point("test_anchor", 0)
        assert point == (100, 110)
        
        # Index 2
        # Y = 100 + 10 + (2 * 20) = 150.
        point = selector.get_dropdown_click_point("test_anchor", 2)
        assert point == (100, 150)

    def test_tier_mapping(self, mock_config):
        """Test tier to index mapping."""
        selector = DropdownSelector()
        
        # get_tier_click_point(tier)
        # Tier 4 -> Index 4 (Based on code logic: Index 0=All, 1=T1 ... 4=T4)
        
        # Call
        selector.get_tier_click_point(4)
        
        # Check config calls
        # Expect "tier_dropdown", index 4
        # Verify get_dropdown_click_point was called logic-wise (we tested calc above)
        # Let's spy on internal method if needed, but here we just check result if we trust calc
        # With our mock config settings:
        # Y = 100 + 10 + (4 * 20) = 190
        point = selector.get_tier_click_point(4)
        assert point == (100, 190)

    def test_invalid_inputs(self, mock_config):
        """Test validation."""
        selector = DropdownSelector()
        assert selector.get_tier_click_point(3) is None # Min T4
        assert selector.get_enchant_click_point(5) is None # Max 4
        assert selector.get_quality_click_point(6) is None # Max 5 


# =================================================================================================
# MODULE 4: Updater Tests
# =================================================================================================

class TestUpdater:
    def test_parse_version(self):
        """Test version parsing logic."""
        assert _parse_version("v1.2.3") == (1, 2, 3)
        assert _parse_version("1.0") == (1, 0)
        assert _parse_version("invalid") == (0, 0, 0)

    @patch("src.core.updater.requests.get")
    def test_check_for_update_available(self, mock_get):
        """Test when update is available."""
        # Mock response
        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "tag_name": "v9.9.9",
            "assets": [
                {"name": "GBot.zip", "browser_download_url": "http://test.com/GBot.zip", "size": 1024}
            ],
            "body": "New features"
        }
        mock_get.return_value = mock_resp
        
        # Mock current version to be lower
        with patch("src.core.updater.CURRENT_VERSION", "1.0.0"):
            result = check_for_update()
            
        assert result is not None
        assert result["version"] == "9.9.9"
        assert result["download_url"] == "http://test.com/GBot.zip"

    @patch("src.core.updater.requests.get")
    def test_check_for_update_not_found(self, mock_get):
        """Test when no update is available (older version)."""
        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "tag_name": "v0.0.1", # Extremely old
            "assets": []
        }
        mock_get.return_value = mock_resp
        
        # Mock current version to be "1.0.0"
        with patch("src.core.updater.CURRENT_VERSION", "1.0.0"):
            result = check_for_update()
            
        assert result is None

    @patch("src.core.updater.requests.get")
    def test_check_for_update_network_error(self, mock_get):
        """Test network error handling."""
        mock_get.side_effect = Exception("Network Error")
        
        result = check_for_update()
        assert result is None
