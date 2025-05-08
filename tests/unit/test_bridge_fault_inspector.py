import unittest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, mock_open
import sys
from pathlib import Path

# Add project root to path to allow importing the module under test
project_root = Path(__file__).resolve().parents[2]
sys.path.append(str(project_root))

# Module under test (assuming it's now in the path)
from runtime.analytics import bridge_fault_inspector

class TestTimestampNormalization(unittest.TestCase):

    def setUp(self):
        # Prevent actual logging during tests
        patcher = patch('runtime.analytics.bridge_fault_inspector.logger')
        self.addCleanup(patcher.stop)
        self.mock_logger = patcher.start()
        
        # Mock local timezone to be something specific for predictable testing
        # Let's pretend local is UTC+2
        self.mock_local_tz = timezone(timedelta(hours=2), 'MockTZ') 
        patcher_tz = patch('runtime.analytics.bridge_fault_inspector.get_local_tz', return_value=self.mock_local_tz)
        self.addCleanup(patcher_tz.stop)
        patcher_tz.start()
        
        # Mock datetime.now() to return a fixed UTC time
        self.fixed_now_utc = datetime(2023, 10, 27, 12, 0, 0, tzinfo=timezone.utc)
        patcher_now = patch('runtime.analytics.bridge_fault_inspector.datetime')
        self.addCleanup(patcher_now.stop)
        mock_dt = patcher_now.start()
        mock_dt.now.return_value = self.fixed_now_utc
        mock_dt.strptime = datetime.strptime # Keep original strptime
        mock_dt.fromisoformat = datetime.fromisoformat # Keep original fromisoformat
        mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw) # Allow constructor calls


    def test_parse_integrity_logs_normalization(self):
        """Verify integrity log timestamps are converted to UTC."""
        # Naive timestamp string (assumed local: UTC+2 -> 2023-10-27 08:00:00 UTC)
        log_content_naive = "* **2023-10-27 10:00:00** - **Check:** `TestCheck` - **Status:** WARN - **Details:** Test Details"
        # Edge case: Timestamp exactly at cutoff (should be included)
        cutoff_local_str = (self.fixed_now_utc - timedelta(hours=1)).astimezone(self.mock_local_tz).strftime("%Y-%m-%d %H:%M:%S")
        log_content_cutoff = f"* **{cutoff_local_str}** - **Check:** `CutoffCheck` - **Status:** FAIL - **Details:** Cutoff"
        # Edge case: Timestamp just before cutoff (should be excluded)
        before_cutoff_local_str = (self.fixed_now_utc - timedelta(hours=1, seconds=1)).astimezone(self.mock_local_tz).strftime("%Y-%m-%d %H:%M:%S")
        log_content_before = f"* **{before_cutoff_local_str}** - **Check:** `BeforeCutoff` - **Status:** WARN - **Details:** Too old"
        
        log_data = f"{log_content_before}\n{log_content_cutoff}\n{log_content_naive}\n"

        mock_file = mock_open(read_data=log_data)
        with patch('builtins.open', mock_file):
            with patch('pathlib.Path.exists', return_value=True):
                 results = bridge_fault_inspector.parse_integrity_logs(timespan_hours=1)

        self.assertEqual(len(results), 2, "Should parse 2 entries within the timespan")

        # Check naive timestamp conversion (10:00 local -> 08:00 UTC)
        self.assertEqual(results[1]['check'], 'TestCheck')
        self.assertEqual(results[1]['timestamp'].tzinfo, timezone.utc)
        self.assertEqual(results[1]['timestamp'], datetime(2023, 10, 27, 8, 0, 0, tzinfo=timezone.utc))
        
        # Check cutoff timestamp conversion (local -> 11:00 UTC)
        self.assertEqual(results[0]['check'], 'CutoffCheck')
        self.assertEqual(results[0]['timestamp'].tzinfo, timezone.utc)
        self.assertEqual(results[0]['timestamp'], self.fixed_now_utc - timedelta(hours=1))


    def test_parse_stress_results_normalization(self):
        """Verify stress log ISO timestamps are normalized to UTC."""
        # ISO with Z (already UTC)
        ts_utc = "2023-10-27T11:30:00Z"
        # ISO with offset (+2 -> UTC)
        ts_offset = "2023-10-27T13:30:00+02:00" # Should become 11:30:00 UTC
        # ISO naive (should assume UTC per logic)
        ts_naive = "2023-10-27T11:30:00" # Should become 11:30:00 UTC

        log_lines = [
            f"## Stress Test Run - {self.fixed_now_utc.isoformat().replace('+00:00', 'Z')} ##",
            # Valid entry with Z
            f"| 1 | `uuid-1` | {ts_utc} | ... | ... | ... | 100 | Notes |",
            # Valid entry with offset
            f"| 2 | `uuid-2` | {ts_offset} | ... | ... | ... | 150 | Notes |",
             # Valid entry naive
            f"| 3 | `uuid-3` | {ts_naive} | ... | ... | ... | 200 | Notes |",
            # Entry outside timespan (using Z for simplicity)
            f"| 4 | `uuid-4` | {(self.fixed_now_utc - timedelta(hours=2)).isoformat().replace('+00:00', 'Z')} | ... | ... | ... | 50 | Too old |"
        ]
        log_data = "\n".join(log_lines)

        mock_file = mock_open(read_data=log_data)
        with patch('builtins.open', mock_file):
             with patch('pathlib.Path.exists', return_value=True):
                results = bridge_fault_inspector.parse_stress_results(timespan_hours=1) # Look back 1 hour

        self.assertEqual(len(results), 3, "Should parse 3 entries within the timespan")

        expected_utc = datetime(2023, 10, 27, 11, 30, 0, tzinfo=timezone.utc)
        
        # Check Z timestamp
        self.assertEqual(results[0]['uuid'], 'uuid-1')
        self.assertEqual(results[0]['timestamp'], expected_utc)
        self.assertEqual(results[0]['timestamp'].tzinfo, timezone.utc)
        
        # Check offset timestamp
        self.assertEqual(results[1]['uuid'], 'uuid-2')
        self.assertEqual(results[1]['timestamp'], expected_utc)
        self.assertEqual(results[1]['timestamp'].tzinfo, timezone.utc)

        # Check naive timestamp
        self.assertEqual(results[2]['uuid'], 'uuid-3')
        self.assertEqual(results[2]['timestamp'], expected_utc)
        self.assertEqual(results[2]['timestamp'].tzinfo, timezone.utc)


if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False) 